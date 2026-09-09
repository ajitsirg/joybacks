from __future__ import annotations

from decimal import Decimal

from django.db.models import Case, Count, DecimalField, F, Sum, When
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from associates.models import Associate
from commissions.models import CommissionEntry, CommissionRun
from genealogy.models import GenealogyClosure
from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
from wallets.models import Wallet
from wallets.visibility import visible_wallet_balance


def _associate_scope_ids(user):
    """None = staff (all). Else associate PKs for self + downline."""
    if user.is_staff or user.is_superuser:
        return None
    me = getattr(user, "associate", None)
    if not me:
        return []
    ids = list(
        GenealogyClosure.objects.filter(ancestor=me).values_list("descendant_id", flat=True)
    )
    if me.pk not in ids:
        ids.append(me.pk)
    # Pending directs may not be in closure yet
    for pk in Associate.objects.filter(sponsor=me, is_deleted=False).values_list("id", flat=True):
        if pk not in ids:
            ids.append(pk)
    return ids


def _wallet_map(associate: Associate | None) -> dict[str, Decimal]:
    out = {t.value: Decimal("0") for t in Wallet.WalletType}
    if not associate:
        return out
    for w in Wallet.objects.filter(associate=associate, is_deleted=False):
        out[w.wallet_type] = visible_wallet_balance(w)
    return out


def _credited_entries(associate: Associate | None):
    qs = CommissionEntry.objects.filter(is_deleted=False).exclude(status=CommissionEntry.Status.VOIDED)
    if associate:
        qs = qs.filter(beneficiary=associate)
    return qs


def _sum_amount(qs) -> Decimal:
    return qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def _sum_net(qs) -> Decimal:
    """Associate-facing totals: net after admin charge (legacy rows fall back to amount)."""
    expr = Case(
        When(net_amount__gt=0, then=F("net_amount")),
        default=F("amount"),
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )
    return qs.aggregate(total=Sum(expr))["total"] or Decimal("0")


def _income_breakdown_tiles(associate: Associate | None) -> dict[str, Decimal]:
    """
    Board tiles use real payout streams:
    - Referral = sale level 1
    - Level = sale levels 2+
    - S.P. / ROI = ROI-on-ROI (performance % on base ROI)
    - Reward = reward milestone cash
    """
    empty = {
        "referral_income": Decimal("0"),
        "level_income": Decimal("0"),
        "sp_income": Decimal("0"),
        "roi_income": Decimal("0"),
        "reward_income": Decimal("0"),
    }
    if not associate:
        return empty
    qs = _credited_entries(associate)
    sale = qs.filter(run__run_type=CommissionRun.RunType.LEVEL)
    roi = qs.filter(run__run_type=CommissionRun.RunType.ROI)
    reward = qs.filter(run__run_type=CommissionRun.RunType.REWARD)
    return {
        "referral_income": _sum_net(sale.filter(level=1)),
        "level_income": _sum_net(sale.filter(level__gte=2)),
        "sp_income": _sum_net(roi.filter(level__gte=1)),
        "roi_income": _sum_net(roi.filter(level__gte=1)),
        "reward_income": _sum_net(reward),
    }


def _today_income(associate: Associate | None) -> Decimal:
    if not associate:
        return Decimal("0")
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return _sum_net(_credited_entries(associate).filter(created_at__gte=start))


