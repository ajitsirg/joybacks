"""Single source check: every income stream uses the official rupee table."""

from decimal import Decimal

from django.test import TestCase

from associates.rewards import compute_reward_level
from commissions.constants import DEFAULT_LEVEL_PERCENTS, FARHOUSE_SALE_AMOUNT
from configuration.rewards import REWARD_SLABS
from investments.calc import roi_level_income
from investments.constants import DEFAULT_GROWTH_PERCENTS, MONTHLY_RETURN_AMOUNT


class OfficialAmountTableTests(TestCase):
    def test_sale_level_income_on_220000(self):
        expected = {
            1: Decimal("11000.00"),
            2: Decimal("5500.00"),
            3: Decimal("4400.00"),
            4: Decimal("2200.00"),
            5: Decimal("1100.00"),
        }
        for level, pct in DEFAULT_LEVEL_PERCENTS:
            got = (FARHOUSE_SALE_AMOUNT * pct / Decimal("100")).quantize(Decimal("0.01"))
            self.assertEqual(got, expected[level], f"sale L{level}")

    def test_roi_on_roi_on_2200_base_not_on_principal(self):
        expected = {
            1: Decimal("110.00"),
            2: Decimal("55.00"),
            3: Decimal("44.00"),
            4: Decimal("44.00"),
            5: Decimal("22.00"),
            6: Decimal("22.00"),
            7: Decimal("11.00"),
            8: Decimal("11.00"),
            9: Decimal("5.50"),
            10: Decimal("5.50"),
        }
        total = Decimal("0")
        for level, _pct in DEFAULT_GROWTH_PERCENTS:
            got = roi_level_income(base_roi=MONTHLY_RETURN_AMOUNT, network_level=level)
            self.assertEqual(got, expected[level], f"ROI L{level}")
            self.assertNotEqual(got, (FARHOUSE_SALE_AMOUNT * _pct / Decimal("100")).quantize(Decimal("0.01")))
            total += got
        self.assertEqual(total, Decimal("330.00"))

    def test_reward_milestones_and_screenshot_case(self):
        official = {
            1: Decimal("75000"),
            2: Decimal("150000"),
            3: Decimal("400000"),
            4: Decimal("1000000"),
            5: Decimal("3000000"),
            6: Decimal("6000000"),
            7: Decimal("10000000"),
            8: Decimal("25000000"),
            9: Decimal("50000000"),
        }
        self.assertEqual(len(REWARD_SLABS), 9)
        for slab in REWARD_SLABS:
            self.assertEqual(slab.reward, official[slab.level], f"M{slab.level}")
        level, _ = compute_reward_level(
            total_business=Decimal("14740000"),
            leg1=Decimal("10120000"),
            leg2=Decimal("2640000"),
            leg3=Decimal("1980000"),
        )
        self.assertEqual(level, 2)
        level4, _ = compute_reward_level(
            total_business=Decimal("14740000"),
            leg1=Decimal("10120000"),
            leg2=Decimal("3000000"),
            leg3=Decimal("1980000"),
        )
        self.assertEqual(level4, 2)
