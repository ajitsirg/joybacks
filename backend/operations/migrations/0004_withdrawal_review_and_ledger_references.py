import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0003_aadhaar_front_back_unique_uploads"),
        ("wallets", "0005_fund_transfer_permission"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="withdrawalrequest",
            name="hold_ledger_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="withdrawal_holds",
                to="wallets.ledgerentry",
            ),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="refund_ledger_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="withdrawal_refunds",
                to="wallets.ledgerentry",
            ),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_withdrawals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="withdrawalrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("verified", "Verified"),
                    ("completed", "Completed"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
    ]
