from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0002_company_join_package_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="require_join_pan",
            field=models.BooleanField(default=False, help_text="Require PAN on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_aadhaar",
            field=models.BooleanField(default=False, help_text="Require Aadhaar on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_bank_name",
            field=models.BooleanField(default=False, help_text="Require bank name on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_account_number",
            field=models.BooleanField(default=False, help_text="Require account number on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_ifsc",
            field=models.BooleanField(default=False, help_text="Require IFSC on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_upi",
            field=models.BooleanField(default=False, help_text="Require UPI ID on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_profile_photo",
            field=models.BooleanField(default=False, help_text="Require profile photo on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_aadhaar_document",
            field=models.BooleanField(default=False, help_text="Require Aadhaar card upload on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_pan_document",
            field=models.BooleanField(default=False, help_text="Require PAN card upload on Join"),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="require_join_bank_document",
            field=models.BooleanField(default=False, help_text="Require bank proof upload on Join"),
        ),
    ]
