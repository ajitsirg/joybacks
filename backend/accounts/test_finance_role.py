from django.contrib.auth.models import Group
from django.test import TestCase

from accounts.models import Permission, Role
from accounts.rbac_seed import FINANCE_PERM_CODES, FINANCE_ROLE_NAME, ensure_finance_manager_role


class FinanceManagerRoleTests(TestCase):
    def test_finance_manager_has_fund_transfer_permission(self):
        for code, name, module in (
            ("wallets.transfer", "Transfer Funds", "wallets"),
            ("fund.view", "View Fund", "fund"),
            ("fund.transfer", "Transfer Funds", "fund"),
            ("users.view", "View Users", "users"),
            ("wallets.view", "View Wallets", "wallets"),
            ("income.view", "View Income", "income"),
            ("reports.view", "View Reports", "reports"),
            ("withdrawals.view", "View Withdrawals", "withdrawals"),
            ("withdrawals.approve", "Approve Withdrawals", "withdrawals"),
            ("deposits.view", "View Deposits", "deposits"),
            ("deposits.approve", "Approve Deposits", "deposits"),
        ):
            Permission.objects.update_or_create(code=code, defaults={"name": name, "module": module})

        role = ensure_finance_manager_role()
        self.assertEqual(role.name, FINANCE_ROLE_NAME)
        codes = set(role.permissions.values_list("code", flat=True))
        self.assertTrue({"fund.transfer", "wallets.transfer", "fund.view"}.issubset(codes))
        self.assertEqual(codes, set(FINANCE_PERM_CODES))
        self.assertTrue(Group.objects.filter(name=FINANCE_ROLE_NAME).exists())
        group = Group.objects.get(name=FINANCE_ROLE_NAME)
        self.assertTrue(group.permissions.filter(codename="can_fund_transfer").exists())
        self.assertTrue(Role.objects.get(name=FINANCE_ROLE_NAME).permissions.filter(code="fund.transfer").exists())
