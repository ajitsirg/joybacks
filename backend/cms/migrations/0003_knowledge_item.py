import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0002_landing_page"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField(blank=True, help_text="Steps or short description.")),
                (
                    "audience",
                    models.CharField(
                        choices=[
                            ("all", "Everyone"),
                            ("associate", "Associates"),
                            ("staff", "Admin / Staff"),
                            ("finance", "Finance Manager"),
                        ],
                        db_index=True,
                        default="all",
                        max_length=20,
                    ),
                ),
                (
                    "media_type",
                    models.CharField(
                        choices=[
                            ("pdf", "PDF"),
                            ("image", "Image"),
                            ("video", "Video"),
                            ("link", "Video link"),
                        ],
                        default="pdf",
                        max_length=20,
                    ),
                ),
                ("file", models.FileField(blank=True, null=True, upload_to="knowledge/%Y/%m/")),
                ("video_url", models.URLField(blank=True, help_text="YouTube / Vimeo link if no file.")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_published", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Knowledge item",
                "verbose_name_plural": "Knowledge center",
                "ordering": ["sort_order", "-created_at"],
            },
        ),
    ]
