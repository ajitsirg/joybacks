from decimal import Decimal

from django.db import migrations, models


def forwards_flags(apps, schema_editor):
    Associate = apps.get_model("associates", "Associate")
    for row in Associate.objects.all().iterator():
        invested = Decimal(row.join_amount or 0) > 0 or Decimal(row.personal_business or 0) > 0
        flag = "green" if invested else "gray"
        if row.flag_color != flag:
            row.flag_color = flag
            row.save(update_fields=["flag_color"])


def backwards_flags(apps, schema_editor):
    Associate = apps.get_model("associates", "Associate")
    Associate.objects.filter(flag_color="gray").update(flag_color="pink")


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0003_join_leader_approval"),
    ]

    operations = [
        migrations.AlterField(
            model_name="associate",
            name="flag_color",
            field=models.CharField(
                choices=[
                    ("green", "Green — has investment"),
                    ("gray", "Gray — joined, no investment"),
                    ("blue", "Blue (legacy)"),
                    ("pink", "Pink (legacy)"),
                ],
                db_index=True,
                default="gray",
                max_length=20,
            ),
        ),
        migrations.RunPython(forwards_flags, backwards_flags),
    ]
