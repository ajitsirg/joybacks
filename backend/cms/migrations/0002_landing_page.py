import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LandingPageSettings",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("eyebrow", models.CharField(default="Exclusive Channel Partner Invitation", max_length=120)),
                ("headline", models.CharField(default="Join Our Resort Villa Partner Network", max_length=200)),
                (
                    "intro",
                    models.TextField(
                        blank=True,
                        default=(
                            "We invite brokers, consultants, and channel partners to join our "
                            "Resort Villa Investment Project — designed for premium lifestyle assets "
                            "and high appreciation potential."
                        ),
                    ),
                ),
                ("investment_label", models.CharField(default="Investment starts at just", max_length=120)),
                ("investment_value", models.CharField(default="₹ 2 Lakh", max_length=80)),
                ("income_banner", models.CharField(default="One Time & Regular Income", max_length=160)),
                (
                    "cta_title",
                    models.CharField(
                        default="Join our channel partner network today and grow with us",
                        max_length=200,
                    ),
                ),
                (
                    "cta_body",
                    models.TextField(
                        blank=True,
                        default=(
                            "Partner with us to grow your business with transparent payouts "
                            "and long-term association."
                        ),
                    ),
                ),
                ("slogan", models.CharField(default="Build Wealth | Earn More | Grow Together", max_length=200)),
                ("phone", models.CharField(blank=True, default="+91 800 0928 080", max_length=40)),
                ("email", models.EmailField(blank=True, default="info@joyadventureresort.com", max_length=254)),
                ("website", models.CharField(blank=True, default="www.joyadventureresort.com", max_length=200)),
                ("address", models.TextField(blank=True, default="Joy Adventure Resort, Jaipur, Rajasthan")),
                (
                    "banner_image",
                    models.ImageField(
                        blank=True,
                        help_text="Optional wide banner. Recommended: 1200×675 px (16:9), JPG/WebP under 800 KB.",
                        null=True,
                        upload_to="landing/",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
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
                "verbose_name": "Landing page settings",
                "verbose_name_plural": "Landing page settings",
            },
        ),
        migrations.CreateModel(
            name="LandingBenefit",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=160)),
                ("body", models.CharField(blank=True, max_length=255)),
                (
                    "icon_key",
                    models.CharField(
                        default="trending",
                        help_text="Icon key: trending, money, users, clipboard, shield, handshake",
                        max_length=40,
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
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
                "verbose_name": "Landing benefit",
                "verbose_name_plural": "Landing benefits",
                "ordering": ["sort_order", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="LandingGalleryItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=160)),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Recommended: 800×500 px, JPG/WebP under 400 KB.",
                        null=True,
                        upload_to="landing/gallery/",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
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
                "verbose_name": "Landing gallery item",
                "verbose_name_plural": "Landing gallery",
                "ordering": ["sort_order", "created_at"],
            },
        ),
    ]
