"""10% admin charge on sale / ROI / reward — staff see it, associates do not."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from associates.models import Associate
from commissions.charges import net_after_charge
from commissions.constants import FARHOUSE_SALE_AMOUNT
from commissions.models import AdminCharge
from genealogy.services import GenealogyService
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()
SALE = FARHOUSE_SALE_AMOUNT


class AdminChargeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _user(self, username: str, *, staff: bool = False) -> User:
        return User.objects.create_user(
            username=username,
            password="x",
            email=f"{username}@t.test",
            is_staff=staff,
        )

    def _assoc(self, code: str, *, sponsor: Associate | None = None) -> Associate:
        user = self._user(code.lower())
        digits = "".join(ch for ch in code if ch.isdigit()) or "1"
        a = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}"[:20],
            mobile=(digits * 4)[:10],
            sponsor=sponsor,
            status=Associate.Status.ACTIVE,
            join_amount=SALE,
            personal_business=SALE,
            total_business=SALE,
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        WalletService.ensure_wallets(a)
        return a

    def test_sale_income_credits_net_and_records_charge(self):
        root = self._assoc("JOYCHG001")
        buyer = self._assoc("JOYCHG002", sponsor=root)
        buyer.status = Associate.Status.INACTIVE
        buyer.save(update_fields=["status"])
        apply_investment_business(associate=buyer, amount=SALE, reference="CHG-SALE")
        income = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.INCOME)
        self.assertEqual(income.balance, net_after_charge(Decimal("11000.00")))
        row = AdminCharge.objects.get(associate=root, kind=AdminCharge.Kind.INCOME)
        self.assertEqual(row.gross_amount, Decimal("11000.00"))
        self.assertEqual(row.charge_percent, Decimal("10.00"))
        self.assertEqual(row.charge_amount, Decimal("1100.00"))
        self.assertEqual(row.net_amount, Decimal("9900.00"))

    def test_associate_cannot_list_admin_charges(self):
        root = self._assoc("JOYCHG003")
        self.client.force_authenticate(user=root.user)
        resp = self.client.get("/api/v1/commissions/admin-charges/")
        self.assertEqual(resp.status_code, 403)

    def test_staff_lists_admin_charges(self):
        root = self._assoc("JOYCHG004")
        buyer = self._assoc("JOYCHG005", sponsor=root)
        buyer.status = Associate.Status.INACTIVE
        buyer.save(update_fields=["status"])
        apply_investment_business(associate=buyer, amount=SALE, reference="CHG-STAFF")
        staff = self._user("adminchg", staff=True)
        self.client.force_authenticate(user=staff)
        resp = self.client.get("/api/v1/commissions/admin-charges/")
        self.assertEqual(resp.status_code, 200)
        rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        self.assertTrue(any(r["associate_id"] == root.associate_id for r in rows))
        self.assertTrue(any(Decimal(str(r["charge_amount"])) == Decimal("1100.00") for r in rows))
