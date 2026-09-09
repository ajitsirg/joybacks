from decimal import Decimal

from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline

from configuration.models import (
    ActivationRule,
    CompanySettings,
    GenealogySettings,
    LevelIncomePlan,
    LevelIncomeSlab,
    PerformanceIncomePlan,
    PerformanceIncomeSlab,
    ROIPlan,
    RewardMaster,
    WithdrawalSettings,
)


class LevelSlabInline(TabularInline):
    model = LevelIncomeSlab
    extra = 0
    tab = True
    fields = ("level", "percent", "title", "is_active")
    ordering = ("level",)


class PerfSlabInline(TabularInline):
    model = PerformanceIncomeSlab
    extra = 0
    tab = True
    fields = ("level", "percent", "required_directs", "is_active")
    ordering = ("level",)


@admin.register(CompanySettings)
class CompanySettingsAdmin(ModelAdmin):
    list_display = (
        "name",
        "currency_code",
        "require_leader_approval",
        "require_join_otp",
        "show_platinum_package",
        "show_silver_package",
        "show_users_flag_column",
        "show_users_card_column",
        "show_income_referral",
        "show_income_sp_profit",
        "show_income_section",
        "is_active",
    )
    list_editable = (
        "require_leader_approval",
        "require_join_otp",
        "show_platinum_package",
        "show_silver_package",
        "show_users_flag_column",
        "show_users_card_column",
        "show_income_referral",
        "show_income_sp_profit",
        "show_income_section",
    )
    list_filter = (
        "require_leader_approval",
        "require_join_otp",
        "show_platinum_package",
        "show_silver_package",
        "show_users_flag_column",
        "show_users_card_column",
        "show_income_referral",
        "show_income_sp_profit",
        "show_income_section",
        "is_active",
    )
    fieldsets = (
        (
            "Company",
            {
                "fields": (
                    "name",
                    "legal_name",
                    "support_email",
                    "support_phone",
                    "address",
                    "logo",
                    "is_active",
                )
            },
        ),
        (
            "Admin charges",
            {
                "description": (
                    "Taken from sale / level income, ROI level income, and reward commissions. "
                    "Associates receive the remaining amount. Charge rows are visible only to admin and finance."
                ),
                "fields": ("admin_charge_percent",),
            },
        ),
        (
            "Reward Achievement poster (app)",
            {
                "classes": ("tab",),
                "description": (
                    "Shown on Plans → Reward Achievement. "
                    "Recommended: 1200×675 px (16:9) or 1080×1350 px (4:5). JPG/WebP under 800 KB."
                ),
                "fields": ("reward_poster_image",),
            },
        ),
        (
            "Join approval",
            {
                "classes": ("tab",),
                "description": (
                    "Team Approvals — OFF (default): menu hidden; new members become Active and open the dashboard. "
                    "ON: show Team Approvals menu; joins stay Pending until the lead approves. "
                    "Join OTP — OFF (default): skip OTP (step 4); after KYC submit goes to dashboard when active. "
                    "ON: show OTP Verify step and require a valid OTP."
                ),
                "fields": ("require_leader_approval", "require_join_otp"),
            },
        ),
        (
            "Join packages (show / hide)",
            {
                "classes": ("tab",),
                "description": (
                    "Toggle which membership cards appear on Join / Register. "
                    "Gray (₹0) is always available. Platinum & Silver stay hidden until you enable them. "
                    "Associate flags are separate: gray = joined with no investment, green = has investment."
                ),
                "fields": ("show_platinum_package", "show_silver_package"),
            },
        ),
        (
            "Join KYC & bank (mandatory?)",
            {
                "classes": ("tab",),
                "description": (
                    "Off = optional (user can skip). On = must fill/upload on Join / Register. "
                    "Aadhaar document requires BOTH front and back images before it counts as attached."
                ),
                "fields": (
                    "require_join_pan",
                    "require_join_aadhaar",
                    "require_join_bank_name",
                    "require_join_account_number",
                    "require_join_ifsc",
                    "require_join_upi",
                    "require_join_profile_photo",
                    "require_join_aadhaar_document",
                    "require_join_pan_document",
                    "require_join_bank_document",
                ),
            },
        ),
        (
            "Users table columns (show / hide)",
            {
                "classes": ("tab",),
                "description": (
                    "Flag and Card columns on All / Active / Inactive / Blocked Users tables. "
                    "Both are OFF by default. Turn on here to show them in the app."
                ),
                "fields": (
                    "show_users_flag_column",
                    "show_users_card_column",
                ),
            },
        ),
        (
            "Sidebar Income menu (show / hide)",
            {
                "classes": ("tab",),
                "description": (
                    "Each toggle is off by default. Turn on only the Income pages you want in the sidebar."
                ),
                "fields": (
                    "show_income_referral",
                    "show_income_sp_profit",
                    "show_income_section",
                ),
            },
        ),
        (
            "Theme & currency",
            {
                "classes": ("tab",),
                "fields": ("currency_code", "currency_symbol", "theme_primary", "theme_accent"),
            },
        ),
        (
            "Notifications",
            {
                "classes": ("tab",),
                "fields": ("sms_enabled", "email_enabled", "otp_length"),
            },
        ),
    )


