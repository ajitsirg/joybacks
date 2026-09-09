from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0008_associate_performance_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="associate",
            name="can_fund_transfer",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "If on, this associate can use Fund → Transfer for self and under-leg "
                    "with fixed package amounts. On by default for every associate."
                ),
            ),
        ),
    ]
