"""ROI-on-ROI calculation tests."""

from decimal import Decimal

from django.test import TestCase

from investments.calc import base_roi_amount, roi_level_income, roi_rate_percent
from investments.constants import INVESTMENT_PRINCIPAL, MONTHLY_RETURN_AMOUNT


class RoiOnRoiCalcTests(TestCase):
    def test_base_roi_one_percent(self):
        self.assertEqual(base_roi_amount(INVESTMENT_PRINCIPAL), MONTHLY_RETURN_AMOUNT)

    def test_level_income_on_base_roi_not_investment(self):
        base = Decimal("2200.00")
        # Level 1: 2200 × 5% = 110 (NOT 220000 × 5%)
        self.assertEqual(roi_level_income(base_roi=base, network_level=1), Decimal("110.00"))
        self.assertEqual(roi_level_income(base_roi=base, network_level=2), Decimal("55.00"))
        self.assertEqual(roi_level_income(base_roi=base, network_level=10), Decimal("5.50"))

    def test_ten_levels_total_330(self):
        base = Decimal("2200.00")
        total = sum(roi_level_income(base_roi=base, network_level=n) for n in range(1, 11))
        self.assertEqual(total, Decimal("330.00"))

    def test_roi_rate_default(self):
        self.assertEqual(roi_rate_percent(), Decimal("1.0000"))
