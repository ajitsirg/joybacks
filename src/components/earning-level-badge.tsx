import { cn } from "@/lib/utils";

type Kind = "reward" | "performance" | "earning";

const KIND_STYLE: Record<Kind, { on: string; off: string; titleOn: string; titleOff: string }> = {
  reward: {
    on: "bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)] ring-[color:var(--hero-border)]",
    off: "bg-muted text-muted-foreground ring-border",
    titleOn: "Reward Achievement level",
    titleOff: "No Reward Achievement level yet",
  },
  earning: {
    on: "bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)] ring-[color:var(--hero-border)]",
    off: "bg-muted text-muted-foreground ring-border",
    titleOn: "Reward / earning level",
    titleOff: "No reward level yet",
  },
  performance: {
    on: "bg-[color:var(--info-tint)] text-[color:var(--info-text)] ring-[color:var(--info)]/30",
    off: "bg-muted text-muted-foreground ring-border",
    titleOn: "Performance Income level",
    titleOff: "No Performance level yet",
  },
};

/** Always-visible level chip for tables and profiles. */
export function LevelBadge({
  level,
  name,
  kind = "reward",
  className,
}: {
  level?: unknown;
  name?: unknown;
  kind?: Kind;
  className?: string;
}) {
  const n = Number(level ?? 0) || 0;
  const label = String(name ?? "").trim() || (n > 0 ? `Level ${n}` : "No level");
  const earned = n > 0 && label.toLowerCase() !== "no level";
  const style = KIND_STYLE[kind];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ring-1",
        earned ? style.on : style.off,
        className,
      )}
      title={earned ? `${style.titleOn} ${n}` : style.titleOff}
    >
      {label}
    </span>
  );
}

/** @deprecated use LevelBadge kind="reward" */
export function EarningLevelBadge(props: { level?: unknown; name?: unknown; className?: string }) {
  return <LevelBadge {...props} kind="reward" />;
}
