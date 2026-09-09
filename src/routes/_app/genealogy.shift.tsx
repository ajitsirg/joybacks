import { createFileRoute, Link, Navigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowDown, GitBranch, Loader2, Shield } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AssociatesAPI, GenealogyAPI } from "@/lib/api";
import { useAuth } from "@/lib/rbac";

export const Route = createFileRoute("/_app/genealogy/shift")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Shift Associate — JoyClub Associate" },
      {
        name: "description",
        content: "Place any associate under any other. Full leg moves with them.",
      },
    ],
  }),
  component: ShiftAssociatePage,
});

type Preview = {
  associate_id: string;
  name: string;
  status: string;
  sponsor_id: string;
  direct_count: number;
};

function normalizeJoy(raw: string) {
  return raw.trim().toUpperCase().replace(/\s+/g, "");
}

function PreviewCard({
  label,
  loading,
  error,
  data,
}: {
  label: string;
  loading: boolean;
  error: string | null;
  data: Preview | null;
}) {
  if (loading) {
    return (
      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking {label}…
      </p>
    );
  }
  if (error) {
    return <p className="text-xs text-[color:var(--danger)]">{error}</p>;
  }
  if (!data) return null;
  return (
    <div className="rounded-xl border border-border bg-muted/30 px-3 py-2 text-xs">
      <p className="font-semibold text-[color:var(--brand-dark)]">
        {data.name || "—"} · {data.associate_id}
      </p>
      <p className="mt-0.5 text-muted-foreground capitalize">
        Status {data.status || "—"} · current sponsor {data.sponsor_id || "—"} · directs{" "}
        {data.direct_count}
      </p>
    </div>
  );
}

function useAssociatePreview(joyId: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Preview | null>(null);

  useEffect(() => {
    const id = normalizeJoy(joyId);
    if (!id || id.length < 4) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    const t = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      AssociatesAPI.get(id)
        .then((row) => {
          if (cancelled) return;
          setData({
            associate_id: String(row.associate_id || row.username || id).toUpperCase(),
            name: String(row.name || ""),
            status: String(row.status || ""),
            sponsor_id: String(row.sponsor_id || ""),
            direct_count: Number(row.direct_count ?? 0),
          });
        })
        .catch((e) => {
          if (cancelled) return;
          setData(null);
          setError(e instanceof Error ? e.message : "Associate not found");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 350);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [joyId]);

  return { loading, error, data };
}

function ShiftAssociatePage() {
  const { session, hydrated } = useAuth();
  const [fromId, setFromId] = useState("");
  const [underId, setUnderId] = useState("");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{
    moved_count: number;
    old_sponsor_id: string | null;
    new_sponsor_id: string;
    subtree_ids: string[];
  } | null>(null);

  const fromPreview = useAssociatePreview(fromId);
  const underPreview = useAssociatePreview(underId);

  if (!hydrated) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }
  if (!session) return null;
  if (!(session.isSuperuser || session.isStaff)) {
    return <Navigate to="/genealogy" />;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const from = normalizeJoy(fromId);
    const under = normalizeJoy(underId);
    if (!from || !under) {
      toast.error("Enter both JOY IDs");
      return;
    }
    if (from === under) {
      toast.error("Cannot place an associate under themselves");
      return;
    }
    if (fromPreview.error || underPreview.error) {
      toast.error("Fix invalid JOY IDs before shifting");
      return;
    }
    if (
      !window.confirm(
        `Shift ${from} under ${under}?\n\nEntire downline moves with them.`,
      )
    ) {
      return;
    }
    setSaving(true);
    setResult(null);
    try {
      const res = await GenealogyAPI.shift(from, under);
      setResult({
        moved_count: res.moved_count,
        old_sponsor_id: res.old_sponsor_id,
        new_sponsor_id: res.new_sponsor_id,
        subtree_ids: res.subtree_ids,
      });
      toast.success(`Shifted ${from} under ${under} (${res.moved_count} in leg)`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Shift failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <PageHeader
        title="Shift Associate"
        subtitle="Simple form — type JOY ID to move, and JOY ID of new upline."
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[color:var(--brand-tint)] px-2.5 py-1 text-xs font-medium text-[color:var(--brand-dark)]">
            <Shield className="h-3.5 w-3.5" /> Admin
          </span>
        }
      />

      <form onSubmit={(e) => void submit(e)} className="space-y-5 rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="space-y-2">
          <Label htmlFor="from-id">1. Move this associate (JOY ID)</Label>
          <Input
            id="from-id"
            autoFocus
            autoComplete="off"
            placeholder="e.g. JOY9998887771"
            value={fromId}
            onChange={(e) => {
              setFromId(e.target.value.toUpperCase());
              setResult(null);
            }}
            className="h-12 font-mono text-base tracking-wide"
          />
          <PreviewCard
            label="associate"
            loading={fromPreview.loading}
            error={fromPreview.error}
            data={fromPreview.data}
          />
        </div>

        <div className="flex justify-center text-muted-foreground">
          <ArrowDown className="h-5 w-5" />
        </div>

        <div className="space-y-2">
          <Label htmlFor="under-id">2. Place under this associate (new sponsor JOY ID)</Label>
          <Input
            id="under-id"
            autoComplete="off"
            placeholder="e.g. JOYIND0041"
            value={underId}
            onChange={(e) => setUnderId(e.target.value.toUpperCase())}
            className="h-12 font-mono text-base tracking-wide"
          />
          <PreviewCard
            label="new sponsor"
            loading={underPreview.loading}
            error={underPreview.error}
            data={underPreview.data}
          />
        </div>

        <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-950">
          Entire downline / leg of the moved associate moves with them. Cannot place someone under
          their own downline.
        </p>

        <Button
          type="submit"
          className="h-12 w-full gap-2 text-base"
          disabled={
            saving ||
            !normalizeJoy(fromId) ||
            !normalizeJoy(underId) ||
            !!fromPreview.error ||
            !!underPreview.error ||
            fromPreview.loading ||
            underPreview.loading
          }
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitBranch className="h-4 w-4" />}
          Shift now
        </Button>
      </form>

      {result ? (
        <div className="rounded-2xl border border-[color:var(--brand)]/30 bg-[color:var(--brand-tint)]/40 p-4 text-sm">
          <p className="font-semibold text-[color:var(--brand-dark)]">Shift complete</p>
          <p className="mt-1">
            Old sponsor: <strong>{result.old_sponsor_id || "—"}</strong> → New:{" "}
            <strong>{result.new_sponsor_id}</strong>
          </p>
          <p className="mt-1">People moved in leg: {result.moved_count}</p>
          <div className="mt-2 max-h-40 overflow-y-auto rounded-lg bg-white/70 p-2 font-mono text-xs">
            {result.subtree_ids.join(", ")}
          </div>
          <Button asChild size="sm" variant="outline" className="mt-3">
            <Link to="/genealogy" search={{ focus: normalizeJoy(fromId) }}>
              Open tree at moved associate
            </Link>
          </Button>
        </div>
      ) : null}
    </div>
  );
}
