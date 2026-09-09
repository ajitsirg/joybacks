"""Shared base models for JoyClub Associate."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def delete(self, soft: bool = True, *, force: bool = False):
        # Default: soft-delete. Admin purge may pass force=True to hard-delete.
        from django.conf import settings

        if force:
            return super().delete()
        if not soft and not settings.DEBUG:
            soft = True
        if soft:
            return super().update(is_deleted=True, deleted_at=timezone.now())
        return super().delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteAllManager(models.Manager):
    """Includes soft-deleted rows; queryset still supports soft/force delete."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AuditUserModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteAllManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, soft: bool = True, *, force: bool = False):
        # Default: soft-delete. Admin purge may pass force=True to hard-delete.
        if force:
            return super().delete(using=using, keep_parents=keep_parents)
        if not soft and not settings.DEBUG:
            soft = True
        if soft:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=["is_deleted", "deleted_at"])
            return (1, {self._meta.label: 1})
        return super().delete(using=using, keep_parents=keep_parents)


class BaseModel(UUIDModel, TimeStampedModel, AuditUserModel, SoftDeleteModel):
    """Canonical enterprise base for all domain tables."""

    class Meta:
        abstract = True
