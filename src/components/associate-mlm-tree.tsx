import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Loader2, ZoomIn } from "lucide-react";
import { toast } from "sonner";
import { GenealogyAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

export type TreeNode = {
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
  children?: TreeNode[];
};

const AVATAR_COLORS = ["#F4C430", "#7EC8E3", "#8FCF9A", "#F5A26B", "#C9A8E0", "#F5D56A", "#A8D5E5"];

function initials(name?: string, id?: string): string {
  const n = (name || "").trim();
  if (n) {
    const parts = n.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return [...n].slice(0, 2).join("").toUpperCase();
  }
  return (id || "JC").slice(-2).toUpperCase();
}

function isInvested(flag?: string): boolean {
  const f = (flag || "gray").toLowerCase();
  return f === "green" || f === "blue";
}

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i);
  return h | 0;
}

async function loadSubtree(associateId: string, maxDepth: number): Promise<TreeNode> {
  const res = await GenealogyAPI.tree(associateId);
  const root: TreeNode = { ...(res.node as TreeNode), children: [] };

  async function fill(node: TreeNode, depth: number) {
    if (depth >= maxDepth) return;
    const page = await GenealogyAPI.tree(node.associate_id);
    const kids = ((page.children as TreeNode[]) ?? []).map((c) => ({ ...c, children: [] as TreeNode[] }));
    node.children = kids;
    await Promise.all(kids.map((c) => fill(c, depth + 1)));
  }

  await fill(root, 0);
  return root;
}

function PersonCard({ node, depth }: { node: TreeNode; depth: number }) {
  const id = node.username || node.associate_id;
  const invested = isInvested(node.flag_color);
  const color = AVATAR_COLORS[Math.abs(hashCode(id)) % AVATAR_COLORS.length];
  const active = String(node.status ?? "active").toLowerCase() === "active";
  const isLeader = depth === 0;
  const shortName = (node.name || "—").trim().split(/\s+/)[0] || "—";

  return (
    <Link
      to="/users/$associateId"
      params={{ associateId: node.associate_id }}
      className="group relative z-[1] mx-auto flex w-[3.35rem] flex-col items-center sm:w-[3.75rem]"
      title={`${id} · ${node.name || "—"} · L${depth}${invested ? " · invested" : ""}`}
    >
      <span
        className={cn(
          "grid h-8 w-8 place-items-center rounded-full border-2 text-[9px] font-extrabold text-[#0B3D24] shadow-sm transition group-hover:scale-105 sm:h-9 sm:w-9 sm:text-[10px]",
          isLeader ? "border-[#F5D56A] ring-2 ring-[#F5D56A]/40" : "border-white group-hover:border-[#2E75B6]",
        )}
        style={{ background: color }}
      >
        {initials(node.name, id)}
      </span>
      <span
        className={cn(
          "absolute right-[0.35rem] top-5 h-2 w-2 rounded-full border border-white sm:right-[0.45rem] sm:top-6",
          invested ? "bg-[#149A56]" : "bg-stone-400",
        )}
      />
      <span className="mt-0.5 max-w-full truncate text-center text-[8px] font-extrabold leading-tight text-[#1B4F72] group-hover:underline sm:text-[9px]">
        {id.replace(/^JOY/i, "")}
      </span>
      <span className="max-w-full truncate text-center text-[7px] leading-none text-[#3D5A6C] sm:text-[8px]">
        {shortName}
      </span>
      {!active ? (
        <span className="mt-0.5 rounded bg-amber-100 px-0.5 text-[6px] font-bold uppercase leading-none text-amber-800">
          {String(node.status).slice(0, 3)}
        </span>
      ) : (
        <span
          className={cn(
            "mt-0.5 rounded px-1 text-[6px] font-extrabold leading-none text-white sm:text-[7px]",
            isLeader ? "bg-[#2E75B6]" : "bg-[#7FB3D5]",
          )}
        >
          L{depth}
        </span>
      )}
    </Link>
  );
}

