from decimal import Decimal

from django.db import migrations, models


SLABS = {
    1: (Decimal("1400000"), Decimal("600000"), Decimal("400000"), Decimal("400000"), Decimal("30000")),
    2: (Decimal("2500000"), Decimal("1000000"), Decimal("750000"), Decimal("750000"), Decimal("75000")),
    3: (Decimal("5000000"), Decimal("2000000"), Decimal("1500000"), Decimal("1500000"), Decimal("150000")),
    4: (Decimal("10000000"), Decimal("4000000"), Decimal("3000000"), Decimal("3000000"), Decimal("400000")),
    5: (Decimal("20000000"), Decimal("8000000"), Decimal("6000000"), Decimal("6000000"), Decimal("1000000")),
    6: (Decimal("50000000"), Decimal("20000000"), Decimal("15000000"), Decimal("15000000"), Decimal("3000000")),
    7: (Decimal("100000000"), Decimal("40000000"), Decimal("30000000"), Decimal("30000000"), Decimal("6000000")),
    8: (Decimal("200000000"), Decimal("80000000"), Decimal("60000000"), Decimal("60000000"), Decimal("10000000")),
    9: (Decimal("500000000"), Decimal("200000000"), Decimal("150000000"), Decimal("150000000"), Decimal("25000000")),
    10: (Decimal("1000000000"), Decimal("400000000"), Decimal("300000000"), Decimal("300000000"), Decimal("50000000")),
}


def backfill_leg_targets(apps, schema_editor):
    RewardMaster = apps.get_model("configuration", "RewardMaster")
    for row in RewardMaster.objects.all():
        n = int(row.milestone_number or row.sort_order or 0)
        if not n:
            name = (row.name or "").strip().lower()
            if name.startswith("level "):
                try:
                    n = int(name.split()[1])
                except (IndexError, ValueError):
                    n = 0
        slab = SLABS.get(n)
        if not slab:
            continue
        total, l1, l2, l3, reward = slab
        row.milestone_number = n
        row.sort_order = n
        if not row.leg1_target:
            row.leg1_target = l1
        if not row.leg2_target:
            row.leg2_target = l2
        if not row.leg3_target:
            row.leg3_target = l3
        if not row.business_target:
            row.business_target = total
        if not row.reward_amount:
            row.reward_amount = reward
        row.save()


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0015_aadhaar_front_back_help"),
    ]

    operations = [
        migrations.AddField(
            model_name="rewardmaster",
            name="milestone_number",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=0,
                help_text="S.No. in the Reward Achievement table (1–10).",
            ),
        ),
        migrations.AddField(
            model_name="rewardmaster",
            name="leg1_target",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=16),
        ),
        migrations.AddField(
            model_name="rewardmaster",
            name="leg2_target",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=16),
        ),
        migrations.AddField(
            model_name="rewardmaster",
            name="leg3_target",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=16),
        ),
        migrations.AlterField(
            model_name="rewardmaster",
            name="business_target",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Total business target (Leg 1 + Leg 2 + Leg 3).",
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name="rewardmaster",
            name="leg_business",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Legacy single-leg target. Prefer Leg 1 / 2 / 3 targets below.",
                max_digits=16,
            ),
        ),
        migrations.RunPython(backfill_leg_targets, migrations.RunPython.noop),
    ]
