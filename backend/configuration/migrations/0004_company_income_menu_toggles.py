from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0003_company_join_kyc_requirements"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="show_income_section",
            field=models.BooleanField(
                default=False,
                help_text="Show the Income menu (Referral / ROI / Reward). Off = hidden.",
            ),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="show_income_sp_profit",
            field=models.BooleanField(
                default=False,
                help_text="Show S.P. Profit under Income. Off = hidden.",
            ),
        ),
    ]
