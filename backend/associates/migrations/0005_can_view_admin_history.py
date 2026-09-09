from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0004_flag_gray_green_investment"),
    ]

    operations = [
        migrations.AddField(
            model_name="associate",
            name="can_view_admin_history",
            field=models.BooleanField(
                default=False,
                help_text="If on, this associate can see Fund → Admin History in the app. Off by default.",
            ),
        ),
    ]
