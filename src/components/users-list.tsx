import { Link, useNavigate } from "@tanstack/react-router";
import { Fragment, useEffect, useMemo, useState } from "react";
import { Loader2, Minus, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { LevelBadge } from "@/components/earning-level-badge";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AssociatesAPI, AuthAPI, ConfigAPI, setTokens, unwrapList } from "@/lib/api";
import { useAuth } from "@/lib/rbac";
import { cn } from "@/lib/utils";

type Row = Record<string, unknown>;

const flagDot: Record<string, string> = {
  green: "bg-[var(--flag-green)]",
  gray: "bg-[var(--flag-gray)]",
  blue: "bg-[var(--flag-gray)]",
  pink: "bg-[var(--flag-gray)]",
};

function money(v: unknown) {
  return `₹ ${Number(v ?? 0).toLocaleString("en-IN")}`;
}

function joinDate(v: unknown) {
  if (!v) return "—";
  const d = new Date(String(v));
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function UserList({
  status,
  earningLevel,
  performanceLevel,
  treeLevel,
  legLevel,
  title,
  subtitle,
  hideStatusFilter,
  scope,
}: {
  status?: string;
  /** Filter to associates who achieved this reward / earning level. */
  earningLevel?: number;
  /** Filter to associates who achieved this performance level. */
  performanceLevel?: number;
  /** Absolute genealogy depth from company root. */
  treeLevel?: number;
  /** Relative under-leg depth (1 = direct). */
  legLevel?: number;
  title: string;
  subtitle?: string;
  hideStatusFilter?: boolean;
  /** "my" = under-leg only; omit for All Associates (staff = everyone). */
  scope?: "my" | "all";
}) {
  const navigate = useNavigate();
  const { session, applyApiUser } = useAuth();
  const isStaff = !!session?.isStaff;
  const myAssociateId = String(session?.associateId || "").toUpperCase();
  const canOpenProfile = (aid: string) =>
    isStaff || (!!aid && aid.toUpperCase() === myAssociateId);
  const showLegLevel = scope === "my" || !isStaff;
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFlag, setShowFlag] = useState(false);
  const [showCard, setShowCard] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState(status || "all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loginAsId, setLoginAsId] = useState<string | null>(null);

  useEffect(() => {
    setStatusFilter(status || "all");
  }, [status]);

  useEffect(() => {
    setLoading(true);
    AssociatesAPI.list({
      ...(statusFilter && statusFilter !== "all" ? { status: statusFilter } : {}),
      ...(earningLevel != null ? { earning_level: earningLevel } : {}),
      ...(performanceLevel != null ? { performance_level: performanceLevel } : {}),
      ...(treeLevel != null ? { tree_level: treeLevel } : {}),
      ...(legLevel != null ? { leg_level: legLevel } : {}),
      ...(scope === "my" ? { scope: "my" } : {}),
      page_size: 500,
    })
      .then((d) =>
        setRows(
          unwrapList(d).map((r, i) => ({
            ...r,
            id: (r.id as string | number | undefined) ?? String(r.associate_id ?? r.username ?? i),
          })),
        ),
      )
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load associates"))
      .finally(() => setLoading(false));
  }, [statusFilter, earningLevel, performanceLevel, treeLevel, legLevel, scope]);

  useEffect(() => {
    ConfigAPI.runtime()
      .then((d) => {
        const m = (d.menu as Record<string, unknown> | undefined) ?? {};
        setShowFlag(!!m.show_users_flag_column);
        setShowCard(!!m.show_users_card_column);
      })
      .catch(() => {
        setShowFlag(false);
        setShowCard(false);
      });
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = rows.filter((r) => {
      if (needle) {
        const hay = `${r.associate_id} ${r.username} ${r.name} ${r.mobile} ${r.sponsor_id} ${r.lead_reference}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      if (dateFrom || dateTo) {
        const created = r.created_at ? new Date(String(r.created_at)) : null;
        if (!created || Number.isNaN(created.getTime())) return false;
        if (dateFrom) {
          const from = new Date(dateFrom);
          from.setHours(0, 0, 0, 0);
          if (created < from) return false;
        }
        if (dateTo) {
          const to = new Date(dateTo);
          to.setHours(23, 59, 59, 999);
          if (created > to) return false;
        }
      }
      return true;
    });
    if (showLegLevel) {
      list.sort((a, b) => Number(a.leg_level ?? 0) - Number(b.leg_level ?? 0));
    } else {
      list.sort((a, b) => Number(a.tree_level ?? 0) - Number(b.tree_level ?? 0));
    }
    return list;
  }, [rows, q, dateFrom, dateTo, showLegLevel]);

  function toggle(id: string) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function resetFilters() {
    setQ("");
    setDateFrom("");
    setDateTo("");
    if (!status) setStatusFilter("all");
  }

  async function loginAs(associateId: string) {
    if (!isStaff) {
      toast.error("Only staff can login as a user");
      return;
    }
    setLoginAsId(associateId);
    try {
      const result = await AuthAPI.impersonate(associateId);
      setTokens({ access: result.access, refresh: result.refresh });
      applyApiUser(result.user);
      toast.success(`Logged in as ${associateId}`);
      void navigate({ to: "/dashboard" });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Login as failed");
    } finally {
      setLoginAsId(null);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title={title}
        subtitle={subtitle ?? `${filtered.length} associates`}
        actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
      />

      <div className="rounded-2xl border border-border bg-card p-3 sm:p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Start date</label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="h-10" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">End date</label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="h-10" />
          </div>
          {!status && !hideStatusFilter ? (
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">ID status</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="blocked">Blocked</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <div
            className={cn(
              !status && !hideStatusFilter ? "lg:col-span-2" : "sm:col-span-2 lg:col-span-3",
            )}
          >
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Search user</label>
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Name, Username, number"
              className="h-10"
            />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button type="button" size="sm" className="bg-[color:var(--brand)] hover:bg-[color:var(--brand-dark)]">
            Search Now
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={resetFilters}>
            Reset
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold">{scope === "my" ? "My under-leg" : "All Users"}</h3>
          <p className="text-xs text-muted-foreground">
            {scope === "my"
              ? "Only your under-leg associates with relative level (L1 = direct)"
              : "Click + to open profile details for each associate"}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] text-sm">
            <thead className="bg-[color:var(--brand-dark)] text-left text-xs uppercase tracking-wide text-white">
              <tr>
                <th className="w-20 px-3 py-3 font-medium">Sr.</th>
                <th className="px-3 py-3 font-medium">Name</th>
                <th className="px-3 py-3 font-medium">User Name</th>
                <th className="px-3 py-3 font-medium">
                  {showLegLevel ? "Leg Level" : "Tree Level"}
                </th>
                {isStaff ? <th className="px-3 py-3 font-medium">Password</th> : null}
                <th className="px-3 py-3 font-medium">Sponsor Id</th>
                <th className="px-3 py-3 font-medium">Wallet Balance</th>
                <th className="px-3 py-3 font-medium">Fund Wallet</th>
                <th className="px-3 py-3 font-medium">Mobile</th>
                {scope === "my" ? null : (
                  <th className="px-3 py-3 font-medium">Joining Date</th>
                )}
                {showFlag ? <th className="px-3 py-3 font-medium">Flag</th> : null}
                {showCard ? <th className="px-3 py-3 font-medium">Card</th> : null}
                <th className="px-3 py-3 font-medium">Reward</th>
                <th className="px-3 py-3 font-medium">Performance</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={15} className="px-4 py-16 text-center text-muted-foreground">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={15} className="px-4 py-16 text-center text-muted-foreground">
                    No associates found
                  </td>
                </tr>
              ) : (
                filtered.map((r, idx) => {
                  const id = String(r.id);
                  const aid = String(r.username ?? r.associate_id ?? "");
                  const open = !!expanded[id];
                  const colSpan =
                    10 +
                    (scope === "my" ? 0 : 1) +
                    (showFlag ? 1 : 0) +
                    (showCard ? 1 : 0) +
                    (isStaff ? 1 : 0);
                  const levelNum = showLegLevel
                    ? Number(r.leg_level ?? 0)
                    : Number(r.tree_level ?? 0);
                  const levelLabel =
                    levelNum > 0 ? `Level ${levelNum}` : showLegLevel ? "—" : "Root / —";
                  return (
                    <Fragment key={id}>
                      <tr className="border-t border-border hover:bg-[color:var(--muted)]/50">
                        <td className="px-3 py-2.5">
                          <button
                            type="button"
                            onClick={() => toggle(id)}
                            className={cn(
                              "inline-flex h-7 w-7 items-center justify-center rounded-md text-white",
                              open ? "bg-red-500 hover:bg-red-600" : "bg-sky-600 hover:bg-sky-700",
                            )}
                            aria-label={open ? "Collapse profile" : "Expand profile"}
                          >
                            {open ? <Minus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                          </button>
                          <span className="ml-2 tabular-nums text-muted-foreground">{idx + 1}</span>
                        </td>
                        <td className="px-3 py-2.5 font-medium">
                          {canOpenProfile(aid) ? (
                            <Link
                              to="/users/$associateId"
                              params={{ associateId: aid }}
                              className="hover:underline"
                            >
                              {String(r.name || aid || "—")}
                            </Link>
                          ) : (
                            <span>{String(r.name || aid || "—")}</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          {canOpenProfile(aid) ? (
                            <Link
                              to="/users/$associateId"
                              params={{ associateId: aid }}
                              className="font-semibold text-[color:var(--brand-dark)] hover:underline"
                            >
                              {aid || "—"}
                            </Link>
                          ) : (
                            <span className="font-semibold text-[color:var(--brand-dark)]">{aid || "—"}</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex rounded-full bg-[color:var(--brand-tint)] px-2.5 py-0.5 text-xs font-semibold text-[color:var(--brand-dark)]">
                            {levelLabel}
                          </span>
                        </td>
                        {isStaff ? (
                          <td className="px-3 py-2.5 font-mono text-xs">
                            {String(r.login_password || "—")}
                          </td>
                        ) : null}
                        <td className="px-3 py-2.5">{String(r.sponsor_id || r.lead_reference || "—")}</td>
                        <td className="px-3 py-2.5 tabular-nums">{money(r.wallet_balance)}</td>
                        <td className="px-3 py-2.5 tabular-nums">{money(r.fund_wallet)}</td>
                        <td className="px-3 py-2.5">{String(r.mobile || "—")}</td>
                        {scope === "my" ? null : (
                          <td className="px-3 py-2.5 whitespace-nowrap">{joinDate(r.created_at)}</td>
                        )}
                        {showFlag ? (
                          <td className="px-3 py-2.5">
                            <span className="inline-flex items-center gap-1.5 capitalize">
                              <span
                                className={`h-2.5 w-2.5 rounded-sm ${flagDot[String(r.flag_color)] ?? flagDot.gray}`}
                              />
                              {String(r.flag_color ?? "gray") === "green" ? "Invested" : "No investment"}
                            </span>
                          </td>
                        ) : null}
                        {showCard ? (
                          <td className="px-3 py-2.5 capitalize">{String(r.card_tier ?? "gray")}</td>
                        ) : null}
                        <td className="px-3 py-2.5">
                          <LevelBadge
                            kind="reward"
                            level={r.reward_level ?? r.earning_level}
                            name={r.reward_level_name ?? r.earning_level_name}
                          />
                        </td>
                        <td className="px-3 py-2.5">
                          <LevelBadge
                            kind="performance"
                            level={r.performance_level}
                            name={r.performance_level_name}
                          />
                        </td>
                      </tr>
                      {open ? (
                        <tr className="border-t border-border bg-[color:var(--hero)]/50">
                          <td colSpan={colSpan} className="px-4 py-3">
                            <div className="flex flex-wrap items-center gap-x-8 gap-y-3 text-sm">
                              <div>
                                <span className="text-muted-foreground">Direct Member : </span>
                                <span className="font-semibold tabular-nums">{Number(r.direct_count ?? 0)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Direct Active : </span>
                                <span className="font-semibold tabular-nums">
                                  {Number(r.direct_active_count ?? 0)}
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">
                                  {showLegLevel ? "Leg Level" : "Tree Level"} :{" "}
                                </span>
                                <span className="font-semibold">{levelLabel}</span>
                              </div>
                              <div className="inline-flex items-center gap-2">
                                <span className="text-muted-foreground">Status :</span>
                                <StatusBadge status={String(r.status)} />
                              </div>
                              <div className="ml-auto flex flex-wrap items-center gap-2">
                                {canOpenProfile(aid) ? (
                                  <>
                                    <span className="text-muted-foreground">Action :</span>
                                    <Button asChild size="sm" variant="outline" className="gap-1.5">
                                      <Link to="/users/$associateId" params={{ associateId: aid }}>
                                        <Pencil className="h-3.5 w-3.5" />
                                        {isStaff ? "Edit" : "View"}
                                      </Link>
                                    </Button>
                                  </>
                                ) : null}
                                {isStaff ? (
                                  <Button
                                    size="sm"
                                    className="bg-emerald-600 hover:bg-emerald-700"
                                    disabled={!aid || loginAsId === aid}
                                    onClick={() => void loginAs(aid)}
                                  >
                                    {loginAsId === aid ? (
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    ) : (
                                      "Login"
                                    )}
                                  </Button>
                                ) : null}
                              </div>
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
