from django.db import migrations, models
import operations.upload_paths


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0002_join_leader_approval"),
    ]

    operations = [
        migrations.AddField(
            model_name="kycsubmission",
            name="aadhaar_back",
            field=models.FileField(
                blank=True,
                help_text="Aadhaar back image. Both front + back required to count as attached.",
                null=True,
                upload_to=operations.upload_paths.kyc_aadhaar_back,
                verbose_name="Aadhaar back",
            ),
        ),
        migrations.AlterField(
            model_name="kycsubmission",
            name="aadhaar_document",
            field=models.FileField(
                blank=True,
                help_text="Aadhaar front image",
                null=True,
                upload_to=operations.upload_paths.kyc_aadhaar_front,
                verbose_name="Aadhaar front",
            ),
        ),
        migrations.AlterField(
            model_name="kycsubmission",
            name="profile_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=operations.upload_paths.kyc_profile_photo,
            ),
        ),
        migrations.AlterField(
            model_name="kycsubmission",
            name="pan_document",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=operations.upload_paths.kyc_pan_document,
            ),
        ),
        migrations.AlterField(
            model_name="kycsubmission",
            name="bank_document",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=operations.upload_paths.kyc_bank_document,
            ),
        ),
    ]
