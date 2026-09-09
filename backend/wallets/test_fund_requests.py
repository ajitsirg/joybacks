"""Associates request fund transfers; only staff can execute or approve."""

import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from associates.models import Associate
from commissions.constants import FARHOUSE_SALE_AMOUNT
from genealogy.services import GenealogyService
from wallets.models import FundTransferRequest, Wallet
from wallets.services import WalletService

User = get_user_model()
SALE = FARHOUSE_SALE_AMOUNT


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FundTransferRequestAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _proof(self, name="receipt.png"):
        return SimpleUploadedFile(name, b"fake-payment-proof", content_type="image/png")

    def _request_body(self, associate_id, amount, *, payment_method="upi", note="", utr="UTR12345678"):
        return {
            "associate_id": associate_id,
            "amount": str(amount),
            "payment_method": payment_method,
            "note": note,
            "utr": utr,
            "proof": self._proof(),
        }

    def _user(self, username: str, *, staff: bool = False) -> User:
        user = User.objects.create_user(
            username=username,
            password="x",
            email=f"{username}@t.test",
            is_staff=staff,
        )
        return user

    def _assoc(self, code: str, *, sponsor: Associate | None = None) -> Associate:
        user = self._user(code.lower())
        digits = "".join(ch for ch in code if ch.isdigit()) or "1"
        mobile = (digits * 4)[:10]
        a = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}"[:20],
            mobile=mobile,
            sponsor=sponsor,
            status=Associate.Status.ACTIVE,
            join_amount=SALE,
            personal_business=SALE,
            total_business=SALE,
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        WalletService.ensure_wallets(a)
        return a

    def _main(self, assoc: Associate) -> Wallet:
        return Wallet.objects.get(associate=assoc, wallet_type=Wallet.WalletType.MAIN)

    def test_associate_cannot_execute_fund_transfer(self):
        member = self._assoc("JOYFTREQ01")
        self.client.force_authenticate(user=member.user)
        resp = self.client.post(
            "/api/v1/wallets/transfer/",
            {
                "associate_id": member.associate_id,
                "amount": str(SALE),
                "payment_method": "upi",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("request", resp.data["detail"].lower())
        self.assertEqual(self._main(member).balance, Decimal("0.00"))

    def test_associate_creates_request_and_staff_approves(self):
        root = self._assoc("JOYFTREQ02")
        member = self._assoc("JOYFTREQ03", sponsor=root)
        staff = self._user("adminft", staff=True)
        WalletService.credit(
            associate=root,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED-REQ",
            narration="seed",
        )

        self.client.force_authenticate(user=root.user)
        created = self.client.post(
            "/api/v1/wallets/transfer/requests/",
            self._request_body(
                member.associate_id,
                SALE,
                note="Please credit my downline",
                utr="UPI1234567890",
            ),
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["status"], "pending")
        self.assertEqual(created.data["beneficiary_associate_id"], member.associate_id)
        self.assertEqual(created.data["utr"], "UPI1234567890")
        self.assertTrue(created.data["proof_url"])
        req_id = created.data["id"]
        self.assertEqual(self._main(root).balance, SALE)
        self.assertEqual(self._main(member).balance, Decimal("0.00"))

        self.client.force_authenticate(user=staff)
        denied = self.client.post(
            f"/api/v1/wallets/transfer/requests/{req_id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertIn("password", denied.data["detail"].lower())
        self.assertEqual(self._main(root).balance, SALE)

        wrong = self.client.post(
            f"/api/v1/wallets/transfer/requests/{req_id}/approve/",
            {"password": "not-the-password"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 403)
        self.assertIn("incorrect", wrong.data["detail"].lower())

        approved = self.client.post(
            f"/api/v1/wallets/transfer/requests/{req_id}/approve/",
            {"password": "x"},
            format="json",
        )
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], "approved")
        self.assertEqual(self._main(root).balance, Decimal("0.00"))
        self.assertEqual(self._main(member).balance, SALE)

        row = FundTransferRequest.objects.get(pk=req_id)
        self.assertEqual(row.reviewed_by_id, staff.id)

    def test_associate_cannot_request_self_transfer(self):
        member = self._assoc("JOYFTREQSELF")
        self.client.force_authenticate(user=member.user)
        created = self.client.post(
            "/api/v1/wallets/transfer/requests/",
            {
                "associate_id": member.associate_id,
                "amount": str(SALE),
                "payment_method": "upi",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 400, created.data)

    def test_associate_cannot_approve_own_request(self):
        root = self._assoc("JOYFTREQ04")
        child = self._assoc("JOYFTREQ04B", sponsor=root)
        WalletService.credit(
            associate=root,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED-OWN",
            narration="seed",
        )
        self.client.force_authenticate(user=root.user)
        created = self.client.post(
            "/api/v1/wallets/transfer/requests/",
            self._request_body(child.associate_id, SALE, payment_method="neft"),
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        denied = self.client.post(
            f"/api/v1/wallets/transfer/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self._main(root).balance, SALE)

    def test_request_requires_utr_and_proof(self):
        root = self._assoc("JOYFTUTR01")
        child = self._assoc("JOYFTUTR02", sponsor=root)
        WalletService.credit(
            associate=root,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED-UTR",
            narration="seed",
        )
        self.client.force_authenticate(user=root.user)
        missing = self.client.post(
            "/api/v1/wallets/transfer/requests/",
            {
                "associate_id": child.associate_id,
                "amount": str(SALE),
                "payment_method": "upi",
            },
            format="json",
        )
        self.assertEqual(missing.status_code, 400, missing.data)
        self.assertIn("utr", missing.data["detail"].lower())

        no_file = self.client.post(
            "/api/v1/wallets/transfer/requests/",
            {
                "associate_id": child.associate_id,
                "amount": str(SALE),
                "payment_method": "upi",
                "utr": "UTR99990001",
            },
            format="json",
        )
        self.assertEqual(no_file.status_code, 400, no_file.data)
        self.assertIn("upload", no_file.data["detail"].lower())

    def test_request_rejected_when_main_balance_is_zero(self):
        root = self._assoc("JOYFTNOBAL")
        child = self._assoc("JOYFTNOBAL2", sponsor=root)
        self.client.force_authenticate(user=root.user)
        created = self.client.post(
            "/api/v1/wallets/transfer/requests/",
            {
                "associate_id": child.associate_id,
                "amount": str(SALE),
                "payment_method": "upi",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 400, created.data)
        self.assertIn("not enough", created.data["detail"].lower())

    def test_staff_transfer_debits_sender_and_credits_recipient(self):
        sender = self._assoc("JOYFTFROM1")
        member = self._assoc("JOYFTREQ05", sponsor=sender)
        staff = self._user("adminft2", staff=True)
        WalletService.credit(
            associate=sender,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED-FROM",
            narration="seed",
        )
        self.client.force_authenticate(user=staff)
        resp = self.client.post(
            "/api/v1/wallets/transfer/",
            {
                "associate_id": member.associate_id,
                "from_associate_id": sender.associate_id,
                "wallet_type": "main",
                "amount": str(SALE),
                "payment_method": "upi",
                "apply_business": False,
                "narration": "Admin move",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(self._main(sender).balance, Decimal("0.00"))
        self.assertEqual(self._main(member).balance, SALE)

    def test_staff_company_mint_still_credits(self):
        member = self._assoc("JOYFTMINT1")
        staff = self._user("adminft3", staff=True)
        self.client.force_authenticate(user=staff)
        resp = self.client.post(
            "/api/v1/wallets/transfer/",
            {
                "associate_id": member.associate_id,
                "wallet_type": "main",
                "amount": str(SALE),
                "payment_method": "upi",
                "apply_business": False,
                "company_mint": True,
                "narration": "Admin credit",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(self._main(member).balance, SALE)
