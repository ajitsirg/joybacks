import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_net_amount(apps, schema_editor):
    CommissionEntry = apps.get_model("commissions", "CommissionEntry")
    CommissionEntry.objects.filter(net_amount=0).update(net_amount=models.F("amount"))


class Migration(migrations.Migration):
    dependencies = [
        ("associates", "0014_alter_can_fund_transfer_help"),
        ("wallets", "0004_fund_request_utr_proof"),
        ("commissions", "0004_monthly_growth_roi"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="commissionentry",
            name="admin_charge_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=16),
        ),
        migrations.AddField(
            model_name="commissionentry",
            name="net_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Amount credited to the associate after admin charge.",
                max_digits=16,
            ),
        ),
        migrations.RunPython(backfill_net_amount, migrations.RunPython.noop),
        migrations.CreateModel(
            name="AdminCharge",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("kind", models.CharField(choices=[("income", "Sale / Level Income"), ("roi", "ROI Level Income"), ("reward", "Reward Income")], db_index=True, max_length=20)),
                ("wallet_type", models.CharField(max_length=20)),
                ("gross_amount", models.DecimalField(decimal_places=2, max_digits=16)),
                ("charge_percent", models.DecimalField(decimal_places=2, max_digits=5)),
                ("charge_amount", models.DecimalField(decimal_places=2, max_digits=16)),
                ("net_amount", models.DecimalField(decimal_places=2, max_digits=16)),
                ("reference", models.CharField(blank=True, db_index=True, max_length=80)),
                ("narration", models.CharField(blank=True, max_length=255)),
                (
                    "associate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="admin_charges",
                        to="associates.associate",
                    ),
                ),
                (
                    "commission_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_charges",
                        to="commissions.commissionentry",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ledger_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_charges",
                        to="wallets.ledgerentry",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Admin charge",
                "verbose_name_plural": "Admin charges",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="admincharge",
            index=models.Index(fields=["kind", "created_at"], name="commissions_kind_cr_idx"),
        ),
    ]