@admin.register(GenealogySettings)
class GenealogySettingsAdmin(ModelAdmin):
    list_display = ("name", "leg_mode", "max_legs", "max_depth", "sponsor_required", "is_active")
    list_editable = ("leg_mode", "max_legs", "max_depth", "sponsor_required", "is_active")
    list_filter = ("leg_mode", "is_active", "sponsor_required")
    list_filter_submit = True
    fieldsets = (
        (
            "Direct legs (width under one sponsor)",
            {
                "description": (
                    "How many direct joins each associate may have. "
                    "3 Leg / 5 Leg / 10 Leg auto-set Max legs. Unlimited = no direct limit."
                ),
                "fields": ("name", "leg_mode", "max_legs", "is_active"),
            },
        ),
        (
            "Join levels / tree depth (allow Level 11+)",
            {
                "description": (
                    "Controls how deep a new associate may join under the root. "
                    "Example: max 10 blocks level-11 joins; set 100 or 200 to allow deep teams. "
                    "0 = unlimited. Change here anytime — no code deploy needed."
                ),
                "fields": ("max_depth",),
            },
        ),
        (
            "Rules",
            {
                "fields": ("sponsor_required", "allow_same_leg_spillover"),
            },
        ),
    )


@admin.register(WithdrawalSettings)
class WithdrawalSettingsAdmin(ModelAdmin):
    list_display = ("name", "min_amount", "max_amount", "charge_percent", "maker_checker_threshold", "is_active")


@admin.register(ActivationRule)
class ActivationRuleAdmin(ModelAdmin):
    list_display = ("name", "min_deposit", "min_business", "require_kyc", "is_active")


@admin.register(LevelIncomePlan)
class LevelIncomePlanAdmin(ModelAdmin):
    list_display = ("name", "code", "max_levels", "is_active", "has_poster")
    list_filter = ("is_active",)
    list_editable = ("max_levels", "is_active")
    actions = ("fill_missing_slabs",)
    inlines = [LevelSlabInline]
    prepopulated_fields = {"code": ("name",)}
    fieldsets = (
        (
            None,
            {
                "description": (
                    "Set Max levels up to 200, then add percent slabs (or run action "
                    "“Fill missing slabs up to max levels”)."
                ),
                "fields": ("name", "code", "max_levels", "is_active", "tagline", "description"),
            },
        ),
        (
            "Plan poster image (app)",
            {
                "description": (
                    "Shown under the Direct / Level Income plan in the associate app. "
                    "Recommended sizes: 1080×1350 px (portrait 4:5 — best for mobile) "
                    "or 1200×675 px (16:9 wide). Use JPG or WebP under 800 KB."
                ),
                "fields": ("poster_image",),
            },
        ),
    )

    @admin.display(boolean=True, description="Poster")
    def has_poster(self, obj):
        return bool(obj.poster_image)

    @admin.action(description="Fill missing slabs up to max levels")
    def fill_missing_slabs(self, request, queryset):
        created = 0
        for plan in queryset:
            existing = set(plan.slabs.filter(is_deleted=False).values_list("level", flat=True))
            last = (
                plan.slabs.filter(is_deleted=False, is_active=True)
                .order_by("-level")
                .first()
            )
            last_pct = Decimal(last.percent) if last else Decimal("0.1000")
            for level in range(1, int(plan.max_levels or 0) + 1):
                if level in existing:
                    continue
                # Deeper levels keep a small trailing percent (admin can edit later)
                pct = last_pct if level > 1 else Decimal("1.0000")
                LevelIncomeSlab.objects.create(
                    plan=plan,
                    level=level,
                    percent=pct,
                    title=f"Level {level}",
                    is_active=True,
                )
                created += 1
        self.message_user(
            request,
            f"Created {created} missing level-income slab(s).",
            level=messages.SUCCESS,
        )


