from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="show_platinum_package",
            field=models.BooleanField(
                default=False,
                help_text="Show Platinum (₹2,00,000) option on Join / Register",
            ),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="show_silver_package",
            field=models.BooleanField(
                default=False,
                help_text="Show Silver (₹20,000) option on Join / Register",
            ),
        ),
    ]
