"""Archive / purge associates from Django admin.

Default delete = archive (soft-delete): hidden from frontend, kept in admin Recycle Bin
with related wallets/ledger/commissions/investments soft-deleted alongside.

Optional hard=True permanently destroys rows (superuser action only).
"""

from __future__ import annotations

from collections import deque
from decimal import Decimal
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from associates.models import Associate

logger = logging.getLogger(__name__)

PROTECTED_ASSOCIATE_IDS = frozenset({"JOYSIDDHI01", "JOY00000001"})


class PurgeError(ValueError):
    """Raised when an associate/user cannot be archived or purged."""


def _company_fallback() -> Associate | None:
    for aid in ("JOYSIDDHI01", "JOY00000001"):
        a = Associate.objects.filter(associate_id__iexact=aid, is_deleted=False).first()
        if a:
            return a
    return Associate.objects.filter(sponsor__isnull=True, is_deleted=False).order_by("created_at").first()


def _soft_qs(qs) -> int:
    """Soft-delete rows (kept for admin recycle bin)."""
    count = qs.filter(is_deleted=False).count()
    if count:
        qs.filter(is_deleted=False).delete(soft=True)
    return count


def _hard_qs(qs) -> int:
    count = qs.count()
    if count:
        qs.delete(force=True)
    return count


def _resolve_upper_level(assoc: Associate, reparent_to: Associate | None) -> Associate | None:
    if reparent_to and not reparent_to.is_deleted and reparent_to.pk != assoc.pk:
        return reparent_to
    if assoc.sponsor_id:
        sponsor = Associate.all_objects.filter(pk=assoc.sponsor_id, is_deleted=False).first()
        if sponsor and sponsor.pk != assoc.pk:
            return sponsor
    fallback = _company_fallback()
    if fallback and fallback.pk != assoc.pk:
        return fallback
    return None


def _force_shift_leg_to_upper(*, child: Associate, upper: Associate) -> int:
    from genealogy.models import GenealogyNode
    from genealogy.services import GenealogyService

    try:
        result = GenealogyService.shift_subtree(child, upper, force=True)
        return int(result.get("moved_count") or 1)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "shift_subtree failed for %s → %s (%s); forcing leg rebuild",
            child.associate_id,
            upper.associate_id,
            exc,
        )

    subtree_ids: set = {child.pk}
    queue: deque = deque([child.pk])
    while queue:
        parent_id = queue.popleft()
        for cid in Associate.all_objects.filter(
            sponsor_id=parent_id, is_deleted=False
        ).values_list("id", flat=True):
            if cid not in subtree_ids:
                subtree_ids.add(cid)
                queue.append(cid)

    child.sponsor = upper
    child.sponsor_associate_id = upper.associate_id
    child.placement_leg = 0
    child.save(update_fields=["sponsor", "sponsor_associate_id", "placement_leg", "updated_at"])

    ordered: list[tuple[Associate, Associate]] = [(child, upper)]
    bfs: deque[Associate] = deque([child])
    seen = {child.pk}
    while bfs:
        parent = bfs.popleft()
        kids = Associate.all_objects.filter(
            sponsor=parent, is_deleted=False, id__in=subtree_ids
        ).order_by("created_at")
        for kid in kids:
            if kid.pk in seen:
                continue
            seen.add(kid.pk)
            ordered.append((kid, parent))
            bfs.append(kid)

    nodes = list(
        GenealogyNode.all_objects.filter(associate_id__in=subtree_ids)
        .select_related("associate")
        .order_by("-depth")
    )
    for node in nodes:
        GenealogyService.hard_detach(node.associate)

    if not GenealogyNode.objects.filter(associate=upper).exists():
        GenealogyService.ensure_root(upper)

    for person, sponsor in ordered:
        GenealogyService.attach_under_sponsor(person, sponsor, force=True)

    GenealogyService._refresh_direct_counts(upper)
    return len(subtree_ids)


def _clawback_external_commissions(assoc: Associate, aid: str) -> int:
    from commissions.models import CommissionEntry
    from wallets.models import Wallet
    from wallets.services import WalletService

    external = list(
        CommissionEntry.all_objects.filter(source_associate=assoc, is_deleted=False)
        .exclude(beneficiary=assoc)
        .exclude(status=CommissionEntry.Status.VOIDED)
        .select_related("beneficiary")
    )
    clawed = 0
    for entry in external:
        amt = Decimal(entry.amount or 0)
        if amt <= 0:
            continue
        ben = entry.beneficiary
        if ben.is_deleted:
            continue
        WalletService.ensure_wallets(ben)
        w = Wallet.objects.filter(associate=ben, wallet_type=entry.wallet_type).first()
        if not w:
            continue
        take = min(Decimal(w.balance or 0) - Decimal(w.held_balance or 0), amt)
        if take > 0:
            try:
                WalletService.debit(
                    associate=ben,
                    wallet_type=entry.wallet_type,
                    amount=take,
                    reference=f"ARCHIVE-{aid}-{entry.id}",
                    narration=f"Reverse commission after archiving {aid}",
                    meta={"archived_entry": str(entry.id), "source": aid},
                )
                clawed += 1
            except ValueError:
                w.balance = max(Decimal("0.00"), Decimal(w.balance or 0) - take)
                w.save(update_fields=["balance", "updated_at"])
                clawed += 1
        entry.status = CommissionEntry.Status.VOIDED
        entry.save(update_fields=["status", "updated_at"])
    return clawed


