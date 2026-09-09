import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { DataTable, type Column } from "@/components/data-table";
import { RoiLevelHistory, RoiPerformanceBoard } from "@/components/roi-performance-board";
import { SaleLevelBoard, SaleLevelHistory } from "@/components/sale-level-board";
import { CommissionsAPI, unwrapList } from "@/lib/api";
import { useAuth } from "@/lib/rbac";

type Row = Record<string, unknown>;

function rewardMilestoneNo(r: Row): number {
  const ref = String(r.reference ?? "");
  const match = ref.match(/REWARD-[ML](\d+)/i);
  if (match) return Number(match[1]);
  return Number(r.level ?? 0);
}

function timeFromNow(raw: unknown): string {
  const d = new Date(String(raw ?? ""));
  if (Number.isNaN(d.getTime())) return "—";
  const diff = Date.now() - d.getTime();
  const abs = Math.abs(diff);
  const mins = Math.round(abs / 60000);
  const hours = Math.round(abs / 3600000);
  const days = Math.round(abs / 86400000);
  let rel = "just now";
  if (mins >= 1 && mins < 60) rel = `${mins} min ago`;
  else if (hours < 24) rel = `${hours} hr ago`;
  else if (days < 30) rel = `${days} day${days === 1 ? "" : "s"} ago`;
  else rel = d.toLocaleDateString("en-IN");
  return `${rel} · ${d.toLocaleString("en-IN")}`;
}

function rewardRefLabel(r: Row): string {
  const ref = String(r.reference || "—");
  const n = rewardMilestoneNo(r);
  if (/REWARD-L\d+/i.test(ref) && n) return `REWARD-M${n} (legacy kept)`;
  return ref;
}