/** Classic org-chart branch: parent → continuous lines → each child. */
function OrgBranch({ node, depth, maxDepth }: { node: TreeNode; depth: number; maxDepth: number }) {
  const children = node.children ?? [];
  const showKids = children.length > 0 && depth < maxDepth;

  return (
    <li>
      <PersonCard node={node} depth={depth} />
      {showKids ? (
        <ul>
          {children.map((child) => (
            <OrgBranch key={child.associate_id} node={child} depth={depth + 1} maxDepth={maxDepth} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

const MAX_TREE_DEPTH = 100;
const DEPTH_OPTIONS = Array.from({ length: MAX_TREE_DEPTH }, (_, i) => i + 1);

export function AssociateMlmTree({
  rootId,
  maxDepth = 10,
}: {
  rootId: string;
  maxDepth?: number;
  /** @deprecated clicks open profile now */
  onOpenRoot?: (id: string) => void;
}) {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [depth, setDepth] = useState(Math.min(Math.max(maxDepth, 1), MAX_TREE_DEPTH));

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!rootId) return;
      setLoading(true);
      try {
        const data = await loadSubtree(rootId, depth);
        if (!cancelled) setTree(data);
      } catch (e) {
        if (!cancelled) {
          setTree(null);
          toast.error(e instanceof Error ? e.message : "Failed to load tree structure");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [rootId, depth]);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-[#B8D4E8] bg-[#EEF6FB] py-16 text-[#2E75B6]">
        <Loader2 className="h-5 w-5 animate-spin" /> Building network tree…
      </div>
    );
  }

  if (!tree) {
    return (
      <div className="rounded-2xl border border-dashed border-[#B8D4E8] bg-[#EEF6FB] p-10 text-center text-sm text-muted-foreground">
        No tree data for this account yet.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-[#F5A623]/45 bg-[#EEF6FB] shadow-sm">
      <div className="bg-[#F38118] px-4 py-3 text-center">
        <h2 className="text-base font-extrabold tracking-wide text-white sm:text-lg">
          Multilevel Marketing Structure
        </h2>
        <p className="mt-0.5 text-xs text-white/90">JoyClub Associate Network · tap any member for profile</p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#B8D4E8] bg-white/90 px-4 py-2 text-xs">
        <span className="font-medium text-[#1B4F72]">
          Lines show sponsor → downline · green dot = invested
        </span>
        <label className="inline-flex items-center gap-2 text-[#3D5A6C]">
          <ZoomIn className="h-3.5 w-3.5" />
          Depth
          <select
            className="rounded-md border border-[#B8D4E8] bg-white px-2 py-1 font-semibold text-[#1B4F72]"
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          >
            {DEPTH_OPTIONS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Compact org-chart connectors */}
      <style>{`
        .joy-org {
          --line: #2E75B6;
          --line-w: 1.5px;
          --gap-y: 10px;
          --gap-x: 2px;
        }
        .joy-org, .joy-org ul {
          padding-top: var(--gap-y);
          position: relative;
          display: flex;
          justify-content: center;
          margin: 0;
          list-style: none;
        }
        .joy-org {
          padding-top: 4px;
          padding-bottom: 12px;
          padding-inline: 6px;
        }
        .joy-org ul::before {
          content: "";
          position: absolute;
          top: 0;
          left: 50%;
          border-left: var(--line-w) solid var(--line);
          width: 0;
          height: var(--gap-y);
          transform: translateX(-50%);
        }
        .joy-org li {
          list-style: none;
          text-align: center;
          position: relative;
          padding: var(--gap-y) var(--gap-x) 0;
          margin: 0;
        }
        .joy-org li::before,
        .joy-org li::after {
          content: "";
          position: absolute;
          top: 0;
          right: 50%;
          border-top: var(--line-w) solid var(--line);
          width: 50%;
          height: var(--gap-y);
        }
        .joy-org li::after {
          right: auto;
          left: 50%;
          border-left: var(--line-w) solid var(--line);
        }
        .joy-org li:only-child::before,
        .joy-org li:only-child::after {
          display: none;
        }
        .joy-org > li {
          padding-top: 0;
        }
        .joy-org > li::before,
        .joy-org > li::after {
          display: none;
        }
        .joy-org li:first-child::before,
        .joy-org li:last-child::after {
          border: 0 none;
        }
        .joy-org li:last-child::before {
          border-right: var(--line-w) solid var(--line);
          border-radius: 0 4px 0 0;
        }
        .joy-org li:first-child::after {
          border-radius: 4px 0 0 0;
        }
      `}</style>

      <div className="overflow-x-auto overscroll-x-contain">
        <div className="inline-block min-w-full">
          <ul className="joy-org">
            <OrgBranch node={tree} depth={0} maxDepth={depth} />
          </ul>
        </div>
      </div>
    </div>
  );
}
