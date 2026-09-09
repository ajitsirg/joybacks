"""Auth & RBAC service layer."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import DeviceLogin, OTPChallenge, StaffProfile, User
from audit.services import write_audit

# Temporary fixed OTP for join/login flows. Set FIXED_OTP="" to use random codes.
FIXED_OTP = os.environ.get("FIXED_OTP", "111111").strip()


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class AuthService:
    @staticmethod
    def issue_tokens(user: User) -> dict:
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user,
        }

    @staticmethod
    def login(
        *,
        email: str = "",
        password: str = "",
        username: str = "",
        mobile: str = "",
        ip: str | None = None,
        user_agent: str = "",
        remember_me: bool = False,
    ) -> dict:
        """
        Staff: email + password.
        Associate: username (JOY + mobile) + password. Mobile field not required.
        """
        user = None
        password = (password or "").strip()
        username = (username or "").strip().upper()
        # If user typed only digits, treat as mobile and prefix JOY
        if username and username.isdigit():
            username = f"JOY{username}"
        mobile = "".join(ch for ch in (mobile or "") if ch.isdigit())
        if len(mobile) > 10 and mobile.startswith("91"):
            mobile = mobile[2:]
        if len(mobile) == 11 and mobile.startswith("0"):
            mobile = mobile[1:]

        if username:
            # Allow JOY… IDs and demo usernames that still start with JOY
            if not username.startswith("JOY"):
                raise ValueError("Username must start with JOY (e.g. JOYDEMO0001)")

            from associates.models import Associate

            # 1) Prefer associate_id (canonical)
            assoc = (
                Associate.objects.select_related("user")
                .filter(associate_id__iexact=username)
                .first()
            )
            if assoc and assoc.user_id:
                user = assoc.user
            # 2) User.username
            if user is None:
                user = User.objects.filter(username__iexact=username, is_active=True).first()
            # 3) Unique mobile match from digits in username (avoid .first() on duplicates)
            if user is None:
                digits = "".join(ch for ch in username if ch.isdigit())
                if digits:
                    matches = list(
                        Associate.objects.select_related("user").filter(mobile=digits)[:2]
                    )
                    if len(matches) == 1 and matches[0].user_id:
                        user = matches[0].user

            if user is None or not user.is_active:
                raise ValueError("Invalid username or password")
            if not user.check_password(password):
                raise ValueError("Invalid username or password")
            try:
                assoc = user.associate
            except Associate.DoesNotExist as exc:
                raise ValueError("Associate account not found") from exc
            if assoc is None:
                raise ValueError("Associate account not found")
        else:
            email = (email or "").strip()
            # Case-insensitive staff email login (Django auth is case-sensitive by default)
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user is None or not user.check_password(password):
                raise ValueError("Invalid email or password")

        if hasattr(user, "staff_profile") and user.staff_profile.is_suspended:
            raise ValueError("Account is suspended")

        user.last_login = timezone.now()
        update_fields = ["last_login"]
        # Never wipe a known IP if the proxy did not forward one this request
        if ip:
            user.last_login_ip = ip
            update_fields.append("last_login_ip")
        user.save(update_fields=update_fields)

        DeviceLogin.objects.create(
            user=user,
            device_name=(user_agent or "unknown")[:120],
            user_agent=user_agent or "",
            ip_address=ip,
        )
        write_audit(
            actor=user,
            action="auth.login",
            module="accounts",
            object_type="User",
            object_id=str(user.pk),
            ip_address=ip,
            metadata={"remember_me": remember_me, "username": username or email},
        )
        payload = AuthService.issue_tokens(user)
        if remember_me:
            payload["remember_me"] = True
        return payload

    @staticmethod
    def create_otp(*, phone_or_email: str, purpose: str) -> str:
        code = FIXED_OTP if FIXED_OTP else f"{secrets.randbelow(1_000_000):06d}"
        OTPChallenge.objects.filter(
            phone_or_email=phone_or_email,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True)
        OTPChallenge.objects.create(
            phone_or_email=phone_or_email.lower().strip(),
            purpose=purpose,
            code_hash=_hash_otp(code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        return code  # In production: send via SMS/email gateway from configuration

    @staticmethod
    def verify_otp(*, phone_or_email: str, purpose: str, code: str) -> bool:
        code = (code or "").strip()
        # Temporary master OTP — always accepted while FIXED_OTP is set
        if FIXED_OTP and code == FIXED_OTP:
            OTPChallenge.objects.filter(
                phone_or_email=phone_or_email.lower().strip(),
                purpose=purpose,
                is_used=False,
            ).update(is_used=True)
            return True

        challenge = (
            OTPChallenge.objects.filter(
                phone_or_email=phone_or_email.lower().strip(),
                purpose=purpose,
                is_used=False,
                expires_at__gte=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if not challenge:
            return False
        challenge.attempts += 1
        if challenge.attempts > 5:
            challenge.is_used = True
            challenge.save(update_fields=["attempts", "is_used"])
            return False
        if challenge.code_hash != _hash_otp(code):
            challenge.save(update_fields=["attempts"])
            return False
        challenge.is_used = True
        challenge.save(update_fields=["is_used", "attempts"])
        return True


class RBACService:
    @staticmethod
    def user_permissions(user: User) -> list[str]:
        if user.is_superuser:
            from accounts.models import Permission

            return list(Permission.objects.values_list("code", flat=True))
        if not hasattr(user, "staff_profile"):
            return []
        return sorted(user.staff_profile.permission_codes())

    @staticmethod
    @transaction.atomic
    def ensure_staff(user: User, employee_code: str, role_names: list[str] | None = None) -> StaffProfile:
        from accounts.models import Role

        profile, _ = StaffProfile.objects.get_or_create(
            user=user,
            defaults={"employee_code": employee_code},
        )
        if role_names:
            roles = Role.objects.filter(name__in=role_names)
            profile.roles.set(roles)
        return profile
