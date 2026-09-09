"""Associate (member) management & sponsor linkage."""

from __future__ import annotations

import secrets
import string
from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import BaseModel

# Full package / platinum join amount (configurable seed also mirrors this)
PLATINUM_JOIN_AMOUNT = Decimal("220000")
SILVER_MIN_PERCENT = Decimal("10")  # 10% of platinum = ₹22,000


USERNAME_PREFIX = "JOY"


def username_from_mobile(mobile: str) -> str:
    """Canonical associate username: JOY + mobile digits."""
    digits = "".join(ch for ch in (mobile or "") if ch.isdigit())
    return f"{USERNAME_PREFIX}{digits}"


def generate_associate_id() -> str:
    """Fallback random associate IDs always start with JOY."""
    return USERNAME_PREFIX + "".join(secrets.choice(string.digits) for _ in range(8))


def generate_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return USERNAME_PREFIX + "".join(secrets.choice(alphabet) for _ in range(5))


def flag_from_investment(*amounts: Decimal) -> str:
    """
    Display flag — only two colors:
    - gray  → joined, no investment yet
    - green → has any investment (join package / deposit / personal business)
    """
    for raw in amounts:
        if Decimal(raw or 0) > 0:
            return "green"
    return "gray"


def tier_from_amount(amount: Decimal) -> tuple[str, str]:
    """
    Returns (card_tier, flag_color).

    Card tier still tracks join package (platinum / silver / gray) when admin
    enables those packages. Flag color is only gray vs green from investment.
    """
    amount = Decimal(amount or 0)
    flag = flag_from_investment(amount)
    if amount >= PLATINUM_JOIN_AMOUNT:
        return "platinum", flag
    silver_min = (PLATINUM_JOIN_AMOUNT * SILVER_MIN_PERCENT / Decimal("100")).quantize(Decimal("0.01"))
    if amount >= silver_min:
        return "silver", flag
    return "gray", flag


