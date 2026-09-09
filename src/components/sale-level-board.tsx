import { useEffect, useMemo, useState } from "react";
import { Lock, Unlock } from "lucide-react";
import { toast } from "sonner";
import { DashboardAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

export type SaleLevelSlab = {
  level: number;
  percent: string;
  required_sales: number;
  unlocked: boolean;
  earned: string;
};

export type SaleLevels = {
  qualified_direct_sales: number;
  unlocked_level: number;
  current_level: number;
  total_level_income: string;
  today_level_income: string;
  slabs: SaleLevelSlab[];
};

function inr(n: unknown) {
  return `₹ ${Number(n ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(value: string | number | undefined): string {
  const n = Number(value ?? 0);
  if (Number.isNaN(n)) return "0%";
  const trimmed = Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
  return `${trimmed}%`;
}

export function SaleLevelBoard({ data }: { data?: SaleLevels | null }) {
  const [fetched, setFetched] = useState<SaleLevels | null>(null);

  useEffect(() => {
    if (data) return;
    let cancelled = false;
    DashboardAPI.admin()
      .then((dash) => {
        if (cancelled) return;
        setFetched((dash.sale_levels as SaleLevels | undefined) ?? null);
      })
      .catch((e) => {
        if (!cancelled) toast.error(e instanceof Error ? e.message : "Sale levels failed");
      });
    return () => {
      cancelled = true;
    };
  }, [data]);

  const board = data ?? fetched;
  if (!board || !board.slabs?.length) return null;

  const current = Number(board.current_level || board.unlocked_level || 0);

  return (
    <section className="space-y-3">
      <h2 className="px-0.5 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        My Sale Commission Levels
      </h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Current Level" value={current ? `Level ${current}` : "None"} />
        <Stat label="Immediate Members (with sale)" value={String(board.qualified_direct_sales ?? 0)} />
        <Stat label="Today's Level Income" value={inr(board.today_level_income)} />
        <Stat label="Total Level Income" value={inr(board.total_level_income)} />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {board.slabs.map((s) => (
          <div
            key={s.level}
            className={cn(
              "rounded-lg border px-2.5 py-2 shadow-sm",
              s.unlocked ? "border-[color:var(--brand)]/30 bg-card" : "border-border bg-muted/40",
            )}
          >
            <div className="flex items-center justify-between gap-1">
              <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                Level {s.level}
              </div>
              {s.unlocked ? (
                <Unlock className="h-3 w-3 text-[color:var(--brand-dark)]" />
              ) : (
                <Lock className="h-3 w-3 text-muted-foreground" />
              )}
            </div>
            <div className="mt-0.5 text-lg font-semibold tabular-nums text-[color:var(--brand-dark)]">
              {formatPercent(s.percent)}
            </div>
            <div className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
              {s.unlocked ? `Earned ${inr(s.earned)}` : `Need ${s.required_sales} immediate members`}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-sm">
      <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold tabular-nums text-[color:var(--brand-dark)]">
        {value}
      </div>
    </div>
  );
}

function money(n: unknown) {
  return Math.round(Number(n ?? 0) * 100) / 100;
}

function isCredited(status: unknown) {
  const s = String(status ?? "credited").toLowerCase();
  return s === "credited" || s === "";
}

export function SaleLevelHistory({
  rows,
}: {
  rows: {
    level?: unknown;
    percent?: unknown;
    sale_amount?: unknown;
    amount?: unknown;
    status?: unknown;
  }[];
}) {
  const summary = useMemo(() => {
    const byLevel = new Map<number, { percent: string; sale: number; earned: number }>();
    for (const r of rows) {
      if (!isCredited(r.status)) continue;
      const level = Number(r.level ?? 0);
      if (level < 1 || level > 5) continue;
      const prev = byLevel.get(level) ?? {
        percent: String(r.percent ?? ""),
        sale: 0,
        earned: 0,
      };
      prev.earned = money(prev.earned + money(r.amount));
      prev.sale = money(prev.sale + money(r.sale_amount));
      if (!prev.percent) prev.percent = String(r.percent ?? "");
      byLevel.set(level, prev);
    }
    return Array.from({ length: 5 }, (_, i) => {
      const level = i + 1;
      const row = byLevel.get(level);
      return {
        level,
        percent: row?.percent ?? "",
        sale: row?.sale ?? 0,
        earned: row?.earned ?? 0,
      };
    });
  }, [rows]);

  if (!rows.length) return null;

  return (
    <div className="mb-4 overflow-x-auto rounded-xl border border-border bg-card">
      <table className="w-full min-w-[520px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th className="px-3 py-2">Level</th>
            <th className="px-3 py-2 text-right">Percentage</th>
            <th className="px-3 py-2 text-right">Sales at Level</th>
            <th className="px-3 py-2 text-right">Earned</th>
          </tr>
        </thead>
        <tbody>
          {summary.map((s) => (
            <tr key={s.level} className="border-b border-border/70 last:border-0">
              <td className="px-3 py-2">Level {s.level}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {s.percent ? formatPercent(s.percent) : "—"}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">{inr(s.sale)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{inr(s.earned)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
