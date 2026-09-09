from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wallets", "0003_fund_transfer_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundtransferrequest",
            name="utr",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="UTR / bank or UPI transaction ID from the associate.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="fundtransferrequest",
            name="proof",
            field=models.FileField(
                blank=True,
                help_text="Payment screenshot, receipt, or PDF.",
                null=True,
                upload_to="fund-transfers/proofs/%Y/%m/",
            ),
        ),
    ]
