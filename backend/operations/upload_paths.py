"""Unique media paths so browser caches do not keep stale profile/KYC images."""

from __future__ import annotations

import uuid
from pathlib import Path


def _unique(folder: str, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".bin"
    if len(ext) > 12:
        ext = ".bin"
    return f"{folder}/{uuid.uuid4().hex}{ext}"


def kyc_profile_photo(instance, filename: str) -> str:
    return _unique("kyc/profile", filename)


def kyc_aadhaar_front(instance, filename: str) -> str:
    return _unique("kyc/aadhaar/front", filename)


def kyc_aadhaar_back(instance, filename: str) -> str:
    return _unique("kyc/aadhaar/back", filename)


def kyc_pan_document(instance, filename: str) -> str:
    return _unique("kyc/pan", filename)


def kyc_bank_document(instance, filename: str) -> str:
    return _unique("kyc/bank", filename)
