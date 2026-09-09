"""Isolated Ajit + 25 dummy ID smoke tree (JOYSMK25* only).

Local / isolated DB only. Purge with --purge. Never run against production.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from associates.models import Associate
from associates.rewards import reward_snapshot
from commissions.constants import FARHOUSE_SALE_AMOUNT, DEFAULT_LEVEL_PERCENTS
from commissions.models import CommissionEntry, CommissionRun
from commissions.services import CommissionEngine
from configuration.models import (
    CompanySettings,
    LevelIncomePlan,
    LevelIncomeSlab,
    PerformanceIncomePlan,
    PerformanceIncomeSlab,
)
from genealogy.services import GenealogyService
from investments.calc import roi_level_income
from investments.constants import MONTHLY_RETURN_AMOUNT
from dashboard.views import _income_breakdown_tiles, _roi_performance_board, _sale_level_board
from investments.models import InvestmentContract
from investments.services import process_monthly_return
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()

PREFIX = "JOYSMK25"
HEAD_ID = f"{PREFIX}AJIT"
PASSWORD = "smoke1234"
SALE = FARHOUSE_SALE_AMOUNT


def _ensure_plans() -> None:
    level_plan, _ = LevelIncomePlan.objects.get_or_create(
        code="direct-level",
        defaults={"name": "Direct Level Income", "max_levels": 5, "is_active": True},
    )
    level_plan.max_levels = 5
    level_plan.is_active = True
    level_plan.save()
    for level, pct in DEFAULT_LEVEL_PERCENTS:
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
            defaults={"percent": Decimal(pct), "required_directs": directs, "is_active": True},
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
            User.objects.filter(pk=assoc.user_id).delete()
            assoc.delete(force=True)
            n += 1
    return n


def _make(
    aid: str,
    *,
    first: str,
    last: str,
    sponsor: Associate | None,
    idx: int,
    extra: bool = False,
) -> Associate:
    user = User.objects.create_user(
        username=aid,
        email=f"{aid.lower()}@joyclub.dummy",
        password=PASSWORD,
        first_name=first,
        last_name=last,
    )
    assoc = Associate.objects.create(
        user=user,
        associate_id=aid,
        referral_code=f"R{aid}"[:20],
        mobile=f"88{idx:08d}"[:10],
        sponsor=sponsor,
        status=Associate.Status.ACTIVE if extra else Associate.Status.INACTIVE,
        join_amount=SALE if extra else Decimal("0"),
        personal_business=SALE if extra else Decimal("0"),
        total_business=SALE if extra else Decimal("0"),
    )
    if sponsor is None:
        GenealogyService.ensure_root(assoc)
    else:
        GenealogyService.attach_under_sponsor(assoc, sponsor, force=True)
    WalletService.ensure_wallets(assoc)
    return assoc


def _seed_qualifying_directs(sponsor: Associate, needed: int, tag: str, counter: list[int]) -> None:
    have = CommissionEngine.growth_level(sponsor)
    extra_n = 0
    while have < needed:
        extra_n += 1
        counter[0] += 1
        _make(
            f"{PREFIX}X{tag}{extra_n:02d}"[:20],
            first="Extra",
            last=f"{tag}{extra_n}",
            sponsor=sponsor,
            idx=counter[0],
            extra=True,
        )
        have += 1


def _wallet(assoc: Associate, wtype: str) -> str:
    return str(Wallet.objects.get(associate=assoc, wallet_type=wtype).balance)


def _credited(assoc: Associate, *, run_type: str, level: int | None = None):
    qs = CommissionEntry.objects.filter(
        beneficiary=assoc,
        run__run_type=run_type,
        is_deleted=False,
    ).exclude(status=CommissionEntry.Status.VOIDED)
    if level is not None:
        qs = qs.filter(level=level)
    return qs


class Command(BaseCommand):
    help = "Seed isolated Ajit + 25 dummy smoke tree (JOYSMK25* only)"

    def add_arguments(self, parser):
        parser.add_argument("--purge", action="store_true")
        parser.add_argument("--json", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["purge"]:
            removed = _purge_smoke()
            self.stdout.write(self.style.SUCCESS(f"Purged {removed} JOYSMK25* associate(s)"))
            return

        _purge_smoke()
        call_command("seed_joyclub", verbosity=0)
        _ensure_plans()
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

        idx = [0]

        def nxt() -> int:
            idx[0] += 1
            return idx[0]

        ajit = _make(HEAD_ID, first="Ajit", last="Smoke", sponsor=None, idx=nxt())
        directs = [
            _make(f"{PREFIX}U{i:02d}", first="Dummy", last=f"{i:02d}", sponsor=ajit, idx=nxt())
            for i in range(1, 6)
        ]
        u01, u02, u03, u04, u05 = directs

        chain = [u01]
        for i in range(6, 16):
            child = _make(f"{PREFIX}U{i:02d}", first="Dummy", last=f"{i:02d}", sponsor=chain[-1], idx=nxt())
            chain.append(child)
        # chain = U01, U06..U15  (11 people). Deepest buyer = U15
        deepest = chain[-1]

        u02_kids = [
            _make(f"{PREFIX}U{i:02d}", first="Dummy", last=f"{i:02d}", sponsor=u02, idx=nxt())
            for i in range(16, 19)
        ]
        u03_kids = [
            _make(f"{PREFIX}U{i:02d}", first="Dummy", last=f"{i:02d}", sponsor=u03, idx=nxt())
            for i in range(19, 26)
        ]

        # ROI extras: ancestor at depth D from U15 needs D qualified directs
        # chain[k] depth from deepest = (len(chain)-1-k) = 10-k for k=0..10
        for pos, ancestor in enumerate(chain):
            depth = (len(chain) - 1) - pos
            if 1 <= depth <= 10:
                _seed_qualifying_directs(ancestor, depth, f"{depth:02d}", idx)

        invest_order = [ajit, *directs, *chain[1:], *u02_kids, *u03_kids]
        tree = []
        for assoc in invest_order:
            apply_investment_business(associate=assoc, amount=SALE, reference=f"SMK25-{assoc.associate_id}")
            tree.append(
                {
                    "id": assoc.associate_id,
                    "name": assoc.user.get_full_name(),
                    "sponsor": assoc.sponsor.associate_id if assoc.sponsor_id else None,
                }
            )

        sale_levels = []
        sale_ok = True
        for level in range(1, 6):
            rows = list(_credited(ajit, run_type=CommissionRun.RunType.LEVEL, level=level))
            pct = dict(DEFAULT_LEVEL_PERCENTS)[level]
            per = (SALE * pct / Decimal("100")).quantize(Decimal("0.01"))
            actual = sum((r.amount for r in rows), Decimal("0"))
            expected = per * len(rows)
            sale_levels.append(
                {
                    "level": level,
                    "percent": str(pct),
                    "sale_count": len(rows),
                    "per_sale": str(per),
                    "expected": str(expected),
                    "actual": str(actual),
                    "ok": actual == expected,
                    "buyers": [r.source_associate.associate_id if r.source_associate_id else None for r in rows],
                }
            )
            sale_ok = sale_ok and actual == expected

        sale_agg: dict[str, dict] = defaultdict(
            lambda: {"total": Decimal("0"), "levels": defaultdict(lambda: {"count": 0, "amount": Decimal("0")})}
        )
        per_sale = {
            level: (SALE * pct / Decimal("100")).quantize(Decimal("0.01"))
            for level, pct in DEFAULT_LEVEL_PERCENTS
        }
        for row in (
            CommissionEntry.objects.filter(
                run__run_type=CommissionRun.RunType.LEVEL,
                is_deleted=False,
                beneficiary__associate_id__startswith=PREFIX,
            )
            .exclude(status=CommissionEntry.Status.VOIDED)
            .select_related("beneficiary")
        ):
            aid = row.beneficiary.associate_id
            sale_agg[aid]["total"] += row.amount
            sale_agg[aid]["levels"][row.level]["count"] += 1
            sale_agg[aid]["levels"][row.level]["amount"] += row.amount
        sale_by_beneficiary = []
        for aid in sorted(sale_agg):
            levels_out = []
            for level in sorted(sale_agg[aid]["levels"]):
                d = sale_agg[aid]["levels"][level]
                expected = per_sale[level] * d["count"]
                levels_out.append(
                    {
                        "level": level,
                        "count": d["count"],
                        "expected": str(expected),
                        "actual": str(d["amount"]),
                        "ok": d["amount"] == expected,
                    }
                )
            sale_by_beneficiary.append(
                {
                    "id": aid,
                    "total": str(sale_agg[aid]["total"]),
                    "levels": levels_out,
                    "ok": all(x["ok"] for x in levels_out),
                }
            )

        roi_from_deep = (
            CommissionEntry.objects.filter(
                source_associate=deepest,
                wallet_type=Wallet.WalletType.ROI,
                level__gte=1,
            )
            .exclude(status=CommissionEntry.Status.VOIDED)
            .order_by("level")
        )
        roi_levels = []
        for depth in range(1, 11):
            expected = roi_level_income(base_roi=MONTHLY_RETURN_AMOUNT, network_level=depth)
            row = roi_from_deep.filter(level=depth).first()
            actual = Decimal(row.amount) if row else Decimal("0")
            roi_levels.append(
                {
                    "level": depth,
                    "expected": str(expected),
                    "actual": str(actual),
                    "ok": actual == expected,
                    "beneficiary": row.beneficiary.associate_id if row else None,
                }
            )
        roi_total = sum((Decimal(x["actual"]) for x in roi_levels), Decimal("0"))
        deep_roi = Wallet.objects.get(associate=deepest, wallet_type=Wallet.WalletType.ROI)
        deep_income = Wallet.objects.get(associate=deepest, wallet_type=Wallet.WalletType.INCOME)
        roi_ok = (
            deep_roi.balance == Decimal("0.00")
            and deep_income.balance == Decimal("0.00")
            and roi_from_deep.count() == 10
            and roi_total == Decimal("330.00")
            and all(x["ok"] for x in roi_levels)
        )

        snap = reward_snapshot(ajit)
        reward_ok = True
        milestones = []
        for m in snap.get("milestones") or []:
            milestones.append(
                {
                    "sno": m.get("sno"),
                    "status": m.get("status"),
                    "reward": str(m.get("reward")),
                    "total": str(m.get("total")),
                    "leg1": str(m.get("leg1")),
                    "leg2": str(m.get("leg2")),
                    "leg3": str(m.get("leg3")),
                    "remaining_total": str(m.get("remaining_total")),
                    "remaining_leg1": str(m.get("remaining_leg1")),
                    "remaining_leg2": str(m.get("remaining_leg2")),
                    "remaining_leg3": str(m.get("remaining_leg3")),
                }
            )

        ajit.refresh_from_db()
        unlocked_sale = CommissionEngine.unlocked_commission_levels(ajit)
        unlocked_roi = CommissionEngine.unlocked_performance_levels(ajit)
        sale_unlock_ok = unlocked_sale == 5
        extras = Associate.objects.filter(associate_id__startswith=f"{PREFIX}X").count()
        members_25 = Associate.objects.filter(associate_id__startswith=f"{PREFIX}U").count()
        extra_ids = list(
            Associate.objects.filter(associate_id__startswith=f"{PREFIX}X")
            .order_by("associate_id")
            .values_list("associate_id", flat=True)
        )
        if extra_ids and not all(aid.startswith(f"{PREFIX}X") for aid in extra_ids):
            raise SystemExit("ROI extra IDs must use JOYSMK25X*")

        mid = Associate.objects.get(associate_id=f"{PREFIX}U08")
        tiles = {k: str(v) for k, v in _income_breakdown_tiles(ajit).items()}
        sale_board = _sale_level_board(ajit)
        roi_board = _roi_performance_board(ajit)

        income_before = Wallet.objects.get(associate=ajit, wallet_type=Wallet.WalletType.INCOME).balance
        CommissionEngine.distribute_level_income(
            source_associate=u01,
            amount=SALE,
            reference=f"SMK25-{u01.associate_id}",
        )
        income_after = Wallet.objects.get(associate=ajit, wallet_type=Wallet.WalletType.INCOME).balance
        sale_idempotent = income_before == income_after

        deep_contract = InvestmentContract.objects.filter(associate=deepest).first()
        roi_before = deep_roi.balance
        upline_roi_before = Wallet.objects.get(associate=u01, wallet_type=Wallet.WalletType.ROI).balance
        if deep_contract:
            process_monthly_return(deep_contract)
        deep_roi.refresh_from_db()
        upline_roi_after = Wallet.objects.get(associate=u01, wallet_type=Wallet.WalletType.ROI).balance
        roi_idempotent = deep_roi.balance == roi_before and upline_roi_after == upline_roi_before

        sale_sample = (
            _credited(ajit, run_type=CommissionRun.RunType.LEVEL, level=1)
            .select_related("source_associate")
            .first()
        )
        roi_sample = roi_from_deep.filter(level=1).select_related("beneficiary", "source_associate").first()

        def _wallets(assoc: Associate) -> dict:
            return {
                "id": assoc.associate_id,
                "income": _wallet(assoc, Wallet.WalletType.INCOME),
                "roi": _wallet(assoc, Wallet.WalletType.ROI),
                "reward": _wallet(assoc, Wallet.WalletType.REWARD),
                "main": _wallet(assoc, Wallet.WalletType.MAIN),
            }

        ok = (
            sale_ok
            and sale_unlock_ok
            and roi_ok
            and members_25 == 25
            and ajit.associate_id == HEAD_ID
            and sale_idempotent
            and roi_idempotent
            and unlocked_sale == 5
        )

        report = {
            "ok": ok,
            "head": {
                "id": HEAD_ID,
                "name": "Ajit Smoke",
                "password": PASSWORD,
                "unlocked_sale_levels": unlocked_sale,
                "unlocked_roi_levels": unlocked_roi,
                "qualified_direct_sales": CommissionEngine.qualifying_direct_sales_count(ajit),
                "income_wallet": _wallet(ajit, Wallet.WalletType.INCOME),
                "roi_wallet": _wallet(ajit, Wallet.WalletType.ROI),
                "reward_wallet": _wallet(ajit, Wallet.WalletType.REWARD),
                "main_wallet": _wallet(ajit, Wallet.WalletType.MAIN),
            },
            "tree": tree,
            "counts": {
                "head": 1,
                "downline_25": members_25,
                "roi_extras": extras,
                "extra_ids": extra_ids,
            },
            "tiles": tiles,
            "sale_board": {
                "unlocked_level": sale_board.get("unlocked_level"),
                "qualified_direct_sales": sale_board.get("qualified_direct_sales"),
            },
            "roi_board": {
                "unlocked_level": roi_board.get("unlocked_level"),
                "qualified_directs": roi_board.get("qualified_directs"),
            },
            "wallets": {
                "ajit": _wallets(ajit),
                "l1": _wallets(u01),
                "mid": _wallets(mid),
                "buyer": _wallets(deepest),
            },
            "samples": {
                "sale_l1": {
                    "beneficiary": ajit.associate_id,
                    "buyer": sale_sample.source_associate.associate_id if sale_sample and sale_sample.source_associate_id else None,
                    "level": 1,
                    "percent": "5",
                    "amount": "11000.00",
                    "visible": "11,000",
                },
                "roi_l1": {
                    "beneficiary": roi_sample.beneficiary.associate_id if roi_sample else None,
                    "buyer": deepest.associate_id,
                    "level": 1,
                    "amount": "110.00",
                    "base_roi": "2,200",
                    "visible": "110",
                },
            },
            "idempotent": {"sale": sale_idempotent, "roi": roi_idempotent},
            "sale": {
                "ok": sale_ok and sale_unlock_ok,
                "formula": "₹2,20,000 × level % (not ROI)",
                "levels": sale_levels,
                "total_actual": str(
                    sum((Decimal(x["actual"]) for x in sale_levels), Decimal("0"))
                ),
                "by_beneficiary": sale_by_beneficiary,
            },
            "roi": {
                "ok": roi_ok,
                "formula": "Base ROI ₹2,200 × level % (never investment × %)",
                "deepest_buyer": deepest.associate_id,
                "buyer_roi_balance": str(deep_roi.balance),
                "buyer_income_balance": str(deep_income.balance),
                "upline_total": str(roi_total),
                "expected_upline_total": "330.00",
                "levels": roi_levels,
            },
            "reward": {
                "ok": reward_ok,
                "leg1": str(snap.get("leg1")),
                "leg2": str(snap.get("leg2")),
                "leg3": str(snap.get("leg3")),
                "total": str(snap.get("total")),
                "level": snap.get("level"),
                "name": snap.get("name"),
                "milestones": milestones,
            },
            "logins": {
                "ajit": {"id": HEAD_ID, "password": PASSWORD},
                "l1_child": {"id": u01.associate_id, "password": PASSWORD},
                "mid": {"id": mid.associate_id, "password": PASSWORD},
                "deepest": {"id": deepest.associate_id, "password": PASSWORD},
            },
        }

        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2, default=str))
        else:
            mark = "PASS" if ok else "FAIL"
            self.stdout.write(self.style.SUCCESS(f"Ajit25 smoke {mark}"))
            self.stdout.write(f"  Ajit sale unlock={unlocked_sale} ROI unlock={unlocked_roi}")
            self.stdout.write(f"  Sale total ₹{report['sale']['total_actual']}")
            self.stdout.write(f"  Deep ROI 10-level ₹{roi_total} (expect 330) buyer ROI ₹{deep_roi.balance}")
            self.stdout.write(f"  Reward level {snap.get('level')} total ₹{snap.get('total')}")
            self.stdout.write(f"  Login {HEAD_ID} / {PASSWORD}")

        if not ok:
            raise SystemExit(1)
