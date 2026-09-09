from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0009_can_fund_transfer"),
    ]

    operations = [
        migrations.AddField(
            model_name="associate",
            name="login_password",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Last password set via the app (admin list/profile). "
                    "Login still uses Django’s hashed password — update both together."
                ),
                max_length=128,
            ),
        ),
    ]
