import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { AssociatesAPI } from "@/lib/api";
import { DocThumb } from "@/components/doc-thumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/_app/team/approvals")({
  head: () => ({ meta: [{ title: "Team Approvals — JoyClub Associate" }] }),
  component: TeamApprovalsPage,
});

type JoinRow = {
  associate_id: string;
  name: string;
  mobile: string;
  join_amount: string;
  card_tier: string;
  flag_color: string;
  created_at: string;
  kyc?: {
    full_name: string;
    pan: string;
    aadhaar: string;
    bank_name: string;
    account_number: string;
    ifsc: string;
    upi_id: string;
    profile_photo_url?: string | null;
    aadhaar_document_url?: string | null;
    aadhaar_front_url?: string | null;
    aadhaar_back_url?: string | null;
    aadhaar_attached?: boolean;
    pan_document_url?: string | null;
    bank_document_url?: string | null;
  } | null;
};

function TeamApprovalsPage() {
  const [rows, setRows] = useState<JoinRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await AssociatesAPI.pendingJoins();
      setRows(res.results as JoinRow[]);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function approve(id: string) {
    setBusy(id);
    try {
      await AssociatesAPI.leaderApprove(id);
      toast.success(`${id} approved`);
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(null);
    }
  }

  async function reject(id: string) {
    setBusy(id);
    try {
      await AssociatesAPI.leaderReject(id, reason[id] || "Rejected by lead");
      toast.success(`${id} rejected`);
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold text-[color:var(--brand-dark)]">Team join approvals</h1>
        <p className="text-sm text-muted-foreground">
          Review Aadhaar, PAN, bank, UPI and profile photo from joiners under you. Approve to activate them.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="rounded-2xl border border-[color:var(--border)] bg-white p-8 text-sm text-muted-foreground">
          No pending join requests.
        </div>
      ) : (
        <div className="space-y-4">
          {rows.map((row) => (
            <div key={row.associate_id} className="rounded-2xl border border-[color:var(--border)] bg-white p-4 shadow-sm md:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-lg font-semibold">{row.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {row.associate_id} · {row.mobile} · {row.card_tier} · ₹{row.join_amount}
                  </div>
                </div>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">PENDING</span>
              </div>

              {row.kyc && (
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="space-y-1 text-sm">
                    <div><span className="text-muted-foreground">Full name:</span> {row.kyc.full_name}</div>
                    <div><span className="text-muted-foreground">PAN:</span> {row.kyc.pan}</div>
                    <div><span className="text-muted-foreground">Aadhaar:</span> {row.kyc.aadhaar}</div>
                    <div><span className="text-muted-foreground">Bank:</span> {row.kyc.bank_name}</div>
                    <div><span className="text-muted-foreground">Account:</span> {row.kyc.account_number}</div>
                    <div><span className="text-muted-foreground">IFSC:</span> {row.kyc.ifsc}</div>
                    <div><span className="text-muted-foreground">UPI:</span> {row.kyc.upi_id}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <DocThumb label="Profile" url={row.kyc.profile_photo_url} />
                    <DocThumb
                      label="Aadhaar front"
                      url={row.kyc.aadhaar_front_url || row.kyc.aadhaar_document_url}
                    />
                    <DocThumb label="Aadhaar back" url={row.kyc.aadhaar_back_url} />
                    <DocThumb label="PAN" url={row.kyc.pan_document_url} />
                    <DocThumb label="Bank proof" url={row.kyc.bank_document_url} />
                    <div className="col-span-full text-xs text-muted-foreground">
                      Aadhaar:{" "}
                      {row.kyc.aadhaar_attached
                        ? "attached (front + back)"
                        : "incomplete — need front and back"}
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
                <Input
                  placeholder="Reject reason (optional)"
                  value={reason[row.associate_id] ?? ""}
                  onChange={(e) => setReason((r) => ({ ...r, [row.associate_id]: e.target.value }))}
                  className="sm:max-w-xs"
                />
                <div className="flex gap-2">
                  <Button disabled={busy === row.associate_id} onClick={() => void approve(row.associate_id)}>
                    Approve
                  </Button>
                  <Button
                    variant="outline"
                    disabled={busy === row.associate_id}
                    onClick={() => void reject(row.associate_id)}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

