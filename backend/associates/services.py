"""Associate registration & lifecycle services."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from associates.models import (
    PLATINUM_JOIN_AMOUNT,
    SILVER_MIN_PERCENT,
    Associate,
    tier_from_amount,
    username_from_mobile,
)
from associates.validators import validate_sponsor
from audit.services import write_audit
from configuration.models import CompanySettings
from genealogy.models import GenealogyNode
from genealogy.services import GenealogyService
from wallets.models import Wallet
from wallets.services import WalletService

UserModel = get_user_model()


def can_edit_associate(actor: User | None, target: Associate) -> bool:
    """Only the associate themself, or staff / superadmin. Team leads cannot edit others."""
    if actor is None or not getattr(actor, "is_authenticated", False):
        return False
    if actor.is_staff or actor.is_superuser:
        return True
    me = getattr(actor, "associate", None)
    return bool(me and me.id == target.id)


def can_view_associate_details(actor: User | None, target: Associate) -> bool:
    """Full profile (KYC, bank, etc.): self or staff / superadmin only."""
    return can_edit_associate(actor, target)


def can_view_associate_profile(actor: User | None, target: Associate) -> bool:
    """Team / tree profile page: self, staff, or a member in the viewer's downline."""
    if can_edit_associate(actor, target):
        return True
    if actor is None or not getattr(actor, "is_authenticated", False):
        return False
    me = getattr(actor, "associate", None)
    if not me:
        return False
    from genealogy.models import GenealogyClosure

    return GenealogyClosure.objects.filter(
        ancestor=me, descendant=target, depth__gt=0
    ).exists()

def _assert_join_package_allowed(join_amount: Decimal) -> None:
    """Respect CompanySettings toggles for Platinum / Silver join cards."""
    company = CompanySettings.current()
    amount = Decimal(join_amount or 0)
    silver_min = (PLATINUM_JOIN_AMOUNT * SILVER_MIN_PERCENT / Decimal("100")).quantize(Decimal("0.01"))
    if amount >= PLATINUM_JOIN_AMOUNT and not company.show_platinum_package:
        raise ValueError("Platinum membership is currently unavailable")
    if silver_min <= amount < PLATINUM_JOIN_AMOUNT and not company.show_silver_package:
        raise ValueError("Silver membership is currently unavailable")


def _assert_join_kyc_requirements(
    *,
    pan: str,
    aadhaar: str,
    bank_name: str,
    account_number: str,
    ifsc: str,
    upi_id: str,
    profile_photo,
    aadhaar_document,
    aadhaar_back,
    pan_document,
    bank_document,
) -> None:
    """Enforce only the KYC fields toggled on in CompanySettings (default: all optional)."""
    company = CompanySettings.current()
    text_checks = (
        (company.require_join_pan, "PAN", pan),
        (company.require_join_aadhaar, "Aadhaar", aadhaar),
        (company.require_join_bank_name, "Bank name", bank_name),
        (company.require_join_account_number, "Account number", account_number),
        (company.require_join_ifsc, "IFSC", ifsc),
        (company.require_join_upi, "UPI ID", upi_id),
    )
    for required, label, value in text_checks:
        if required and not str(value or "").strip():
            raise ValueError(f"{label} is required for joining")

    file_checks = (
        (company.require_join_profile_photo, "Profile photo", profile_photo),
        (company.require_join_pan_document, "PAN card document", pan_document),
        (company.require_join_bank_document, "Bank account proof", bank_document),
    )
    for required, label, value in file_checks:
        if required and not value:
            raise ValueError(f"{label} is required")

    # Aadhaar counts as attached only when BOTH front and back are present.
    if company.require_join_aadhaar_document:
        if not aadhaar_document:
            raise ValueError("Aadhaar front image is required")
        if not aadhaar_back:
            raise ValueError("Aadhaar back image is required")


