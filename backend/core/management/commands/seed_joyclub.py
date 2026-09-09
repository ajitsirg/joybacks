"""Seed JoyClub Associate with configurable MLM defaults (no hardcoded runtime logic)."""

from __future__ import annotations

import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Permission, Role, StaffProfile, User
from associates.models import Associate
from configuration.models import (
    CompanySettings,
    GenealogySettings,
    LevelIncomePlan,
    LevelIncomeSlab,
    PerformanceIncomePlan,
    PerformanceIncomeSlab,
    ROIPlan,
    WithdrawalSettings,
)
from genealogy.services import GenealogyService
from wallets.services import WalletService

PERMISSIONS = [
    ("users.view", "View Users", "users"),
    ("users.manage", "Manage Users", "users"),
    ("associates.view", "View Associates", "associates"),
    ("associates.manage", "Manage Associates", "associates"),
    ("withdrawals.view", "View Withdrawals", "withdrawals"),
    ("withdrawals.approve", "Approve Withdrawals", "withdrawals"),
    ("deposits.view", "View Deposits", "deposits"),
    ("deposits.approve", "Approve Deposits", "deposits"),
    ("kyc.view", "View KYC", "kyc"),
    ("kyc.approve", "Approve KYC", "kyc"),
    ("kyc.reject", "Reject KYC", "kyc"),
    ("income.view", "View Income", "income"),
    ("reports.view", "View Reports", "reports"),
    ("settings.manage", "Manage Settings", "settings"),
    ("rbac.manage", "Manage RBAC", "rbac"),
    ("audit.view", "View Audit", "audit"),
    ("genealogy.view", "View Genealogy", "genealogy"),
    ("wallets.view", "View Wallets", "wallets"),
    ("wallets.transfer", "Transfer Funds", "wallets"),
    ("fund.view", "View Fund", "fund"),
    ("fund.transfer", "Transfer Funds", "fund"),
    ("commissions.run", "Run Commissions", "commissions"),
    ("rewards.manage", "Manage Rewards", "rewards"),
]

# Farmhouse level income: unlock by direct sales; % editable in admin
LEVEL_DEFAULTS = [
    (1, "5.0000"),
    (2, "2.5000"),
    (3, "2.0000"),
    (4, "1.0000"),
    (5, "0.5000"),
]

PERF_DEFAULTS = [
    (1, "5.0000", 1),
    (2, "2.5000", 2),
    (3, "2.0000", 3),
    (4, "2.0000", 4),
    (5, "1.0000", 5),
    (6, "1.0000", 6),
    (7, "0.5000", 7),
    (8, "0.5000", 8),
    (9, "0.2500", 9),
    (10, "0.2500", 10),
]

# Joy Adventure Resort — Reward Achievement (from configuration.rewards)


