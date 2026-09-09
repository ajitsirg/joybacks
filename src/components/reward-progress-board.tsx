import { useEffect, useState } from "react";
import { Loader2, Trophy } from "lucide-react";
import { toast } from "sonner";
import { RewardAchievementTable } from "@/components/reward-achievement-table";
import { Button } from "@/components/ui/button";
import { AssociatesAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

function inr(n: unknown) {
  return `₹ ${Number(n ?? 0).toLocaleString("en-IN")}`;
}

type Leg = {
  slot: number;
  associate_id: string;
  name: string;
  business: string;
  locked: boolean;
};

type Candidate = { associate_id: string; name: string; business: string };

type Milestone = {
  sno: number;
  total: string;
  leg1: string;
  leg2: string;
  leg3: string;
  reward: string;
  status: string;
  remaining_total: string;
  remaining_leg1: string;
  remaining_leg2: string;
  remaining_leg3: string;
};

type Progress = {
  total: string;
  leg1: string;
  leg2: string;
  leg3: string;
  level: number;
  name: string;
  current_milestone: number;
  next_milestone: number | null;
  remaining_total: string;
  remaining_leg1: string;
  remaining_leg2: string;
  remaining_leg3: string;
  auto: boolean;
  legs: Leg[];
  next_targets: {
    sno: number;
    total: string;
    leg1: string;
    leg2: string;
    leg3: string;
    reward: string;
  } | null;
  milestones: Milestone[];
  candidates: Candidate[];
};

function statusOf(have: number, need: number) {
  return have >= need ? "Achieved" : "Pending";
}

export function RewardProgressBoard() {
  const [data, setData] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pick, setPick] = useState<[string, string, string]>(["", "", ""]);

  function apply(d: Progress) {
    setData(d);
    const legs = d.legs ?? [];
    setPick([
      legs[0]?.associate_id ?? "",
      legs[1]?.associate_id ?? "",
      legs[2]?.associate_id ?? "",
    ]);
  }

  useEffect(() => {
    let cancelled = false;
    AssociatesAPI.rewardProgress()
      .then((raw) => {
        if (!cancelled) apply(raw as unknown as Progress);
      })
      .catch((e) => {
        if (!cancelled) toast.error(e instanceof Error ? e.message : "Could not load reward progress");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function saveLegs(auto: boolean) {
    setSaving(true);
    try {
      const raw = await AssociatesAPI.assignRewardLegs(
        auto ? { auto: true } : { legs: pick },
      );
      apply(raw as unknown as Progress);
      toast.success(auto ? "Using current top 3 performers" : "Reward legs saved");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save legs");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-[color:var(--border)] bg-white px-4 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading reward progress…
      </div>
    );
  }

  if (!data) return null;

  const next = data.next_targets;
  const rows = next
    ? [
        { label: "Leg 1", target: next.leg1, current: data.leg1, remain: data.remaining_leg1 },
        { label: "Leg 2", target: next.leg2, current: data.leg2, remain: data.remaining_leg2 },
        { label: "Leg 3", target: next.leg3, current: data.leg3, remain: data.remaining_leg3 },
        { label: "Total", target: next.total, current: data.total, remain: data.remaining_total },
      ]
    : [];
  const nextAllOk = rows.length > 0 && rows.every((r) => Number(r.current) >= Number(r.target));

  return (
    <div className="space-y-4">
      <section className="overflow-hidden rounded-2xl border border-[color:var(--border)] bg-white shadow-sm">
        <div className="border-b border-[color:var(--border)] bg-gradient-to-r from-[color:var(--brand-dark)] to-[color:var(--brand)] px-4 py-3 text-white">
          <div className="text-[10px] uppercase tracking-[0.2em] text-amber-200/90">
            Performance reward · 3 legs
          </div>
          <div className="flex flex-wrap items-center gap-2 text-base font-semibold">
            <Trophy className="h-4 w-4 text-amber-300" />
            {data.level > 0 ? `Level ${data.level} Unlocked` : "No milestone yet"}
            {data.next_milestone ? (
              <span className="text-sm font-normal text-white/80">
                · Next Milestone {data.next_milestone}
              </span>
            ) : data.level >= 9 ? (
              <span className="text-sm font-normal text-white/80">· All 9 levels done</span>
            ) : null}
          </div>
        </div>

        <div className="grid gap-3 p-4 sm:grid-cols-3">
          {(data.legs ?? []).map((leg) => (
            <div key={leg.slot} className="rounded-xl border border-[color:var(--border)] bg-[color:var(--hero)] p-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Leg {leg.slot}
                {leg.locked ? " · Pinned" : " · Top performer"}
              </div>
              <div className="mt-1 truncate text-sm font-semibold text-[color:var(--brand-dark)]">
                {leg.associate_id || "—"}
              </div>
              <div className="truncate text-xs text-muted-foreground">{leg.name || "Not assigned"}</div>
              <div className="mt-2 text-lg font-bold tabular-nums">{inr(leg.business)}</div>
            </div>
          ))}
        </div>

        <div className="px-4 pb-2 text-sm text-muted-foreground">
          Combined reward business:{" "}
          <span className="font-semibold tabular-nums text-foreground">{inr(data.total)}</span>
          {" "}(Leg 1 + Leg 2 + Leg 3 only)
        </div>

        {next ? (
          <div className="overflow-x-auto px-4 pb-4">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-2 pr-3">Requirement</th>
                  <th className="py-2 pr-3">Current / Target</th>
                  <th className="py-2 pr-3">Remaining</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const ok = Number(r.current) >= Number(r.target);
                  return (
                    <tr key={r.label} className="border-t border-[color:var(--border)]">
                      <td className="py-2 pr-3 font-medium">{r.label}</td>
                      <td className="py-2 pr-3 tabular-nums">
                        {inr(r.current)} / {inr(r.target)}
                      </td>
                      <td className="py-2 pr-3 tabular-nums">{inr(r.remain)}</td>
                      <td className={cn("py-2 font-semibold", ok ? "text-emerald-700" : "text-amber-800")}>
                        {statusOf(Number(r.current), Number(r.target))}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="mt-2 text-sm">
              Milestone {next.sno} overall:{" "}
              <span className={cn("font-semibold", nextAllOk ? "text-emerald-700" : "text-amber-800")}>
                {nextAllOk ? "Achieved" : "Pending"}
              </span>
              {" · "}
              pays {inr(next.reward)} only when all three legs and the total are achieved.
            </p>
          </div>
        ) : null}

        {(data.candidates ?? []).length > 0 ? (
          <div className="border-t border-[color:var(--border)] px-4 py-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Choose your 3 reward legs
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {([0, 1, 2] as const).map((i) => (
                <label key={i} className="text-xs">
                  <span className="mb-1 block text-muted-foreground">Leg {i + 1}</span>
                  <select
                    className="w-full rounded-lg border border-[color:var(--border)] bg-white px-2 py-2 text-sm"
                    value={pick[i]}
                    onChange={(e) => {
                      const nextPick: [string, string, string] = [pick[0], pick[1], pick[2]];
                      nextPick[i] = e.target.value;
                      setPick(nextPick);
                    }}
                  >
                    <option value="">Select member</option>
                    {data.candidates.map((c) => (
                      <option key={`${i}-${c.associate_id}`} value={c.associate_id}>
                        {c.associate_id} · {inr(c.business)}
                        {c.name ? ` · ${c.name}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button type="button" size="sm" disabled={saving} onClick={() => void saveLegs(false)}>
                Save selected legs
              </Button>
              <Button type="button" size="sm" variant="outline" disabled={saving} onClick={() => void saveLegs(true)}>
                Use top 3 automatically
              </Button>
            </div>
          </div>
        ) : (
          <p className="px-4 pb-4 text-sm text-muted-foreground">
            Add first-line members. The strongest three become your reward legs.
          </p>
        )}
      </section>

      <RewardAchievementTable
        variant="inline"
        progress={{
          total: Number(data.total),
          leg1: Number(data.leg1),
          leg2: Number(data.leg2),
          leg3: Number(data.leg3),
          level: Number(data.level),
          milestones: data.milestones,
        }}
      />
    </div>
  );
}
