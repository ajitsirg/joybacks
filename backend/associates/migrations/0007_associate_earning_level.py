from decimal import Decimal

from django.db import migrations, models


def backfill_earning_levels(apps, schema_editor):
    Associate = apps.get_model("associates", "Associate")
    RewardMaster = apps.get_model("configuration", "RewardMaster")
    qs = RewardMaster.objects.filter(is_deleted=False, is_active=True).order_by(
        "business_target", "sort_order"
    )
    level_rows = list(qs.filter(name__istartswith="Level "))
    rewards = level_rows or list(qs)
    for assoc in Associate.objects.all().iterator():
        volume = Decimal(assoc.total_business or 0)
        level = 0
        name = "No level"
        for reward in rewards:
            if volume < Decimal(reward.business_target or 0):
                break
            digits = "".join(ch for ch in (reward.name or "") if ch.isdigit())
            n = int(digits) if digits else int(reward.sort_order or 0) or (level + 1)
            level = n
            name = reward.name or f"Level {n}"
        if assoc.earning_level != level or assoc.earning_level_name != name:
            assoc.earning_level = level
            assoc.earning_level_name = name
            assoc.save(update_fields=["earning_level", "earning_level_name", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0006_can_view_reward_achievers"),
        ("configuration", "0012_genealogy_10_leg_depth"),
    ]

    operations = [
        migrations.AddField(
            model_name="associate",
            name="earning_level",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=0,
                help_text="Highest Reward Achievement level earned from team business (0 = none).",
            ),
        ),
        migrations.AddField(
            model_name="associate",
            name="earning_level_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Display name from Reward Master, e.g. Level 3.",
                max_length=80,
            ),
        ),
        migrations.RunPython(backfill_earning_levels, migrations.RunPython.noop),
    ]
