import { useState } from "react";
import { ChevronDown, ChevronUp, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

/** Official Joy Adventure Resort — Reward Achievement slabs (fixed schedule). */
export const REWARD_ACHIEVEMENT_ROWS = [
  { sno: 1, total: 2_500_000, leg1: 1_000_000, leg2: 750_000, leg3: 750_000, reward: 75_000 },
  { sno: 2, total: 5_000_000, leg1: 2_000_000, leg2: 1_500_000, leg3: 1_500_000, reward: 150_000 },
  { sno: 3, total: 10_000_000, leg1: 4_000_000, leg2: 3_000_000, leg3: 3_000_000, reward: 400_000 },
  { sno: 4, total: 20_000_000, leg1: 8_000_000, leg2: 6_000_000, leg3: 6_000_000, reward: 1_000_000 },
  { sno: 5, total: 50_000_000, leg1: 20_000_000, leg2: 15_000_000, leg3: 15_000_000, reward: 3_000_000 },
  { sno: 6, total: 100_000_000, leg1: 40_000_000, leg2: 30_000_000, leg3: 30_000_000, reward: 6_000_000 },
  { sno: 7, total: 200_000_000, leg1: 80_000_000, leg2: 60_000_000, leg3: 60_000_000, reward: 10_000_000 },
  { sno: 8, total: 500_000_000, leg1: 200_000_000, leg2: 150_000_000, leg3: 150_000_000, reward: 25_000_000 },
  { sno: 9, total: 1_000_000_000, leg1: 400_000_000, leg2: 300_000_000, leg3: 300_000_000, reward: 50_000_000 },
] as const;

function inr(n: number) {
  return n.toLocaleString("en-IN");
}

export type RewardMilestoneRow = {
  sno: number;
  status: "achieved" | "pending" | "locked" | string;
  reward?: string | number;
};

export type RewardProgress = {
  total?: number;
  leg1?: number;
  leg2?: number;
  leg3?: number;
  level?: number;
  milestones?: RewardMilestoneRow[];
};

type Props = {
  /** Sticky bottom panel on every dashboard (default). */
  variant?: "sticky" | "inline";
  className?: string;
  defaultOpen?: boolean;
  /** Live associate totals — highlights achieved rows and shows your vs need. */
  progress?: RewardProgress | null;
};

function CellNeed({ have, need }: { have: number; need: number }) {
  const ok = have >= need;
  const remain = Math.max(need - have, 0);
  return (
    <div className="tabular-nums">
      <div className={cn("font-medium", ok ? "text-emerald-800" : "text-foreground")}>₹ {inr(need)}</div>
      <div className={cn("text-[10px] sm:text-xs", ok ? "text-emerald-700" : "text-muted-foreground")}>
        You: ₹ {inr(have)}
        {ok ? "" : ` · remain ₹ ${inr(remain)}`}
      </div>
    </div>
  );
}

export function RewardAchievementTable({
  variant = "sticky",
  className,
  defaultOpen = true,
  progress,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const haveTotal = Number(progress?.total ?? 0);
  const have1 = Number(progress?.leg1 ?? 0);
  const have2 = Number(progress?.leg2 ?? 0);
  const have3 = Number(progress?.leg3 ?? 0);
  const level = Number(progress?.level ?? 0);
  const showProgress = progress != null;

  const table = (
    <div className="overflow-x-auto">
      {showProgress ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-[color:var(--border)] bg-[color:var(--brand-tint)]/60 px-3 py-2 text-xs sm:text-sm">
          <span className="font-semibold text-[color:var(--brand-dark)]">
            {level > 0 ? `Level ${level} Unlocked` : "No level yet"}
          </span>
          <span className="tabular-nums text-muted-foreground">
            Total ₹ {inr(haveTotal)} · Leg1 ₹ {inr(have1)} · Leg2 ₹ {inr(have2)} · Leg3 ₹ {inr(have3)}
          </span>
        </div>
      ) : null}
      <table className="w-full min-w-[720px] border-collapse text-left text-xs sm:text-sm">
        <thead>
          <tr className="bg-[color:var(--brand-dark)] text-white">
            <th className="px-2 py-2.5 font-semibold sm:px-3">S. No.</th>
            <th className="px-2 py-2.5 font-semibold sm:px-3">Total Business</th>
            <th className="px-2 py-2.5 font-semibold sm:px-3">Leg 1 Business</th>
            <th className="px-2 py-2.5 font-semibold sm:px-3">Leg 2 Business</th>
            <th className="px-2 py-2.5 font-semibold sm:px-3">Leg 3 Business</th>
            <th className="px-2 py-2.5 font-semibold sm:px-3">Reward</th>
            <th className="px-2 py-2.5 font-semibold sm:px-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {REWARD_ACHIEVEMENT_ROWS.map((row, i) => {
            const fromApi = progress?.milestones?.find((m) => Number(m.sno) === row.sno);
            const allFour =
              haveTotal >= row.total && have1 >= row.leg1 && have2 >= row.leg2 && have3 >= row.leg3;
            const status = showProgress
              ? (fromApi?.status ?? (allFour ? "achieved" : "pending"))
              : "";
            const achieved = status === "achieved";
            const pending = status === "pending";
            const locked = status === "locked";
            return (
              <tr
                key={row.sno}
                className={cn(
                  "border-b border-[color:var(--border)]",
                  achieved
                    ? "bg-emerald-50"
                    : pending
                      ? "bg-amber-50"
                      : locked
                        ? "bg-slate-50 text-muted-foreground"
                        : i % 2 === 0
                          ? "bg-white"
                          : "bg-[color:var(--brand-tint)]/50",
                )}
              >
                <td className="px-2 py-2 text-center font-medium sm:px-3">{row.sno}</td>
                <td className="px-2 py-2 sm:px-3">
                  {showProgress ? <CellNeed have={haveTotal} need={row.total} /> : <span className="font-medium tabular-nums">₹ {inr(row.total)}</span>}
                </td>
                <td className="px-2 py-2 sm:px-3">
                  {showProgress ? <CellNeed have={have1} need={row.leg1} /> : <span className="tabular-nums">₹ {inr(row.leg1)}</span>}
                </td>
                <td className="px-2 py-2 sm:px-3">
                  {showProgress ? <CellNeed have={have2} need={row.leg2} /> : <span className="tabular-nums">₹ {inr(row.leg2)}</span>}
                </td>
                <td className="px-2 py-2 sm:px-3">
                  {showProgress ? <CellNeed have={have3} need={row.leg3} /> : <span className="tabular-nums">₹ {inr(row.leg3)}</span>}
                </td>
                <td className="px-2 py-2 font-semibold tabular-nums text-[color:var(--brand-dark)] sm:px-3">
                  ₹ {inr(row.reward)}
                </td>
                <td
                  className={cn(
                    "px-2 py-2 text-xs font-semibold uppercase tracking-wide sm:px-3",
                    achieved ? "text-emerald-700" : pending ? "text-amber-800" : "text-slate-500",
                  )}
                >
                  {status ? status.charAt(0).toUpperCase() + status.slice(1) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  if (variant === "inline") {
    return (
      <section
        className={cn(
          "overflow-hidden rounded-2xl border border-[color:var(--border)] bg-white shadow-sm",
          className,
        )}
      >
        <div className="border-b border-[color:var(--border)] bg-gradient-to-r from-[color:var(--brand-dark)] to-[color:var(--brand)] px-4 py-3 text-white">
          <div className="text-[10px] uppercase tracking-[0.2em] text-amber-200/90">
            Joy Adventure Resort
          </div>
          <div className="flex items-center gap-2 text-base font-semibold tracking-wide">
            <Trophy className="h-4 w-4 text-amber-300" />
            Reward Achievement
          </div>
        </div>
        {table}
      </section>
    );
  }

  return (
    <div
      className={cn(
        "sticky bottom-0 z-30 border-t border-[color:var(--border)] bg-white/95 shadow-[0_-8px_24px_rgba(15,36,24,0.08)] backdrop-blur supports-[backdrop-filter]:bg-white/90",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 bg-gradient-to-r from-[color:var(--brand-dark)] to-[color:var(--brand)] px-3 py-2.5 text-left text-white sm:px-4"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.18em] text-amber-200/90">
            Joy Adventure Resort · Fixed schedule
          </div>
          <div className="flex items-center gap-2 text-sm font-semibold sm:text-base">
            <Trophy className="h-4 w-4 shrink-0 text-amber-300" />
            Reward Achievement
          </div>
        </div>
        <span className="inline-flex items-center gap-1 rounded-md bg-white/10 px-2 py-1 text-xs">
          {open ? "Hide" : "Show"}
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </span>
      </button>
      {open ? (
        <div className="max-h-[min(42vh,360px)] overflow-auto border-t border-[color:var(--border)]">
          {table}
        </div>
      ) : null}
    </div>
  );
}