@admin.register(PerformanceIncomePlan)
class PerformanceIncomePlanAdmin(ModelAdmin):
    list_display = ("name", "code", "max_levels", "total_percent", "is_active", "has_poster")
    list_filter = ("is_active",)
    list_editable = ("max_levels", "is_active")
    actions = ("fill_missing_slabs",)
    inlines = [PerfSlabInline]
    prepopulated_fields = {"code": ("name",)}
    fieldsets = (
        (
            None,
            {
                "description": (
                    "Raise Max levels (e.g. 100 or 200), save, then run action "
                    "“Fill missing slabs up to max levels” — or add Level 11+ rows manually."
                ),
                "fields": ("name", "code", "max_levels", "is_active"),
            },
        ),
        (
            "Plan poster image (app)",
            {
                "description": (
                    "Shown under the Performance Level Income tiles in the associate app. "
                    "Recommended: 1200×675 px (16:9 — matches your resort poster) "
                    "or 1080×1350 px (4:5 for phones). JPG/WebP under 800 KB."
                ),
                "fields": ("poster_image",),
            },
        ),
    )

    @admin.display(description="Total %")
    def total_percent(self, obj):
        total = sum(
            (s.percent for s in obj.slabs.filter(is_active=True, is_deleted=False)),
            start=Decimal("0"),
        )
        return f"{total}%"

    @admin.display(boolean=True, description="Poster")
    def has_poster(self, obj):
        return bool(obj.poster_image)

    @admin.action(description="Fill missing slabs up to max levels")
    def fill_missing_slabs(self, request, queryset):
        created = 0
        for plan in queryset:
            existing = set(plan.slabs.filter(is_deleted=False).values_list("level", flat=True))
            last = (
                plan.slabs.filter(is_deleted=False, is_active=True)
                .order_by("-level")
                .first()
            )
            last_pct = Decimal(last.percent) if last else Decimal("0.2500")
            for level in range(1, int(plan.max_levels or 0) + 1):
                if level in existing:
                    continue
                PerformanceIncomeSlab.objects.create(
                    plan=plan,
                    level=level,
                    percent=last_pct,
                    required_directs=level,
                    min_business=Decimal("0"),
                    is_active=True,
                )
                created += 1
        self.message_user(
            request,
            f"Created {created} missing performance slab(s). Edit % / directs as needed.",
            level=messages.SUCCESS,
        )


@admin.register(ROIPlan)
class ROIPlanAdmin(ModelAdmin):
    list_display = ("name", "code", "percent", "cycle_days", "is_active")
    prepopulated_fields = {"code": ("name",)}


@admin.register(RewardMaster)
class RewardMasterAdmin(ModelAdmin):
    list_display = (
        "milestone_number",
        "name",
        "business_target",
        "leg1_target",
        "leg2_target",
        "leg3_target",
        "reward_amount",
        "is_active",
    )
    list_editable = (
        "business_target",
        "leg1_target",
        "leg2_target",
        "leg3_target",
        "reward_amount",
        "is_active",
    )
    list_filter = ("reward_type", "is_active")
    list_filter_submit = True
    ordering = ("sort_order", "milestone_number")
    fieldsets = (
        (
            None,
            {
                "description": (
                    "Exact rupee targets for Reward Achievement. "
                    "A milestone unlocks only when Leg 1, Leg 2, Leg 3 and Total are all met. "
                    "Total should equal Leg 1 + Leg 2 + Leg 3."
                ),
                "fields": (
                    "name",
                    "milestone_number",
                    "sort_order",
                    "reward_type",
                    "is_active",
                ),
            },
        ),
        (
            "Targets (₹)",
            {
                "fields": (
                    "business_target",
                    "leg1_target",
                    "leg2_target",
                    "leg3_target",
                    "leg_business",
                    "reward_amount",
                )
            },
        ),
        ("Poster", {"fields": ("image", "description")}),
    )
