"""Ensure demo associate JOYDEMO0001 with a full sample tree, wallets, and ops data."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from associates.models import Associate, generate_referral_code, tier_from_amount
from commissions.services import CommissionEngine
from configuration.models import GenealogySettings
from configuration.repository import ConfigRepository
from genealogy.services import GenealogyService
from notifications.models import Notification
from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
from operations.services import DepositService, WithdrawalService
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()

ASSOCIATE_ID = "JOYDEMO0001"
MOBILE = "9000999999"
PASSWORD = "demo1234"
EMAIL = "demo.associate@joyclub.member"
JOIN_AMOUNT = Decimal("220000")

# Downline under JOYDEMO0001 (aid, first, last, mobile, join_amount, sponsor_key)
# sponsor_key: "demo" | child associate_id
DOWNLINE = [
    ("JOYDEMO0002", "Aarav", "Mehta", "9000111102", Decimal("220000"), "demo"),
    ("JOYDEMO0003", "Priya", "Shah", "9000111103", Decimal("22000"), "demo"),
    ("JOYDEMO0004", "Rohan", "Das", "9000111104", Decimal("0"), "demo"),
    ("JOYDEMO0005", "Isha", "Verma", "9000111105", Decimal("220000"), "JOYDEMO0002"),
    ("JOYDEMO0006", "Kavya", "Nair", "9000111106", Decimal("22000"), "JOYDEMO0002"),
    ("JOYDEMO0007", "Dev", "Joshi", "9000111107", Decimal("22000"), "JOYDEMO0003"),
    ("JOYDEMO0008", "Meera", "Shah", "9000111108", Decimal("0"), "JOYDEMO0003"),
    ("JOYDEMO0009", "Arjun", "Kapoor", "9000111109", Decimal("220000"), "JOYDEMO0005"),
]


class Command(BaseCommand):
    help = "Create/reset rich demo associate JOYDEMO0001 / demo1234 with team & money data"

    def handle(self, *args, **options):
        root = (
            Associate.objects.filter(associate_id="JOY00000001").first()
            or Associate.objects.filter(sponsor__isnull=True).order_by("created_at").first()
        )
        if not root:
            self.stderr.write("No root associate — run: python manage.py seed_joyclub")
            return

        admin = (
            User.objects.filter(email__iexact="admin@joyclub.associate").first()
            or User.objects.filter(is_staff=True).order_by("id").first()
        )

        demo = self._upsert_associate(
            associate_id=ASSOCIATE_ID,
            email=EMAIL,
            first="Demo",
            last="Leader",
            mobile=MOBILE,
            sponsor=root,
            join_amount=JOIN_AMOUNT,
            password=PASSWORD,
            city="Mumbai",
            state="Maharashtra",
        )
        WalletService.ensure_wallets(demo)
        self._ensure_kyc(
            demo,
            status=KYCSubmission.Status.APPROVED,
            pan="DEMOP0001F",
            aadhaar="XXXX-XXXX-0001",
            bank="HDFC Bank",
            account="501000000001",
        )

        by_id: dict[str, Associate] = {"demo": demo, ASSOCIATE_ID: demo, root.associate_id: root}
        tree_pairs: list[tuple[Associate, Associate]] = [(demo, root)]

        for aid, first, last, mobile, join_amt, sponsor_key in DOWNLINE:
            sponsor = by_id.get(sponsor_key) or demo
            child = self._upsert_associate(
                associate_id=aid,
                email=f"{aid.lower()}@joyclub.demo",
                first=first,
                last=last,
                mobile=mobile,
                sponsor=sponsor,
                join_amount=join_amt,
                password=PASSWORD,
            )
            WalletService.ensure_wallets(child)
            self._ensure_kyc(
                child,
                status=KYCSubmission.Status.APPROVED,
                pan=f"DEMO{aid[-4:]}F",
                aadhaar=f"XXXX-XXXX-{aid[-4:]}",
                bank="ICICI Bank",
                account=f"50100{aid[-4:]}",
            )
            by_id[aid] = child
            tree_pairs.append((child, sponsor))

        # Temporarily unlimited legs so demo tree can be built even when root is full
        gs = ConfigRepository.genealogy()
        old_mode, old_max = gs.leg_mode, gs.max_legs
        gs.leg_mode = GenealogySettings.LegMode.UNLIMITED
        gs.max_legs = 0
        gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
        try:
            GenealogyService.rebuild_tree(tree_pairs)
        except Exception as exc:
            self.stdout.write(f"Genealogy rebuild note: {exc}")
            for child, sponsor in tree_pairs:
                try:
                    GenealogyService.rebuild_under_sponsor(child, sponsor)
                except Exception as inner:
                    self.stdout.write(f"  attach {child.associate_id}: {inner}")
        finally:
            gs.leg_mode = old_mode
            gs.max_legs = old_max
            gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])

        # Pending join under demo (approvals queue)
        self._upsert_pending_join(demo)

        # Pending KYC on a direct
        if by_id.get("JOYDEMO0004"):
            self._ensure_kyc(
                by_id["JOYDEMO0004"],
                status=KYCSubmission.Status.PENDING,
                pan="PEND0004F",
                aadhaar="XXXX-XXXX-PEND",
                bank="SBI",
                account="50100999904",
                force_new=True,
            )

        # Deposits — approve invested members (drives commissions + business)
        for aid in (ASSOCIATE_ID, "JOYDEMO0002", "JOYDEMO0003", "JOYDEMO0005", "JOYDEMO0006", "JOYDEMO0007", "JOYDEMO0009"):
            a = by_id.get(aid)
            if not a or a.join_amount <= 0:
                continue
            amount = Decimal("15000") if aid == ASSOCIATE_ID else (Decimal("8000") + Decimal(aid[-1]) * 500)
            self._approve_deposit(a, amount=amount, txn=f"TXN-DEMO-DONE-{aid}", actor=admin)

        # Extra personal deposit for demo
        self._approve_deposit(demo, amount=Decimal("25000"), txn="TXN-DEMO-DONE-JOYDEMO0001-B", actor=admin)

        # Pending deposit on demo
        DepositRequest.objects.get_or_create(
            associate=demo,
            transaction_id="TXN-DEMO-PENDING-JOYDEMO0001",
            defaults={
                "amount": Decimal("10000"),
                "wallet_type": "main",
                "status": DepositRequest.Status.PENDING,
            },
        )

        # Income extras
        try:
            CommissionEngine.distribute_roi(
                associate=demo, base_amount=Decimal("10000"), reference="SEED-ROI-JOYDEMO0001"
            )
        except Exception as exc:
            self.stdout.write(f"ROI note: {exc}")

        self._credit_once(
            demo,
            Wallet.WalletType.REWARD,
            Decimal("5000"),
            "SEED-REWARD-JOYDEMO0001",
            "Demo reward credit",
        )
        self._credit_once(
            demo,
            Wallet.WalletType.WITHDRAW,
            Decimal("8000"),
            "SEED-WD-JOYDEMO0001",
            "Demo withdraw wallet",
        )

        if not WithdrawalRequest.objects.filter(
            associate=demo, status=WithdrawalRequest.Status.PENDING
        ).exists():
            try:
                WithdrawalService.create(
                    associate=demo,
                    amount=Decimal("1500"),
                    bank_detail="HDFC ****0001 — Demo Leader",
                )
            except Exception as exc:
                self.stdout.write(f"Withdrawal note: {exc}")

        # Refresh counts
        for a in Associate.objects.filter(associate_id__startswith="JOYDEMO"):
            a.direct_count = a.directs.filter(is_deleted=False).count()
            a.direct_active_count = a.directs.filter(
                status=Associate.Status.ACTIVE, is_deleted=False
            ).count()
            if hasattr(a, "sync_flag_color"):
                a.sync_flag_color()
            a.save()

        for title, body in (
            ("Welcome to JoyClub", "Your demo account is ready with sample team & income."),
            ("Deposit approved", "₹25,000 deposit was credited to your main wallet."),
            ("New join request", "A new associate is waiting for your approval."),
            ("Reward unlocked", "₹5,000 reward credited — keep growing your network!"),
        ):
            if not Notification.objects.filter(user=demo.user, title=title).exists():
                Notification.objects.create(
                    user=demo.user,
                    title=title,
                    body=body,
                    channel="in_app",
                    is_read=False,
                )

        demo.refresh_from_db()
        wallets = {
            w.wallet_type: str(w.balance)
            for w in Wallet.objects.filter(associate=demo)
        }
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: {ASSOCIATE_ID} / {PASSWORD} | "
                f"directs={demo.direct_count} business={demo.total_business} wallets={wallets}"
            )
        )

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
        password: str,
        city: str = "",
        state: str = "",
    ) -> Associate:
        tier, flag = tier_from_amount(join_amount)
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
            status=Associate.Status.ACTIVE,
            activated_at=timezone.now(),
            kyc_verified=True,
            join_amount=join_amount,
            card_tier=tier,
            flag_color=flag,
            city=city or "Mumbai",
            state=state or "Maharashtra",
            country="India",
            login_password=password,
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
        aid = "JOYDEMOWAIT"
        email = "demo.wait@joyclub.demo"
        user = User.objects.filter(username__iexact=aid).first()
        if not user:
            user = User.objects.filter(email__iexact=email).first()
        if user:
            user.username = aid
            user.email = email
            user.first_name = "Waiting"
            user.last_name = "Member"
            user.phone = "9000111199"
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
                phone="9000111199",
                user_type="associate",
            )
        assoc = Associate.objects.filter(associate_id__iexact=aid).first()
        if not assoc:
            assoc = Associate.objects.filter(user=user).first()
        fields = dict(
            user=user,
            associate_id=aid,
            mobile="9000111199",
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id,
            lead_reference=sponsor.associate_id,
            status=Associate.Status.PENDING,
            kyc_verified=False,
            join_amount=Decimal("0"),
            card_tier=Associate.CardTier.GRAY,
            flag_color=Associate.FlagColor.GRAY,
            login_password=PASSWORD,
        )
        if assoc:
            for k, v in fields.items():
                setattr(assoc, k, v)
            if not assoc.referral_code:
                assoc.referral_code = generate_referral_code()
            assoc.save()
        else:
            Associate.objects.create(referral_code=generate_referral_code(), **fields)
        WalletService.ensure_wallets(
            Associate.objects.get(associate_id=aid)
        )
        KYCSubmission.objects.get_or_create(
            associate=Associate.objects.get(associate_id=aid),
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

    def _approve_deposit(
        self, assoc: Associate, *, amount: Decimal, txn: str, actor
    ) -> None:
        dep, created = DepositRequest.objects.get_or_create(
            associate=assoc,
            transaction_id=txn,
            defaults={
                "amount": amount,
                "wallet_type": "main",
                "status": DepositRequest.Status.PENDING,
            },
        )
        if dep.status == DepositRequest.Status.PENDING:
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
        from wallets.models import LedgerEntry

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
        except TypeError:
            # Older signature variants
            WalletService.credit(
                associate=assoc,
                wallet_type=wallet_type,
                amount=amount,
                reference=reference,
            )
        except Exception as exc:
            self.stdout.write(f"Credit {reference}: {exc}")
