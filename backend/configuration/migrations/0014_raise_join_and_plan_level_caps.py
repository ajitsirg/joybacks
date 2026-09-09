from django.core.validators import MaxValueValidator
from django.db import migrations, models


def bump_genealogy_depth(apps, schema_editor):
    GenealogySettings = apps.get_model("configuration", "GenealogySettings")
    # Existing installs were capped at 10 — raise so Level 11+ joins work unless admin lowers.
    GenealogySettings.objects.filter(max_depth__lte=10).update(max_depth=200)


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0013_company_users_flag_card_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="genealogysettings",
            name="max_depth",
            field=models.PositiveIntegerField(
                default=200,
                help_text=(
                    "Max join / tree levels under root (associate depth). "
                    "Set 100 or 200 to allow deep teams (Level 11+). "
                    "0 = unlimited. Django admin controls who can join how deep."
                ),
                validators=[MaxValueValidator(1000)],
                verbose_name="Max join levels (tree depth)",
            ),
        ),
        migrations.AlterField(
            model_name="levelincomeplan",
            name="max_levels",
            field=models.PositiveIntegerField(
                default=5,
                help_text=(
                    "How many upline levels pay income (1–200). "
                    "Add a slab row for each level in admin."
                ),
                validators=[MaxValueValidator(200)],
            ),
        ),
        migrations.AlterField(
            model_name="performanceincomeplan",
            name="max_levels",
            field=models.PositiveIntegerField(
                default=10,
                help_text=(
                    "Max performance levels (1–200). Raise this, then add slabs (Level 11, 12, …) "
                    "or use admin action “Fill missing slabs up to max levels”."
                ),
                validators=[MaxValueValidator(200)],
            ),
        ),
        migrations.AlterField(
            model_name="rewardmaster",
            name="name",
            field=models.CharField(
                help_text=(
                    'Use "Level 1", "Level 2", … "Level 100". '
                    "Add more rows here to unlock higher reward levels."
                ),
                max_length=160,
            ),
        ),
        migrations.RunPython(bump_genealogy_depth, migrations.RunPython.noop),
    ]