class Associate(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        BLOCKED = "blocked", "Blocked"
        REJECTED = "rejected", "Rejected by leader"

    class CardTier(models.TextChoices):
        PLATINUM = "platinum", "Platinum Card"
        SILVER = "silver", "Silver Card"
        GRAY = "gray", "Gray Card"

    class FlagColor(models.TextChoices):
        GREEN = "green", "Green — has investment"
        GRAY = "gray", "Gray — joined, no investment"
        # Legacy values kept so old rows remain readable until migrated
        BLUE = "blue", "Blue (legacy)"
        PINK = "pink", "Pink (legacy)"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="associate")
    associate_id = models.CharField(max_length=20, unique=True, db_index=True)
    referral_code = models.CharField(max_length=20, unique=True, db_index=True)
    sponsor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="directs",
    )
    sponsor_associate_id = models.CharField(max_length=20, blank=True, db_index=True)
    lead_reference = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
        help_text="Mandatory lead / introducer reference at joining",
    )
    placement_leg = models.PositiveIntegerField(default=0, help_text="Leg index under sponsor; 0 = auto")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    mobile = models.CharField(max_length=20, db_index=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, default="India")
    kyc_verified = models.BooleanField(default=False)
    can_view_admin_history = models.BooleanField(
        default=False,
        help_text="If on, this associate can see Fund → Admin History in the app. Off by default.",
    )
    can_view_reward_achievers = models.BooleanField(
        default=False,
        help_text="If on, this associate can see Users → Reward Achievers in the app. Off by default.",
    )
    can_fund_transfer = models.BooleanField(
        default=True,
        help_text=(
            "Unused. Associates can only request a fund transfer; only staff can execute."
        ),
    )
    login_password = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Plaintext copy of the last password set at join or password change. "
            "Shown to staff/superadmin only. Login still uses Django’s hash — "
            "always set both via set_login_password()."
        ),
    )
    rejection_reason = models.TextField(blank=True)
    join_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    card_tier = models.CharField(max_length=20, choices=CardTier.choices, default=CardTier.GRAY, db_index=True)
    flag_color = models.CharField(max_length=20, choices=FlagColor.choices, default=FlagColor.GRAY, db_index=True)
    total_business = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    personal_business = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    earning_level = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text="Reward Achievement level from team business / Reward Master (0 = none).",
    )
    earning_level_name = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Reward level label from Reward Master, e.g. Level 3.",
    )
    performance_level = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text="Performance Income level from active directs (0 = none).",
    )
    performance_level_name = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Performance level label, e.g. Level 3.",
    )
    direct_count = models.PositiveIntegerField(default=0)
    direct_active_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["sponsor", "status"]),
            models.Index(fields=["card_tier", "flag_color"]),
            models.Index(fields=["mobile"]),
        ]

    def __str__(self) -> str:
        return f"{self.associate_id} ({self.mobile})"

    @property
    def username(self) -> str:
        return self.associate_id

    def set_login_password(self, raw_password: str, *, save_user: bool = True) -> None:
        """Hash password for login and store plaintext copy for staff/superadmin."""
        password = str(raw_password or "")
        if not password:
            raise ValueError("Password is required")
        if self.user_id:
            self.user.set_password(password)
            if save_user:
                self.user.save(update_fields=["password"])
        self.login_password = password

    def sync_flag_color(self, *, save: bool = True) -> str:
        """Set flag from investment: gray (none) or green (any)."""
        flag = flag_from_investment(self.join_amount, self.personal_business)
        if self.flag_color != flag:
            self.flag_color = flag
            if save:
                self.save(update_fields=["flag_color", "updated_at"])
        return flag

    def invested_amount(self) -> Decimal:
        """Investment used for Active status (₹2.2L gate): join package or personal business."""
        return max(Decimal(self.personal_business or 0), Decimal(self.join_amount or 0))

    @staticmethod
    def compute_earning_level(
        total_business: Decimal,
        *,
        leg1: Decimal | None = None,
        leg2: Decimal | None = None,
        leg3: Decimal | None = None,
    ) -> tuple[int, str]:
        """
        Highest Reward Achievement tier from the 40/30/30 poster.

        Requires total business AND power-leg / 2nd / 3rd leg amounts.
        """
        from associates.rewards import compute_reward_level

        return compute_reward_level(
            total_business=Decimal(total_business or 0),
            leg1=Decimal(leg1 or 0),
            leg2=Decimal(leg2 or 0),
            leg3=Decimal(leg3 or 0),
        )

    def sync_earning_level(self, *, save: bool = True) -> tuple[int, str]:
        """Refresh reward level from 9 official slabs and pay newly unlocked cash."""
        from associates.rewards import compute_reward_level_for, pay_unlocked_rewards

        level, name = compute_reward_level_for(self)
        changed = self.earning_level != level or self.earning_level_name != name
        if changed:
            self.earning_level = level
            self.earning_level_name = name
            if save:
                self.save(update_fields=["earning_level", "earning_level_name", "updated_at"])
        if level > 0:
            # Idempotent: credits any unlocked slab not yet paid (catch-up).
            pay_unlocked_rewards(associate=self, old_level=0, new_level=level)
        return level, name

    @staticmethod
    def compute_performance_level(
        *,
        direct_active_count: int,
        total_business: Decimal,
    ) -> tuple[int, str]:
        """
        Highest Performance Income slab where active directs and team business qualify.
        """
        from configuration.repository import ConfigRepository

        plan = ConfigRepository.active_performance_plan()
        if not plan:
            return 0, "No level"
        directs = int(direct_active_count or 0)
        volume = Decimal(total_business or 0)
        level = 0
        name = "No level"
        for slab in plan.slabs.filter(is_active=True, is_deleted=False).order_by("level"):
            need = int(slab.required_directs or 0) or int(slab.level)
            if directs < need:
                break
            if volume < Decimal(slab.min_business or 0):
                break
            level = int(slab.level)
            name = f"Level {level}"
        return level, name

    def sync_performance_level(self, *, save: bool = True) -> tuple[int, str]:
        """
        Refresh performance / Growth Level from qualifying direct farmhouse sales.

        Growth Level N requires N direct qualifying sales (PerformanceIncomePlan slabs).
        """
        from commissions.services import CommissionEngine

        level = int(CommissionEngine.unlocked_performance_levels(self))
        name = f"Level {level}" if level else "No level"
        changed = self.performance_level != level or self.performance_level_name != name
        if changed:
            self.performance_level = level
            self.performance_level_name = name
            if save:
                self.save(
                    update_fields=["performance_level", "performance_level_name", "updated_at"]
                )
        return level, name

    def sync_rank_levels(self, *, save: bool = True) -> None:
        """Refresh both Reward (earning) and Performance levels."""
        self.sync_earning_level(save=False)
        self.sync_performance_level(save=False)
        if save:
            self.save(
                update_fields=[
                    "earning_level",
                    "earning_level_name",
                    "performance_level",
                    "performance_level_name",
                    "updated_at",
                ]
            )

    def sync_status_from_investment(self, *, save: bool = True) -> str:
        """
        Gray / no-investment members stay Inactive.
        Active only when investment >= ₹2,20,000 (platinum).
        Pending / rejected / blocked are left unchanged.
        """
        from django.utils import timezone

        flag = flag_from_investment(self.join_amount, self.personal_business)
        flag_changed = self.flag_color != flag
        if flag_changed:
            self.flag_color = flag

        if self.status in {
            Associate.Status.PENDING,
            Associate.Status.REJECTED,
            Associate.Status.BLOCKED,
        }:
            if save and flag_changed:
                self.save(update_fields=["flag_color", "updated_at"])
            return self.status

        invested = self.invested_amount()
        # No investment (gray) or under ₹2.2L → Inactive; ₹2.2L+ → Active
        if invested >= PLATINUM_JOIN_AMOUNT:
            status_changed = self.status != Associate.Status.ACTIVE
            if status_changed:
                self.status = Associate.Status.ACTIVE
                if not self.activated_at:
                    self.activated_at = timezone.now()
            if save and (status_changed or flag_changed):
                fields = ["status", "flag_color", "updated_at"]
                if status_changed:
                    fields.append("activated_at")
                self.save(update_fields=fields)
        else:
            status_changed = self.status != Associate.Status.INACTIVE
            if status_changed:
                self.status = Associate.Status.INACTIVE
            if save and (status_changed or flag_changed):
                self.save(update_fields=["status", "flag_color", "updated_at"])
        return self.status

    def save(self, *args, **kwargs):
        if not self.associate_id:
            for _ in range(20):
                candidate = generate_associate_id()
                if not Associate.all_objects.filter(associate_id=candidate).exists():
                    self.associate_id = candidate
                    break
        if not self.referral_code:
            for _ in range(20):
                candidate = generate_referral_code()
                if not Associate.all_objects.filter(referral_code=candidate).exists():
                    self.referral_code = candidate
                    break
        super().save(*args, **kwargs)


