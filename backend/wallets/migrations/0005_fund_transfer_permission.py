from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("wallets", "0004_fund_request_utr_proof"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="fundtransferrequest",
            options={
                "ordering": ["-created_at"],
                "permissions": [("can_fund_transfer", "Can execute fund transfers")],
                "verbose_name": "Fund transfer request",
            },
        ),
    ]