def _deactivate_user(user) -> None:
    if not user:
        return
    user.is_active = False
    stamp = timezone.now().strftime("%Y%m%d%H%M%S")
    # Keep email readable in recycle bin; only mark inactive
    if not getattr(user, "must_change_password", False):
        pass
    user.save(update_fields=["is_active"])


@transaction.atomic
def archive_associate(
    *,
    associate: Associate,
    reparent_to: Associate | None = None,
    hard: bool = False,
) -> dict:
    """
    Remove associate from the live app (frontend/API).

    soft (default):
      - shift under-leg to upper sponsor
      - claw back commissions paid to others from this member
      - soft-delete wallets, ledger, own commissions, investments
      - detach genealogy, soft-delete associate, deactivate login
      - data remains in Django admin Recycle Bin

    hard=True:
      - same cleanup then permanently destroy associate + user rows
    """
    from commissions.models import CommissionEntry
    from genealogy.services import GenealogyService
    from investments.models import InvestmentContract
    from wallets.models import FundTransferRequest, LedgerEntry, Wallet

    assoc = Associate.all_objects.select_for_update().get(pk=associate.pk)
    aid = assoc.associate_id
    if aid.upper() in {x.upper() for x in PROTECTED_ASSOCIATE_IDS}:
        raise PurgeError(f"Cannot delete protected company account {aid}")

    user = assoc.user if assoc.user_id else None
    if user and (user.is_superuser or user.is_staff):
        raise PurgeError(f"Cannot delete staff/superuser account linked to {aid}")

    if assoc.is_deleted and not hard:
        raise PurgeError(f"{aid} is already in the deleted accounts bucket")

    target = _resolve_upper_level(assoc, reparent_to)
    children = list(
        Associate.all_objects.filter(sponsor=assoc, is_deleted=False).order_by("created_at")
    )
    underleg_moved = 0
    reparented_ids: list[str] = []
    for child in children:
        if target is None:
            raise PurgeError(
                f"{aid} has under-leg but no upper-level sponsor/company root to shift them to"
            )
        moved = _force_shift_leg_to_upper(child=child, upper=target)
        underleg_moved += moved
        reparented_ids.append(child.associate_id)

    invested = Decimal(assoc.personal_business or 0)
    if invested > 0 and not assoc.is_deleted:
        for link in GenealogyService.upline(assoc):
            ancestor = Associate.all_objects.select_for_update().filter(pk=link.ancestor_id).first()
            if not ancestor or ancestor.pk == assoc.pk or ancestor.is_deleted:
                continue
            ancestor.total_business = max(
                Decimal("0.00"), Decimal(ancestor.total_business or 0) - invested
            )
            ancestor.sync_rank_levels(save=False)
            ancestor.save(
                update_fields=[
                    "total_business",
                    "earning_level",
                    "earning_level_name",
                    "performance_level",
                    "performance_level_name",
                    "updated_at",
                ]
            )

    sponsor = Associate.all_objects.filter(pk=assoc.sponsor_id).first() if assoc.sponsor_id else None
    clawed = _clawback_external_commissions(assoc, aid)

    wallets = list(Wallet.all_objects.filter(associate=assoc))
    wallet_ids = [w.pk for w in wallets]
    remove = _hard_qs if hard else _soft_qs

    ledger_n = 0
    if wallet_ids:
        ledger_n = remove(LedgerEntry.all_objects.filter(wallet_id__in=wallet_ids))
    # Zero live balances before soft-delete so restore starts clean if needed
    if not hard:
        for w in wallets:
            if w.balance or w.held_balance:
                w.balance = Decimal("0.00")
                w.held_balance = Decimal("0.00")
                w.save(update_fields=["balance", "held_balance", "updated_at"])
    wallet_n = remove(Wallet.all_objects.filter(associate=assoc))
    remove(
        FundTransferRequest.all_objects.filter(Q(requester=assoc) | Q(beneficiary=assoc))
    )

    commission_n = remove(
        CommissionEntry.all_objects.filter(Q(beneficiary=assoc) | Q(source_associate=assoc))
    )
    contract_n = remove(InvestmentContract.all_objects.filter(associate=assoc))

    # Soft-delete ops rows so they leave live ops queues but stay in bin
    try:
        from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest

        kyc_n = remove(KYCSubmission.all_objects.filter(associate=assoc))
        dep_n = remove(DepositRequest.all_objects.filter(associate=assoc))
        wd_n = remove(WithdrawalRequest.all_objects.filter(associate=assoc))
    except Exception:  # noqa: BLE001
        kyc_n = dep_n = wd_n = 0

    GenealogyService.hard_detach(assoc)

    assoc.personal_business = Decimal("0.00")
    assoc.total_business = Decimal("0.00")
    assoc.join_amount = Decimal("0.00")
    assoc.earning_level = 0
    assoc.earning_level_name = "No level"
    assoc.performance_level = 0
    assoc.performance_level_name = "No level"
    assoc.direct_count = 0
    assoc.direct_active_count = 0
    assoc.status = Associate.Status.INACTIVE
    assoc.is_deleted = True
    assoc.deleted_at = timezone.now()
    assoc.sponsor = None
    assoc.sponsor_associate_id = ""
    assoc.save(
        update_fields=[
            "personal_business",
            "total_business",
            "join_amount",
            "earning_level",
            "earning_level_name",
            "performance_level",
            "performance_level_name",
            "direct_count",
            "direct_active_count",
            "status",
            "is_deleted",
            "deleted_at",
            "sponsor",
            "sponsor_associate_id",
            "updated_at",
        ]
    )

    if sponsor is not None:
        GenealogyService._refresh_direct_counts(
            Associate.all_objects.filter(pk=sponsor.pk, is_deleted=False).first()
        )
        sponsor_alive = Associate.objects.filter(pk=sponsor.pk).first()
        if sponsor_alive:
            sponsor_alive.sync_performance_level(save=True)
    if target and (sponsor is None or target.pk != sponsor.pk):
        GenealogyService._refresh_direct_counts(target)
        target_alive = Associate.objects.filter(pk=target.pk).first()
        if target_alive:
            target_alive.sync_performance_level(save=True)

    user_deleted = False
    deleted_user_id = user.pk if user else None
    if hard:
        assoc.delete(force=True)
        if user is not None:
            user.delete()
            user_deleted = True
    else:
        _deactivate_user(user)

    return {
        "associate_id": aid,
        "archived": not hard,
        "hard": hard,
        "reparented": len(children),
        "reparented_ids": reparented_ids,
        "underleg_moved": underleg_moved,
        "reparent_to": target.associate_id if target else None,
        "wallets_removed": wallet_n,
        "ledger_removed": ledger_n,
        "commissions_removed": commission_n,
        "commissions_clawed": clawed,
        "contracts_removed": contract_n,
        "kyc_removed": kyc_n,
        "deposits_removed": dep_n,
        "withdrawals_removed": wd_n,
        "user_deleted": user_deleted,
        "user_deactivated": (not hard) and user is not None,
        "user_id": deleted_user_id,
    }


