import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("associates", "0012_deleted_associate_proxy"),
    ]

    operations = [
        migrations.CreateModel(
            name="RewardLegAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("slot", models.PositiveSmallIntegerField(help_text="1, 2, or 3")),
                (
                    "locked",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "If on, this slot stays on the chosen member. "
                            "If off, the engine keeps the current top performer."
                        ),
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rewardlegassignment_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reward_leg_assignments",
                        to="associates.associate",
                    ),
                ),
                (
                    "performer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reward_leg_for",
                        to="associates.associate",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rewardlegassignment_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["slot"], "unique_together": {("owner", "slot")}},
        ),
        migrations.CreateModel(
            name="RewardAchievement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("milestone", models.PositiveSmallIntegerField(db_index=True)),
                ("total_business", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("leg1_business", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("leg2_business", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("leg3_business", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("reward_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("qualified_at", models.DateTimeField(auto_now_add=True)),
                ("credited_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("credited", "Credited"), ("pending", "Pending")],
                        default="credited",
                        max_length=20,
                    ),
                ),
                ("reference", models.CharField(db_index=True, max_length=80, unique=True)),
                (
                    "associate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reward_achievements",
                        to="associates.associate",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rewardachievement_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rewardachievement_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["associate", "milestone"]},
        ),
        migrations.AddConstraint(
            model_name="rewardachievement",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("associate", "milestone"),
                name="uniq_live_reward_achievement",
            ),
        ),
    ]
