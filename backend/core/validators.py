"""Shared email / mobile validation for JoyClub (India-first)."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator

# Indian mobile: 10 digits, starts with 6–9
_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
_EMAIL_VALIDATOR = EmailValidator(message="Enter a valid email address.")


def normalize_mobile(value: str | None) -> str:
    """Strip non-digits; drop leading 91 / 0 when a 10-digit number remains."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def validate_mobile(value: str | None) -> str:
    """Return normalized 10-digit Indian mobile or raise ValidationError."""
    mobile = normalize_mobile(value)
    if not _MOBILE_RE.match(mobile):
        raise DjangoValidationError(
            "Enter a valid 10-digit Indian mobile number (starts with 6–9)."
        )
    return mobile


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def validate_email_address(value: str | None, *, required: bool = False) -> str:
    """Return normalized email, or '' if blank and not required."""
    email = normalize_email(value)
    if not email:
        if required:
            raise DjangoValidationError("Email is required.")
        return ""
    try:
        _EMAIL_VALIDATOR(email)
    except DjangoValidationError as exc:
        raise DjangoValidationError("Enter a valid email address.") from exc
    return email
