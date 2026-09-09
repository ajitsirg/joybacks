import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { DataTable, type Column } from "@/components/data-table";
import { CommissionsAPI, unwrapList } from "@/lib/api";

export const Route = createFileRoute("/_app/income/admin-charges")({
  head: () => ({ meta: [{ title: "Admin Charges — JoyClub Associate" }] }),
  component: AdminChargesPage,
});

type Row = Record<string, unknown>;

function money(v: unknown) {
  return `₹ ${Number(v ?? 0).toLocaleString("en-IN")}`;
}

function AdminChargesPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    CommissionsAPI.adminCharges({ page_size: 200 })
      .then((d) => {
        if (!cancelled) setRows(unwrapList(d));
      })
      .catch((e) => {
        if (!cancelled) toast.error(e instanceof Error ? e.message : "Failed to load charges");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const cols: Column<Row>[] = [
    { key: "associate_id", header: "Associate", cell: (r) => String(r.associate_id ?? "—") },
    {
      key: "associate_name",
      header: "Name",
      cell: (r) => <span className="text-muted-foreground">{String(r.associate_name ?? "")}</span>,
    },
    { key: "kind_label", header: "Commission", cell: (r) => String(r.kind_label || r.kind) },
    {
      key: "gross_amount",
      header: "Gross",
      cell: (r) => <span className="tabular-nums">{money(r.gross_amount)}</span>,
      sortValue: (r) => Number(r.gross_amount ?? 0),
    },
    {
      key: "charge_percent",
      header: "%",
      cell: (r) => `${Number(r.charge_percent ?? 0)}%`,
    },
    {
      key: "charge_amount",
      header: "Admin charge",
      cell: (r) => <span className="tabular-nums font-medium">{money(r.charge_amount)}</span>,
      sortValue: (r) => Number(r.charge_amount ?? 0),
    },
    {
      key: "net_amount",
      header: "Paid to associate",
      cell: (r) => <span className="tabular-nums">{money(r.net_amount)}</span>,
      sortValue: (r) => Number(r.net_amount ?? 0),
    },
    { key: "reference", header: "Reference", cell: (r) => String(r.reference || "—") },
    {
      key: "created_at",
      header: "Date",
      cell: (r) => (r.created_at ? new Date(String(r.created_at)).toLocaleString("en-IN") : "—"),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Admin Charges"
        subtitle="10% company charge on sale, ROI, and reward commissions. Hidden from associates."
      />
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading charges…</p>
      ) : (
        <DataTable
          data={rows}
          columns={cols}
          searchable={(r) => `${r.associate_id} ${r.associate_name} ${r.reference} ${r.kind}`}
        />
      )}
    </div>
  );
}
