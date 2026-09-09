from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0006_level_income_poster"),
    ]

    operations = [
        migrations.AddField(
            model_name="performanceincomeplan",
            name="poster_image",
            field=models.ImageField(
                blank=True,
                help_text=(
                    "Optional banner under the plan on the app. "
                    "Recommended: 1200×675 px (16:9) or 1080×1350 px (portrait 4:5). "
                    "JPG/WebP, under 800 KB."
                ),
                null=True,
                upload_to="plans/performance-income/",
            ),
        ),
    ]