def _sale_level_board(associate: Associate | None) -> dict:
    """Associate dashboard: unlocked sale (farmhouse) levels vs direct qualifying sales."""
    from commissions.constants import MAX_COMMISSION_LEVELS
    from commissions.services import CommissionEngine
    from configuration.repository import ConfigRepository

    empty = {
        "qualified_direct_sales": 0,
        "unlocked_level": 0,
        "current_level": 0,
        "total_level_income": "0",
        "today_level_income": "0",
        "slabs": [],
    }
    if not associate:
        return empty
    unlocked = CommissionEngine.unlocked_commission_levels(associate)
    sales = CommissionEngine.qualifying_direct_sales_count(associate)
    qs = _credited_entries(associate).filter(run__run_type=CommissionRun.RunType.LEVEL)
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    max_levels = MAX_COMMISSION_LEVELS
    plan = ConfigRepository.active_level_plan()
    if plan and plan.max_levels:
        max_levels = min(MAX_COMMISSION_LEVELS, int(plan.max_levels))
    slabs = []
    for level in range(1, max_levels + 1):
        slabs.append(
            {
                "level": level,
                "percent": str(ConfigRepository.level_percent(level)),
                "required_sales": level,
                "unlocked": level <= unlocked,
                "earned": str(_sum_net(qs.filter(level=level))),
            }
        )
    return {
        "qualified_direct_sales": sales,
        "unlocked_level": unlocked,
        "current_level": unlocked,
        "total_level_income": str(_sum_net(qs)),
        "today_level_income": str(_sum_net(qs.filter(created_at__gte=start))),
        "slabs": slabs,
    }


def _roi_performance_board(associate: Associate | None) -> dict:
    """Associate dashboard: unlocked ROI-on-ROI levels vs qualified directs."""
    from commissions.services import CommissionEngine
    from configuration.repository import ConfigRepository
    from investments.constants import MAX_GROWTH_LEVELS

    empty = {
        "qualified_directs": 0,
        "unlocked_level": 0,
        "current_level": 0,
        "total_roi_income": "0",
        "today_roi_income": "0",
        "slabs": [],
    }
    if not associate:
        return empty
    unlocked = CommissionEngine.unlocked_performance_levels(associate)
    directs = CommissionEngine.growth_level(associate)
    qs = _credited_entries(associate).filter(run__run_type=CommissionRun.RunType.ROI)
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    slabs = []
    for level in range(1, MAX_GROWTH_LEVELS + 1):
        slabs.append(
            {
                "level": level,
                "percent": str(ConfigRepository.performance_percent(level)),
                "required_directs": ConfigRepository.performance_required_directs(level),
                "unlocked": level <= unlocked,
                "earned": str(_sum_net(qs.filter(level=level))),
            }
        )
    return {
        "qualified_directs": directs,
        "unlocked_level": unlocked,
        "current_level": unlocked,
        "total_roi_income": str(_sum_net(qs)),
        "today_roi_income": str(_sum_net(qs.filter(created_at__gte=start))),
        "slabs": slabs,
    }


def _reward_progress(associate: Associate | None) -> dict:
    """Live 9-level reward totals for the associate dashboard / reward table."""
    empty = {
        "total": Decimal("0"),
        "leg1": Decimal("0"),
        "leg2": Decimal("0"),
        "leg3": Decimal("0"),
        "level": 0,
        "name": "No level",
    }
    if not associate:
        return empty
    from associates.rewards import reward_snapshot

    return reward_snapshot(associate)


