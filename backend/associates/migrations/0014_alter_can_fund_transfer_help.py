from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("associates", "0013_reward_legs_and_achievements"),
    ]

    operations = [
        migrations.AlterField(
            model_name="associate",
            name="can_fund_transfer",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Unused. Associates can only request a fund transfer; "
                    "only staff can execute."
                ),
            ),
        ),
    ]
