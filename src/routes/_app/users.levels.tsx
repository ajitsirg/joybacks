import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Layers, Loader2, Network, Trophy } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { UserList } from "@/components/users-list";
import { Button } from "@/components/ui/button";
import { AssociatesAPI, ConfigAPI } from "@/lib/api";
import { REWARD_ACHIEVEMENT_ROWS } from "@/components/reward-achievement-table";
import { useAuth } from "@/lib/rbac";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/users/levels")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Users by Level — JoyClub Associate" },
      {
        name: "description",
        content: "Click a level to see only associates on that network / reward / performance level.",
      },
    ],
  }),
  component: UsersByLevelPage,
});

type Kind = "network" | "reward" | "performance";
type LevelRow = { level: number; name: string; count: number };

function UsersByLevelPage() {
  const { session } = useAuth();
  const isStaff = !!(session?.isStaff || session?.isSuperuser);
  const [kind, setKind] = useState<Kind>("network");
  const [summary, setSummary] = useState<LevelRow[]>([]);
  const [summaryKind, setSummaryKind] = useState<"tree" | "leg" | "reward" | "performance">("tree");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<LevelRow | null>(null);
  const [maxPerf, setMaxPerf] = useState(10);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const apiKind = kind === "network" ? (isStaff ? "tree" : "leg") : kind;
      const [sum, runtime] = await Promise.all([
        AssociatesAPI.levelSummary(apiKind),
        ConfigAPI.runtime().catch(() => null),
      ]);
      setSummary(sum.results ?? []);
      setSummaryKind((sum.kind as typeof summaryKind) || apiKind);
      const perf = (runtime as { performance_income?: { max_levels?: number } } | null)
        ?.performance_income;
      if (perf?.max_levels) setMaxPerf(Number(perf.max_levels) || 10);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load levels");
    } finally {
      setLoading(false);
    }
  }, [kind, isStaff]);

  useEffect(() => {
    setSelected(null);
    void load();
  }, [load]);

  const countByLevel = useMemo(() => {
    const m = new Map<number, LevelRow>();
    for (const r of summary) m.set(r.level, r);
    return m;
  }, [summary]);

  const cards: LevelRow[] = useMemo(() => {
    if (kind === "network") {
      const levels = summary
        .map((s) => s.level)
        .filter((n) => (summaryKind === "tree" ? n >= 0 : n >= 1));
      const maxFromData = Math.max(0, ...levels, 1);
      const start = summaryKind === "tree" ? 0 : 1;
      const out: LevelRow[] = [];
      for (let n = start; n <= maxFromData; n++) {
        if (summaryKind === "tree" && n === 0) {
          const hit = countByLevel.get(0);
          if (hit && hit.count > 0) {
            out.push({ level: 0, name: "Root", count: hit.count });
          }
          continue;
        }
        const hit = countByLevel.get(n);
        out.push({
          level: n,
          name: hit?.name || `Level ${n}`,
          count: hit?.count ?? 0,
        });
      }
      return out;
    }
    if (kind === "reward") {
      const maxFromData = Math.max(0, ...summary.map((s) => s.level), REWARD_ACHIEVEMENT_ROWS.length);
      const max = Math.max(maxFromData, REWARD_ACHIEVEMENT_ROWS.length);
      const out: LevelRow[] = [];
      for (let n = 1; n <= max; n++) {
        const hit = countByLevel.get(n);
        out.push({
          level: n,
          name: hit?.name || `Level ${n}`,
          count: hit?.count ?? 0,
        });
      }
      const none = countByLevel.get(0);
      if (none && none.count > 0) {
        out.unshift({ level: 0, name: none.name || "No level", count: none.count });
      }
      return out;
    }
    const maxFromData = Math.max(0, ...summary.map((s) => s.level), maxPerf);
    const max = Math.min(Math.max(maxFromData, 1), 50);
    const out: LevelRow[] = [];
    for (let n = 1; n <= max; n++) {
      const hit = countByLevel.get(n);
      out.push({
        level: n,
        name: hit?.name || `Level ${n}`,
        count: hit?.count ?? 0,
      });
    }
    const none = countByLevel.get(0);
    if (none && none.count > 0) {
      out.unshift({ level: 0, name: none.name || "No level", count: none.count });
    }
    return out;
  }, [kind, summary, countByLevel, maxPerf, summaryKind]);

  if (selected) {
    const label =
      selected.level === 0
        ? kind === "network"
          ? "Root"
          : "No level"
        : selected.name || `Level ${selected.level}`;
    const useLeg = kind === "network" && summaryKind === "leg";
    const useTree = kind === "network" && summaryKind === "tree";
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => setSelected(null)}>
            <ArrowLeft className="h-3.5 w-3.5" />
            All levels
          </Button>
          <span className="text-sm text-muted-foreground">
            {kind === "network" ? "Network" : kind === "reward" ? "Reward" : "Performance"} · {label}
          </span>
        </div>
        <UserList
          title={`${label} associates`}
          subtitle={`${selected.count} associate(s) on ${label}`}
          hideStatusFilter
          scope={useLeg || !isStaff ? "my" : undefined}
          treeLevel={useTree ? selected.level : undefined}
          legLevel={useLeg ? selected.level : undefined}
          earningLevel={kind === "reward" ? selected.level : undefined}
          performanceLevel={kind === "performance" ? selected.level : undefined}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Users by Level"
        subtitle="Click a level to open the same associate list — only that level."
        actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
      />

      <div className="inline-flex flex-wrap rounded-xl border border-border bg-card p-1">
        <button
          type="button"
          onClick={() => setKind("network")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium",
            kind === "network"
              ? "bg-[color:var(--brand)] text-white"
              : "text-muted-foreground hover:bg-muted",
          )}
        >
          <Network className="h-3.5 w-3.5" />
          Network levels
        </button>
        <button
          type="button"
          onClick={() => setKind("reward")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium",
            kind === "reward"
              ? "bg-[color:var(--brand)] text-white"
              : "text-muted-foreground hover:bg-muted",
          )}
        >
          <Trophy className="h-3.5 w-3.5" />
          Reward levels
        </button>
        <button
          type="button"
          onClick={() => setKind("performance")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium",
            kind === "performance"
              ? "bg-[color:var(--brand)] text-white"
              : "text-muted-foreground hover:bg-muted",
          )}
        >
          <Layers className="h-3.5 w-3.5" />
          Performance levels
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading levels…
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {cards.map((c) => {
            const active = c.count > 0;
            const title =
              kind === "network" && c.level === 0
                ? "Root"
                : c.level === 0
                  ? "No level"
                  : `Level ${c.level}`;
            return (
              <button
                key={`${kind}-${c.level}`}
                type="button"
                onClick={() => setSelected(c)}
                className={cn(
                  "rounded-2xl border p-4 text-left transition",
                  active
                    ? "border-[color:var(--brand)]/30 bg-gradient-to-br from-white to-[color:var(--brand-tint)]/60 shadow-sm hover:-translate-y-0.5 hover:shadow-md"
                    : "border-border bg-card hover:bg-muted/60",
                )}
              >
                <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  {kind === "network" ? "Network" : kind === "reward" ? "Reward" : "Performance"}
                </div>
                <div className="mt-1 text-lg font-bold text-[color:var(--brand-dark)]">{title}</div>
                {c.name && c.level > 0 && c.name !== `Level ${c.level}` ? (
                  <div className="truncate text-xs text-muted-foreground">{c.name}</div>
                ) : null}
                <div className="mt-3 flex items-end justify-between gap-2">
                  <span className="text-2xl font-bold tabular-nums">{c.count}</span>
                  <span className="text-xs text-muted-foreground">associates</span>
                </div>
                <div className="mt-2 text-[11px] font-medium text-[color:var(--brand)]">
                  {active ? "View list →" : "Empty — open anyway"}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
