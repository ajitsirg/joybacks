from rest_framework.permissions import BasePermission


def has_finance_permission(user, *codes: str) -> bool:
    """Return whether an active Finance staff member has any required app permission."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, "staff_profile", None)
    if not user.is_staff or profile is None or profile.is_suspended:
        return False
    granted = profile.permission_codes()
    return any(code in granted for code in codes)


class FinancePermission(BasePermission):
    """DRF permission base for endpoints guarded by seeded Finance permissions."""

    permission_codes: tuple[str, ...] = ()

    def has_permission(self, request, view):
        return has_finance_permission(request.user, *self.permission_codes)
