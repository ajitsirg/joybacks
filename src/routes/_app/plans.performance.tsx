import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { ConfigAPI } from "@/lib/api";

export const Route = createFileRoute("/_app/plans/performance")({
  head: () => ({ meta: [{ title: "Performance Income — JoyClub Associate" }] }),
  component: Page,
});

type Slab = {
  level: number;
  percent: string;
  required_directs: number;
  is_active?: boolean;
};

type PerfPlan = {
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

function Page() {
  const [plan, setPlan] = useState<PerfPlan | null>(null);

  useEffect(() => {
    ConfigAPI.runtime()
      .then((d) => setPlan((d.performance_income as PerfPlan) ?? null))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"));
  }, []);

  const slabs = (plan?.slabs ?? [])
    .filter((s) => s.is_active !== false)
    .slice()
    .sort((a, b) => a.level - b.level);

  return (
    <div className="w-full max-w-full space-y-3 pb-6">
      <PageHeader
        title="Performance Level Income"
        subtitle={`ROI-on-ROI slabs from admin (not of investment). Total configured: ${formatPercent(plan?.total_percent ?? slabs.reduce((a, s) => a + Number(s.percent || 0), 0))}.`}
      />

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-5">
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
              {s.required_directs} directs
            </div>
          </div>
        ))}
      </div>

      {!slabs.length && (
        <p className="text-sm text-muted-foreground">No active performance slabs found.</p>
      )}

      {plan?.poster_image_url ? (
        <figure className="w-full overflow-hidden rounded-xl border border-border bg-card">
          <img
            src={plan.poster_image_url}
            alt={plan.name || "Performance level income plan"}
            className="block h-auto w-full max-w-full object-contain object-top"
            loading="lazy"
          />
        </figure>
      ) : (
        <p className="text-sm text-muted-foreground">
          Upload the plan image in Django Admin → Performance income plan → Plan poster image
          (1200×675 or 1080×1350, under 800 KB).
        </p>
      )}
    </div>
  );
}
