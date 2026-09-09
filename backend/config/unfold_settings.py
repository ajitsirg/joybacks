"""Django Unfold admin theme — JoyClub Associate branding."""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def environment_callback(request):
    from django.conf import settings

    if settings.DEBUG:
        return ["Local", "info"]
    return ["Production", "success"]


def pending_kyc_badge(request):
    try:
        from operations.models import KYCSubmission

        return KYCSubmission.objects.filter(status="pending").count() or None
    except Exception:
        return None


def pending_withdraw_badge(request):
    try:
        from operations.models import WithdrawalRequest

        return WithdrawalRequest.objects.filter(status="pending").count() or None
    except Exception:
        return None


def pending_fund_transfer_badge(request):
    try:
        from wallets.models import FundTransferRequest

        return FundTransferRequest.objects.filter(status="pending").count() or None
    except Exception:
        return None


def pending_deposit_badge(request):
    try:
        from operations.models import DepositRequest

        return DepositRequest.objects.filter(status="pending").count() or None
    except Exception:
        return None


UNFOLD = {
    "SITE_TITLE": "JoyClub Associate",
    "SITE_HEADER": "JoyClub Associate",
    "SITE_SUBHEADER": "Platform control center",
    "SITE_URL": "/",
    "SITE_SYMBOL": "diversity_3",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "ENVIRONMENT": "config.unfold_settings.environment_callback",
    "DASHBOARD_CALLBACK": "dashboard.admin_dashboard.dashboard_callback",
    "BORDER_RADIUS": "10px",
    "COLORS": {
        "primary": {
            "50": "oklch(97% 0.025 155)",
            "100": "oklch(93% 0.05 155)",
            "200": "oklch(87% 0.08 155)",
            "300": "oklch(76% 0.11 155)",
            "400": "oklch(62% 0.13 155)",
            "500": "oklch(48% 0.13 155)",
            "600": "oklch(42% 0.12 155)",
            "700": "oklch(35% 0.11 155)",
            "800": "oklch(28% 0.09 155)",
            "900": "oklch(22% 0.07 155)",
            "950": "oklch(15% 0.05 155)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Overview"),
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Network"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Associates"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:associates_associate_changelist"),
                    },
                    {
                        "title": _("Deleted / deactivated"),
                        "icon": "delete",
                        "link": reverse_lazy("admin:associates_deletedassociate_changelist"),
                    },
                    {
                        "title": _("Genealogy nodes"),
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:genealogy_genealogynode_changelist"),
                    },
                ],
            },
            {
                "title": _("Operations"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("KYC"),
                        "icon": "badge",
                        "link": reverse_lazy("admin:operations_kycsubmission_changelist"),
                        "badge": "config.unfold_settings.pending_kyc_badge",
                        "badge_variant": "warning",
                    },
                    {
                        "title": _("Deposits"),
                        "icon": "south",
                        "link": reverse_lazy("admin:operations_depositrequest_changelist"),
                        "badge": "config.unfold_settings.pending_deposit_badge",
                        "badge_variant": "info",
                    },
                    {
                        "title": _("Withdrawals"),
                        "icon": "north",
                        "link": reverse_lazy("admin:operations_withdrawalrequest_changelist"),
                        "badge": "config.unfold_settings.pending_withdraw_badge",
                        "badge_variant": "danger",
                    },
                ],
            },
            {
                "title": _("Finance"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Wallets"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:wallets_wallet_changelist"),
                    },
                    {
                        "title": _("Ledger"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:wallets_ledgerentry_changelist"),
                    },
                    {
                        "title": _("Fund Transfer"),
                        "icon": "swap_horiz",
                        "link": reverse_lazy("admin:wallets_fundtransferrequest_changelist"),
                        "badge": "config.unfold_settings.pending_fund_transfer_badge",
                        "badge_variant": "warning",
                    },
                    {
                        "title": _("Commission runs"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:commissions_commissionrun_changelist"),
                    },
                    {
                        "title": _("Commission entries"),
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:commissions_commissionentry_changelist"),
                    },
                    {
                        "title": _("Admin charges"),
                        "icon": "percent",
                        "link": reverse_lazy("admin:commissions_admincharge_changelist"),
                    },
                ],
            },
            {
                "title": _("Plans & settings"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Company"),
                        "icon": "apartment",
                        "link": reverse_lazy("admin:configuration_companysettings_changelist"),
                    },
                    {
                        "title": _("Genealogy / legs"),
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:configuration_genealogysettings_changelist"),
                    },
                    {
                        "title": _("Rewards"),
                        "icon": "emoji_events",
                        "link": reverse_lazy("admin:configuration_rewardmaster_changelist"),
                    },
                    {
                        "title": _("Level income"),
                        "icon": "stairs",
                        "link": reverse_lazy("admin:configuration_levelincomeplan_changelist"),
                    },
                    {
                        "title": _("Performance plans"),
                        "icon": "speed",
                        "link": reverse_lazy("admin:configuration_performanceincomeplan_changelist"),
                    },
                    {
                        "title": _("ROI plans"),
                        "icon": "show_chart",
                        "link": reverse_lazy("admin:configuration_roiplan_changelist"),
                    },
                    {
                        "title": _("Withdrawal rules"),
                        "icon": "rule",
                        "link": reverse_lazy("admin:configuration_withdrawalsettings_changelist"),
                    },
                ],
            },
            {
                "title": _("Content"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("News"),
                        "icon": "newspaper",
                        "link": reverse_lazy("admin:cms_newsitem_changelist"),
                    },
                    {
                        "title": _("Help tickets"),
                        "icon": "support_agent",
                        "link": reverse_lazy("admin:cms_helpticket_changelist"),
                    },
                    {
                        "title": _("QR & wallet"),
                        "icon": "qr_code_2",
                        "link": reverse_lazy("admin:cms_qrwalletsetting_changelist"),
                    },
                    {
                        "title": _("Landing page"),
                        "icon": "web",
                        "link": reverse_lazy("admin:cms_landingpagesettings_changelist"),
                    },
                    {
                        "title": _("Landing benefits"),
                        "icon": "star",
                        "link": reverse_lazy("admin:cms_landingbenefit_changelist"),
                    },
                    {
                        "title": _("Landing gallery"),
                        "icon": "photo_library",
                        "link": reverse_lazy("admin:cms_landinggalleryitem_changelist"),
                    },
                    {
                        "title": _("Knowledge center"),
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:cms_knowledgeitem_changelist"),
                    },
                ],
            },
            {
                "title": _("Access & audit"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                    {
                        "title": _("Roles"),
                        "icon": "admin_panel_settings",
                        "link": reverse_lazy("admin:accounts_role_changelist"),
                    },
                    {
                        "title": _("Permissions"),
                        "icon": "key",
                        "link": reverse_lazy("admin:accounts_permission_changelist"),
                    },
                    {
                        "title": _("Staff profiles"),
                        "icon": "badge",
                        "link": reverse_lazy("admin:accounts_staffprofile_changelist"),
                    },
                    {
                        "title": _("Audit log"),
                        "icon": "history",
                        "link": reverse_lazy("admin:audit_auditlog_changelist"),
                    },
                    {
                        "title": _("Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                ],
            },
        ],
    },
}