class AssociateService:
    @staticmethod
    @transaction.atomic
    def register(
        *,
        first_name: str,
        last_name: str,
        mobile: str,
        password: str,
        lead_reference: str,
        join_amount: Decimal = Decimal("0"),
        email: str = "",
        otp_verified: bool = False,
        actor: User | None = None,
        ip: str | None = None,
        # Mandatory join KYC
        pan: str = "",
        aadhaar: str = "",
        bank_name: str = "",
        account_number: str = "",
        ifsc: str = "",
        upi_id: str = "",
        profile_photo=None,
        aadhaar_document=None,
        aadhaar_back=None,
        pan_document=None,
        bank_document=None,
    ) -> Associate:
        from configuration.repository import ConfigRepository
        from django.core.exceptions import ValidationError as DjangoValidationError

        from core.validators import validate_email_address, validate_mobile

        if ConfigRepository.company().require_join_otp and not otp_verified:
            raise ValueError("OTP verification required")

        try:
            mobile = validate_mobile(mobile)
            email_clean = validate_email_address(email, required=True)
        except DjangoValidationError as exc:
            raise ValueError(exc.messages[0] if exc.messages else str(exc)) from exc

        lead_reference = (lead_reference or "").strip().upper()
        if not lead_reference:
            raise ValueError("Lead reference is mandatory for joining")

        _assert_join_kyc_requirements(
            pan=pan,
            aadhaar=aadhaar,
            bank_name=bank_name,
            account_number=account_number,
            ifsc=ifsc,
            upi_id=upi_id,
            profile_photo=profile_photo,
            aadhaar_document=aadhaar_document,
            aadhaar_back=aadhaar_back,
            pan_document=pan_document,
            bank_document=bank_document,
        )

        sponsor = validate_sponsor(lead_reference)
        _assert_join_package_allowed(Decimal(join_amount or 0))

        if Associate.objects.filter(mobile=mobile).exists():
            raise ValueError("Mobile number already registered")

        # Username / Associate ID = JOY + mobile (e.g. JOY9214337040)
        associate_id = username_from_mobile(mobile)
        if Associate.objects.filter(associate_id__iexact=associate_id).exists():
            raise ValueError("This mobile / username is already registered")
        if UserModel.objects.filter(username__iexact=associate_id).exists():
            raise ValueError("This mobile / username is already registered")

        if UserModel.objects.filter(email__iexact=email_clean).exists():
            raise ValueError("This email is already registered")

        user = UserModel.objects.create_user(
            email=email_clean,
            password=password,
            username=associate_id,
            first_name=first_name,
            last_name=last_name,
            phone=mobile,
            user_type=User.UserType.ASSOCIATE,
        )

        card_tier, flag_color = tier_from_amount(Decimal(join_amount or 0))
        company = CompanySettings.current()
        needs_leader = bool(company.require_leader_approval)

        associate = Associate.objects.create(
            user=user,
            associate_id=associate_id,
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id,
            lead_reference=sponsor.associate_id,
            mobile=mobile,
            join_amount=Decimal(join_amount or 0),
            card_tier=card_tier,
            flag_color=flag_color,
            status=Associate.Status.PENDING,
            activated_at=None,
            kyc_verified=False,
            # Staff/superadmin-visible plaintext (login still uses Django hash)
            login_password=password,
        )

        if not email:
            user.email = f"{associate_id.lower()}@joyclub.member"
            user.save(update_fields=["email"])

        WalletService.ensure_wallets(associate)

        from operations.models import KYCSubmission

        KYCSubmission.objects.create(
            associate=associate,
            full_name=f"{first_name} {last_name}".strip() or associate.associate_id,
            pan=pan.strip().upper(),
            aadhaar="".join(ch for ch in str(aadhaar) if ch.isdigit()),
            bank_name=bank_name.strip(),
            account_number=account_number.strip(),
            ifsc=ifsc.strip().upper(),
            upi_id=upi_id.strip(),
            profile_photo=profile_photo,
            aadhaar_document=aadhaar_document,
            aadhaar_back=aadhaar_back,
            pan_document=pan_document,
            bank_document=bank_document,
            status=KYCSubmission.Status.PENDING,
        )

        sponsor.direct_count = sponsor.directs.filter(is_deleted=False).count()
        sponsor.save(update_fields=["direct_count", "updated_at"])

        from notifications.models import Notification

        if needs_leader:
            Notification.objects.create(
                user=sponsor.user,
                title="New join request",
                body=(
                    f"{associate.associate_id} ({first_name} {last_name}) requested to join under you. "
                    "Review Aadhaar, PAN, bank, UPI and profile photo, then approve or reject."
                ),
                link="/team/approvals",
                meta={"associate_id": associate.associate_id},
            )
        else:
            # Instant activation — leader approval disabled in Company Settings
            AssociateService.leader_approve(associate, actor=user, bypass_leader_check=True)
            associate.refresh_from_db()
            Notification.objects.create(
                user=sponsor.user,
                title="New associate joined",
                body=f"{associate.associate_id} ({first_name} {last_name}) joined under you.",
                link=f"/users/{associate.associate_id}",
                meta={"associate_id": associate.associate_id},
            )

        write_audit(
            actor=actor or user,
            action="associate.join_request",
            module="associates",
            object_type="Associate",
            object_id=str(associate.id),
            ip_address=ip,
            metadata={
                "username": associate.associate_id,
                "lead_reference": sponsor.associate_id,
                "join_amount": str(join_amount),
                "card_tier": card_tier,
                "flag_color": flag_color,
                "status": associate.status,
                "require_leader_approval": needs_leader,
            },
        )
        return associate

    @staticmethod
    @transaction.atomic
    def leader_approve(associate: Associate, *, actor: User, bypass_leader_check: bool = False) -> Associate:
        if associate.status != Associate.Status.PENDING:
            raise ValueError("Only pending join requests can be approved")
        if not bypass_leader_check and not actor.is_staff and not actor.is_superuser:
            leader = getattr(actor, "associate", None)
            if not leader or associate.sponsor_id != leader.id:
                raise PermissionError("Only the lead / sponsor can approve this joiner")

        from operations.models import KYCSubmission

        kyc = associate.kyc_submissions.filter(status=KYCSubmission.Status.PENDING).order_by("-created_at").first()
        if not kyc:
            kyc = associate.kyc_submissions.order_by("-created_at").first()
        if not kyc:
            raise ValueError("Joiner has not submitted KYC documents")

        kyc.status = KYCSubmission.Status.APPROVED
        kyc.reviewed_by = actor
        kyc.reviewed_at = timezone.now()
        kyc.rejection_reason = ""
        kyc.save()

        if not GenealogyNode.objects.filter(associate=associate).exists():
            GenealogyService.attach_under_sponsor(associate, associate.sponsor)

        # Approved by lead → Inactive until ₹2.2L investment; Active only after investment gate
        associate.status = Associate.Status.INACTIVE
        associate.kyc_verified = True
        associate.rejection_reason = ""
        associate.activated_at = None
        associate.save(
            update_fields=["status", "activated_at", "kyc_verified", "rejection_reason", "updated_at"]
        )

        if Decimal(associate.join_amount or 0) > 0:
            join_amt = Decimal(associate.join_amount)
            WalletService.credit(
                associate=associate,
                wallet_type=Wallet.WalletType.MAIN,
                amount=join_amt,
                reference=f"JOIN-{associate.associate_id}",
                narration=f"Joining package ({associate.card_tier})",
            )
            # Apply team business + level commissions (farmhouse sale pipeline)
            from wallets.business import apply_investment_business

            apply_investment_business(
                associate=associate,
                amount=join_amt,
                reference=f"JOIN-{associate.associate_id}",
            )
            associate.refresh_from_db()
        else:
            associate.sync_flag_color()
            associate.sync_rank_levels()
            associate.sync_status_from_investment(save=True)

        if associate.sponsor_id:
            sponsor = Associate.objects.select_for_update().get(pk=associate.sponsor_id)
            sponsor.direct_count = sponsor.directs.filter(is_deleted=False).count()
            sponsor.direct_active_count = sponsor.directs.filter(
                status=Associate.Status.ACTIVE, is_deleted=False
            ).count()
            sponsor.sync_performance_level(save=False)
            sponsor.save(
                update_fields=[
                    "direct_count",
                    "direct_active_count",
                    "performance_level",
                    "performance_level_name",
                    "updated_at",
                ]
            )

        from notifications.models import Notification

        if associate.status == Associate.Status.ACTIVE:
            body = (
                "Your documents were approved and your investment qualifies you as an "
                "Active JoyClub Associate."
            )
        else:
            body = (
                "Your documents were approved. Invest at least ₹2,20,000 to become Active "
                "and introduce new associates."
            )
        Notification.objects.create(
            user=associate.user,
            title="Join approved",
            body=body,
            link="/dashboard",
        )

        write_audit(
            actor=actor,
            action="associate.leader_approve",
            module="associates",
            object_type="Associate",
            object_id=str(associate.id),
        )
        return associate

    @staticmethod
    @transaction.atomic
    def leader_reject(associate: Associate, *, actor: User, reason: str = "") -> Associate:
        if associate.status != Associate.Status.PENDING:
            raise ValueError("Only pending join requests can be rejected")
        if not actor.is_staff and not actor.is_superuser:
            leader = getattr(actor, "associate", None)
            if not leader or associate.sponsor_id != leader.id:
                raise PermissionError("Only the lead / sponsor can reject this joiner")

        from operations.models import KYCSubmission

        kyc = associate.kyc_submissions.filter(status=KYCSubmission.Status.PENDING).order_by("-created_at").first()
        if kyc:
            kyc.status = KYCSubmission.Status.REJECTED
            kyc.reviewed_by = actor
            kyc.reviewed_at = timezone.now()
            kyc.rejection_reason = reason or "Rejected by lead"
            kyc.save()

        associate.status = Associate.Status.REJECTED
        associate.rejection_reason = reason or "Rejected by lead"
        associate.kyc_verified = False
        associate.save(update_fields=["status", "rejection_reason", "kyc_verified", "updated_at"])

        from notifications.models import Notification

        Notification.objects.create(
            user=associate.user,
            title="Join request rejected",
            body=associate.rejection_reason or "Your lead rejected the join request.",
            link="/login",
        )

        write_audit(
            actor=actor,
            action="associate.leader_reject",
            module="associates",
            object_type="Associate",
            object_id=str(associate.id),
            metadata={"reason": reason},
        )
        return associate

    @staticmethod
    @transaction.atomic
    def activate(associate: Associate, actor: User | None = None) -> Associate:
        """Staff path: finish pending join, then sync Active only if investment >= ₹2.2L."""
        if associate.status == Associate.Status.PENDING and actor:
            try:
                return AssociateService.leader_approve(associate, actor=actor)
            except Exception:
                pass
        if associate.status in {Associate.Status.REJECTED, Associate.Status.BLOCKED}:
            raise ValueError("Cannot activate a rejected or blocked associate")
        associate.sync_status_from_investment(save=True)
        associate.sync_rank_levels(save=True)
        if associate.sponsor_id:
            sponsor = associate.sponsor
            sponsor.direct_active_count = sponsor.directs.filter(
                status=Associate.Status.ACTIVE, is_deleted=False
            ).count()
            sponsor.sync_performance_level(save=False)
            sponsor.save(
                update_fields=[
                    "direct_active_count",
                    "performance_level",
                    "performance_level_name",
                    "updated_at",
                ]
            )
        write_audit(
            actor=actor,
            action="associate.activate",
            module="associates",
            object_type="Associate",
            object_id=str(associate.id),
            metadata={"status": associate.status, "personal_business": str(associate.personal_business)},
        )
        return associate

    @staticmethod
    @transaction.atomic
    def update_details(
        associate: Associate,
        *,
        actor: User,
        data: dict,
        files: dict | None = None,
        ip: str | None = None,
    ) -> Associate:
        """Update personal + KYC details for self / team lead / staff / superadmin."""
        if not can_edit_associate(actor, associate):
            raise PermissionError("You cannot update this associate")

        from django.core.exceptions import ValidationError as DjangoValidationError

        from core.validators import validate_email_address, validate_mobile
        from operations.models import KYCSubmission

        files = files or {}
        is_staff_actor = bool(actor.is_staff or actor.is_superuser)
        user = associate.user
        changed: list[str] = []

        if "first_name" in data and data["first_name"] is not None:
            user.first_name = str(data["first_name"]).strip()
            changed.append("first_name")
        if "last_name" in data and data["last_name"] is not None:
            user.last_name = str(data["last_name"]).strip()
            changed.append("last_name")
        if "email" in data and data["email"] is not None:
            try:
                user.email = validate_email_address(str(data["email"]), required=True)
            except DjangoValidationError as exc:
                raise ValueError(exc.messages[0] if exc.messages else str(exc)) from exc
            changed.append("email")

        if "mobile" in data and data["mobile"] is not None:
            try:
                mobile = validate_mobile(str(data["mobile"]))
            except DjangoValidationError as exc:
                raise ValueError(exc.messages[0] if exc.messages else str(exc)) from exc
            clash = (
                Associate.objects.filter(mobile=mobile, is_deleted=False)
                .exclude(pk=associate.pk)
                .exists()
            )
            if clash:
                raise ValueError("Mobile number already used by another associate")

            old_id = associate.associate_id
            new_id = username_from_mobile(mobile)
            if new_id != old_id:
                id_taken = (
                    Associate.objects.filter(associate_id__iexact=new_id, is_deleted=False)
                    .exclude(pk=associate.pk)
                    .exists()
                    or UserModel.objects.filter(username__iexact=new_id).exclude(pk=user.pk).exists()
                )
                if id_taken:
                    raise ValueError(
                        f"Cannot rename username to {new_id} — already used by another account"
                    )
                associate.associate_id = new_id
                user.username = new_id
                # Keep downline sponsor / lead references in sync with the new JOY username
                Associate.objects.filter(sponsor=associate).update(
                    sponsor_associate_id=new_id,
                    lead_reference=new_id,
                )
                Associate.objects.filter(lead_reference__iexact=old_id).exclude(
                    sponsor=associate
                ).update(lead_reference=new_id)
                changed.append("associate_id")
                changed.append("username")

            associate.mobile = mobile
            user.phone = mobile
            changed.append("mobile")

        for field in ("city", "state", "country"):
            if field in data and data[field] is not None:
                setattr(associate, field, str(data[field]).strip())
                changed.append(field)

        # Password change (self or staff editor) — requires matching confirm_password
        raw_password = data.get("password")
        if raw_password is not None and str(raw_password).strip():
            password = str(raw_password)
            confirm = str(data.get("confirm_password") or "")
            if len(password) < 6:
                raise ValueError("Password must be at least 6 characters")
            if password != confirm:
                raise ValueError("Password and confirm password do not match")
            associate.set_login_password(password, save_user=False)
            changed.append("password")
            changed.append("login_password")

        if is_staff_actor:
            if "status" in data and data["status"]:
                status = str(data["status"]).strip().lower()
                if status not in Associate.Status.values:
                    raise ValueError("Invalid status")
                associate.status = status
                changed.append("status")
            if "can_view_admin_history" in data and data["can_view_admin_history"] is not None:
                associate.can_view_admin_history = bool(data["can_view_admin_history"])
                changed.append("can_view_admin_history")
            if "can_view_reward_achievers" in data and data["can_view_reward_achievers"] is not None:
                associate.can_view_reward_achievers = bool(data["can_view_reward_achievers"])
                changed.append("can_view_reward_achievers")
            if "can_fund_transfer" in data and data["can_fund_transfer"] is not None:
                associate.can_fund_transfer = bool(data["can_fund_transfer"])
                changed.append("can_fund_transfer")

        user.save()
        associate.save()

        kyc_keys = (
            "full_name",
            "pan",
            "aadhaar",
            "bank_name",
            "account_number",
            "ifsc",
            "upi_id",
        )
        file_keys = (
            "profile_photo",
            "aadhaar_document",
            "aadhaar_back",
            "pan_document",
            "bank_document",
        )
        has_kyc_text = any(k in data and data[k] is not None for k in kyc_keys)
        has_kyc_files = any(files.get(k) for k in file_keys)

        if has_kyc_text or has_kyc_files:
            kyc = associate.kyc_submissions.order_by("-created_at").first()
            full_name = (
                str(data.get("full_name") or "").strip()
                or (kyc.full_name if kyc else "")
                or (user.get_full_name() or user.username)
            )
            if kyc is None:
                kyc = KYCSubmission(associate=associate, full_name=full_name)

            for key in kyc_keys:
                if key in data and data[key] is not None:
                    val = str(data[key]).strip()
                    if key == "pan":
                        val = val.upper()
                    if key == "ifsc":
                        val = val.upper()
                    if key == "aadhaar":
                        digits = "".join(ch for ch in val if ch.isdigit())
                        val = digits or val
                    setattr(kyc, key, val)
                    changed.append(f"kyc.{key}")

            if "full_name" not in data or not str(data.get("full_name") or "").strip():
                kyc.full_name = full_name

            # aadhaar_front is an API alias for aadhaar_document (front side)
            if files.get("aadhaar_front") and not files.get("aadhaar_document"):
                files["aadhaar_document"] = files["aadhaar_front"]

            for key in file_keys:
                f = files.get(key)
                if f is not None:
                    setattr(kyc, key, f)
                    changed.append(f"kyc.{key}")

            # Non-staff edits to KYC reset verification so lead/admin can re-check
            if not is_staff_actor and (has_kyc_text or has_kyc_files):
                kyc.status = KYCSubmission.Status.PENDING
                kyc.rejection_reason = ""
                kyc.reviewed_by = None
                kyc.reviewed_at = None
                associate.kyc_verified = False
                associate.save(update_fields=["kyc_verified", "updated_at"])
                changed.append("kyc.status")

            kyc.save()

        write_audit(
            actor=actor,
            action="associate.update_details",
            module="associates",
            object_type="Associate",
            object_id=str(associate.id),
            ip_address=ip,
            metadata={"associate_id": associate.associate_id, "changed": changed},
        )
        return Associate.objects.select_related("user", "sponsor").get(pk=associate.pk)


def secrets_token() -> str:
    import secrets

    return secrets.token_hex(3)
