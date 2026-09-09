from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0012_genealogy_10_leg_depth"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="show_users_flag_column",
            field=models.BooleanField(
                default=False,
                help_text="Show Flag (Invested / No investment) column on Users tables. Off = hidden.",
                verbose_name="Show Flag column (Users tables)",
            ),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="show_users_card_column",
            field=models.BooleanField(
                default=False,
                help_text="Show Card (Platinum / Silver / Gray) column on Users tables. Off = hidden.",
                verbose_name="Show Card column (Users tables)",
            ),
        ),
    ]
