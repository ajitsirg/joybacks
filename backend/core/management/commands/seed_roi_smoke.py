"""Isolated ROI-on-ROI smoke fixture (JOYSMOKEROI* IDs only).

Creates a 10-level upline chain + buyer, one ₹2.2L investment, verifies:
  Base ROI = ₹2,200
  Level total = ₹330 (110 + 55 + … + 5.50)

Safe for local / isolated DB only. Purge with --purge.

  cd backend && .venv/bin/python manage.py seed_roi_smoke
  cd backend && .venv/bin/python manage.py seed_roi_smoke --purge
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from associates.models import Associate
from commissions.constants import FARHOUSE_SALE_AMOUNT
from commissions.models import CommissionEntry
from configuration.models import LevelIncomePlan, LevelIncomeSlab, PerformanceIncomePlan, PerformanceIncomeSlab
from genealogy.services import GenealogyService
from investments.calc import roi_level_income
from investments.constants import MONTHLY_RETURN_AMOUNT
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()

PREFIX = "JOYSMOKEROI"
BUYER_ID = f"{PREFIX}BUY"
PASSWORD = "smoke1234"
SALE = FARHOUSE_SALE_AMOUNT

LEVEL_AMOUNTS = [
    Decimal("110.00"),
    Decimal("55.00"),
    Decimal("44.00"),
    Decimal("44.00"),
    Decimal("22.00"),
    Decimal("22.00"),
    Decimal("11.00"),
    Decimal("11.00"),
    Decimal("5.50"),
    Decimal("5.50"),
]


def _ensure_plans() -> None:
    level_plan, _ = LevelIncomePlan.objects.get_or_create(
        code="direct-level",
        defaults={"name": "Direct Level Income", "max_levels": 5, "is_active": True},
    )
    level_plan.max_levels = 5
    level_plan.is_active = True
    level_plan.save()
    for level, pct in [(1, "5"), (2, "2.5"), (3, "2"), (4, "1"), (5, "0.5")]:
        LevelIncomeSlab.objects.update_or_create(
            plan=level_plan,
            level=level,
            defaults={"percent": Decimal(pct), "is_active": True},
        )
    perf, _ = PerformanceIncomePlan.objects.get_or_create(
        code="performance-10",
        defaults={"name": "Performance Income", "max_levels": 10, "is_active": True},
    )
    perf.max_levels = 10
    perf.is_active = True
    perf.save()
    for level, pct, directs in [
        (1, "5", 1),
        (2, "2.5", 2),
        (3, "2", 3),
        (4, "2", 4),
        (5, "1", 5),
        (6, "1", 6),
        (7, "0.5", 7),
        (8, "0.5", 8),
        (9, "0.25", 9),
        (10, "0.25", 10),
    ]:
        PerformanceIncomeSlab.objects.update_or_create(
            plan=perf,
            level=level,
            defaults={
                "percent": Decimal(pct),
                "required_directs": directs,
                "is_active": True,
            },
        )


def _purge_smoke() -> int:
    from associates.purge import archive_associate

    qs = Associate.all_objects.filter(associate_id__startswith=PREFIX).order_by("-created_at")
    n = 0
    for assoc in qs:
        try:
            archive_associate(associate=assoc, hard=True)
            n += 1
        except Exception:
            User.objects.filter(associate__associate_id=assoc.associate_id).delete()
            assoc.delete(force=True)
            n += 1
    return n


class Command(BaseCommand):
    help = "Seed isolated ROI-on-ROI smoke data (JOYSMOKEROI* only)"

    def add_arguments(self, parser):
        parser.add_argument("--purge", action="store_true", help="Remove all JOYSMOKEROI* rows")
        parser.add_argument("--json", action="store_true", help="Print credentials + verification JSON")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["purge"]:
            removed = _purge_smoke()
            self.stdout.write(self.style.SUCCESS(f"Purged {removed} smoke associate(s)"))
            return

        _purge_smoke()
        call_command("seed_joyclub", verbosity=0)

        _ensure_plans()

        from configuration.models import CompanySettings

        company = CompanySettings.objects.order_by("id").first()
        if company:
            company.show_income_section = True
            company.show_income_referral = True
            company.show_income_sp_profit = True
            company.save(
                update_fields=[
                    "show_income_section",
                    "show_income_referral",
                    "show_income_sp_profit",
                    "updated_at",
                ]
            )

        chain: list[Associate] = []
        for i in range(11):
            aid = f"{PREFIX}{i:02d}"
            sponsor = chain[-1] if chain else None
            user = User.objects.create_user(
                username=aid.lower(),
                email=f"{aid.lower()}@smoke.test",
                password=PASSWORD,
            )
            assoc = Associate.objects.create(
                user=user,
                associate_id=aid,
                referral_code=f"R{aid}"[:20],
                mobile=f"99{i:08d}"[:10],
                sponsor=sponsor,
                status=Associate.Status.ACTIVE,
                join_amount=SALE,
                personal_business=SALE,
                total_business=SALE,
            )
            if sponsor is None:
                GenealogyService.ensure_root(assoc)
            else:
                GenealogyService.attach_under_sponsor(assoc, sponsor, force=True)
            WalletService.ensure_wallets(assoc)
            chain.append(assoc)

        buyer_user = User.objects.create_user(
            username=BUYER_ID.lower(),
            email=f"{BUYER_ID.lower()}@smoke.test",
            password=PASSWORD,
        )
        buyer = Associate.objects.create(
            user=buyer_user,
            associate_id=BUYER_ID,
            referral_code="RSMKBUY",
            mobile="9900000099",
            sponsor=chain[-1],
            status=Associate.Status.INACTIVE,
            join_amount=Decimal("0"),
            personal_business=Decimal("0"),
            total_business=Decimal("0"),
        )
        GenealogyService.attach_under_sponsor(buyer, chain[-1], force=True)
        WalletService.ensure_wallets(buyer)

        apply_investment_business(associate=buyer, amount=SALE, reference="SMOKE-ROI-INV-1")

        buyer_roi = Wallet.objects.get(associate=buyer, wallet_type=Wallet.WalletType.ROI)
        buyer_income = Wallet.objects.get(associate=buyer, wallet_type=Wallet.WalletType.INCOME)
        upline_entries = CommissionEntry.objects.filter(
            source_associate=buyer,
            wallet_type=Wallet.WalletType.ROI,
            level__gte=1,
        ).exclude(status=CommissionEntry.Status.VOIDED).order_by("level")

        levels = []
        for depth in range(1, 11):
            expected = roi_level_income(base_roi=MONTHLY_RETURN_AMOUNT, network_level=depth)
            row = upline_entries.filter(level=depth).first()
            actual = Decimal(row.amount) if row else Decimal("0")
            levels.append(
                {
                    "level": depth,
                    "expected": str(expected),
                    "actual": str(actual),
                    "ok": actual == expected,
                    "beneficiary": row.beneficiary.associate_id if row else None,
                }
            )

        total_upline = sum(Decimal(x["actual"]) for x in levels)
        ok = (
            buyer_roi.balance == Decimal("0.00")
            and buyer_income.balance == Decimal("0.00")
            and upline_entries.count() == 10
            and total_upline == Decimal("330.00")
            and all(x["ok"] for x in levels)
        )

        report = {
            "ok": ok,
            "base_roi": str(MONTHLY_RETURN_AMOUNT),
            "buyer_id": BUYER_ID,
            "buyer_roi_balance": str(buyer_roi.balance),
            "buyer_income_balance": str(buyer_income.balance),
            "upline_total": str(total_upline),
            "expected_upline_total": "330.00",
            "levels": levels,
            "logins": {
                "l1_upline": {"id": chain[10].associate_id, "password": PASSWORD, "expected_level_income": "110.00"},
                "buyer": {"id": BUYER_ID, "password": PASSWORD, "expected_base_roi": "0.00"},
                "root_l10": {"id": chain[0].associate_id, "password": PASSWORD, "expected_level_income": "5.50"},
            },
        }

        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("ROI smoke fixture ready"))
            for row in levels:
                mark = "✓" if row["ok"] else "✗"
                self.stdout.write(
                    f"  {mark} L{row['level']}: {row['actual']} (expected {row['expected']}) → {row['beneficiary']}"
                )
            self.stdout.write(f"  Buyer wallets (must be ₹0 — no ₹2,200 payout): ROI ₹{buyer_roi.balance} Income ₹{buyer_income.balance}")
            self.stdout.write(f"  Upline total: ₹{total_upline} (expected ₹330.00)")
            self.stdout.write(f"  Login L1 upline: {chain[10].associate_id} / {PASSWORD}")

        if not ok:
            raise SystemExit(1)
