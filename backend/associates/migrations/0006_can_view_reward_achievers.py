from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0005_can_view_admin_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="associate",
            name="can_view_reward_achievers",
            field=models.BooleanField(
                default=False,
                help_text="If on, this associate can see Users → Reward Achievers in the app. Off by default.",
            ),
        ),
    ]
