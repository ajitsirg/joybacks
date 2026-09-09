import { Link } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string;
  trend?: number;
  icon: LucideIcon;
  spark?: { v: number }[];
  tone?: "hero" | "plain" | "alert";
  to?: string;
};

export function KpiCard({ label, value, trend, icon: Icon, spark, tone = "plain", to }: Props) {
  const positive = (trend ?? 0) >= 0;
  const color = positive ? "var(--brand)" : "var(--danger)";
  const body = (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl px-3.5 py-2.5 transition duration-200",
        "before:absolute before:inset-y-2 before:left-0 before:w-[3px] before:rounded-full before:content-['']",
        tone === "hero" &&
          "bg-gradient-to-br from-white via-white to-[color:var(--brand-tint)]/70 shadow-[0_1px_0_rgba(15,36,24,0.04)] ring-1 ring-[color:var(--brand)]/10 before:bg-[color:var(--brand)]",
        tone === "plain" &&
          "bg-white/90 ring-1 ring-black/[0.06] before:bg-[color:var(--muted-foreground)]/35",
        tone === "alert" &&
          "bg-gradient-to-br from-white to-[#FFF8EB] ring-1 ring-[color:var(--warn)]/25 before:bg-[color:var(--warn)]",
        to && "hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-12px_rgba(11,107,58,0.45)]",
      )}
    >
      <div className="flex items-center gap-3 pl-1.5">
        <div className="min-w-0 flex-1">
          <div
            className={cn(
              "text-[10px] font-semibold uppercase tracking-[0.14em]",
              tone === "alert" ? "text-[color:var(--warn-text)]" : "text-[color:var(--muted-foreground)]",
            )}
          >
            {label}
          </div>
          <div className="mt-0.5 truncate text-xl font-bold tracking-tight tabular-nums text-[color:var(--foreground)]">
            {value}
          </div>
        </div>
        <div
          className={cn(
            "grid h-9 w-9 shrink-0 place-items-center rounded-full transition duration-200",
            tone === "hero" && "bg-[color:var(--brand)] text-white group-hover:scale-105",
            tone === "plain" && "bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)]",
            tone === "alert" && "bg-[color:var(--warn-tint)] text-[color:var(--warn-text)]",
          )}
        >
          <Icon className="h-4 w-4" strokeWidth={2.25} />
        </div>
        {trend !== undefined && (
          <span
            className="inline-flex shrink-0 items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[10px] font-semibold"
            style={{
              background: positive ? "var(--brand-tint)" : "var(--danger-tint)",
              color: positive ? "var(--brand-dark)" : "var(--danger-text)",
            }}
          >
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(trend).toFixed(1)}%
          </span>
        )}
      </div>
      {spark && spark.length > 0 && (
        <div className="mt-1.5 h-7 opacity-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={spark}>
              <defs>
                <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#spark-${label})`} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
  if (!to) return body;
  return (
    <Link to={to as never} className="block outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--brand)]/40">
      {body}
    </Link>
  );
}
