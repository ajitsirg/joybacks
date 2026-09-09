from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0009_company_require_leader_approval"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="require_join_otp",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If ON: Join shows OTP Verify (step 4) and registration requires a valid OTP. "
                    "If OFF (default): after KYC (step 3) the form submits and active members go to the dashboard."
                ),
            ),
        ),
    ]
