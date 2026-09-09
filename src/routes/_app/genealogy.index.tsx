import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, LayoutList, Loader2, Network, Search } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { AssociateMlmTree } from "@/components/associate-mlm-tree";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { AuthAPI, ConfigAPI, GenealogyAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

type GenealogySearch = { focus?: string };

export const Route = createFileRoute("/_app/genealogy/")({
  head: () => ({ meta: [{ title: "Associate Tree — JoyClub Associate" }] }),
  validateSearch: (search: Record<string, unknown>): GenealogySearch => ({
    focus: typeof search.focus === "string" ? search.focus : undefined,
  }),
  component: AssociateTreePage,
});

type Node = {
  associate_id: string;
  username?: string;
  name?: string;
  mobile?: string;
  status?: string;
  card_tier?: string;
  flag_color?: string;
  join_amount?: string | number;
  total_business?: string | number;
  direct_count?: number;
  children_count?: number;
};

const FLAG: Record<string, { bar: string; soft: string; label: string }> = {
  green: { bar: "bg-[var(--flag-green)]", soft: "bg-[var(--flag-green)]/12", label: "Has investment" },
  gray: { bar: "bg-[var(--flag-gray)]", soft: "bg-[var(--flag-gray)]/15", label: "Joined — no investment" },
  blue: { bar: "bg-[var(--flag-green)]", soft: "bg-[var(--flag-green)]/12", label: "Has investment" },
  pink: { bar: "bg-[var(--flag-gray)]", soft: "bg-[var(--flag-gray)]/15", label: "Joined — no investment" },
};

function TreeRow({
  node,
  depth = 0,
  isLast = true,
  ancestorContinues = [],
}: {
  node: Node;
  depth?: number;
  isLast?: boolean;
  ancestorContinues?: boolean[];
}) {
  const [open, setOpen] = useState(depth < 1);
  const [children, setChildren] = useState<Node[] | null>(null);
  const [loading, setLoading] = useState(false);

  const directs = Number(node.direct_count ?? node.children_count ?? 0);
  const rawFlag = (node.flag_color ?? "gray").toLowerCase();
  const flagKey = rawFlag === "blue" ? "green" : rawFlag === "pink" ? "gray" : rawFlag;
  const flag = FLAG[flagKey] ?? FLAG.gray;
  const active = String(node.status ?? "active").toLowerCase() === "active";
  const id = node.username ?? node.associate_id;
  const invested = flagKey === "green";

  async function loadChildren() {
    if (children !== null) return;
    setLoading(true);
    try {
      const res = await GenealogyAPI.tree(node.associate_id);
      setChildren((res.children as Node[]) ?? []);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load children");
      setChildren([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) void loadChildren();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, node.associate_id]);

  return (
    <>
      <div
        className={cn(
          "group grid grid-cols-[minmax(0,1fr)_7.5rem_4.5rem] items-center gap-2 border-b border-[color:var(--border)]/50 pr-3 transition-colors",
          "hover:bg-[color:var(--brand-tint)]/45",
          depth === 0 && "bg-[color:var(--brand-tint)]/25",
        )}
        style={{ minHeight: 40 }}
      >
        <div className="flex min-w-0 items-center">
          <div className="flex h-10 shrink-0 self-stretch">
            {ancestorContinues.map((cont, i) => (
              <div key={i} className="relative w-4">
                {cont ? <span className="absolute inset-y-0 left-[7px] w-px bg-[color:var(--brand)]/25" /> : null}
              </div>
            ))}
            {depth > 0 ? (
              <div className="relative w-4">
                <span
                  className={cn(
                    "absolute left-[7px] w-px bg-[color:var(--brand)]/25",
                    isLast ? "top-0 h-1/2" : "inset-y-0",
                  )}
                />
                <span className="absolute left-[7px] top-1/2 h-px w-[9px] bg-[color:var(--brand)]/25" />
              </div>
            ) : (
              <div className="w-2" />
            )}
          </div>

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className={cn(
              "mr-1.5 grid h-6 w-6 shrink-0 place-items-center rounded-md border transition",
              "border-[color:var(--border)] bg-white text-[color:var(--brand-dark)]",
              "hover:border-[color:var(--brand)] hover:bg-[color:var(--brand)] hover:text-white",
            )}
            aria-expanded={open}
            aria-label={open ? "Collapse" : "Expand"}
          >
            {loading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : open ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>

          <span className={cn("mr-2 h-7 w-1 shrink-0 rounded-full", flag.bar)} title={flag.label} />

          <div className="min-w-0 flex-1 py-1.5">
            <div className="flex min-w-0 items-center gap-1.5">
              <Link
                to="/users/$associateId"
                params={{ associateId: node.associate_id }}
                className="truncate text-[13px] font-semibold tracking-tight text-[color:var(--foreground)] hover:text-[color:var(--brand-dark)] hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {id}
              </Link>
              <span
                className={cn(
                  "rounded px-1 py-px text-[9px] font-bold uppercase tracking-wide",
                  flag.soft,
                  invested ? "text-[var(--flag-green)]" : "text-stone-600",
                )}
              >
                {invested ? "Invested" : "No invest"}
              </span>
              {!active && (
                <span className="rounded bg-stone-200 px-1 text-[9px] font-semibold uppercase text-stone-600">
                  {node.status}
                </span>
              )}
            </div>
            <div className="truncate text-[11px] leading-tight text-muted-foreground">
              <span className="text-foreground/80">{node.name || "—"}</span>
              {node.mobile ? <span className="text-muted-foreground"> · {node.mobile}</span> : null}
            </div>
          </div>
        </div>

        <div className="text-right text-[13px] font-semibold tabular-nums text-foreground">
          ₹{Number(node.total_business ?? 0).toLocaleString("en-IN")}
        </div>

        <div className="text-right">
          <span
            className={cn(
              "inline-flex min-w-[2rem] justify-end rounded-md px-1.5 py-0.5 text-xs font-semibold tabular-nums",
              directs > 0 ? "bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)]" : "text-muted-foreground",
            )}
          >
            {directs}
          </span>
        </div>
      </div>

      {open &&
        children?.map((child, index) => (
          <TreeRow
            key={child.associate_id}
            node={child}
            depth={depth + 1}
            isLast={index === children.length - 1}
            ancestorContinues={[...ancestorContinues, !isLast]}
          />
        ))}
    </>
  );
}

function AssociateTreePage() {
  const { focus } = Route.useSearch();
  const [rootId, setRootId] = useState("");
  const [query, setQuery] = useState("");
  const [root, setRoot] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);
  const [isStaff, setIsStaff] = useState(false);
  const [myId, setMyId] = useState("");
  const [maxLegs, setMaxLegs] = useState(0);
  const [view, setView] = useState<"structure" | "list">("structure");

  async function load(id: string) {
    const target = id.trim().toUpperCase();
    if (!target) return;
    setLoading(true);
    try {
      const res = await GenealogyAPI.tree(target);
      setRoot(res.node as Node);
      setRootId(target);
      setQuery(target);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "You can only open your own downline");
    } finally {
      setLoading(false);
    }
  }

  async function openFullCompanyTree() {
    setLoading(true);
    try {
      const roots = await GenealogyAPI.roots();
      const first = roots.results?.[0];
      const id = String(first?.associate_id || first?.username || "").toUpperCase();
      if (!id) {
        // Fallback: server picks company root when associate_id omitted
        const res = await GenealogyAPI.tree();
        const node = res.node as Node;
        const rid = String(node.associate_id || "").toUpperCase();
        setRoot(node);
        setRootId(rid);
        setQuery(rid);
        return;
      }
      await load(id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to open full company tree");
      setLoading(false);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        const me = await AuthAPI.me();
        const staff = !!(me.is_staff || me.is_superuser);
        setIsStaff(staff);
        const aid = me.associate?.associate_id || "";
        setMyId(aid);
        try {
          const runtime = await ConfigAPI.runtime();
          const g =
            (runtime.genealogy as { max_legs?: number; leg_mode?: string; effective_max_legs?: number } | undefined) ??
            {};
          const fromMode = g.leg_mode && g.leg_mode !== "unlimited" ? Number(g.leg_mode) : 0;
          setMaxLegs(Number(g.effective_max_legs ?? g.max_legs ?? fromMode) || 0);
        } catch {
          /* ignore */
        }

        if (focus) {
          const start = focus.toUpperCase();
          setQuery(start);
          await load(start);
          return;
        }

        if (staff) {
          // Admin / staff: open full company tree from the top root
          await openFullCompanyTree();
          return;
        }

        if (aid) {
          setQuery(aid.toUpperCase());
          await load(aid.toUpperCase());
          return;
        }

        setLoading(false);
        toast.error("No associate profile linked to this login");
      } catch (e) {
        setLoading(false);
        toast.error(e instanceof Error ? e.message : "Failed to resolve your tree root");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus]);

  return (
    <div>
      <PageHeader
        title="Associate Tree"
        subtitle={
          isStaff
            ? "Full company tree (admin). Search any JOY id, or reopen Full tree from the top root."
            : `Your downline only — rooted at ${myId || "you"}`
        }
        actions={
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <div className="inline-flex rounded-lg border border-[color:var(--border)] bg-white p-0.5">
              <button
                type="button"
                onClick={() => setView("structure")}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold",
                  view === "structure"
                    ? "bg-[#F38118] text-white"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Network className="h-3.5 w-3.5" /> Structure
              </button>
              <button
                type="button"
                onClick={() => setView("list")}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold",
                  view === "list" ? "bg-[#2E75B6] text-white" : "text-muted-foreground hover:text-foreground",
                )}
              >
                <LayoutList className="h-3.5 w-3.5" /> List
              </button>
            </div>
            {isStaff ? (
              <Button
                type="button"
                variant="outline"
                className="w-full gap-1 sm:w-auto"
                onClick={() => void openFullCompanyTree()}
              >
                <Network className="h-4 w-4" /> Full tree
              </Button>
            ) : null}
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value.toUpperCase())}
              placeholder={isStaff ? "Any JOY id" : "Downline JOY id"}
              className="w-full sm:w-44"
            />
            <Button onClick={() => void load(query)} className="w-full gap-1 sm:w-auto">
              <Search className="h-4 w-4" /> Open
            </Button>
          </div>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="font-medium text-[color:var(--brand-dark)]">Root {rootId || "—"}</span>
        <span className="rounded-full bg-[color:var(--brand-tint)] px-2 py-0.5 font-medium text-[color:var(--brand-dark)]">
          Legs: {maxLegs > 0 ? `${maxLegs} per associate` : "Unlimited"}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[var(--flag-gray)]" /> Gray — joined, no investment
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[var(--flag-green)]" /> Green — has investment
        </span>
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-10 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading associate tree…
        </div>
      )}

      {!loading && root && view === "structure" && (
        <AssociateMlmTree rootId={rootId} maxDepth={isStaff ? 100 : 10} />
      )}

      {!loading && root && view === "list" && (
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-white shadow-[0_1px_0_rgba(15,36,24,0.03)]">
          <div className="grid grid-cols-[minmax(0,1fr)_7.5rem_4.5rem] gap-2 border-b border-[color:var(--border)] bg-[color:var(--muted)]/40 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            <div className="pl-10">Associate</div>
            <div className="text-right">Business</div>
            <div className="text-right">Directs</div>
          </div>
          <TreeRow node={root} />
        </div>
      )}

      {!loading && !root && (
        <div className="rounded-xl border border-dashed p-8 text-sm text-muted-foreground">
          No tree data for this account yet.
        </div>
      )}
    </div>
  );
}
