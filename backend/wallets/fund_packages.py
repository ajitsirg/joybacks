"""Fixed fund-transfer / top-up package amounts (₹ lakhs)."""

from __future__ import annotations

from decimal import Decimal

# 2.20, 4.40, 6.60, 11.00, 22.00, 44.00, 88.00 lakh
FUND_TRANSFER_AMOUNTS: tuple[Decimal, ...] = (
    Decimal("220000.00"),
    Decimal("440000.00"),
    Decimal("660000.00"),
    Decimal("1100000.00"),
    Decimal("2200000.00"),
    Decimal("4400000.00"),
    Decimal("8800000.00"),
)

FUND_TRANSFER_AMOUNT_SET = frozenset(FUND_TRANSFER_AMOUNTS)

# Payment / funding methods for fund transfer
PAYMENT_METHODS: tuple[tuple[str, str], ...] = (
    ("upi", "UPI"),
    ("bank_transfer", "Bank Transfer"),
    ("cheque", "Cheque"),
    ("neft", "NEFT"),
    ("imps", "IMPS"),
    ("rtgs", "RTGS"),
)

PAYMENT_METHOD_CODES = frozenset(code for code, _ in PAYMENT_METHODS)


def format_lakh(amount: Decimal) -> str:
    lakhs = amount / Decimal("100000")
    return f"₹{lakhs.quantize(Decimal('0.01'))} Lakh"


def is_fixed_fund_amount(amount: Decimal) -> bool:
    return amount in FUND_TRANSFER_AMOUNT_SET


def normalize_payment_method(raw: str | None) -> str:
    code = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "banktransfer": "bank_transfer",
        "bank": "bank_transfer",
    }
    code = aliases.get(code, code)
    if code not in PAYMENT_METHOD_CODES:
        raise ValueError(
            "Payment method must be one of: UPI, Bank Transfer, Cheque, NEFT, IMPS, RTGS"
        )
    return code


def payment_method_label(code: str) -> str:
    for c, label in PAYMENT_METHODS:
        if c == code:
            return label
    return code
