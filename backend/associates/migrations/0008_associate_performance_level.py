from decimal import Decimal

from django.db import migrations, models


def backfill_performance_levels(apps, schema_editor):
    Associate = apps.get_model("associates", "Associate")
    PerformanceIncomePlan = apps.get_model("configuration", "PerformanceIncomePlan")
    PerformanceIncomeSlab = apps.get_model("configuration", "PerformanceIncomeSlab")

    plan = (
        PerformanceIncomePlan.objects.filter(is_deleted=False, is_active=True)
        .order_by("created_at")
        .first()
    )
    slabs = []
    if plan:
        slabs = list(
            PerformanceIncomeSlab.objects.filter(
                plan=plan, is_deleted=False, is_active=True
            ).order_by("level")
        )

    for assoc in Associate.objects.all().iterator():
        # Reward / earning rename cleanup: ensure name set
        if assoc.earning_level and not (assoc.earning_level_name or "").strip():
            assoc.earning_level_name = f"Level {assoc.earning_level}"
        if not assoc.earning_level:
            assoc.earning_level_name = assoc.earning_level_name or "No level"

        directs = int(assoc.direct_active_count or 0)
        volume = Decimal(assoc.total_business or 0)
        level = 0
        name = "No level"
        for slab in slabs:
            if directs < int(slab.required_directs or 0):
                break
            if volume < Decimal(slab.min_business or 0):
                break
            level = int(slab.level)
            name = f"Level {level}"
        assoc.performance_level = level
        assoc.performance_level_name = name
        assoc.save(
            update_fields=[
                "earning_level_name",
                "performance_level",
                "performance_level_name",
                "updated_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0007_associate_earning_level"),
        ("configuration", "0012_genealogy_10_leg_depth"),
    ]

    operations = [
        migrations.AddField(
            model_name="associate",
            name="performance_level",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=0,
                help_text="Performance Income level from active directs (0 = none).",
            ),
        ),
        migrations.AddField(
            model_name="associate",
            name="performance_level_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Performance level label, e.g. Level 3.",
                max_length=80,
            ),
        ),
        migrations.AlterField(
            model_name="associate",
            name="earning_level",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=0,
                help_text="Reward Achievement level from team business / Reward Master (0 = none).",
            ),
        ),
        migrations.AlterField(
            model_name="associate",
            name="earning_level_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Reward level label from Reward Master, e.g. Level 3.",
                max_length=80,
            ),
        ),
        migrations.RunPython(backfill_performance_levels, migrations.RunPython.noop),
    ]
