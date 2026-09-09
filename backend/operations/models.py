from decimal import Decimal

from django.conf import settings
from django.db import models

from associates.models import Associate
from core.models import BaseModel
from operations.upload_paths import (
    kyc_aadhaar_back,
    kyc_aadhaar_front,
    kyc_bank_document,
    kyc_pan_document,
    kyc_profile_photo,
)


class KYCSubmission(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    associate = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="kyc_submissions")
    full_name = models.CharField(max_length=160)
    pan = models.CharField(max_length=20)
    aadhaar = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=40)
    ifsc = models.CharField(max_length=20)
    upi_id = models.CharField(max_length=120, blank=True)
    profile_photo = models.ImageField(upload_to=kyc_profile_photo, blank=True, null=True)
    # Front of Aadhaar (legacy field name kept for API compatibility)
    aadhaar_document = models.FileField(
        upload_to=kyc_aadhaar_front,
        blank=True,
        null=True,
        help_text="Aadhaar front image",
        verbose_name="Aadhaar front",
    )
    aadhaar_back = models.FileField(
        upload_to=kyc_aadhaar_back,
        blank=True,
        null=True,
        help_text="Aadhaar back image. Both front + back required to count as attached.",
        verbose_name="Aadhaar back",
    )
    pan_document = models.FileField(upload_to=kyc_pan_document, blank=True, null=True)
    bank_document = models.FileField(upload_to=kyc_bank_document, blank=True, null=True)
    document_front = models.FileField(upload_to="kyc/", blank=True, null=True)
    document_back = models.FileField(upload_to="kyc/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="kyc_reviews"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "KYC submission"

    @property
    def aadhaar_front(self):
        """Alias: front side is stored in aadhaar_document."""
        return self.aadhaar_document

    @property
    def aadhaar_attached(self) -> bool:
        """True only when both front and back images are present."""
        return bool(self.aadhaar_document) and bool(self.aadhaar_back)


class DepositRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    associate = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    wallet_type = models.CharField(max_length=20, default="main")
    transaction_id = models.CharField(max_length=80, blank=True, db_index=True)
    payment_proof = models.FileField(upload_to="deposits/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="deposit_reviews"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class WithdrawalRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    associate = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    charge_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    net_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    bank_detail = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    requires_maker_checker = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_withdrawals",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="withdrawal_reviews"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    hold_ledger_entry = models.ForeignKey(
        "wallets.LedgerEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="withdrawal_holds",
    )
    refund_ledger_entry = models.ForeignKey(
        "wallets.LedgerEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="withdrawal_refunds",
    )

    class Meta:
        ordering = ["-created_at"]
