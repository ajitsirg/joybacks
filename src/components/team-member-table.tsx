import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { AssociatesAPI, unwrapList } from "@/lib/api";
import { cn } from "@/lib/utils";

type Row = Record<string, unknown>;

function packageLabel(r: Row) {
  const amt = Number(r.join_amount ?? 0);
  const status = String(r.status || "").toLowerCase();
  if (amt <= 0 || status !== "active") {
    return `${amt || 0} Not Active`;
  }
  return `₹ ${amt.toLocaleString("en-IN")}`;
}

function levelNum(r: Row) {
  return Number(r.leg_level ?? r.tree_level ?? 0);
}

function levelLabel(r: Row) {
  const n = levelNum(r);
  return n > 0 ? `LEVEL ${n}` : "ROOT";
}

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const active = s === "active";
  return (
    <span
      className={cn(
        "inline-flex min-w-[4.5rem] items-center justify-center rounded px-2.5 py-1 text-xs font-semibold text-white",
        active ? "bg-emerald-600" : s === "pending" ? "bg-amber-500" : "bg-slate-500",
      )}
    >
      {active ? "Active" : status ? status.charAt(0).toUpperCase() + status.slice(1) : "—"}
    </span>
  );
}

/** All Team table matching reference screenshots */
export function TeamMemberTable({
  title = "All Team",
  subtitle,
  legLevel,
  showView = false,
}: {
  title?: string;
  subtitle?: string;
  /** If set, only this under-leg level (1 = direct). */
  legLevel?: number;
  showView?: boolean;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    AssociatesAPI.list({
      scope: "my",
      page_size: 500,
      ...(legLevel != null ? { leg_level: legLevel } : {}),
    })
      .then((d) => {
        const list = unwrapList(d).map((r, i) => ({
          ...r,
          id: (r.id as string | number | undefined) ?? String(r.associate_id ?? i),
        }));
        // Level 1 first, then 2, … then by name
        list.sort((a, b) => {
          const la = levelNum(a);
          const lb = levelNum(b);
          if (la !== lb) return la - lb;
          return String(a.name || "").localeCompare(String(b.name || ""));
        });
        setRows(list);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load team"))
      .finally(() => setLoading(false));
  }, [legLevel]);

  return (
    <div className="space-y-4">
      <PageHeader title={title} subtitle={subtitle ?? `${rows.length} member(s)`} />

      <div className="overflow-hidden rounded-xl border border-border bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[780px] text-sm">
            <thead className="border-b border-border bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-700">
              <tr>
                <th className="px-3 py-3">Sr No.</th>
                <th className="px-3 py-3">User Name</th>
                <th className="px-3 py-3">User ID</th>
                <th className="px-3 py-3">Package</th>
                <th className="px-3 py-3">Level</th>
                <th className="px-3 py-3">Status</th>
                {showView ? <th className="px-3 py-3">View</th> : null}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={showView ? 7 : 6} className="px-4 py-16 text-center text-muted-foreground">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={showView ? 7 : 6} className="px-4 py-16 text-center text-muted-foreground">
                    No team members found
                  </td>
                </tr>
              ) : (
                rows.map((r, idx) => {
                  const aid = String(r.associate_id ?? r.username ?? "");
                  const lvl = Math.max(1, levelNum(r) || 1);
                  return (
                    <tr key={String(r.id)} className="border-b border-border last:border-0 hover:bg-slate-50/80">
                      <td className="px-3 py-3 tabular-nums text-slate-600">{idx + 1}</td>
                      <td className="px-3 py-3 font-medium text-slate-900">{String(r.name || aid || "—")}</td>
                      <td className="px-3 py-3 text-slate-800">{aid || "—"}</td>
                      <td className="px-3 py-3 text-slate-700">{packageLabel(r)}</td>
                      <td className="px-3 py-3 font-semibold uppercase tracking-wide text-slate-800">
                        {levelLabel(r)}
                      </td>
                      <td className="px-3 py-3">
                        <StatusPill status={String(r.status || "pending")} />
                      </td>
                      {showView ? (
                        <td className="px-3 py-3">
                          <Link
                            to="/users/team/level/$level"
                            params={{ level: String(lvl) }}
                            className="font-medium text-sky-500 hover:text-sky-600 hover:underline"
                          >
                            View
                          </Link>
                        </td>
                      ) : null}
                    </tr>
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
