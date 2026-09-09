import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { DataTable, type Column } from "@/components/data-table";
import { PageHeader } from "@/components/app-shell";
import { WalletsAPI, unwrapList } from "@/lib/api";

export const Route = createFileRoute("/_app/fund/admin-history")({
  head: () => ({
    meta: [
      { title: "Admin Fund History — JoyClub Associate" },
      { name: "description", content: "Admin fund transfers from live ledger." },
    ],
  }),
  component: AdminFundHistory,
});

type Row = Record<string, unknown>;

function AdminFundHistory() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      setLoading(true);
      WalletsAPI.ledger({ page_size: 300 })
        .then((d) => {
          if (!cancelled) setRows(unwrapList(d));
        })
        .catch((e) => {
          if (!cancelled) toast.error(e instanceof Error ? e.message : "Failed to load ledger");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };
    load();
    const onFocus = () => load();
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") onFocus();
    });
    return () => {
      cancelled = true;
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  const adminRows = useMemo(
    () =>
      rows.filter((r) => {
        const ref = String(r.reference ?? "").toUpperCase();
        const nar = String(r.narration ?? "").toLowerCase();
        return ref.includes("ADMIN") || nar.includes("admin fund") || nar.includes("transfer");
      }),
    [rows],
  );

  const cols: Column<Row>[] = [
    { key: "associate_id", header: "To Associate", cell: (r) => String(r.associate_id ?? "—") },
    { key: "wallet_type", header: "Wallet", cell: (r) => String(r.wallet_type ?? "").toUpperCase() },
    {
      key: "amount",
      header: "Amount",
      cell: (r) => <span className="tabular-nums">₹ {Number(r.amount ?? 0).toLocaleString("en-IN")}</span>,
      sortValue: (r) => Number(r.amount ?? 0),
    },
    { key: "entry_type", header: "Type", cell: (r) => <span className="capitalize">{String(r.entry_type)}</span> },
    { key: "narration", header: "Narration", cell: (r) => String(r.narration || "—") },
    {
      key: "created_at",
      header: "Date",
      cell: (r) => (r.created_at ? new Date(String(r.created_at)).toLocaleString("en-IN") : "—"),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Admin Fund History"
        subtitle="Admin-initiated transfers from the live ledger"
        actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
      />
      <DataTable data={adminRows} columns={cols} searchable={(r) => `${r.associate_id} ${r.narration}`} />
    </div>
  );
}
