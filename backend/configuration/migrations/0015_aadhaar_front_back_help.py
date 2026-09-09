from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0014_raise_join_and_plan_level_caps"),
    ]

    operations = [
        migrations.AlterField(
            model_name="companysettings",
            name="require_join_aadhaar_document",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Require Aadhaar front + back images on Join. "
                    "Counts as attached only when both are uploaded."
                ),
                verbose_name="Require Aadhaar front & back",
            ),
        ),
    ]