class AdminDashboardView(APIView):
    """Live dashboard KPIs — global for staff, team-scoped for associates."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = _associate_scope_ids(request.user)
        is_staff = scope is None
        me = getattr(request.user, "associate", None)

        if scope is not None and not scope:
            return Response({"detail": "Associate profile required"}, status=403)

        assoc_qs = Associate.objects.filter(is_deleted=False)
        wallet_qs = Wallet.objects.filter(is_deleted=False)
        income_qs = CommissionEntry.objects.all()
        deposit_qs = DepositRequest.objects.all()
        withdraw_qs = WithdrawalRequest.objects.all()
        kyc_qs = KYCSubmission.objects.all()

        if scope is not None:
            assoc_qs = assoc_qs.filter(id__in=scope)
            # Own wallets / income; team counts for people KPIs
            wallet_qs = wallet_qs.filter(associate=me) if me else wallet_qs.none()
            income_qs = income_qs.filter(beneficiary=me) if me else income_qs.none()
            deposit_qs = deposit_qs.filter(associate_id__in=scope)
            withdraw_qs = withdraw_qs.filter(associate=me) if me else withdraw_qs.none()
            kyc_qs = kyc_qs.filter(associate_id__in=scope)

        if me and not is_staff:
            me.sync_earning_level(save=True)
            me.refresh_from_db(
                fields=["earning_level", "earning_level_name", "total_business"]
            )

        users_total = assoc_qs.count()
        users_active = assoc_qs.filter(status=Associate.Status.ACTIVE).count()
        pending_kyc = kyc_qs.filter(status=KYCSubmission.Status.PENDING).count()
        pending_deposits = deposit_qs.filter(status=DepositRequest.Status.PENDING).count()
        pending_withdrawals = withdraw_qs.filter(status=WithdrawalRequest.Status.PENDING).count()
        wallet_sum = wallet_qs.aggregate(total=Sum("balance"))["total"] or Decimal("0")
        income_qs = income_qs.exclude(status=CommissionEntry.Status.VOIDED).filter(is_deleted=False)
        income_sum = (
            (income_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0"))
            if is_staff
            else _sum_net(income_qs)
        )
        splits = _income_breakdown_tiles(me if not is_staff else None)

        wallets = _wallet_map(me if not is_staff else None)
        today_income = _today_income(me if not is_staff else None)
        progress = _reward_progress(me if not is_staff else None)
        leg1, leg2, leg3 = progress["leg1"], progress["leg2"], progress["leg3"]
        team_volume = progress["total"]

        since = timezone.now() - timezone.timedelta(days=14)
        trend = (
            deposit_qs.filter(status=DepositRequest.Status.COMPLETED, applied_at__gte=since)
            .annotate(day=TruncDate("applied_at"))
            .values("day")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("day")
        )

        income_breakdown = (
            income_qs.values("wallet_type").annotate(total=Sum("amount")).order_by("-total")
        )

        recent = []
        for d in deposit_qs.select_related("associate").order_by("-created_at")[:8]:
            recent.append(
                {
                    "type": "deposit",
                    "label": f"Deposit {d.status}",
                    "associate_id": d.associate.associate_id,
                    "amount": str(d.amount),
                    "at": d.created_at.isoformat(),
                }
            )
        for w in withdraw_qs.select_related("associate").order_by("-created_at")[:8]:
            recent.append(
                {
                    "type": "withdrawal",
                    "label": f"Withdrawal {w.status}",
                    "associate_id": w.associate.associate_id,
                    "amount": str(w.amount),
                    "at": w.created_at.isoformat(),
                }
            )
        recent.sort(key=lambda x: x["at"], reverse=True)

        payload = {
            "scope": "global" if is_staff else "team",
            "generated_at": timezone.now().isoformat(),
            "kpis": {
                "users_total": users_total,
                "users_active": users_active,
                "pending_kyc": pending_kyc,
                "pending_deposits": pending_deposits,
                "pending_withdrawals": pending_withdrawals,
                "wallet_balance": str(wallet_sum),
                "income_paid": str(income_sum),
                "direct_count": int(me.direct_count) if me and not is_staff else users_total,
                "direct_active_count": int(me.direct_active_count)
                if me and not is_staff
                else users_active,
                "earning_level": int(progress["level"]) if me and not is_staff else None,
                "earning_level_name": (progress["name"] or "") if me and not is_staff else None,
                "reward_level": int(progress["level"]) if me and not is_staff else None,
                "reward_level_name": (progress["name"] or "") if me and not is_staff else None,
                "performance_level": int(me.performance_level or 0) if me and not is_staff else None,
                "performance_level_name": (me.performance_level_name or "") if me and not is_staff else None,
                "personal_business": str(me.personal_business) if me and not is_staff else None,
                "total_business": str(me.total_business) if me and not is_staff else None,
                # Associate home metrics (ATM-style board)
                "today_income": str(today_income if not is_staff else Decimal("0")),
                "total_income": str(income_sum if not is_staff else income_sum),
                "referral_income": str(splits["referral_income"]),
                "sp_income": str(splits["sp_income"]),
                "level_income": str(splits["level_income"]),
                "reward_income": str(
                    wallets.get("reward", Decimal("0"))
                    if not is_staff
                    else splits["reward_income"]
                ),
                "roi_income": str(splits["roi_income"]),
                "team_business": str(me.total_business) if me and not is_staff else str(Decimal("0")),
                "reward_total_business": str(team_volume) if me and not is_staff else str(Decimal("0")),
                "income_wallet": str(wallets.get("income", Decimal("0"))),
                "main_wallet": str(wallets.get("main", Decimal("0"))),
                "reward_wallet": str(wallets.get("reward", Decimal("0"))),
                "roi_wallet": str(wallets.get("roi", Decimal("0"))),
                "withdraw_wallet": str(wallets.get("withdraw", Decimal("0"))),
                "fund_wallet_1": str(wallets.get("main", Decimal("0"))),
                "fund_wallet_2": str(wallets.get("reward", Decimal("0"))),
                "fund_wallet_3": str(wallets.get("roi", Decimal("0"))),
                "leg1_business": str(leg1),
                "leg2_business": str(leg2),
                "leg3_business": str(leg3),
                "card_tier": (me.card_tier if me and not is_staff else None),
                "associate_id": (me.associate_id if me and not is_staff else None),
                "associate_name": (
                    (me.user.get_full_name() or me.user.username) if me and not is_staff else None
                ),
                "city": (me.city if me and not is_staff else None),
                "state": (me.state if me and not is_staff else None),
                "status": (me.status if me and not is_staff else None),
                "profile_photo_url": None,
            },
            "trend": [
                {"day": str(row["day"]), "amount": str(row["amount"] or 0), "count": row["count"]}
                for row in trend
            ],
            "income_breakdown": [
                {"wallet_type": row["wallet_type"], "total": str(row["total"] or 0)}
                for row in income_breakdown
            ],
            "recent_activity": recent[:12],
            "roi_performance": _roi_performance_board(me if not is_staff else None),
            "sale_levels": _sale_level_board(me if not is_staff else None),
        }

        if me and not is_staff:
            from core.media_urls import absolute_media_url

            kyc = me.kyc_submissions.order_by("-created_at").first()
            photo = None
            if kyc and kyc.profile_photo:
                photo = absolute_media_url(
                    kyc.profile_photo,
                    request,
                    version=getattr(kyc, "updated_at", None),
                )
            payload["kpis"]["profile_photo_url"] = photo
            payload["profile"] = {
                "associate_id": me.associate_id,
                "name": me.user.get_full_name() or me.user.username,
                "card_tier": me.card_tier,
                "status": me.status,
                "city": me.city or "",
                "state": me.state or "",
                "photo_url": photo,
                "direct_count": int(me.direct_count or 0),
                "direct_active_count": int(me.direct_active_count or 0),
            }

        response = Response(payload)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        return response


class BusinessReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = _associate_scope_ids(request.user)
        if scope is not None and not scope:
            return Response({"detail": "Associate profile required"}, status=403)

        qs = Associate.objects.select_related("user", "sponsor").filter(is_deleted=False)
        if scope is not None:
            qs = qs.filter(id__in=scope)

        rows = []
        for a in qs.order_by("-total_business")[:500]:
            income = _sum_amount(_credited_entries(a))
            rows.append(
                {
                    "associate_id": a.associate_id,
                    "name": a.user.get_full_name() or a.user.username,
                    "sponsor_id": a.sponsor_associate_id,
                    "status": a.status,
                    "personal_business": str(a.personal_business),
                    "total_business": str(a.total_business),
                    "earning_level": int(a.earning_level or 0),
                    "earning_level_name": a.earning_level_name or "",
                    "reward_level": int(a.earning_level or 0),
                    "reward_level_name": a.earning_level_name or "",
                    "performance_level": int(a.performance_level or 0),
                    "performance_level_name": a.performance_level_name or "",
                    "direct_count": a.direct_count,
                    "income_total": str(income),
                    "mobile": a.mobile,
                }
            )
        response = Response({"results": rows, "count": len(rows)})
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
