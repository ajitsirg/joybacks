"""
Create a rich dummy associate directly under Ganpati Maharaj (JOYSIDDHI01)
with ~100 direct + indirect active members and large wallet balances.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from associates.models import PLATINUM_JOIN_AMOUNT, Associate, generate_referral_code, tier_from_amount
from configuration.models import GenealogySettings
from configuration.repository import ConfigRepository
from genealogy.models import GenealogyNode
from genealogy.services import GenealogyService
from operations.models import KYCSubmission
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()

# Login for the dummy leader
LEADER_ID = "JOY9998887771"
LEADER_MOBILE = "9998887771"
LEADER_EMAIL = "dummy.army@joyclubs.in"
LEADER_PASSWORD = "Dummy@123"
LEADER_FIRST = "Dummy"
LEADER_LAST = "Army Leader"

SPONSOR_ID = "JOYSIDDHI01"  # Ganpati Maharaj / Siddhivinayak
TEAM_SIZE = 100
DIRECT_COUNT = 20  # first-level directs under the leader
JOIN_ACTIVE = PLATINUM_JOIN_AMOUNT  # ₹2.2L → Active


class Command(BaseCommand):
    help = (
        f"Create {LEADER_ID} under {SPONSOR_ID} with {TEAM_SIZE} "
        "active downline (direct + indirect) and funded wallets"
    )

    def handle(self, *args, **options):
        sponsor = Associate.objects.filter(associate_id__iexact=SPONSOR_ID, is_deleted=False).first()
        if not sponsor:
            self.stderr.write(
                f"Sponsor {SPONSOR_ID} missing — run: python manage.py ensure_ganpati_line"
            )
            return

        gs = ConfigRepository.genealogy()
        old_mode, old_max = gs.leg_mode, gs.max_legs
        gs.leg_mode = GenealogySettings.LegMode.UNLIMITED
        gs.max_legs = 0
        gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])

        try:
            with transaction.atomic():
                leader = self._upsert(
                    associate_id=LEADER_ID,
                    first=LEADER_FIRST,
                    last=LEADER_LAST,
                    mobile=LEADER_MOBILE,
                    email=LEADER_EMAIL,
                    sponsor=sponsor,
                    join_amount=JOIN_ACTIVE,
                    password=LEADER_PASSWORD,
                    city="Jaipur",
                    state="Rajasthan",
                )
                self._ensure_kyc(leader, pan="DUMMY7771F", aadhaar="XXXX-XXXX-7771")
                WalletService.ensure_wallets(leader)
                self._attach(leader, sponsor)

                directs: list[Associate] = []
                # 20 directs
                for i in range(1, DIRECT_COUNT + 1):
                    aid = f"JOYDUM{i:04d}"
                    mobile = f"98877{i:05d}"[-10:]
                    child = self._upsert(
                        associate_id=aid,
                        first=f"Direct{i}",
                        last="Member",
                        mobile=mobile,
                        email=f"{aid.lower()}@joyclub.dummy",
                        sponsor=leader,
                        join_amount=JOIN_ACTIVE,
                        password=LEADER_PASSWORD,
                    )
                    self._ensure_kyc(child, pan=f"DIR{i:05d}F", aadhaar=f"XXXX-XXXX-{i:04d}")
                    WalletService.ensure_wallets(child)
                    self._attach(child, leader)
                    self._fund_wallets(
                        child,
                        {
                            Wallet.WalletType.MAIN: Decimal("50000"),
                            Wallet.WalletType.INCOME: Decimal("25000"),
                            Wallet.WalletType.WITHDRAW: Decimal("15000"),
                        },
                    )
                    directs.append(child)

                # Remaining as indirects under the 20 directs (4 each = 80)
                indirect_n = TEAM_SIZE - DIRECT_COUNT
                for i in range(1, indirect_n + 1):
                    parent = directs[(i - 1) % len(directs)]
                    aid = f"JOYIND{i:04d}"
                    mobile = f"97766{i:05d}"[-10:]
                    # Mix: most active, a few inactive/gray for realism
                    if i % 11 == 0:
                        join_amt = Decimal("0")
                    elif i % 7 == 0:
                        join_amt = Decimal("22000")
                    else:
                        join_amt = JOIN_ACTIVE
                    child = self._upsert(
                        associate_id=aid,
                        first=f"Indirect{i}",
                        last="Member",
                        mobile=mobile,
                        email=f"{aid.lower()}@joyclub.dummy",
                        sponsor=parent,
                        join_amount=join_amt,
                        password=LEADER_PASSWORD,
                    )
                    self._ensure_kyc(child, pan=f"IND{i:05d}F", aadhaar=f"YYYY-YYYY-{i:04d}")
                    WalletService.ensure_wallets(child)
                    self._attach(child, parent)
                    if join_amt >= JOIN_ACTIVE:
                        self._fund_wallets(
                            child,
                            {
                                Wallet.WalletType.MAIN: Decimal("30000"),
                                Wallet.WalletType.INCOME: Decimal("12000"),
                            },
                        )

                # Team business on leader (enough for a few reward levels)
                team = Associate.objects.filter(sponsor=leader, is_deleted=False)
                all_down = list(team)
                for d in directs:
                    all_down.extend(list(Associate.objects.filter(sponsor=d, is_deleted=False)))
                team_bv = sum((Decimal(a.join_amount or 0) for a in all_down), Decimal("0"))
                leader.personal_business = JOIN_ACTIVE
                leader.total_business = max(team_bv, Decimal("5000000"))
                leader.direct_count = Associate.objects.filter(sponsor=leader, is_deleted=False).count()
                leader.direct_active_count = Associate.objects.filter(
                    sponsor=leader, status=Associate.Status.ACTIVE, is_deleted=False
                ).count()
                leader.sync_flag_color(save=False)
                leader.sync_status_from_investment(save=False)
                leader.sync_rank_levels(save=False)
                leader.save()

                for d in directs:
                    d.direct_count = Associate.objects.filter(sponsor=d, is_deleted=False).count()
                    d.direct_active_count = Associate.objects.filter(
                        sponsor=d, status=Associate.Status.ACTIVE, is_deleted=False
                    ).count()
                    kids = Associate.objects.filter(sponsor=d, is_deleted=False)
                    d.personal_business = d.join_amount
                    d.total_business = d.join_amount + sum(
                        (Decimal(k.join_amount or 0) for k in kids), Decimal("0")
                    )
                    d.sync_flag_color(save=False)
                    d.sync_status_from_investment(save=False)
                    d.sync_rank_levels(save=False)
                    d.save()

                # Heavy wallets for the leader
                self._fund_wallets(
                    leader,
                    {
                        Wallet.WalletType.MAIN: Decimal("1500000"),
                        Wallet.WalletType.INCOME: Decimal("850000"),
                        Wallet.WalletType.REWARD: Decimal("400000"),
                        Wallet.WalletType.ROI: Decimal("275000"),
                        Wallet.WalletType.WITHDRAW: Decimal("600000"),
                    },
                    force_set=True,
                )

                # Bump sponsor counters
                sponsor.direct_count = Associate.objects.filter(sponsor=sponsor, is_deleted=False).count()
                sponsor.direct_active_count = Associate.objects.filter(
                    sponsor=sponsor, status=Associate.Status.ACTIVE, is_deleted=False
                ).count()
                sponsor.save(update_fields=["direct_count", "direct_active_count", "updated_at"])

        finally:
            gs.leg_mode = old_mode
            gs.max_legs = old_max
            gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])

        leader = Associate.objects.get(associate_id=LEADER_ID)
        wallets = {
            w.wallet_type: str(w.balance)
            for w in Wallet.objects.filter(associate=leader)
        }
        downline = Associate.objects.filter(sponsor=leader).count()
        total_under = 0
        # rough count of all with this leader in upline via BFS
        queue = [leader]
        seen = {leader.pk}
        while queue:
            cur = queue.pop()
            for c in Associate.objects.filter(sponsor=cur, is_deleted=False):
                if c.pk in seen:
                    continue
                seen.add(c.pk)
                total_under += 1
                queue.append(c)

        self.stdout.write(self.style.SUCCESS("Dummy army ready under Ganpati Maharaj"))
        self.stdout.write(f"  Login ID : {LEADER_ID}")
        self.stdout.write(f"  Password : {LEADER_PASSWORD}")
        self.stdout.write(f"  Mobile   : {LEADER_MOBILE}")
        self.stdout.write(f"  Sponsor  : {SPONSOR_ID}")
        self.stdout.write(f"  Status   : {leader.status} | earning: {leader.earning_level_name}")
        self.stdout.write(f"  Directs  : {downline} | team size: {total_under}")
        self.stdout.write(f"  Team BV  : {leader.total_business}")
        self.stdout.write(f"  Wallets  : {wallets}")

    def _attach(self, child: Associate, sponsor: Associate) -> None:
        if GenealogyNode.objects.filter(associate=child).exists():
            return
        if not GenealogyNode.objects.filter(associate=sponsor).exists():
            if sponsor.sponsor_id is None:
                GenealogyService.ensure_root(sponsor)
            elif sponsor.sponsor_id:
                self._attach(sponsor, sponsor.sponsor)
        GenealogyService.attach_under_sponsor(child, sponsor)

    def _upsert(
        self,
        *,
        associate_id: str,
        first: str,
        last: str,
        mobile: str,
        email: str,
        sponsor: Associate,
        join_amount: Decimal,
        password: str,
        city: str = "Jaipur",
        state: str = "Rajasthan",
    ) -> Associate:
        tier, flag = tier_from_amount(join_amount)
        active = join_amount >= JOIN_ACTIVE
        user = User.objects.filter(username__iexact=associate_id).first()
        if not user:
            user = User.objects.filter(email__iexact=email).first()
        if user:
            user.username = associate_id
            user.email = email
            user.first_name = first
            user.last_name = last
            user.phone = mobile
            user.user_type = "associate"
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                username=associate_id,
                first_name=first,
                last_name=last,
                phone=mobile,
                user_type="associate",
            )

        assoc = Associate.all_objects.filter(associate_id__iexact=associate_id).first()
        if not assoc:
            assoc = Associate.all_objects.filter(user=user).first()

        fields = dict(
            user=user,
            associate_id=associate_id,
            mobile=mobile,
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id,
            lead_reference=sponsor.associate_id,
            status=Associate.Status.ACTIVE if active else Associate.Status.INACTIVE,
            activated_at=timezone.now() if active else None,
            kyc_verified=True,
            join_amount=join_amount,
            personal_business=join_amount,
            total_business=join_amount,
            card_tier=tier,
            flag_color=flag,
            city=city,
            state=state,
            country="India",
            is_deleted=False,
            deleted_at=None,
            login_password=password,
        )
        if assoc:
            for key, value in fields.items():
                setattr(assoc, key, value)
            if not assoc.referral_code:
                assoc.referral_code = generate_referral_code()
            assoc.save()
        else:
            assoc = Associate.objects.create(**fields, referral_code=generate_referral_code())
        assoc.sync_rank_levels(save=True)
        return assoc

    def _ensure_kyc(self, assoc: Associate, *, pan: str, aadhaar: str) -> None:
        kyc = assoc.kyc_submissions.order_by("-created_at").first()
        if not kyc:
            KYCSubmission.objects.create(
                associate=assoc,
                full_name=assoc.user.get_full_name() or assoc.associate_id,
                pan=pan,
                aadhaar=aadhaar,
                bank_name="HDFC Bank",
                account_number=f"5010{assoc.mobile[-6:]}",
                ifsc="HDFC0001234",
                status=KYCSubmission.Status.APPROVED,
                reviewed_at=timezone.now(),
            )
        else:
            kyc.status = KYCSubmission.Status.APPROVED
            kyc.pan = pan
            kyc.aadhaar = aadhaar
            kyc.reviewed_at = timezone.now()
            kyc.save()

    def _fund_wallets(
        self,
        assoc: Associate,
        amounts: dict[str, Decimal],
        *,
        force_set: bool = False,
    ) -> None:
        """Credit up to target balances (idempotent-ish: top-up only)."""
        for wtype, target in amounts.items():
            wallet, _ = Wallet.objects.get_or_create(
                associate=assoc,
                wallet_type=wtype,
                defaults={"balance": Decimal("0")},
            )
            if force_set:
                need = Decimal(target) - Decimal(wallet.balance or 0)
            else:
                # Only top up if below target
                need = Decimal(target) - Decimal(wallet.balance or 0)
            if need > 0:
                WalletService.credit(
                    associate=assoc,
                    wallet_type=wtype,
                    amount=need,
                    reference=f"DUMMY-FUND-{assoc.associate_id}-{wtype}",
                    narration="Dummy army seed fund",
                )
