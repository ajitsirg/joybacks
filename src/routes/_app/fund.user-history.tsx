import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { DataTable, type Column } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { WalletsAPI, unwrapList } from "@/lib/api";

type HistorySearch = { wallet?: string };

export const Route = createFileRoute("/_app/fund/user-history")({
  ssr: false,
  validateSearch: (s: Record<string, unknown>): HistorySearch => ({
    wallet: typeof s.wallet === "string" ? s.wallet.toLowerCase() : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Users Fund History — JoyClub Associate" },
      { name: "description", content: "Live wallet ledger entries." },
    ],
  }),
  component: UserFundHistory,
});

type Row = Record<string, unknown>;

function UserFundHistory() {
  const { wallet } = Route.useSearch();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      setLoading(true);
      WalletsAPI.ledger({
        page_size: 200,
        ...(wallet ? { wallet__wallet_type: wallet } : {}),
        ...(wallet === "roi" ? { roi_level_only: "1" } : {}),
      })
        .then((d) => {
          if (cancelled) return;
          setRows(
            unwrapList(d).map((r, i) => ({
              ...r,
              id: (r.id as string | number | undefined) ?? `l-${i}`,
            })),
          );
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
  }, [wallet]);

  const cols: Column<Row>[] = [
    {
      key: "associate_id",
      header: "Associate",
      cell: (r) => {
        const id = String(r.associate_id ?? "");
        if (!id) return "—";
        return (
          <Link
            to="/users/$associateId"
            params={{ associateId: id }}
            className="font-semibold text-[color:var(--brand-dark)] underline-offset-2 hover:underline"
          >
            {id}
          </Link>
        );
      },
    },
    {
      key: "wallet_type",
      header: "Wallet",
      cell: (r) => {
        const type = String(r.wallet_type ?? "").toLowerCase();
        return (
          <Link
            to="/fund/user-history"
            search={{ wallet: type } as never}
            className="font-medium uppercase underline-offset-2 hover:underline"
          >
            {type || "—"}
          </Link>
        );
      },
    },
    { key: "entry_type", header: "Type", cell: (r) => <span className="capitalize">{String(r.entry_type)}</span> },
    {
      key: "amount",
      header: "Amount",
      cell: (r) => <span className="tabular-nums">₹ {Number(r.amount ?? 0).toLocaleString("en-IN")}</span>,
      sortValue: (r) => Number(r.amount ?? 0),
    },
    { key: "reference", header: "Reference", cell: (r) => String(r.reference || "—") },
    { key: "narration", header: "Narration", cell: (r) => String(r.narration || "—") },
    {
      key: "created_at",
      header: "Date",
      cell: (r) => (r.created_at ? new Date(String(r.created_at)).toLocaleString("en-IN") : "—"),
      sortValue: (r) => String(r.created_at ?? ""),
    },
  ];

  return (
    <div>
      <PageHeader
        title={wallet ? `${wallet.toUpperCase()} fund history` : "Users Fund History"}
        subtitle={wallet ? `Ledger filtered by ${wallet} wallet` : "Live wallet ledger from the API"}
        actions={
          <div className="flex items-center gap-2">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {wallet && (
              <Link to="/fund/user-history" className="text-sm font-medium text-[color:var(--brand-dark)] underline">
                Clear filter
              </Link>
            )}
            <Link to="/fund/wallets" className="text-sm font-medium text-[color:var(--brand-dark)] underline">
              Wallets
            </Link>
          </div>
        }
      />
      <DataTable data={rows} columns={cols} searchable={(r) => `${r.associate_id} ${r.reference} ${r.narration} ${r.wallet_type}`} />
    </div>
  );
}
