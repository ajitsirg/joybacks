"""Idempotent RBAC roles, including Finance Manager fund-transfer access."""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission as DjangoPermission

from accounts.models import Permission, Role

FINANCE_ROLE_NAME = "Finance Manager"

FINANCE_PERM_CODES = (
    "users.view",
    "withdrawals.view",
    "withdrawals.approve",
    "deposits.view",
    "deposits.approve",
    "income.view",
    "reports.view",
    "wallets.view",
    "wallets.transfer",
    "fund.view",
    "fund.transfer",
)

# Native Django admin permissions so Finance Manager can use Unfold → Finance.
DJANGO_FINANCE_CODENAMES = (
    "view_wallet",
    "view_ledgerentry",
    "view_fundtransferrequest",
    "add_fundtransferrequest",
    "change_fundtransferrequest",
    "can_fund_transfer",
    "view_admincharge",
    "view_commissionentry",
    "view_commissionrun",
    "view_depositrequest",
    "change_depositrequest",
    "view_withdrawalrequest",
    "change_withdrawalrequest",
)

ADMIN_PERM_EXCLUDE = ("rbac.manage",)


def ensure_app_permissions() -> None:
    extras = [
        ("fund.view", "View Fund", "fund"),
        ("fund.transfer", "Transfer Funds", "fund"),
    ]
    for code, name, module in extras:
        Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "module": module},
        )


def ensure_finance_manager_role() -> Role:
    ensure_app_permissions()
    role, _ = Role.objects.get_or_create(
        name=FINANCE_ROLE_NAME,
        defaults={
            "description": "Handles money movement, fund transfer, withdrawals and deposits.",
            "is_system": True,
        },
    )
    role.description = "Handles money movement, fund transfer, withdrawals and deposits."
    role.is_system = True
    role.save()
    role.permissions.set(Permission.objects.filter(code__in=FINANCE_PERM_CODES))
    _sync_django_group(role.name, DJANGO_FINANCE_CODENAMES)
    return role


def ensure_admin_role() -> Role:
    role, _ = Role.objects.get_or_create(
        name="Admin",
        defaults={"description": "Operational admin — most modules, no RBAC changes.", "is_system": True},
    )
    perms = Permission.objects.exclude(code__in=ADMIN_PERM_EXCLUDE)
    role.permissions.set(perms)
    return role


def _sync_django_group(name: str, codenames: tuple[str, ...]) -> Group:
    group, _ = Group.objects.get_or_create(name=name)
    perms = DjangoPermission.objects.filter(codename__in=codenames)
    group.permissions.set(perms)
    return group


def sync_staff_django_groups(user) -> None:
    """Keep Django Groups in sync so Unfold admin honors Finance Manager access."""
    profile = getattr(user, "staff_profile", None)
    role_names = set()
    if profile is not None:
        role_names = set(profile.roles.values_list("name", flat=True))
    if FINANCE_ROLE_NAME in role_names:
        ensure_finance_manager_role()
    system_names = set(Role.objects.filter(is_system=True).values_list("name", flat=True))
    for name in role_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    for group in user.groups.filter(name__in=system_names):
        if group.name not in role_names:
            user.groups.remove(group)
