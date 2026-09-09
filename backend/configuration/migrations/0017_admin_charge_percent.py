from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0016_reward_milestone_legs"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="admin_charge_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("10.00"),
                help_text="Percent taken as company admin charge on sale, ROI, and reward commissions.",
                max_digits=5,
            ),
        ),
    ]
