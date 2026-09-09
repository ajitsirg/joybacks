"""Authentication, RBAC, device login history."""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from core.models import BaseModel, TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, username=extra.pop("username", email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Platform user — staff or associate identity."""

    class UserType(models.TextChoices):
        STAFF = "staff", "Staff"
        ASSOCIATE = "associate", "Associate"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.STAFF)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["user_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.email


class Permission(BaseModel):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    module = models.CharField(max_length=80, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["module", "code"]

    def __str__(self) -> str:
        return self.code


class Role(BaseModel):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StaffProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    employee_code = models.CharField(max_length=40, unique=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="staff_members")
    department = models.CharField(max_length=80, blank=True)
    is_suspended = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.employee_code

    def permission_codes(self) -> set[str]:
        if self.user.is_superuser:
            return set(Permission.objects.values_list("code", flat=True))
        codes: set[str] = set()
        for role in self.roles.prefetch_related("permissions"):
            codes.update(role.permissions.values_list("code", flat=True))
        return codes


class DeviceLogin(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_logins")
    device_name = models.CharField(max_length=120, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class OTPChallenge(UUIDModel, TimeStampedModel):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        REGISTER = "register", "Register"
        RESET = "reset", "Reset Password"

    phone_or_email = models.CharField(max_length=120, db_index=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["phone_or_email", "purpose", "is_used"])]
