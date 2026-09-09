from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0007_performance_income_poster"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="reward_poster_image",
            field=models.ImageField(
                blank=True,
                help_text=(
                    "Poster shown on Plans → Reward Achievement. "
                    "Recommended: 1200×675 px (16:9) or 1080×1350 px (4:5). JPG/WebP under 800 KB."
                ),
                null=True,
                upload_to="plans/reward-achievement/",
            ),
        ),
    ]
