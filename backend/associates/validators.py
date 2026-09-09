from django.db.models import Q
from rest_framework import serializers

from associates.models import Associate
from configuration.repository import ConfigRepository


def validate_sponsor(sponsor_id: str) -> Associate:
    genealogy = ConfigRepository.genealogy()
    if genealogy.sponsor_required and not sponsor_id:
        raise serializers.ValidationError({"lead_reference": "Lead reference is mandatory."})

    key = sponsor_id.strip().upper()
    sponsor = (
        Associate.objects.filter(
            Q(associate_id__iexact=key) | Q(referral_code__iexact=key) | Q(user__username__iexact=key)
        )
        .select_related("user", "genealogy_node")
        .first()
    )
    if not sponsor:
        raise serializers.ValidationError({"lead_reference": "Invalid lead reference / sponsor username."})

    if sponsor.status == Associate.Status.BLOCKED:
        raise serializers.ValidationError({"lead_reference": "Lead / sponsor is blocked."})
    if sponsor.status in {Associate.Status.PENDING, Associate.Status.REJECTED}:
        raise serializers.ValidationError(
            {"lead_reference": "Lead join is not approved yet. They cannot introduce joiners."}
        )
    # Active and Inactive can both introduce joiners — status is not an access lock.

    max_legs = genealogy.effective_max_legs()
    if max_legs > 0:
        current_directs = sponsor.directs.filter(is_deleted=False).count()
        if current_directs >= max_legs:
            raise serializers.ValidationError(
                {
                    "lead_reference": (
                        f"This lead already has {current_directs}/{max_legs} directs "
                        f"(admin genealogy limit). Cannot add more under them."
                    )
                }
            )

    # Join depth (associate level under root) — raised in Genealogy settings (e.g. 100 / 200).
    max_depth = int(genealogy.max_depth or 0)
    if max_depth > 0:
        sponsor_node = getattr(sponsor, "genealogy_node", None)
        sponsor_depth = int(getattr(sponsor_node, "depth", 0) or 0) if sponsor_node else 0
        next_depth = sponsor_depth + 1
        if next_depth > max_depth:
            raise serializers.ValidationError(
                {
                    "lead_reference": (
                        f"This lead is at tree level {sponsor_depth}; new joiner would be "
                        f"level {next_depth}, but admin max join levels is {max_depth}. "
                        "Ask admin to raise Genealogy → Max join levels (e.g. 100 or 200)."
                    )
                }
            )

    return sponsor