class DeletedAssociate(Associate):
    """Proxy for Django admin Recycle Bin — archived / deleted accounts + data."""

    class Meta:
        proxy = True
        verbose_name = "Deleted / deactivated account"
        verbose_name_plural = "Deleted / deactivated accounts"


class RewardLegAssignment(BaseModel):
    """One of the three performance legs used for Reward Achievement."""

    owner = models.ForeignKey(
        Associate,
        on_delete=models.CASCADE,
        related_name="reward_leg_assignments",
    )
    slot = models.PositiveSmallIntegerField(help_text="1, 2, or 3")
    performer = models.ForeignKey(
        Associate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reward_leg_for",
    )
    locked = models.BooleanField(
        default=False,
        help_text="If on, this slot stays on the chosen member. If off, the engine keeps the current top performer.",
    )

    class Meta:
        unique_together = ("owner", "slot")
        ordering = ["slot"]

    def __str__(self) -> str:
        who = self.performer.associate_id if self.performer_id else "—"
        return f"{self.owner.associate_id} L{self.slot} → {who}"


class RewardAchievement(BaseModel):
    """One paid milestone per associate (User + S.No.)."""

    class Status(models.TextChoices):
        CREDITED = "credited", "Credited"
        PENDING = "pending", "Pending"

    associate = models.ForeignKey(
        Associate,
        on_delete=models.CASCADE,
        related_name="reward_achievements",
    )
    milestone = models.PositiveSmallIntegerField(db_index=True)
    total_business = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    leg1_business = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    leg2_business = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    leg3_business = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    reward_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    qualified_at = models.DateTimeField(auto_now_add=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREDITED)
    reference = models.CharField(max_length=80, unique=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["associate", "milestone"],
                condition=models.Q(is_deleted=False),
                name="uniq_live_reward_achievement",
            )
        ]
        ordering = ["associate", "milestone"]

    def __str__(self) -> str:
        return f"{self.associate.associate_id} M{self.milestone} ₹{self.reward_amount}"
