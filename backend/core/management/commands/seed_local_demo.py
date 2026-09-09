"""Seed rich local-only dummy data for JoyClub (this laptop / SQLite).

Safe to re-run. Uses @joyclub.local emails and JOYLOCAL* IDs so it can be purged later.

  cd backend && .venv/bin/python manage.py seed_local_demo

Logins after seed:
  Staff:     admin@joyclub.associate / admin123
  Root:      JOY00000001 / admin123
  Demo lead: JOYLOCAL0001 / demo1234
  Team:      JOYLOCAL0002… / demo1234
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from associates.models import Associate, generate_referral_code, tier_from_amount
from commissions.services import CommissionEngine
from configuration.models import GenealogySettings
from configuration.repository import ConfigRepository
from genealogy.services import GenealogyService
from notifications.models import Notification
from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
from operations.services import DepositService, WithdrawalService
from wallets.models import LedgerEntry, Wallet
from wallets.services import WalletService

User = get_user_model()

PASSWORD = "demo1234"
PREFIX = "JOYLOCAL"

# (aid, first, last, mobile, join_amount, sponsor_aid|"root", city)
# Multi-level tree under company root for My Associates / Fund Transfer / genealogy.
TREE: list[tuple[str, str, str, str, Decimal, str, str]] = [
    # Level 1 under root
    ("JOYLOCAL0001", "Rahul", "Sharma", "9100000001", Decimal("220000"), "root", "Mumbai"),
    ("JOYLOCAL0002", "Sneha", "Patel", "9100000002", Decimal("220000"), "root", "Pune"),
    ("JOYLOCAL0003", "Vikash", "Yadav", "9100000003", Decimal("22000"), "root", "Nagpur"),
    # Level 2 under Rahul
    ("JOYLOCAL0011", "Ananya", "Iyer", "9100000011", Decimal("220000"), "JOYLOCAL0001", "Chennai"),
    ("JOYLOCAL0012", "Karan", "Malhotra", "9100000012", Decimal("440000"), "JOYLOCAL0001", "Delhi"),
    ("JOYLOCAL0013", "Pooja", "Nair", "9100000013", Decimal("22000"), "JOYLOCAL0001", "Kochi"),
    ("JOYLOCAL0014", "Imran", "Khan", "9100000014", Decimal("0"), "JOYLOCAL0001", "Hyderabad"),
    # Level 2 under Sneha
    ("JOYLOCAL0021", "Neha", "Gupta", "9100000021", Decimal("220000"), "JOYLOCAL0002", "Jaipur"),
    ("JOYLOCAL0022", "Amit", "Joshi", "9100000022", Decimal("22000"), "JOYLOCAL0002", "Indore"),
    # Level 3 under Ananya
    ("JOYLOCAL0111", "Riya", "Kapoor", "9100000111", Decimal("220000"), "JOYLOCAL0011", "Surat"),
    ("JOYLOCAL0112", "Dev", "Singh", "9100000112", Decimal("660000"), "JOYLOCAL0011", "Ahmedabad"),
    ("JOYLOCAL0113", "Meera", "Shah", "9100000113", Decimal("22000"), "JOYLOCAL0011", "Vadodara"),
    # Level 3 under Karan
    ("JOYLOCAL0121", "Arjun", "Mehta", "9100000121", Decimal("220000"), "JOYLOCAL0012", "Lucknow"),
    ("JOYLOCAL0122", "Kavya", "Reddy", "9100000122", Decimal("0"), "JOYLOCAL0012", "Bengaluru"),
    # Level 4 under Riya
    ("JOYLOCAL1111", "Sahil", "Verma", "9100001111", Decimal("220000"), "JOYLOCAL0111", "Chandigarh"),
    ("JOYLOCAL1112", "Tanya", "Bose", "9100001112", Decimal("22000"), "JOYLOCAL0111", "Kolkata"),
]


class Command(BaseCommand):
    help = "Seed local-only dummy associates, wallets, KYC, deposits, withdrawals, and income"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-base",
            action="store_true",
            help="Do not run seed_joyclub first",
        )

    def handle(self, *args, **options):
        if not options["skip_base"]:
            self.stdout.write("Ensuring base JoyClub seed…")
            call_command("seed_joyclub")

        root = (
            Associate.objects.filter(associate_id="JOY00000001").first()
            or Associate.objects.filter(sponsor__isnull=True).order_by("created_at").first()
        )
        if not root:
            self.stderr.write(self.style.ERROR("No root associate — seed_joyclub failed"))
            return

        admin = (
            User.objects.filter(email__iexact="admin@joyclub.associate").first()
            or User.objects.filter(is_staff=True).order_by("id").first()
        )

        # Root should be able to fund-transfer and see menus
        root.can_fund_transfer = True
        root.can_view_admin_history = True
        root.can_view_reward_achievers = True
        if not (root.login_password or "").strip():
            root.login_password = "admin123"
        root.save(
            update_fields=[
                "can_fund_transfer",
                "can_view_admin_history",
                "can_view_reward_achievers",
                "login_password",
                "updated_at",
            ]
        )
        WalletService.ensure_wallets(root)
        self._credit_once(
            root,
            Wallet.WalletType.MAIN,
            Decimal("2500000"),
            "LOCAL-SEED-ROOT-MAIN",
            "Local demo fund balance",
        )

        by_id: dict[str, Associate] = {"root": root, root.associate_id: root}
        tree_pairs: list[tuple[Associate, Associate]] = []

        self.stdout.write(f"Building {len(TREE)} local demo associates under {root.associate_id}…")
        for aid, first, last, mobile, join_amt, sponsor_key, city in TREE:
            sponsor = by_id.get(sponsor_key) or root
            assoc = self._upsert_associate(
                associate_id=aid,
                email=f"{aid.lower()}@joyclub.local",
                first=first,
                last=last,
                mobile=mobile,
                sponsor=sponsor,
                join_amount=join_amt,
                city=city,
            )
            assoc.can_fund_transfer = True
            assoc.save(update_fields=["can_fund_transfer", "updated_at"])
            WalletService.ensure_wallets(assoc)
            self._ensure_kyc(
                assoc,
                status=KYCSubmission.Status.APPROVED,
                pan=f"LOCAL{aid[-4:]}F",
                aadhaar=f"XXXX-XXXX-{aid[-4:]}",
                bank="HDFC Bank",
                account=f"50100{aid[-4:]}",
            )
            by_id[aid] = assoc
            tree_pairs.append((assoc, sponsor))

        # Genealogy (temporarily unlimited legs)
        gs = ConfigRepository.genealogy()
        old_mode, old_max = gs.leg_mode, gs.max_legs
        gs.leg_mode = GenealogySettings.LegMode.UNLIMITED
        gs.max_legs = 0
        gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
        try:
            GenealogyService.ensure_root(root)
            GenealogyService.rebuild_tree(tree_pairs)
        except Exception as exc:
            self.stdout.write(f"Genealogy rebuild note: {exc}")
            GenealogyService.ensure_root(root)
            for child, sponsor in tree_pairs:
                try:
                    GenealogyService.rebuild_under_sponsor(child, sponsor)
                except Exception as inner:
                    self.stdout.write(f"  attach {child.associate_id}: {inner}")
        finally:
            gs.leg_mode = old_mode
            gs.max_legs = old_max
            gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])

        # Pending join for Team Approvals
        self._upsert_pending_join(by_id["JOYLOCAL0001"])

        # Pending KYC sample
        self._ensure_kyc(
            by_id["JOYLOCAL0014"],
            status=KYCSubmission.Status.PENDING,
            pan="PEND0014F",
            aadhaar="XXXX-XXXX-PEND",
            bank="SBI",
            account="50100990014",
            force_new=True,
        )

        # Approved deposits → business + level income
        for aid, _f, _l, _m, join_amt, _s, _c in TREE:
            if join_amt <= 0:
                continue
            assoc = by_id[aid]
            amount = (
                min(join_amt, Decimal("50000"))
                if join_amt >= Decimal("220000")
                else join_amt
            )
            self._approve_deposit(
                assoc,
                amount=amount,
                txn=f"TXN-LOCAL-{aid}",
                actor=admin,
            )

        # Extra fund wallets for transfer testing
        for aid, bal in (
            ("JOYLOCAL0001", Decimal("1500000")),
            ("JOYLOCAL0002", Decimal("880000")),
            ("JOYLOCAL0011", Decimal("660000")),
            ("JOYLOCAL0012", Decimal("1100000")),
        ):
            self._credit_once(
                by_id[aid],
                Wallet.WalletType.MAIN,
                bal,
                f"LOCAL-SEED-MAIN-{aid}",
                "Local demo main wallet for fund transfer",
            )

        lead = by_id["JOYLOCAL0001"]
        self._credit_once(
            lead,
            Wallet.WalletType.INCOME,
            Decimal("12500"),
            "LOCAL-SEED-INCOME-0001",
            "Local demo income",
        )
        self._credit_once(
            lead,
            Wallet.WalletType.REWARD,
            Decimal("7500"),
            "LOCAL-SEED-REWARD-0001",
            "Local demo reward",
        )
        self._credit_once(
            lead,
            Wallet.WalletType.WITHDRAW,
            Decimal("9000"),
            "LOCAL-SEED-WD-0001",
            "Local demo withdraw wallet",
        )

        try:
            CommissionEngine.distribute_roi(
                associate=lead, base_amount=Decimal("10000"), reference="LOCAL-ROI-0001"
            )
        except Exception as exc:
            self.stdout.write(f"ROI note: {exc}")

        # Pending / completed queues
        DepositRequest.objects.get_or_create(
            associate=lead,
            transaction_id="TXN-LOCAL-PENDING-0001",
            defaults={
                "amount": Decimal("15000"),
                "wallet_type": "main",
                "status": DepositRequest.Status.PENDING,
            },
        )
        DepositRequest.objects.get_or_create(
            associate=by_id["JOYLOCAL0002"],
            transaction_id="TXN-LOCAL-REJECT-0002",
            defaults={
                "amount": Decimal("5000"),
                "wallet_type": "main",
                "status": DepositRequest.Status.REJECTED,
                "rejection_reason": "Local demo rejected sample",
            },
        )

        if not WithdrawalRequest.objects.filter(
            associate=lead, status=WithdrawalRequest.Status.PENDING
        ).exists():
            try:
                WithdrawalService.create(
                    associate=lead,
                    amount=Decimal("2000"),
                    bank_detail="HDFC ****0001 — Rahul Sharma",
                )
            except Exception as exc:
                self.stdout.write(f"Withdrawal note: {exc}")

        # Refresh ranks / directs
        for a in Associate.objects.filter(associate_id__startswith=PREFIX):
            a.direct_count = a.directs.filter(is_deleted=False).count()
            a.direct_active_count = a.directs.filter(
                status=Associate.Status.ACTIVE, is_deleted=False
            ).count()
            a.sync_flag_color(save=False)
            a.sync_rank_levels(save=False)
            a.sync_status_from_investment(save=False)
            a.save()

        root.direct_count = root.directs.filter(is_deleted=False).count()
        root.direct_active_count = root.directs.filter(
            status=Associate.Status.ACTIVE, is_deleted=False
        ).count()
        root.sync_rank_levels(save=False)
        root.save()

        for title, body in (
            ("Local demo ready", "Sample team, wallets, KYC and deposits are loaded on this laptop."),
            ("Fund Transfer tip", "Main wallet has balance — try Fund → Transfer with fixed packages."),
            ("Team waiting", "A pending join sits under JOYLOCAL0001 for Team Approvals."),
        ):
            Notification.objects.get_or_create(
                user=lead.user,
                title=title,
                defaults={"body": body, "channel": "in_app", "is_read": False},
            )
            Notification.objects.get_or_create(
                user=root.user,
                title=title,
                defaults={"body": body, "channel": "in_app", "is_read": False},
            )

        total = Associate.objects.filter(associate_id__startswith=PREFIX).count()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Local dummy data ready — {total} JOYLOCAL* associates"))
        self.stdout.write("Logins (password demo1234 unless noted):")
        self.stdout.write("  Staff:     admin@joyclub.associate / admin123")
        self.stdout.write(f"  Root:      {root.associate_id} / admin123  (fund balance for transfers)")
        self.stdout.write("  Demo lead: JOYLOCAL0001 / demo1234  (team + wallets + pending ops)")
        self.stdout.write("  Others:    JOYLOCAL0002…JOYLOCAL1112 / demo1234")
        self.stdout.write("Purge later: soft-delete associate_id starting with JOYLOCAL / @joyclub.local")

    def _upsert_associate(
        self,
        *,
        associate_id: str,
        email: str,
        first: str,
        last: str,
        mobile: str,
        sponsor: Associate,
        join_amount: Decimal,
        city: str = "Mumbai",
    ) -> Associate:
        tier, flag = tier_from_amount(join_amount)
        status = (
            Associate.Status.ACTIVE
            if join_amount >= Decimal("220000")
            else Associate.Status.INACTIVE
            if join_amount > 0
            else Associate.Status.INACTIVE
        )
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
            user.set_password(PASSWORD)
            user.save()
        else:
            user = User.objects.create_user(
                email=email,
                password=PASSWORD,
                username=associate_id,
                first_name=first,
                last_name=last,
                phone=mobile,
                user_type="associate",
            )

        assoc = Associate.objects.filter(associate_id__iexact=associate_id).first()
        if not assoc:
            assoc = Associate.objects.filter(user=user).first()
        defaults = dict(
            user=user,
            associate_id=associate_id,
            mobile=mobile,
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id,
            lead_reference=sponsor.associate_id,
            status=status,
            activated_at=timezone.now() if status == Associate.Status.ACTIVE else None,
            kyc_verified=True,
            join_amount=join_amount,
            card_tier=tier,
            flag_color=flag,
            city=city,
            state="Maharashtra",
            country="India",
            can_fund_transfer=True,
            login_password=PASSWORD,
        )
        if assoc:
            for k, v in defaults.items():
                setattr(assoc, k, v)
            if not assoc.referral_code:
                assoc.referral_code = generate_referral_code()
            assoc.save()
        else:
            assoc = Associate.objects.create(
                referral_code=generate_referral_code(),
                **defaults,
            )
        return assoc

    def _upsert_pending_join(self, sponsor: Associate) -> None:
        aid = "JOYLOCALWAIT"
        email = "wait@joyclub.local"
        user = User.objects.filter(username__iexact=aid).first()
        if not user:
            user = User.objects.filter(email__iexact=email).first()
        if user:
            user.username = aid
            user.email = email
            user.first_name = "Waiting"
            user.last_name = "Member"
            user.phone = "9100000099"
            user.user_type = "associate"
            user.set_password(PASSWORD)
            user.save()
        else:
            user = User.objects.create_user(
                email=email,
                password=PASSWORD,
                username=aid,
                first_name="Waiting",
                last_name="Member",
                phone="9100000099",
                user_type="associate",
            )
        assoc = Associate.objects.filter(associate_id__iexact=aid).first()
        fields = dict(
            user=user,
            associate_id=aid,
            mobile="9100000099",
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id,
            lead_reference=sponsor.associate_id,
            status=Associate.Status.PENDING,
            kyc_verified=False,
            join_amount=Decimal("0"),
            card_tier=Associate.CardTier.GRAY,
            flag_color=Associate.FlagColor.GRAY,
            city="Mumbai",
            state="Maharashtra",
            login_password=PASSWORD,
        )
        if assoc:
            for k, v in fields.items():
                setattr(assoc, k, v)
            if not assoc.referral_code:
                assoc.referral_code = generate_referral_code()
            assoc.save()
        else:
            assoc = Associate.objects.create(referral_code=generate_referral_code(), **fields)
        WalletService.ensure_wallets(assoc)
        KYCSubmission.objects.get_or_create(
            associate=assoc,
            status=KYCSubmission.Status.PENDING,
            defaults={
                "full_name": "Waiting Member",
                "pan": "WAIT0001F",
                "aadhaar": "XXXX-XXXX-WAIT",
                "bank_name": "Axis Bank",
                "account_number": "50100000199",
                "ifsc": "UTIB0001234",
            },
        )

    def _ensure_kyc(
        self,
        assoc: Associate,
        *,
        status: str,
        pan: str,
        aadhaar: str,
        bank: str,
        account: str,
        force_new: bool = False,
    ) -> None:
        qs = KYCSubmission.objects.filter(associate=assoc, status=status)
        if qs.exists() and not force_new:
            return
        if force_new and qs.exists():
            return
        KYCSubmission.objects.get_or_create(
            associate=assoc,
            status=status,
            defaults={
                "full_name": assoc.user.get_full_name() or assoc.associate_id,
                "pan": pan,
                "aadhaar": aadhaar,
                "bank_name": bank,
                "account_number": account,
                "ifsc": "HDFC0001234",
                "upi_id": f"{assoc.mobile}@upi",
            },
        )

    def _approve_deposit(self, assoc: Associate, *, amount: Decimal, txn: str, actor) -> None:
        dep, _ = DepositRequest.objects.get_or_create(
            associate=assoc,
            transaction_id=txn,
            defaults={
                "amount": amount,
                "wallet_type": "main",
                "status": DepositRequest.Status.PENDING,
            },
        )
        if dep.status == DepositRequest.Status.PENDING and actor:
            try:
                DepositService.approve(dep, actor=actor)
            except Exception as exc:
                self.stdout.write(f"Deposit {txn}: {exc}")

    def _credit_once(
        self,
        assoc: Associate,
        wallet_type: str,
        amount: Decimal,
        reference: str,
        narration: str,
    ) -> None:
        if LedgerEntry.objects.filter(reference=reference).exists():
            return
        try:
            WalletService.credit(
                associate=assoc,
                wallet_type=wallet_type,
                amount=amount,
                reference=reference,
                narration=narration,
            )
        except Exception as exc:
            self.stdout.write(f"Credit {reference}: {exc}")
