"""All business rules live here — never hardcode commission/ROI/reward logic."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import BaseModel


class CompanySettings(BaseModel):
    """Singleton-ish company profile & theme."""

    name = models.CharField(max_length=160, default="JoyClub Associate")
    legal_name = models.CharField(max_length=200, blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    currency_code = models.CharField(max_length=8, default="INR")
    currency_symbol = models.CharField(max_length=8, default="₹")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    theme_primary = models.CharField(max_length=20, default="#0B6B3A")
    theme_accent = models.CharField(max_length=20, default="#149A56")
    address = models.TextField(blank=True)
    sms_enabled = models.BooleanField(default=False)
    email_enabled = models.BooleanField(default=True)
    otp_length = models.PositiveSmallIntegerField(default=6)
    # Join page membership cards (admin toggles)
    show_platinum_package = models.BooleanField(
        default=False,
        help_text="Show Platinum (₹2,20,000) option on Join / Register",
    )
    show_silver_package = models.BooleanField(
        default=False,
        help_text="Show Silver (₹22,000) option on Join / Register",
    )
    # Join KYC / bank fields — off = optional (user may skip)
    require_join_pan = models.BooleanField(default=False, help_text="Require PAN on Join")
    require_join_aadhaar = models.BooleanField(default=False, help_text="Require Aadhaar on Join")
    require_join_bank_name = models.BooleanField(default=False, help_text="Require bank name on Join")
    require_join_account_number = models.BooleanField(
        default=False, help_text="Require account number on Join"
    )
    require_join_ifsc = models.BooleanField(default=False, help_text="Require IFSC on Join")
    require_join_upi = models.BooleanField(default=False, help_text="Require UPI ID on Join")
    require_join_profile_photo = models.BooleanField(
        default=False, help_text="Require profile photo on Join"
    )
    require_join_aadhaar_document = models.BooleanField(
        default=False,
        help_text="Require Aadhaar front + back images on Join. Counts as attached only when both are uploaded.",
        verbose_name="Require Aadhaar front & back",
    )
    require_join_pan_document = models.BooleanField(
        default=False, help_text="Require PAN card upload on Join"
    )
    require_join_bank_document = models.BooleanField(
        default=False, help_text="Require bank proof upload on Join"
    )
    require_leader_approval = models.BooleanField(
        default=False,
        help_text=(
            "Team Approvals toggle. "
            "If ON: show Team Approvals in the app, and new joins stay Pending until the lead approves. "
            "If OFF (default): hide Team Approvals; joins become Active immediately and open the dashboard."
        ),
        verbose_name="Team Approvals (require leader approval)",
    )
    require_join_otp = models.BooleanField(
        default=False,
        help_text=(
            "If ON: Join shows OTP Verify (step 4) and registration requires a valid OTP. "
            "If OFF (default): after KYC (step 3) the form submits and active members go to the dashboard."
        ),
    )
    # Users table columns (each off = hidden)
    show_users_flag_column = models.BooleanField(
        default=False,
        help_text="Show Flag (Invested / No investment) column on Users tables. Off = hidden.",
        verbose_name="Show Flag column (Users tables)",
    )
    show_users_card_column = models.BooleanField(
        default=False,
        help_text="Show Card (Platinum / Silver / Gray) column on Users tables. Off = hidden.",
        verbose_name="Show Card column (Users tables)",
    )
    # Sidebar Income menu items (each off = hidden)
    show_income_section = models.BooleanField(
        default=False,
        help_text="Show ROI Level Income and Reward Income. Off = hidden.",
    )
    show_income_referral = models.BooleanField(
        default=False,
        help_text="Show Level / Referral Income. Off = hidden.",
    )
    show_income_sp_profit = models.BooleanField(
        default=False,
        help_text="Show S.P. Profit under Income. Off = hidden.",
    )
    admin_charge_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Percent taken as company admin charge on sale, ROI, and reward commissions.",
    )
    reward_poster_image = models.ImageField(
        upload_to="plans/reward-achievement/",
        blank=True,
        null=True,
        help_text=(
            "Poster shown on Plans → Reward Achievement. "
            "Recommended: 1200×675 px (16:9) or 1080×1350 px (4:5). JPG/WebP under 800 KB."
        ),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Company settings"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def current(cls) -> "CompanySettings":
        obj = cls.objects.filter(is_active=True).order_by("created_at").first()
        if obj:
            return obj
        return cls.objects.create(name="JoyClub Associate")


class GenealogySettings(BaseModel):
    """Leg count & tree behaviour — fully admin-configurable."""

    class LegMode(models.TextChoices):
        LEG_3 = "3", "3 Leg"
        LEG_5 = "5", "5 Leg"
        LEG_10 = "10", "10 Leg"
        UNLIMITED = "unlimited", "Unlimited"

    name = models.CharField(max_length=80, default="Default Genealogy")
    leg_mode = models.CharField(
        max_length=20,
        choices=LegMode.choices,
        default=LegMode.LEG_10,
        help_text="How many direct legs (nodes) each associate may have under them. Default: 10 Leg.",
    )
    max_legs = models.PositiveIntegerField(
        default=10,
        help_text="Direct capacity. Auto-filled from Leg mode (3/5/10). 0 = unlimited.",
    )
    max_depth = models.PositiveIntegerField(
        default=200,
        validators=[MaxValueValidator(1000)],
        help_text=(
            "Max join / tree levels under root (associate depth). "
            "Set 100 or 200 to allow deep teams (Level 11+). "
            "0 = unlimited. Django admin controls who can join how deep."
        ),
        verbose_name="Max join levels (tree depth)",
    )
    sponsor_required = models.BooleanField(default=True)
    allow_same_leg_spillover = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.leg_mode})"

    def effective_max_legs(self) -> int:
        """Resolved direct-leg limit. 0 means unlimited."""
        if self.leg_mode == self.LegMode.UNLIMITED:
            return 0
        if self.leg_mode in {self.LegMode.LEG_3, self.LegMode.LEG_5, self.LegMode.LEG_10}:
            try:
                return int(self.leg_mode)
            except (TypeError, ValueError):
                pass
        return int(self.max_legs or 0)

    def save(self, *args, **kwargs):
        # Keep max_legs in sync with preset leg modes so enforcement always works.
        if self.leg_mode == self.LegMode.UNLIMITED:
            self.max_legs = 0
        elif self.leg_mode in {self.LegMode.LEG_3, self.LegMode.LEG_5, self.LegMode.LEG_10}:
            self.max_legs = int(self.leg_mode)
        super().save(*args, **kwargs)


class ActivationRule(BaseModel):
    name = models.CharField(max_length=80)
    min_deposit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    min_business = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    require_kyc = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class WithdrawalSettings(BaseModel):
    name = models.CharField(max_length=80, default="Default Withdrawal")
    min_amount = models.DecimalField(max_digits=14, decimal_places=2, default=500)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2, default=500000)
    charge_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    charge_flat = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    maker_checker_threshold = models.DecimalField(max_digits=14, decimal_places=2, default=50000)
    daily_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class LevelIncomePlan(BaseModel):
    """Direct / level income plan header."""

    name = models.CharField(max_length=120)
    code = models.SlugField(unique=True)
    max_levels = models.PositiveIntegerField(
        default=5,
        validators=[MaxValueValidator(200)],
        help_text="How many upline levels pay income (1–200). Add a slab row for each level in admin.",
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    tagline = models.CharField(
        max_length=160,
        blank=True,
        default="Together We Grow, Together We Succeed",
    )
    poster_image = models.ImageField(
        upload_to="plans/level-income/",
        blank=True,
        null=True,
        help_text=(
            "Optional banner under the plan on the app. "
            "Recommended: 1080×1350 px (portrait 4:5) for mobile, or 1200×675 px (16:9) for wide. "
            "JPG/WebP, under 800 KB."
        ),
    )

    def __str__(self) -> str:
        return self.name


class LevelIncomeSlab(BaseModel):
    plan = models.ForeignKey(LevelIncomePlan, on_delete=models.CASCADE, related_name="slabs")
    level = models.PositiveIntegerField()
    percent = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    title = models.CharField(
        max_length=80,
        blank=True,
        help_text="Short label shown in the app, e.g. Start Your Journey",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("plan", "level")
        ordering = ["level"]

    def clean(self):
        errors = {}
        if self.level is not None and self.level < 1:
            errors["level"] = "Level must be at least 1."
        max_levels = 5
        if self.plan_id:
            max_levels = int(self.plan.max_levels or 5)
        if self.level is not None and self.level > max_levels:
            errors["level"] = f"Level must be between 1 and {max_levels}."
        if self.percent is not None and self.percent < 0:
            errors["percent"] = "Percentage cannot be negative."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.plan.code} L{self.level}: {self.percent}%"


class PerformanceIncomePlan(BaseModel):
    name = models.CharField(max_length=120)
    code = models.SlugField(unique=True)
    max_levels = models.PositiveIntegerField(
        default=10,
        validators=[MaxValueValidator(200)],
        help_text=(
            "Max performance levels (1–200). Raise this, then add slabs (Level 11, 12, …) "
            "or use admin action “Fill missing slabs up to max levels”."
        ),
    )
    is_active = models.BooleanField(default=True)
    poster_image = models.ImageField(
        upload_to="plans/performance-income/",
        blank=True,
        null=True,
        help_text=(
            "Optional banner under the plan on the app. "
            "Recommended: 1200×675 px (16:9) or 1080×1350 px (portrait 4:5). "
            "JPG/WebP, under 800 KB."
        ),
    )

    def __str__(self) -> str:
        return self.name


class PerformanceIncomeSlab(BaseModel):
    plan = models.ForeignKey(PerformanceIncomePlan, on_delete=models.CASCADE, related_name="slabs")
    level = models.PositiveIntegerField()
    percent = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    required_directs = models.PositiveIntegerField(default=0)
    min_business = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("plan", "level")
        ordering = ["level"]

    def clean(self):
        errors = {}
        if self.level is not None and self.level < 1:
            errors["level"] = "Level must be at least 1."
        max_levels = 10
        if self.plan_id:
            max_levels = int(self.plan.max_levels or 10)
        if self.level is not None and self.level > max_levels:
            errors["level"] = f"Level must be between 1 and {max_levels}."
        if self.percent is not None and self.percent < 0:
            errors["percent"] = "Percentage cannot be negative."
        if self.required_directs is not None and self.required_directs < 0:
            errors["required_directs"] = "Required directs cannot be negative."
        if errors:
            raise ValidationError(errors)


class ROIPlan(BaseModel):
    name = models.CharField(max_length=120)
    code = models.SlugField(unique=True)
    percent = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    cycle_days = models.PositiveIntegerField(default=1, help_text="Distribute every N days")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.percent}%)"


class RewardMaster(BaseModel):
    class RewardType(models.TextChoices):
        CASH = "cash", "Cash"
        GIFT = "gift", "Gift"
        TRAVEL = "travel", "Travel"
        OTHER = "other", "Other"

    name = models.CharField(
        max_length=160,
        help_text='Use "Level 1", "Level 2", … "Level 100". Add more rows here to unlock higher reward levels.',
    )
    reward_type = models.CharField(max_length=20, choices=RewardType.choices, default=RewardType.CASH)
    milestone_number = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text="S.No. in the Reward Achievement table (1–10).",
    )
    business_target = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        help_text="Total business target (Leg 1 + Leg 2 + Leg 3).",
    )
    leg_business = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        help_text="Legacy single-leg target. Prefer Leg 1 / 2 / 3 targets below.",
    )
    leg1_target = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    leg2_target = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    leg3_target = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    reward_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    image = models.ImageField(upload_to="rewards/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["sort_order", "business_target"]

    def __str__(self) -> str:
        return self.name
