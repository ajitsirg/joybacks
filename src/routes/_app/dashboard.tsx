import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpFromLine,
  Users,
  TrendingUp,
  Award,
  Wallet,
  ArrowRight,
  Activity,
  Loader2,
  RefreshCw,
  Copy,
  Check,
  IndianRupee,
  Layers,
  GitBranch,
  Gift,
  Landmark,
  Briefcase,
  type LucideIcon,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { KpiCard } from "@/components/kpi-card";
import { PageHeader } from "@/components/app-shell";
import { ReferralShareCard } from "@/components/referral-share-card";
import { RewardAchievementTable } from "@/components/reward-achievement-table";
import { RewardProgressBoard } from "@/components/reward-progress-board";
import { RoiPerformanceBoard, type RoiPerformance } from "@/components/roi-performance-board";
import { SaleLevelBoard, type SaleLevels } from "@/components/sale-level-board";
import { StatusBadge } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { AuthAPI, DashboardAPI, resolveMediaUrl } from "@/lib/api";
import { useAuth } from "@/lib/rbac";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/dashboard")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Dashboard — JoyClub Associate" },
      { name: "description", content: "Live JoyClub Associate operations dashboard." },
    ],
  }),
  component: Dashboard,
});

const COLORS = ["#0B6B3A", "#149A56", "#C9A227", "#3D7A5A", "#E07A3D"];
const POLL_MS = 20_000;

