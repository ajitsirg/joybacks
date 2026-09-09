from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0005_company_show_income_referral"),
    ]

    operations = [
        migrations.AddField(
            model_name="levelincomeplan",
            name="tagline",
            field=models.CharField(
                blank=True,
                default="Together We Grow, Together We Succeed",
                max_length=160,
            ),
        ),
        migrations.AddField(
            model_name="levelincomeplan",
            name="poster_image",
            field=models.ImageField(
                blank=True,
                help_text=(
                    "Optional banner under the plan on the app. "
                    "Recommended: 1080×1350 px (portrait 4:5) for mobile, or 1200×675 px (16:9) for wide. "
                    "JPG/WebP, under 800 KB."
                ),
                null=True,
                upload_to="plans/level-income/",
            ),
        ),
        migrations.AddField(
            model_name="levelincomeslab",
            name="title",
            field=models.CharField(
                blank=True,
                help_text="Short label shown in the app, e.g. Start Your Journey",
                max_length=80,
            ),
        ),
    ]
