from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0004_company_income_menu_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="show_income_referral",
            field=models.BooleanField(
                default=False,
                help_text="Show Level / Referral Income. Off = hidden.",
            ),
        ),
        migrations.AlterField(
            model_name="companysettings",
            name="show_income_section",
            field=models.BooleanField(
                default=False,
                help_text="Show ROI Level Income and Reward Income. Off = hidden.",
            ),
        ),
    ]
