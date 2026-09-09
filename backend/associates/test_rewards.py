"""Reward Achievement 40/30/30 qualification and payout."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from associates.rewards import compute_reward_level, pay_unlocked_rewards
from commissions.charges import net_after_charge
from configuration.rewards import REWARD_SLABS
from genealogy.services import GenealogyService
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()


class RewardAchievementTests(TestCase):
    def test_level_1_amounts_match_poster(self):
        s = REWARD_SLABS[0]
        self.assertEqual(s.total, Decimal("2500000"))
        self.assertEqual(s.leg1, Decimal("1000000"))
        self.assertEqual(s.leg2, Decimal("750000"))
        self.assertEqual(s.leg3, Decimal("750000"))
        self.assertEqual(s.reward, Decimal("75000"))
        self.assertEqual(len(REWARD_SLABS), 9)

    def test_total_alone_does_not_qualify(self):
        level, name = compute_reward_level(
            total_business=Decimal("2500000"),
            leg1=Decimal("2500000"),
            leg2=Decimal("0"),
            leg3=Decimal("0"),
        )
        self.assertEqual(level, 0)
        self.assertEqual(name, "No level")

    def test_level_1_needs_all_three_legs(self):
        level, _ = compute_reward_level(
            total_business=Decimal("2500000"),
            leg1=Decimal("1000000"),
            leg2=Decimal("750000"),
            leg3=Decimal("750000"),
        )
        self.assertEqual(level, 1)

    def test_level_2_amounts(self):
        level, _ = compute_reward_level(
            total_business=Decimal("5000000"),
            leg1=Decimal("2000000"),
            leg2=Decimal("1500000"),
            leg3=Decimal("1500000"),
        )
        self.assertEqual(level, 2)

    def test_old_14l_level_1_no_longer_qualifies(self):
        level, _ = compute_reward_level(
            total_business=Decimal("1400000"),
            leg1=Decimal("600000"),
            leg2=Decimal("400000"),
            leg3=Decimal("400000"),
        )
        self.assertEqual(level, 0)

    def _assoc(self, code: str, *, sponsor=None, business=Decimal("0")) -> Associate:
        user = User.objects.create_user(username=code.lower(), password="x", email=f"{code}@t.test")
        digits = "".join(ch for ch in code if ch.isdigit()) or "1"
        a = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}"[:20],
            mobile=(digits * 4)[:10],
            sponsor=sponsor,
            status=Associate.Status.ACTIVE,
            total_business=business,
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        WalletService.ensure_wallets(a)
        return a

    def test_sale_on_three_legs_pays_75000_reward(self):
        """M1 cash credits when three immediate legs hit 10L + 7.5L + 7.5L."""
        root = self._assoc("JOYRWDROOTS")
        l1 = self._assoc("JOYRWDSL1", sponsor=root, business=Decimal("0"))
        l2 = self._assoc("JOYRWDSL2", sponsor=root, business=Decimal("0"))
        l3 = self._assoc("JOYRWDSL3", sponsor=root, business=Decimal("0"))
        apply_investment_business(associate=l1, amount=Decimal("1100000"), reference="RWD-L1")
        apply_investment_business(associate=l2, amount=Decimal("825000"), reference="RWD-L2")
        apply_investment_business(associate=l3, amount=Decimal("825000"), reference="RWD-L3")
        root.refresh_from_db()
        self.assertEqual(root.earning_level, 1)
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))

    def test_pays_75000_once_on_level_1(self):
        root = self._assoc("JOYRWDROOT")
        self._assoc("JOYRWDLEG1", sponsor=root, business=Decimal("1000000"))
        self._assoc("JOYRWDLEG2", sponsor=root, business=Decimal("750000"))
        self._assoc("JOYRWDLEG3", sponsor=root, business=Decimal("750000"))
        root.total_business = Decimal("2500000")
        root.save(update_fields=["total_business"])
        root.sync_earning_level(save=True)
        root.refresh_from_db()
        self.assertEqual(root.earning_level, 1)
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))
        paid = pay_unlocked_rewards(associate=root, old_level=0, new_level=1)
        self.assertEqual(paid, 0)
        w.refresh_from_db()
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))

    def test_catchup_pays_when_level_already_set(self):
        root = self._assoc("JOYRWDROOTC")
        self._assoc("JOYRWDCL1", sponsor=root, business=Decimal("1000000"))
        self._assoc("JOYRWDCL2", sponsor=root, business=Decimal("750000"))
        self._assoc("JOYRWDCL3", sponsor=root, business=Decimal("750000"))
        root.total_business = Decimal("2500000")
        root.earning_level = 1
        root.earning_level_name = "Level 1"
        root.save(update_fields=["total_business", "earning_level", "earning_level_name"])
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(w.balance, Decimal("0.00"))
        root.sync_earning_level(save=True)
        w.refresh_from_db()
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))

    def test_sponsor_directs_count_without_full_genealogy(self):
        """Legs = all sponsor directs, even if only one child is on the tree."""
        root = self._assoc("JOYRWDROOTG")
        self._assoc("JOYRWDGL1", sponsor=root, business=Decimal("1000000"))
        for code, biz in (("JOYRWDGL2", Decimal("750000")), ("JOYRWDGL3", Decimal("750000"))):
            user = User.objects.create_user(
                username=code.lower(), password="x", email=f"{code}@t.test"
            )
            digits = "".join(ch for ch in code if ch.isdigit()) or "1"
            Associate.objects.create(
                user=user,
                associate_id=code,
                referral_code=f"R{code}"[:20],
                mobile=(digits * 4)[:10],
                sponsor=root,
                status=Associate.Status.ACTIVE,
                total_business=biz,
            )
        root.total_business = Decimal("1000000")
        root.save(update_fields=["total_business"])
        root.sync_earning_level(save=True)
        root.refresh_from_db()
        self.assertEqual(root.earning_level, 1)
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))

    def test_uneven_legs_do_not_qualify_even_if_total_matches(self):
        level, _ = compute_reward_level(
            total_business=Decimal("2500000"),
            leg1=Decimal("1400000"),
            leg2=Decimal("900000"),
            leg3=Decimal("200000"),
        )
        self.assertEqual(level, 0)

    def test_total_is_only_the_three_selected_legs(self):
        from associates.rewards import reward_snapshot

        root = self._assoc("JOYRWDROOTT")
        self._assoc("JOYRWDTA", sponsor=root, business=Decimal("800000"))
        self._assoc("JOYRWDTB", sponsor=root, business=Decimal("700000"))
        self._assoc("JOYRWDT3", sponsor=root, business=Decimal("600000"))
        self._assoc("JOYRWDT4", sponsor=root, business=Decimal("400000"))
        snap = reward_snapshot(root)
        self.assertEqual(snap["leg1"], Decimal("800000"))
        self.assertEqual(snap["leg2"], Decimal("700000"))
        self.assertEqual(snap["leg3"], Decimal("600000"))
        self.assertEqual(snap["total"], Decimal("2100000"))

    def test_locked_legs_ignore_a_stronger_fourth(self):
        from associates.models import RewardAchievement
        from associates.rewards import set_reward_legs

        root = self._assoc("JOYRWDROOTL")
        a = self._assoc("JOYRWDL1", sponsor=root, business=Decimal("1000000"))
        b = self._assoc("JOYRWDL2", sponsor=root, business=Decimal("750000"))
        c = self._assoc("JOYRWDL3", sponsor=root, business=Decimal("750000"))
        self._assoc("JOYRWDL4", sponsor=root, business=Decimal("2000000"))
        set_reward_legs(
            root,
            performer_ids=[a.associate_id, b.associate_id, c.associate_id],
        )
        root.sync_earning_level(save=True)
        root.refresh_from_db()
        self.assertEqual(root.earning_level, 1)
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))
        self.assertTrue(
            RewardAchievement.objects.filter(associate=root, milestone=1, is_deleted=False).exists()
        )

    def test_screenshot_acceptance_m2_yes_m3_pending(self):
        """Leg 1=1.012Cr, Leg 2=26.4L, Leg 3=19.8L → L1–L2 only. Reward = 75k+150k."""
        from associates.models import RewardAchievement
        from associates.rewards import reward_snapshot
        from commissions.models import CommissionEntry

        root = self._assoc("JOYRWDSNAP")
        self._assoc("JOYRWDS1", sponsor=root, business=Decimal("10120000"))
        self._assoc("JOYRWDS2", sponsor=root, business=Decimal("2640000"))
        self._assoc("JOYRWDS3", sponsor=root, business=Decimal("1980000"))
        snap = reward_snapshot(root)
        self.assertEqual(snap["total"], Decimal("14740000"))
        self.assertEqual(snap["level"], 2)
        self.assertEqual(len(snap["milestones"]), 9)
        by_sno = {row["sno"]: row for row in snap["milestones"]}
        self.assertEqual(by_sno[1]["status"], "achieved")
        self.assertEqual(by_sno[2]["status"], "achieved")
        self.assertEqual(by_sno[3]["status"], "pending")
        self.assertEqual(by_sno[4]["status"], "locked")
        self.assertEqual(by_sno[9]["status"], "locked")
        self.assertEqual(by_sno[3]["reward"], Decimal("400000"))
        self.assertFalse(by_sno[3]["leg2_ok"])
        self.assertFalse(by_sno[3]["leg3_ok"])
        self.assertTrue(by_sno[3]["total_ok"])
        self.assertEqual(by_sno[3]["remaining_leg2"], Decimal("360000"))
        self.assertEqual(by_sno[3]["remaining_leg3"], Decimal("1020000"))
        self.assertEqual(by_sno[3]["remaining_total"], Decimal("0"))
        self.assertEqual(by_sno[3]["remaining_leg1"], Decimal("0"))
        root.sync_earning_level(save=True)
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(
            w.balance,
            net_after_charge(Decimal("75000.00")) + net_after_charge(Decimal("150000.00")),
        )
        refs = list(
            CommissionEntry.objects.filter(beneficiary=root).values_list("reference", "amount")
        )
        self.assertEqual(
            sorted(refs),
            [
                (f"REWARD-M1-{root.associate_id}", Decimal("75000.00")),
                (f"REWARD-M2-{root.associate_id}", Decimal("150000.00")),
            ],
        )
        self.assertEqual(RewardAchievement.objects.filter(associate=root, is_deleted=False).count(), 2)

    def test_runtime_rewards_ignore_stale_master(self):
        from configuration.models import RewardMaster
        from configuration.rewards import official_reward_payload

        RewardMaster.objects.create(
            name="Level 1",
            milestone_number=1,
            sort_order=1,
            business_target=Decimal("1400000"),
            reward_amount=Decimal("10000"),
            is_active=True,
        )
        payload = official_reward_payload()
        self.assertEqual(payload[0]["reward_amount"], "75000")
        self.assertEqual(payload[1]["reward_amount"], "150000")
        self.assertEqual(payload[2]["reward_amount"], "400000")
        self.assertEqual(len(payload), 9)

    def test_stale_reward_master_amounts_are_ignored(self):
        from configuration.models import RewardMaster

        RewardMaster.objects.create(
            name="Level 1",
            milestone_number=1,
            sort_order=1,
            business_target=Decimal("1400000"),
            leg1_target=Decimal("600000"),
            leg2_target=Decimal("400000"),
            leg3_target=Decimal("400000"),
            reward_amount=Decimal("10000"),
            is_active=True,
        )
        root = self._assoc("JOYRWDBAD")
        self._assoc("JOYRWDB1", sponsor=root, business=Decimal("1000000"))
        self._assoc("JOYRWDB2", sponsor=root, business=Decimal("750000"))
        self._assoc("JOYRWDB3", sponsor=root, business=Decimal("750000"))
        root.sync_earning_level(save=True)
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.REWARD)
        self.assertEqual(w.balance, net_after_charge(Decimal("75000.00")))

    def test_legacy_l_reference_blocks_duplicate_m_payout(self):
        from commissions.models import CommissionEntry, CommissionRun
        from wallets.models import Wallet as W

        root = self._assoc("JOYRWDLEGACY")
        self._assoc("JOYRWDX1", sponsor=root, business=Decimal("1000000"))
        self._assoc("JOYRWDX2", sponsor=root, business=Decimal("750000"))
        self._assoc("JOYRWDX3", sponsor=root, business=Decimal("750000"))
        run = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.REWARD,
            status=CommissionRun.Status.COMPLETED,
            source_reference=f"REWARD-L1-{root.associate_id}",
            source_amount=Decimal("10000"),
        )
        CommissionEntry.objects.create(
            run=run,
            beneficiary=root,
            source_associate=root,
            level=1,
            percent=Decimal("0"),
            sale_amount=Decimal("2500000"),
            amount=Decimal("10000"),
            wallet_type=W.WalletType.REWARD,
            reference=f"REWARD-L1-{root.associate_id}",
            status=CommissionEntry.Status.CREDITED,
            narration="old",
        )
        root.sync_earning_level(save=True)
        w = Wallet.objects.get(associate=root, wallet_type=W.WalletType.REWARD)
        # Official M1 is ₹75,000; keep the old ₹10,000 row and top up ₹65,000 (net after 10%).
        self.assertEqual(w.balance, net_after_charge(Decimal("65000.00")))
        adj = CommissionEntry.objects.get(
            beneficiary=root, reference=f"REWARD-M1-ADJ-{root.associate_id}"
        )
        self.assertEqual(adj.amount, Decimal("65000.00"))

    def test_bare_legacy_l_ref_tops_up_without_duplicate(self):
        from commissions.models import CommissionEntry, CommissionRun
        from wallets.models import Wallet as W

        root = self._assoc("JOYRWDBARE")
        self._assoc("JOYRWDBA1", sponsor=root, business=Decimal("1000000"))
        self._assoc("JOYRWDBA2", sponsor=root, business=Decimal("750000"))
        self._assoc("JOYRWDBA3", sponsor=root, business=Decimal("750000"))
        run = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.REWARD,
            status=CommissionRun.Status.COMPLETED,
            source_reference="REWARD-L1",
            source_amount=Decimal("10000"),
        )
        CommissionEntry.objects.create(
            run=run,
            beneficiary=root,
            source_associate=root,
            level=1,
            percent=Decimal("0"),
            sale_amount=Decimal("2500000"),
            amount=Decimal("10000"),
            wallet_type=W.WalletType.REWARD,
            reference="REWARD-L1",
            status=CommissionEntry.Status.CREDITED,
            narration="old",
        )
        root.sync_earning_level(save=True)
        w = Wallet.objects.get(associate=root, wallet_type=W.WalletType.REWARD)
        self.assertEqual(w.balance, net_after_charge(Decimal("65000.00")))
        self.assertTrue(
            CommissionEntry.objects.filter(
                beneficiary=root, reference=f"REWARD-M1-ADJ-{root.associate_id}"
            ).exists()
        )
        self.assertEqual(
            CommissionEntry.objects.filter(beneficiary=root, level=1).count(),
            2,
        )
