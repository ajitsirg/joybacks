import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { ConfigAPI } from "@/lib/api";

export const Route = createFileRoute("/_app/plans/direct")({
  head: () => ({ meta: [{ title: "Level Income Plan — JoyClub Associate" }] }),
  component: PlanPage,
});

type Slab = {
  level: number;
  percent: string;
  title?: string;
  is_active?: boolean;
};

type LevelPlan = {
  name?: string;
  poster_image_url?: string | null;
  total_percent?: string;
  slabs?: Slab[];
};

function formatPercent(value: string | number | undefined): string {
  const n = Number(value ?? 0);
  if (Number.isNaN(n)) return "0%";
  const trimmed = Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
  return `${trimmed}%`;
}

function PlanPage() {
  const [plan, setPlan] = useState<LevelPlan | null>(null);

  useEffect(() => {
    ConfigAPI.runtime()
      .then((d) => setPlan((d.level_income as LevelPlan) ?? null))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"));
  }, []);

  const slabs = (plan?.slabs ?? [])
    .filter((s) => s.is_active !== false)
    .slice()
    .sort((a, b) => a.level - b.level);

  return (
    <div className="w-full max-w-full space-y-3 pb-6">
      <PageHeader
        title="Direct / Level Income"
        subtitle={`Farmhouse sale commission (₹2,20,000 × level %). Total configured: ${formatPercent(plan?.total_percent ?? slabs.reduce((a, s) => a + Number(s.percent || 0), 0))}.`}
      />

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
        {slabs.map((s) => (
          <div
            key={s.level}
            className="rounded-lg border border-border bg-card px-2.5 py-2 shadow-sm"
          >
            <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Level {s.level}
            </div>
            <div className="mt-0.5 text-lg font-semibold tabular-nums text-[color:var(--brand-dark)]">
              {formatPercent(s.percent)}
            </div>
            <div className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
              {s.level} immediate member{s.level === 1 ? "" : "s"} to unlock
            </div>
          </div>
        ))}
      </div>

      {plan?.poster_image_url ? (
        <figure className="w-full overflow-hidden rounded-xl border border-border bg-card">
          <img
            src={plan.poster_image_url}
            alt={plan.name || "Direct level income plan"}
            className="block h-auto w-full max-w-full object-contain object-top"
            loading="lazy"
          />
        </figure>
      ) : (
        <p className="text-sm text-muted-foreground">
          Upload the plan image in Django Admin → Level income plan → Plan poster image (1080×1350
          or 1200×675, under 800 KB).
        </p>
      )}
    </div>
  );
}