export function LiveIncomePage({
  title,
  subtitle,
  walletType,
}: {
  title: string;
  subtitle: string;
  walletType?: string;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [levelFilter, setLevelFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const isRoi = walletType === "roi";
  const isSale = walletType === "income";
  const showLevelFilters = isRoi || isSale;
  const { session } = useAuth();
  const myId = session?.associateId || "";
  const isStaff = !!(session?.isStaff || session?.isSuperuser);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      setLoading(true);
      CommissionsAPI.entries({
        page_size: 500,
        ...(walletType ? { wallet_type: walletType } : {}),
        ...(walletType === "roi" ? { min_level: 1, roi_on_roi: "1" } : {}),
        // Associates: own income only so L1 earned matches the dashboard tiles.
        ...(!isStaff && myId ? { "beneficiary__associate_id": myId } : {}),
      })
        .then((d) => {
          if (cancelled) return;
          setRows(
            unwrapList(d).map((r, i) => ({
              ...r,
              id: (r.id as string | number | undefined) ?? `c-${i}`,
            })),
          );
        })
        .catch((e) => {
          if (!cancelled) toast.error(e instanceof Error ? e.message : "Failed");
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
  }, [walletType, isStaff, myId]);

  const filteredRows = rows
    .filter((r) => {
    if (isRoi && Number(r.level ?? 0) < 1) return false;
    if (levelFilter && String(r.level ?? "") !== levelFilter) return false;
    if (statusFilter && String(r.status ?? "").toLowerCase() !== statusFilter) return false;
    const when = String(r.commission_date ?? r.created_at ?? "");
    if (dateFrom && when && when.slice(0, 10) < dateFrom) return false;
    if (dateTo && when && when.slice(0, 10) > dateTo) return false;
    return true;
  })
    .sort((a, b) => {
      const ta = new Date(String(a.commission_date ?? a.created_at ?? 0)).getTime();
      const tb = new Date(String(b.commission_date ?? b.created_at ?? 0)).getTime();
      return tb - ta;
    });

  const isReward = walletType === "reward";
  const cols: Column<Row>[] = [
    {
      key: "beneficiary_id",
      header: "User",
      cell: (r) => {
        const id = String(r.beneficiary_id ?? "");
        if (!id) return "—";
        return (
          <Link
            to="/users/$associateId"
            params={{ associateId: id }}
            className="font-medium text-[color:var(--brand-dark)] underline-offset-2 hover:underline"
          >
            {id}
          </Link>
        );
      },
    },
    ...(isReward
      ? []
      : [
          {
            key: "buyer_id",
            header: "Buyer",
            cell: (r: Row) => {
              const id = String(r.buyer_id ?? r.source_id ?? "");
              if (!id) return "—";
              return (
                <Link
                  to="/users/$associateId"
                  params={{ associateId: id }}
                  className="underline-offset-2 hover:underline"
                >
                  {id}
                </Link>
              );
            },
          } satisfies Column<Row>,
        ]),
    {
      key: "level",
      header: isReward ? "Milestone" : "Net L",
      cell: (r) =>
        isReward ? (rewardMilestoneNo(r) ? `M${rewardMilestoneNo(r)}` : "—") : String(r.level ?? 0),
    },
    ...(isReward
      ? []
      : [
          {
            key: "growth_level",
            header: "ROI L",
            cell: (r: Row) => {
              const g = Number(r.growth_level ?? r.level ?? 0);
              return g ? String(g) : "—";
            },
          } satisfies Column<Row>,
          {
            key: "percent",
            header: "%",
            cell: (r: Row) => String(r.percent),
          } satisfies Column<Row>,
        ]),
    ...(isReward
      ? []
      : [
          {
            key: "sale_amount",
            header: "Sale",
            cell: (r: Row) => {
              const n = Number(r.sale_amount ?? 0);
              return n ? `₹ ${n.toLocaleString("en-IN")}` : "—";
            },
          } satisfies Column<Row>,
          {
            key: "monthly_return_amount",
            header: "Base ROI",
            cell: (r: Row) => {
              const n = Number(r.monthly_return_amount ?? 0);
              return n ? `₹ ${n.toLocaleString("en-IN")}` : "—";
            },
          } satisfies Column<Row>,
          {
            key: "month_index",
            header: "Month",
            cell: (r: Row) => {
              const m = Number(r.month_index ?? 0);
              return m ? String(m) : "—";
            },
          } satisfies Column<Row>,
        ]),
    {
      key: "amount",
      header: isReward ? "Reward" : "Commission",
      cell: (r) => `₹ ${Number(r.amount).toLocaleString("en-IN")}`,
    },
    ...(isReward
      ? []
      : [
          {
            key: "investment_id",
            header: "Investment",
            cell: (r: Row) => {
              const id = String(r.investment_id ?? "");
              return id ? `${id.slice(0, 8)}…` : "—";
            },
          } satisfies Column<Row>,
        ]),
    {
      key: "status",
      header: "Status",
      cell: (r) => String(r.status ?? "credited"),
    },
    {
      key: "reference",
      header: "Ref",
      cell: (r) => (isReward ? rewardRefLabel(r) : String(r.reference || "—")),
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
            className="uppercase underline-offset-2 hover:underline"
          >
            {type || "—"}
          </Link>
        );
      },
    },
    {
      key: "commission_date",
      header: "Time",
      cell: (r) => timeFromNow(r.commission_date ?? r.created_at),
      sortValue: (r) => String(r.commission_date ?? r.created_at ?? ""),
    },
  ];

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
      />
      {isSale ? <SaleLevelBoard /> : null}
      {isRoi ? <RoiPerformanceBoard /> : null}
      {showLevelFilters ? (
        <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <label className="text-xs text-muted-foreground">
            Level
            <select
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
            >
              <option value="">All</option>
              {Array.from({ length: isRoi ? 10 : 5 }, (_, i) => (
                <option key={i + 1} value={String(i + 1)}>
                  Level {i + 1}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-muted-foreground">
            Status
            <select
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All</option>
              <option value="credited">Credited</option>
              <option value="skipped">Skipped</option>
              <option value="voided">Voided</option>
            </select>
          </label>
          <label className="text-xs text-muted-foreground">
            From
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </label>
          <label className="text-xs text-muted-foreground">
            To
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </label>
        </div>
      ) : null}
      {isSale ? <SaleLevelHistory rows={filteredRows} /> : null}
      {isRoi ? <RoiLevelHistory rows={filteredRows} /> : null}
      <DataTable
        data={filteredRows}
        columns={cols}
        searchable={(r) =>
          `${r.beneficiary_id} ${r.buyer_id} ${r.source_id} ${r.reference} ${r.narration}`
        }
      />
    </div>
  );
}
