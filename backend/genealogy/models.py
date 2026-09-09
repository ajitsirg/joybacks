"""Materialized path / closure table for unlimited-depth genealogy."""

from __future__ import annotations

from django.db import models

from associates.models import Associate
from core.models import BaseModel, UUIDModel, TimeStampedModel


class GenealogyNode(BaseModel):
    """One node per associate with path for fast subtree queries."""

    associate = models.OneToOneField(Associate, on_delete=models.CASCADE, related_name="genealogy_node")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    path = models.TextField(db_index=True, help_text="Materialized path e.g. /root/uuid/uuid/")
    depth = models.PositiveIntegerField(default=0, db_index=True)
    leg_index = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["path"]),
            models.Index(fields=["parent", "leg_index"]),
        ]

    def __str__(self) -> str:
        return f"Node[{self.associate.associate_id}] depth={self.depth}"


class GenealogyClosure(UUIDModel, TimeStampedModel):
    """Ancestor → descendant edges for O(1) upline / downline queries."""

    ancestor = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="descendant_links")
    descendant = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="ancestor_links")
    depth = models.PositiveIntegerField(db_index=True)

    class Meta:
        unique_together = ("ancestor", "descendant")
        indexes = [
            models.Index(fields=["ancestor", "depth"]),
            models.Index(fields=["descendant", "depth"]),
        ]