# Back-compat name used by admin / tests
def purge_associate(
    *,
    associate: Associate,
    delete_user: bool = True,  # noqa: ARG001 — kept for callers; archive always deactivates
    reparent_to: Associate | None = None,
    hard: bool = False,
) -> dict:
    return archive_associate(associate=associate, reparent_to=reparent_to, hard=hard)


@transaction.atomic
def restore_associate(*, associate: Associate) -> dict:
    """Bring an archived associate back to the live app (inactive, no sponsor)."""
    assoc = Associate.all_objects.select_for_update().get(pk=associate.pk)
    if not assoc.is_deleted:
        raise PurgeError(f"{assoc.associate_id} is not in the deleted bucket")
    if assoc.associate_id.upper() in {x.upper() for x in PROTECTED_ASSOCIATE_IDS}:
        raise PurgeError("Protected account")

    from wallets.models import Wallet
    from wallets.services import WalletService

    assoc.is_deleted = False
    assoc.deleted_at = None
    assoc.status = Associate.Status.INACTIVE
    assoc.save(update_fields=["is_deleted", "deleted_at", "status", "updated_at"])

    # Restore soft-deleted wallets (balances already zeroed)
    for w in Wallet.all_objects.filter(associate=assoc, is_deleted=True):
        w.is_deleted = False
        w.deleted_at = None
        w.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    WalletService.ensure_wallets(assoc)

    user = assoc.user if assoc.user_id else None
    if user:
        user.is_active = True
        user.save(update_fields=["is_active"])

    from genealogy.services import GenealogyService

    if assoc.sponsor_id and Associate.objects.filter(pk=assoc.sponsor_id).exists():
        GenealogyService.rebuild_under_sponsor(assoc, assoc.sponsor)
    else:
        GenealogyService.ensure_root(assoc)

    return {"associate_id": assoc.associate_id, "restored": True}