function inr(v: unknown) {
  return `₹ ${Number(v ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

type MetricTone = "forest" | "gold" | "teal" | "amber" | "slate";

function MetricTile({
  label,
  value,
  icon: Icon,
  tone = "forest",
  to,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  tone?: MetricTone;
  to?: string;
}) {
  const tones: Record<MetricTone, string> = {
    forest: "from-[#0B6B3A] to-[#074A28]",
    gold: "from-[#B8860B] to-[#8A6508]",
    teal: "from-[#0F766E] to-[#115E59]",
    amber: "from-[#C2410C] to-[#9A3412]",
    slate: "from-[#334155] to-[#1E293B]",
  };
  const body = (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl bg-gradient-to-br p-4 text-white shadow-sm",
        tones[tone],
        to && "transition hover:-translate-y-0.5 hover:shadow-md",
      )}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.12]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 60%, #fff 1px, transparent 1px)",
          backgroundSize: "18px 18px",
        }}
      />
      <div className="relative">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-white/15">
          <Icon className="h-4 w-4" />
        </div>
        <div className="mt-3 truncate text-xl font-bold tracking-tight tabular-nums sm:text-2xl">{value}</div>
        <div className="mt-1 text-xs font-medium uppercase tracking-[0.12em] text-white/85">{label}</div>
      </div>
    </div>
  );
  if (!to) return body;
  return (
    <Link to={to as never} className="block outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--brand)]/40">
      {body}
    </Link>
  );
}

function AssociateHome({
  kpis,
  profile,
  roiPerformance,
  saleLevels,
}: {
  kpis: Record<string, string | number | null>;
  profile: Record<string, unknown> | null;
  roiPerformance?: RoiPerformance | null;
  saleLevels?: SaleLevels | null;
}) {
  const { session } = useAuth();
  const isStaff = !!(session?.isStaff || session?.isSuperuser);
  const canRequestFundTransfer = !isStaff && !!session?.associateId;
  const [copied, setCopied] = useState(false);
  const name = String(profile?.name ?? kpis.associate_name ?? "Associate");
  const aid = String(profile?.associate_id ?? kpis.associate_id ?? "");
  const photo = resolveMediaUrl(
    (profile?.photo_url as string | null | undefined) ??
      (kpis.profile_photo_url as string | null | undefined) ??
      null,
  );
  const city = String(profile?.city ?? kpis.city ?? "").trim();
  const state = String(profile?.state ?? kpis.state ?? "").trim();
  const place = [city, state].filter(Boolean).join(", ") || "JoyClub Associate";
  const packageLabel = String(profile?.card_tier ?? kpis.card_tier ?? "member");
  const status = String(profile?.status ?? kpis.status ?? "active");

  async function copyId() {
    if (!aid) return;
    try {
      await navigator.clipboard.writeText(aid);
      setCopied(true);
      toast.success("Associate ID copied");
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy");
    }
  }

  const metrics: {
    label: string;
    key: string;
    icon: LucideIcon;
    tone: MetricTone;
    to?: string;
  }[] = [
    { label: "Today Income", key: "today_income", icon: IndianRupee, tone: "amber" },
    { label: "Total Income", key: "total_income", icon: TrendingUp, tone: "amber", to: "/income/referral" },
    { label: "Referral Level Income", key: "referral_income", icon: Users, tone: "forest", to: "/income/referral" },
    { label: "S.P. / ROI Income", key: "sp_income", icon: Award, tone: "forest", to: "/income/roi" },
    { label: "Level Income", key: "level_income", icon: Layers, tone: "teal", to: "/income/referral" },
    { label: "Reward Income", key: "reward_income", icon: Gift, tone: "gold", to: "/income/reward" },
    { label: "Team Business", key: "team_business", icon: Briefcase, tone: "slate", to: "/business-report" },
    { label: "Income Wallet Balance", key: "income_wallet", icon: Wallet, tone: "forest", to: "/fund/wallets" },
    { label: "Leg1 Business", key: "leg1_business", icon: GitBranch, tone: "teal", to: "/genealogy" },
    { label: "Leg2 Business", key: "leg2_business", icon: GitBranch, tone: "teal", to: "/genealogy" },
    { label: "Leg3 Business", key: "leg3_business", icon: GitBranch, tone: "teal", to: "/genealogy" },
    { label: "Fund Wallet-1", key: "fund_wallet_1", icon: Landmark, tone: "slate", to: "/fund/wallets" },
    { label: "Fund Wallet-2", key: "fund_wallet_2", icon: Landmark, tone: "slate", to: "/fund/wallets" },
    { label: "Fund Wallet-3", key: "fund_wallet_3", icon: Landmark, tone: "slate", to: "/fund/wallets" },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(260px,320px)_1fr]">
        <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
          <div className="flex flex-col items-center px-5 pb-5 pt-6 text-center">
            <div className="h-20 w-20 overflow-hidden rounded-full border-4 border-[color:var(--brand-tint)] bg-[color:var(--brand)] shadow-sm">
              {photo ? (
                <img src={photo} alt={name} className="h-full w-full object-cover" />
              ) : (
                <div className="grid h-full w-full place-items-center text-xl font-bold text-white">
                  {initials(name) || "JC"}
                </div>
              )}
            </div>
            <div className="mt-4 w-full rounded-lg bg-[color:var(--brand-dark)] px-3 py-2 text-sm font-semibold tracking-wide text-white">
              {place.toUpperCase()}
            </div>
            <div className="mt-3 flex items-center justify-center gap-2 text-sm font-semibold">
              <span>
                ID: <span className="text-[color:var(--brand-dark)]">{aid || "—"}</span>
              </span>
              {aid ? (
                <button
                  type="button"
                  onClick={() => void copyId()}
                  className="rounded-md p-1 text-[color:var(--brand)] hover:bg-[color:var(--brand-tint)]"
                  aria-label="Copy associate ID"
                >
                  {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              ) : null}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              Package: <span className="font-medium capitalize text-foreground">{packageLabel}</span>
            </div>
            <div className="mt-3">
              <StatusBadge status={status} />
            </div>
            <div className="mt-4 grid w-full grid-cols-2 gap-2 text-center text-xs">
              <div className="rounded-xl bg-[color:var(--hero)] px-2 py-2">
                <div className="font-bold tabular-nums text-foreground">{Number(profile?.direct_count ?? kpis.direct_count ?? 0)}</div>
                <div className="text-muted-foreground">Directs</div>
              </div>
              <div className="rounded-xl bg-[color:var(--hero)] px-2 py-2">
                <div className="font-bold tabular-nums text-foreground">
                  {Number(profile?.direct_active_count ?? kpis.direct_active_count ?? 0)}
                </div>
                <div className="text-muted-foreground">Active</div>
              </div>
            </div>
            <Button asChild size="sm" variant="outline" className="mt-4 w-full">
              <Link to="/rbac/profile">View profile</Link>
            </Button>
            {canRequestFundTransfer ? (
              <Button asChild size="sm" className="mt-2 w-full">
                <Link to="/fund/transfer">Request Fund Transfer</Link>
              </Button>
            ) : null}
          </div>
        </div>

        <div>
          <ReferralShareCard />
        </div>
      </div>

      <section>
        <h2 className="mb-2 px-0.5 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          My earnings board
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((m) => (
            <MetricTile
              key={m.key}
              label={m.label}
              value={inr(kpis[m.key])}
              icon={m.icon}
              tone={m.tone}
              to={m.to}
            />
          ))}
        </div>
      </section>

      <SaleLevelBoard data={saleLevels} />
      <RoiPerformanceBoard data={roiPerformance} />
      <RewardProgressBoard />
    </div>
  );
}

function Dashboard() {
  const { session, applyApiUser } = useAuth();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const assocStatus = String(session?.associateStatus ?? "").toLowerCase();
  const showStatusBanner =
    !session?.isStaff &&
    (assocStatus === "inactive" || assocStatus === "pending" || assocStatus === "rejected");

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = !!opts?.silent;
      if (!silent) setRefreshing(true);
      try {
        const [dash, me] = await Promise.all([DashboardAPI.admin(), AuthAPI.me().catch(() => null)]);
        setData(dash);
        setUpdatedAt(new Date());
        if (me) applyApiUser(me);
      } catch (e) {
        if (!silent) toast.error(e instanceof Error ? e.message : "Dashboard failed");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [applyApiUser],
  );

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load({ silent: true }), POLL_MS);
    const onFocus = () => void load({ silent: true });
    const onVisible = () => {
      if (document.visibilityState === "visible") void load({ silent: true });
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  const kpis = (data?.kpis ?? {}) as Record<string, string | number | null>;
  const profile = (data?.profile as Record<string, unknown> | null) ?? null;
  const scope = String(data?.scope ?? "global");
  const isTeam = scope === "team";
  const trend = ((data?.trend as { day: string; amount: string; count: number }[]) ?? []).map((t) => ({
    day: t.day?.slice(5) ?? "",
    income: Number(t.amount),
    users: t.count,
  }));
  const breakdown = ((data?.income_breakdown as { wallet_type: string; total: string }[]) ?? []).map((b, i) => ({
    name: b.wallet_type,
    value: Number(b.total),
    color: COLORS[i % COLORS.length],
  }));
  const recent =
    (data?.recent_activity as {
      type: string;
      label: string;
      associate_id: string;
      amount: string;
      at: string;
    }[]) ?? [];

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" /> Loading live dashboard…
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={isTeam ? "My Dashboard" : "JoyClub Associate"}
        subtitle={
          isTeam
            ? "Your income, wallets, legs and team business — live."
            : "Live network snapshot — auto-refreshes every 20s."
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={refreshing}
              onClick={() => void load()}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            {updatedAt ? (
              <span className="text-xs text-muted-foreground">
                Updated {updatedAt.toLocaleTimeString("en-IN")}
              </span>
            ) : null}
            {!isTeam ? (
              <>
                <PendingChip label="Pending Withdraw" count={Number(kpis.pending_withdrawals ?? 0)} to="/withdraw/pending" />
                <PendingChip label="Pending Deposit" count={Number(kpis.pending_deposits ?? 0)} to="/deposit/pending" />
                <PendingChip label="Pending KYC" count={Number(kpis.pending_kyc ?? 0)} to="/kyc/pending" />
              </>
            ) : null}
          </div>
        }
      />

      {showStatusBanner ? (
        <div
          className={`mb-4 rounded-2xl border px-4 py-3 text-sm ${
            assocStatus === "rejected"
              ? "border-red-200 bg-red-50 text-red-950"
              : "border-amber-200 bg-amber-50 text-amber-950"
          }`}
        >
          <p className="font-semibold">
            Status:{" "}
            {assocStatus === "inactive"
              ? "Inactive"
              : assocStatus === "pending"
                ? "Pending approval"
                : "Rejected"}
          </p>
          <p className="mt-1 opacity-90">
            {session?.waitingMessage ||
              (assocStatus === "inactive"
                ? "Invest at least ₹2,20,000 to become Active. Full app access is available meanwhile."
                : "Full app access is available. Status updates automatically.")}
          </p>
          {assocStatus === "inactive" ? (
            <Link
              to="/deposit/pending"
              className="mt-2 inline-flex text-sm font-semibold text-[color:var(--brand-dark)] underline"
            >
              Go to deposits
            </Link>
          ) : null}
        </div>
      ) : null}

      {isTeam ? (
        <AssociateHome
          kpis={kpis}
          profile={profile}
          roiPerformance={(data?.roi_performance as RoiPerformance | undefined) ?? null}
          saleLevels={(data?.sale_levels as SaleLevels | undefined) ?? null}
        />
      ) : (
        <>
          <div className="mb-4">
            <ReferralShareCard />
          </div>

          <section className="space-y-2">
            <div className="flex items-baseline justify-between gap-2 px-0.5">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
                Network snapshot
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                tone="hero"
                label="Total Associates"
                value={String(kpis.users_total ?? 0)}
                icon={Users}
                to="/users/all"
              />
              <KpiCard
                tone="hero"
                label="Active Associates"
                value={String(kpis.users_active ?? 0)}
                icon={Activity}
                to="/users/active"
              />
              <KpiCard
                tone="hero"
                label="Wallet Balance"
                value={inr(kpis.wallet_balance)}
                icon={Wallet}
                to="/fund/wallets"
              />
              <KpiCard tone="hero" label="Income Paid" value={inr(kpis.income_paid)} icon={TrendingUp} />
            </div>
          </section>

          <section className="mt-4 space-y-2">
            <h2 className="px-0.5 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
              Attention queue
            </h2>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                tone={Number(kpis.pending_withdrawals ?? 0) > 0 ? "alert" : "plain"}
                label="Pending Withdrawals"
                value={String(kpis.pending_withdrawals ?? 0)}
                icon={ArrowUpFromLine}
                to="/withdraw/pending"
              />
              <KpiCard
                tone={Number(kpis.pending_deposits ?? 0) > 0 ? "alert" : "plain"}
                label="Pending Deposits"
                value={String(kpis.pending_deposits ?? 0)}
                icon={Wallet}
                to="/deposit/pending"
              />
              <KpiCard
                tone={Number(kpis.pending_kyc ?? 0) > 0 ? "alert" : "plain"}
                label="Pending KYC"
                value={String(kpis.pending_kyc ?? 0)}
                icon={Award}
                to="/kyc/pending"
              />
              <KpiCard
                label="Income Streams"
                value={String(breakdown.length)}
                icon={TrendingUp}
                to="/fund/user-history"
              />
            </div>
          </section>
        </>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="rounded-2xl bg-white p-5 shadow-[0_1px_0_rgba(15,36,24,0.04)] ring-1 ring-black/[0.06] xl:col-span-2">
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold tracking-tight">Deposit trend</h3>
              <p className="text-xs text-muted-foreground">Completed deposits — last 14 days</p>
            </div>
          </div>
          <div className="h-56 w-full min-w-0 sm:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend.length ? trend : [{ day: "—", income: 0, users: 0 }]}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid var(--border)",
                    background: "var(--card)",
                  }}
                />
                <Area type="monotone" dataKey="income" stroke="var(--brand)" strokeWidth={2} fill="url(#g1)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-[0_1px_0_rgba(15,36,24,0.04)] ring-1 ring-black/[0.06]">
          <h3 className="text-base font-semibold tracking-tight">Income by wallet</h3>
          <p className="text-xs text-muted-foreground">Commission ledger totals</p>
          <div className="h-52 w-full min-w-0 sm:h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={breakdown.length ? breakdown : [{ name: "none", value: 1, color: "#e5e7eb" }]}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {(breakdown.length ? breakdown : [{ color: "#e5e7eb" }]).map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Legend verticalAlign="bottom" iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl bg-white p-5 shadow-[0_1px_0_rgba(15,36,24,0.04)] ring-1 ring-black/[0.06]">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-base font-semibold tracking-tight">Recent activity</h3>
          <Link to="/business-report" className="text-xs font-medium text-[color:var(--brand-dark)] hover:underline">
            Business report →
          </Link>
        </div>
        <ul className="divide-y divide-border">
          {recent.length === 0 && <li className="py-6 text-sm text-muted-foreground">No recent activity yet.</li>}
          {recent.map((a, i) => (
            <li key={`${a.at}-${i}`}>
              <Link
                to="/users/$associateId"
                params={{ associateId: a.associate_id || "JOY00000001" }}
                className="flex items-center gap-3 py-3 hover:bg-[color:var(--brand-tint)]/40"
              >
                <div className="grid h-8 w-8 place-items-center rounded-full bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)]">
                  <Activity className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-foreground">
                    {a.label} · <span className="font-semibold text-[color:var(--brand-dark)]">{a.associate_id}</span> · ₹{" "}
                    {Number(a.amount).toLocaleString("en-IN")}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{new Date(a.at).toLocaleString("en-IN")}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6">
        <RewardAchievementTable variant="inline" />
      </div>
    </div>
  );
}

function PendingChip({ label, count, to }: { label: string; count: number; to: string }) {
  return (
    <Link
      to={to}
      className="group inline-flex items-center gap-2 rounded-full border border-[color:var(--hero-border)] bg-white/80 px-3 py-1.5 text-sm shadow-sm backdrop-blur hover:border-[color:var(--brand)]"
    >
      <span className="grid h-5 w-5 place-items-center rounded-full bg-[color:var(--warn-tint)] text-[10px] font-semibold tabular-nums text-[color:var(--warn-text)]">
        {count}
      </span>
      <span className="text-foreground">{label}</span>
      <ArrowRight className="h-3 w-3 text-muted-foreground group-hover:text-[color:var(--brand-dark)]" />
    </Link>
  );
}
