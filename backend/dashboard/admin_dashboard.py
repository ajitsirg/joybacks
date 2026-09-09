"""Unfold admin index dashboard data for JoyClub Associate."""

from __future__ import annotations

from decimal import Decimal


def dashboard_callback(request, context):
    from associates.models import Associate
    from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
    from wallets.models import Wallet

    associates_total = Associate.objects.count()
    associates_active = Associate.objects.filter(status=Associate.Status.ACTIVE).count()
    associates_pending = Associate.objects.filter(status=Associate.Status.PENDING).count()
    kyc_pending = KYCSubmission.objects.filter(status=KYCSubmission.Status.PENDING).count()
    deposits_pending = DepositRequest.objects.filter(status=DepositRequest.Status.PENDING).count()
    withdrawals_pending = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.PENDING
    ).count()

    try:
        from django.db.models import Sum

        total = Wallet.objects.aggregate(total=Sum("balance")).get("total") or Decimal("0")
    except Exception:
        total = Decimal("0")

    cards = [
        {
            "title": "Total associates",
            "metric": f"{associates_total:,}",
            "footer": f"{associates_active:,} active",
            "icon": "groups",
            "link": "/admin/associates/associate/",
        },
        {
            "title": "Pending joins",
            "metric": f"{associates_pending:,}",
            "footer": "Awaiting lead approval",
            "icon": "hourglass_top",
            "link": "/admin/associates/associate/?status__exact=pending",
        },
        {
            "title": "Pending KYC",
            "metric": f"{kyc_pending:,}",
            "footer": "Documents to review",
            "icon": "badge",
            "link": "/admin/operations/kycsubmission/?status__exact=pending",
        },
        {
            "title": "Pending deposits",
            "metric": f"{deposits_pending:,}",
            "footer": "Awaiting confirmation",
            "icon": "south",
            "link": "/admin/operations/depositrequest/?status__exact=pending",
        },
        {
            "title": "Pending withdrawals",
            "metric": f"{withdrawals_pending:,}",
            "footer": "Payout queue",
            "icon": "north",
            "link": "/admin/operations/withdrawalrequest/?status__exact=pending",
        },
        {
            "title": "Wallet balance",
            "metric": f"₹ {float(total):,.0f}",
            "footer": "All wallet types",
            "icon": "account_balance_wallet",
            "link": "/admin/wallets/wallet/",
        },
    ]

    recent = list(
        Associate.objects.select_related("user")
        .order_by("-created_at")[:8]
        .values("associate_id", "mobile", "status", "card_tier", "join_amount", "created_at")
    )

    context.update(
        {
            "joyclub_cards": cards,
            "joyclub_recent": recent,
        }
    )
    return context