class Command(BaseCommand):
    help = "Seed company settings, plans, RBAC, and root associate"

    @transaction.atomic
    def handle(self, *args, **options):
        UserModel = get_user_model()

        company = CompanySettings.objects.filter(name="JoyClub Associate").order_by("id").first()
        if company is None:
            company = CompanySettings.objects.create(
                name="JoyClub Associate",
                theme_primary="#2563EB",
                theme_accent="#10B981",
                currency_code="INR",
                currency_symbol="₹",
                support_email="support@joyclub.associate",
            )
        self.stdout.write(f"Company: {company.name}")

        if not GenealogySettings.objects.filter(name="Default Genealogy").exists():
            GenealogySettings.objects.create(
                name="Default Genealogy",
                leg_mode="10",
                max_legs=10,
                max_depth=200,
                sponsor_required=True,
            )
        if not WithdrawalSettings.objects.filter(name="Default Withdrawal").exists():
            WithdrawalSettings.objects.create(
                name="Default Withdrawal",
                min_amount=Decimal("500"),
                max_amount=Decimal("500000"),
                charge_percent=Decimal("2.000"),
                maker_checker_threshold=Decimal("50000"),
            )

        level_plan, _ = LevelIncomePlan.objects.get_or_create(
            code="direct-level",
            defaults={
                "name": "Direct Level Income",
                "max_levels": 5,
                "is_active": True,
                "description": (
                    "Farmhouse level income (₹2,20,000 per sale). "
                    "Direct qualifying sales unlock levels 1–5; "
                    "rates: 5% / 2.5% / 2% / 1% / 0.5%."
                ),
            },
        )
        level_plan.max_levels = 5
        level_plan.is_active = True
        level_plan.description = (
            "Farmhouse level income (₹2,20,000 per sale). "
            "Direct qualifying sales unlock levels 1–5; "
            "rates: 5% / 2.5% / 2% / 1% / 0.5%."
        )
        level_plan.save(update_fields=["max_levels", "is_active", "description", "updated_at"])
        for level, pct in LEVEL_DEFAULTS:
            LevelIncomeSlab.objects.update_or_create(
                plan=level_plan,
                level=level,
                defaults={"percent": Decimal(pct), "is_active": True},
            )

        perf_plan, _ = PerformanceIncomePlan.objects.get_or_create(
            code="performance-10",
            defaults={"name": "Performance Income", "max_levels": 10, "is_active": True},
        )
        for level, pct, directs in PERF_DEFAULTS:
            PerformanceIncomeSlab.objects.update_or_create(
                plan=perf_plan,
                level=level,
                defaults={
                    "percent": Decimal(pct),
                    "required_directs": directs,
                    "is_active": True,
                },
            )

        ROIPlan.objects.filter(code="daily-roi").update(is_active=False)
        ROIPlan.objects.update_or_create(
            code="monthly-roi-48",
            defaults={
                "name": "Monthly ROI 48 Months",
                "percent": Decimal("1.0000"),
                "cycle_days": 30,
                "is_active": True,
                "description": (
                    "₹2,20,000 investment earns ₹2,200/month for 48 months. "
                    "Upline Growth Levels 1–10 earn % of each ₹2,200 monthly return."
                ),
            },
        )

        from configuration.rewards import sync_official_milestones

        sync_official_milestones()

        for code, name, module in PERMISSIONS:
            Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "module": module},
            )

        super_role, _ = Role.objects.get_or_create(
            name="Super Admin",
            defaults={"description": "Full access", "is_system": True},
        )
        super_role.permissions.set(Permission.objects.all())

        from accounts.rbac_seed import ensure_admin_role, ensure_finance_manager_role

        ensure_admin_role()
        ensure_finance_manager_role()

        admin_user, created = UserModel.objects.get_or_create(
            email="admin@joyclub.associate",
            defaults={
                "username": "admin",
                "first_name": "JoyClub",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "user_type": User.UserType.STAFF,
            },
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
        profile, _ = StaffProfile.objects.get_or_create(
            user=admin_user,
            defaults={"employee_code": "JC-ADMIN-001"},
        )
        profile.roles.add(super_role)

        # Root / company associate (sponsors first registrations)
        root_user, root_created = UserModel.objects.get_or_create(
            email="root@joyclub.associate",
            defaults={
                "username": "root",
                "first_name": "Company",
                "last_name": "Root",
                "user_type": User.UserType.ASSOCIATE,
            },
        )
        if root_created:
            root_user.set_password("admin123")
            root_user.save()

        root, root_assoc_created = Associate.objects.get_or_create(
            user=root_user,
            defaults={
                "associate_id": "JOY00000001",
                "referral_code": "JOYROOT1",
                "status": Associate.Status.ACTIVE,
                "mobile": "9999999999",
                "lead_reference": "COMPANY",
                "join_amount": Decimal("220000"),
                "card_tier": Associate.CardTier.PLATINUM,
                "flag_color": Associate.FlagColor.GREEN,
            },
        )
        # Normalize IDs → JOY + mobile scheme
        root.associate_id = "JOY00000001"
        root.referral_code = "JOYROOT1"
        root.mobile = "9999999999"
        root.lead_reference = root.lead_reference or "COMPANY"
        root.join_amount = Decimal("220000")
        root.card_tier = Associate.CardTier.PLATINUM
        root.flag_color = Associate.FlagColor.GREEN
        root.status = Associate.Status.ACTIVE
        if not (root.login_password or "").strip():
            root.login_password = "admin123"
        root.save()
        root_user.username = "JOY00000001"
        root_user.phone = "9999999999"
        if not root_user.has_usable_password() or root_created:
            root_user.set_password("admin123")
            root.login_password = "admin123"
            root.save(update_fields=["login_password"])
        root_user.save()
        GenealogyService.ensure_root(root)
        WalletService.ensure_wallets(root)

        from cms.models import HelpTicket, NewsItem, QRWalletSetting
        from genealogy.models import GenealogyClosure
        from notifications.models import Notification
        from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
        from operations.services import DepositService

        NewsItem.objects.get_or_create(
            title="Welcome to JoyClub Associate",
            defaults={"body": "Your multilevel MLM platform is live. All commission rules are admin-configurable.", "is_published": True},
        )
        QRWalletSetting.objects.get_or_create(
            label="UPI Primary",
            defaults={"wallet_address": "joyclub@upi", "is_active": True},
        )
        HelpTicket.objects.get_or_create(
            subject="How do I activate my ID?",
            defaults={"body": "Complete KYC and first deposit to activate.", "email": "member@example.com", "status": "open"},
        )

        # Keep company root on the genealogy graph even without demo members
        GenealogyService.ensure_root(root)

        # Demo tree is OFF by default (production shows real associates only).
        # Set SEED_DEMO_TREE=1 for local/staging sample data.
        seed_demo = os.environ.get("SEED_DEMO_TREE", "0").strip() in {"1", "true", "True", "yes", "YES"}
        if not seed_demo:
            for a in Associate.objects.all():
                a.direct_count = a.directs.filter(is_deleted=False).count()
                a.direct_active_count = a.directs.filter(
                    status=Associate.Status.ACTIVE, is_deleted=False
                ).count()
                a.save(update_fields=["direct_count", "direct_active_count", "updated_at"])
            Notification.objects.get_or_create(
                user=admin_user,
                title="Platform seeded",
                defaults={"body": "Company settings ready. Associate Tree uses live members only.", "channel": "in_app"},
            )
            self.stdout.write(self.style.SUCCESS("JoyClub Associate seed complete (no demo tree)."))
            self.stdout.write("Staff: admin@joyclub.associate / admin123")
            self.stdout.write(f"Root lead username: {root.associate_id} mobile {root.mobile} password admin123")
            return

        # One-time demo tree (active) so Associate Tree is visible in staging.
        # sponsor_key: "root" | associate_id of parent already in this list
        # (email, first, last, aid, mobile, join_amount, sponsor_key)
        demo_people = [
            ("amit@joyclub.demo", "Amit", "Sharma", "JOY10000001", "9811111111", Decimal("220000"), "root"),
            ("neha@joyclub.demo", "Neha", "Patel", "JOY10000002", "9822222222", Decimal("22000"), "JOY10000001"),
            ("vikram@joyclub.demo", "Vikram", "Singh", "JOY10000003", "9833333333", Decimal("0"), "JOY10000001"),
            ("riya@joyclub.demo", "Riya", "Kapoor", "JOY10000004", "9844444444", Decimal("22000"), "JOY10000001"),
            ("arjun@joyclub.demo", "Arjun", "Mehta", "JOY10000005", "9855555555", Decimal("220000"), "JOY10000002"),
            ("kavya@joyclub.demo", "Kavya", "Nair", "JOY10000006", "9866666666", Decimal("22000"), "JOY10000002"),
            ("rohan@joyclub.demo", "Rohan", "Das", "JOY10000007", "9877777777", Decimal("0"), "JOY10000004"),
            ("isha@joyclub.demo", "Isha", "Verma", "JOY10000008", "9888888888", Decimal("220000"), "JOY10000004"),
            ("dev@joyclub.demo", "Dev", "Joshi", "JOY10000009", "9899999999", Decimal("22000"), "JOY10000005"),
            ("meera@joyclub.demo", "Meera", "Shah", "JOY10000010", "9800000001", Decimal("0"), "JOY10000005"),
        ]
        from associates.models import tier_from_amount

        by_id: dict[str, Associate] = {root.associate_id: root}
        for idx, (email, first, last, aid, mobile, join_amt, sponsor_key) in enumerate(demo_people):
            sponsor = root if sponsor_key == "root" else by_id.get(sponsor_key, root)
            tier, flag = tier_from_amount(join_amt)
            user, ucreated = UserModel.objects.get_or_create(
                email=email,
                defaults={
                    "username": aid,
                    "first_name": first,
                    "last_name": last,
                    "phone": mobile,
                    "user_type": User.UserType.ASSOCIATE,
                },
            )
            user.username = aid
            user.phone = mobile
            if ucreated:
                user.set_password("demo1234")
            user.save()
            assoc, acreated = Associate.objects.get_or_create(
                user=user,
                defaults={
                    "associate_id": aid,
                    "sponsor": sponsor,
                    "sponsor_associate_id": sponsor.associate_id,
                    "lead_reference": sponsor.associate_id,
                    "status": Associate.Status.ACTIVE,
                    "mobile": mobile,
                    "kyc_verified": True,
                    "join_amount": join_amt,
                    "card_tier": tier,
                    "flag_color": flag,
                    "login_password": "demo1234",
                },
            )
            assoc.associate_id = aid
            assoc.mobile = mobile
            assoc.sponsor = sponsor
            assoc.sponsor_associate_id = sponsor.associate_id
            assoc.lead_reference = sponsor.associate_id
            assoc.join_amount = join_amt
            assoc.card_tier = tier
            assoc.flag_color = flag
            assoc.status = Associate.Status.ACTIVE
            assoc.kyc_verified = True
            if ucreated or not (assoc.login_password or "").strip():
                assoc.login_password = "demo1234"
            assoc.save()
            WalletService.ensure_wallets(assoc)
            by_id[aid] = assoc

            KYCSubmission.objects.get_or_create(
                associate=assoc,
                status=KYCSubmission.Status.APPROVED,
                defaults={
                    "full_name": f"{first} {last}",
                    "pan": f"ABCDE{1000+idx}F",
                    "aadhaar": f"XXXX-XXXX-{1000+idx}",
                    "bank_name": "HDFC Bank",
                    "account_number": f"50100{idx:06d}",
                    "ifsc": "HDFC0001234",
                },
            )

            # Pending samples for admin queues
            if idx == 0:
                DepositRequest.objects.get_or_create(
                    associate=assoc,
                    transaction_id="TXN-DEMO-PENDING-1",
                    defaults={"amount": Decimal("10000"), "wallet_type": "main", "status": DepositRequest.Status.PENDING},
                )
                KYCSubmission.objects.get_or_create(
                    associate=assoc,
                    status=KYCSubmission.Status.PENDING,
                    defaults={
                        "full_name": f"{first} {last}",
                        "pan": f"PEND{1000+idx}F",
                        "aadhaar": "XXXX-XXXX-9999",
                        "bank_name": "ICICI Bank",
                        "account_number": "50100999999",
                        "ifsc": "ICIC0001234",
                    },
                )

            # Completed deposits to drive commissions/business (idempotent via txn id)
            dep, dcreated = DepositRequest.objects.get_or_create(
                associate=assoc,
                transaction_id=f"TXN-DEMO-DONE-{aid}",
                defaults={
                    "amount": Decimal("5000") + Decimal(idx * 1000),
                    "wallet_type": "main",
                    "status": DepositRequest.Status.PENDING,
                },
            )
            if dcreated or dep.status == DepositRequest.Status.PENDING:
                try:
                    DepositService.approve(dep, actor=admin_user)
                except Exception:
                    pass

        # Rebuild demo genealogy to match sponsor links (fixes older seed drift)
        tree_pairs = []
        for _email, _first, _last, aid, _mobile, _join_amt, sponsor_key in demo_people:
            assoc = by_id[aid]
            sponsor = root if sponsor_key == "root" else by_id[sponsor_key]
            tree_pairs.append((assoc, sponsor))
        GenealogyService.rebuild_tree(tree_pairs)

        # Refresh direct counts
        for a in Associate.objects.all():
            a.direct_count = a.directs.filter(is_deleted=False).count()
            a.direct_active_count = a.directs.filter(status=Associate.Status.ACTIVE, is_deleted=False).count()
            a.save(update_fields=["direct_count", "direct_active_count", "updated_at"])

        Notification.objects.get_or_create(
            user=admin_user,
            title="Platform seeded",
            defaults={"body": "Demo associates, deposits and commissions are ready.", "channel": "in_app"},
        )

        # Sample withdrawal pending
        demo_assoc = Associate.objects.filter(associate_id="JOY10000001").first()
        if demo_assoc:
            from wallets.models import Wallet
            from wallets.services import WalletService as WS

            WS.ensure_wallets(demo_assoc)
            w = Wallet.objects.get(associate=demo_assoc, wallet_type=Wallet.WalletType.WITHDRAW)
            if w.balance < Decimal("2000"):
                WS.credit(
                    associate=demo_assoc,
                    wallet_type=Wallet.WalletType.WITHDRAW,
                    amount=Decimal("5000"),
                    reference="SEED-WD",
                    narration="Seed withdraw wallet",
                )
            if not WithdrawalRequest.objects.filter(associate=demo_assoc, status=WithdrawalRequest.Status.PENDING).exists():
                from operations.services import WithdrawalService

                try:
                    WithdrawalService.create(associate=demo_assoc, amount=Decimal("1500"), bank_detail="HDFC ****1234")
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS("JoyClub Associate seed complete."))
        self.stdout.write("Staff: admin@joyclub.associate / admin123")
        self.stdout.write(f"Root lead username: {root.associate_id} mobile {root.mobile} password admin123")
        self.stdout.write("Associate login: JOY-username + password demo1234")

