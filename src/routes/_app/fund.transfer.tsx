import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AssociatesAPI, WalletsAPI, resolveMediaUrl, unwrapList } from "@/lib/api";
import { useAuth } from "@/lib/rbac";

export const Route = createFileRoute("/_app/fund/transfer")({
  head: () => ({ meta: [{ title: "Fund Transfer — JoyClub Associate" }] }),
  component: FundTransfer,
});

type PackageOpt = { amount: string; label: string; amount_number: number };
type RecipientOpt = { associate_id: string; name: string; is_self: boolean; status?: string };
type TransferRequest = {
  id: string;
  requester_associate_id: string;
  requester_name: string;
  beneficiary_associate_id: string;
  beneficiary_name: string;
  amount: string;
  amount_label: string;
  payment_method: string;
  payment_method_label: string;
  utr: string;
  proof_url: string | null;
  note: string;
  status: string;
  rejection_reason: string;
  reviewed_by_email: string;
  created_at: string;
};

/** Always available even if packages API fails */
const FALLBACK_PACKAGES: PackageOpt[] = [
  { amount: "220000.00", label: "₹2.20 Lakh", amount_number: 220000 },
  { amount: "440000.00", label: "₹4.40 Lakh", amount_number: 440000 },
  { amount: "660000.00", label: "₹6.60 Lakh", amount_number: 660000 },
  { amount: "1100000.00", label: "₹11.00 Lakh", amount_number: 1100000 },
  { amount: "2200000.00", label: "₹22.00 Lakh", amount_number: 2200000 },
  { amount: "4400000.00", label: "₹44.00 Lakh", amount_number: 4400000 },
  { amount: "8800000.00", label: "₹88.00 Lakh", amount_number: 8800000 },
];

const FALLBACK_PAYMENT_METHODS: { code: string; label: string }[] = [
  { code: "upi", label: "UPI" },
  { code: "bank_transfer", label: "Bank Transfer" },
  { code: "cheque", label: "Cheque" },
  { code: "neft", label: "NEFT" },
  { code: "imps", label: "IMPS" },
  { code: "rtgs", label: "RTGS" },
];

function money(v: string | number | null | undefined) {
  return `₹ ${Number(v ?? 0).toLocaleString("en-IN")}`;
}

function recipientLabel(r: RecipientOpt) {
  const tag = r.is_self ? "Self" : "Under-leg";
  const st = r.status ? ` · ${r.status}` : "";
  return `${r.associate_id} — ${r.name} (${tag}${st})`;
}

function RecipientPicker({
  label,
  recipients,
  value,
  onChange,
  placeholder = "Search ID or name…",
}: {
  label: string;
  recipients: RecipientOpt[];
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const selected = recipients.find((r) => r.associate_id === value);
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return recipients.slice(0, 25);
    return recipients
      .filter(
        (r) =>
          r.associate_id.toLowerCase().includes(needle) ||
          r.name.toLowerCase().includes(needle),
      )
      .slice(0, 25);
  }, [recipients, q]);

  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {selected ? (
        <div className="flex items-center justify-between rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm">
          <span className="font-medium">{recipientLabel(selected)}</span>
          <button type="button" className="text-xs underline" onClick={() => onChange("")}>
            Change
          </button>
        </div>
      ) : (
        <>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder} />
          <div className="max-h-48 overflow-y-auto rounded-md border border-input bg-background">
            {filtered.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted-foreground">No match. Type a full ID or pick from the list.</p>
            ) : (
              filtered.map((r) => (
                <button
                  key={r.associate_id}
                  type="button"
                  className="block w-full border-b border-border px-3 py-2 text-left text-sm last:border-0 hover:bg-muted"
                  onClick={() => {
                    onChange(r.associate_id);
                    setQ("");
                  }}
                >
                  {recipientLabel(r)}
                </button>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

function proofHref(url: string | null | undefined) {
  return resolveMediaUrl(url);
}

function ProofLink({ url }: { url: string | null | undefined }) {
  const href = proofHref(url);
  if (!href) return <span className="text-muted-foreground">—</span>;
  const isPdf = /\.pdf(\?|$)/i.test(href);
  return (
    <a href={href} target="_blank" rel="noreferrer" className="text-xs underline">
      {isPdf ? "Open PDF" : "View proof"}
    </a>
  );
}

function statusClass(status: string) {
  if (status === "approved") return "text-emerald-700";
  if (status === "rejected") return "text-red-700";
  return "text-amber-700";
}

function FundTransfer() {
  const { session } = useAuth();
  const isStaff = !!(session?.isStaff || session?.isSuperuser);
  const myId = session?.associateId || "";
  const myName = session?.name || myId;

  const [packages, setPackages] = useState<PackageOpt[]>(FALLBACK_PACKAGES);
  const [paymentMethods, setPaymentMethods] = useState(FALLBACK_PAYMENT_METHODS);
  const [recipients, setRecipients] = useState<RecipientOpt[]>([]);
  const [associateId, setAssociateId] = useState("");
  const [fromAssociateId, setFromAssociateId] = useState("");
  const [companyMint, setCompanyMint] = useState(false);
  const [mainBalance, setMainBalance] = useState<string | null>(null);
  const [amount, setAmount] = useState(FALLBACK_PACKAGES[0].amount);
  const [paymentMethod, setPaymentMethod] = useState(FALLBACK_PAYMENT_METHODS[0].code);
  const [walletType, setWalletType] = useState("main");
  const [narration, setNarration] = useState("");
  const [applyBusiness, setApplyBusiness] = useState(true);
  const [loading, setLoading] = useState(false);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [requests, setRequests] = useState<TransferRequest[]>([]);
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>({});
  const [actingId, setActingId] = useState<string | null>(null);
  const [utr, setUtr] = useState("");
  const [proof, setProof] = useState<File | null>(null);
  const [proofKey, setProofKey] = useState(0);
  const [approveTarget, setApproveTarget] = useState<TransferRequest | null>(null);
  const [approvePassword, setApprovePassword] = useState("");

  const loadRequests = useCallback(async () => {
    try {
      const data = await WalletsAPI.transferRequests({ page_size: 50 });
      setRequests(unwrapList(data) as TransferRequest[]);
    } catch {
      setRequests([]);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const buildFromAssociates = async (selfId: string, _selfName: string): Promise<RecipientOpt[]> => {
        if (!selfId) return [];
        try {
          const team = unwrapList(await AssociatesAPI.list({ page_size: 500, scope: "my" }));
          return team
            .map((row) => ({
              associate_id: String(row.associate_id ?? row.username ?? ""),
              name: String(row.name ?? row.associate_id ?? ""),
              is_self: false,
              status: String(row.status ?? ""),
            }))
            .filter((r) => r.associate_id && r.associate_id !== selfId);
        } catch {
          return [];
        }
      };

      try {
        const data = await WalletsAPI.packages();
        if (cancelled) return;
        if (data.main_balance != null) setMainBalance(String(data.main_balance));
        if (data.packages?.length) {
          setPackages(data.packages);
          setAmount((prev) => prev || data.packages[0].amount);
        }
        if (data.payment_methods?.length) {
          setPaymentMethods(data.payment_methods);
          setPaymentMethod((prev) => prev || data.payment_methods![0].code);
        }
        const selfId = data.associate_id || myId;
        let list = (data.recipients ?? []).filter((r) => !r.is_self && r.associate_id !== selfId);
        if (!isStaff && selfId && list.length === 0) {
          list = await buildFromAssociates(selfId, myName);
        }
        if (isStaff && !list.length) {
          try {
            const all = unwrapList(await AssociatesAPI.list({ page_size: 500 }));
            list = all
              .map((row) => ({
                associate_id: String(row.associate_id ?? row.username ?? ""),
                name: String(row.name ?? row.associate_id ?? ""),
                is_self: String(row.associate_id) === myId,
                status: String(row.status ?? ""),
              }))
              .filter((r) => r.associate_id);
          } catch {
            /* staff can still type ID */
          }
        }
        setRecipients(list);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to load packages");
        if (!isStaff && myId) {
          const list = await buildFromAssociates(myId, myName);
          if (!cancelled) {
            setRecipients(list);
          }
        }
      } finally {
        if (!cancelled) setLoadingMeta(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once on mount
  }, []);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!associateId.trim()) {
      toast.error("Select an associate");
      return;
    }
    if (!isStaff && myId && associateId.trim().toUpperCase() === myId.toUpperCase()) {
      toast.error("You cannot send funds to yourself");
      return;
    }
    if (!amount) {
      toast.error("Select a package amount");
      return;
    }
    if (!paymentMethod) {
      toast.error("Select a payment method");
      return;
    }
    if (!isStaff && mainBalance != null && Number(mainBalance) < Number(amount)) {
      toast.error("Not enough balance");
      return;
    }
    if (isStaff && !companyMint && !fromAssociateId.trim()) {
      toast.error("Select the associate to debit, or enable company mint");
      return;
    }
    if (!isStaff && utr.trim().length < 4) {
      toast.error("Enter the UTR / transaction ID");
      return;
    }
    if (!isStaff && !proof) {
      toast.error("Upload a payment screenshot, receipt, or PDF");
      return;
    }
    setLoading(true);
    try {
      if (isStaff) {
        await WalletsAPI.transfer({
          associate_id: associateId.trim(),
          from_associate_id: companyMint ? undefined : fromAssociateId.trim(),
          company_mint: companyMint,
          wallet_type: walletType,
          amount: Number(amount),
          narration: narration || "Admin fund transfer",
          apply_business: applyBusiness && walletType === "main",
          payment_method: paymentMethod,
        });
        toast.success(
          companyMint
            ? `Credited ${money(amount)} to ${associateId}`
            : `Moved ${money(amount)} from ${fromAssociateId} to ${associateId}`,
        );
      } else {
        await WalletsAPI.requestTransfer({
          associate_id: associateId.trim(),
          amount: Number(amount),
          payment_method: paymentMethod,
          note: narration,
          utr: utr.trim(),
          proof: proof!,
        });
        toast.success("Request sent to admin. Funds are credited only after admin approval.");
        setNarration("");
        setUtr("");
        setProof(null);
        setProofKey((k) => k + 1);
        await loadRequests();
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : isStaff ? "Transfer failed" : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function confirmApprove() {
    if (!approveTarget) return;
    if (!approvePassword.trim()) {
      toast.error("Enter your password to confirm this approval");
      return;
    }
    setActingId(approveTarget.id);
    try {
      await WalletsAPI.approveTransferRequest(approveTarget.id, true, approvePassword);
      toast.success("Request approved and funds credited");
      setApproveTarget(null);
      setApprovePassword("");
      await loadRequests();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setActingId(null);
    }
  }

  async function rejectRequest(id: string) {
    setActingId(id);
    try {
      await WalletsAPI.rejectTransferRequest(id, rejectReasons[id] || "");
      toast.success("Request rejected");
      await loadRequests();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setActingId(null);
    }
  }

  const packageOptions = packages.length ? packages : FALLBACK_PACKAGES;
  const selectedPkg = packageOptions.find((p) => p.amount === amount || p.amount_number === Number(amount));
  const pendingRequests = requests.filter((r) => r.status === "pending");
  const shownRequests = isStaff ? pendingRequests : requests;

  return (
    <div className="space-y-6">
      <PageHeader
        title={isStaff ? "Fund Transfer" : "Request Fund Transfer"}
        subtitle={
          isStaff
            ? "Debit one associate and credit another. Company mint is optional."
            : "Ask admin to move a package from your main wallet to an under-leg member. You cannot send to yourself."
        }
      />

      {loadingMeta ? (
        <p className="text-sm text-muted-foreground">Loading packages…</p>
      ) : (
        <form
          onSubmit={submit}
          className="w-full max-w-lg space-y-4 rounded-2xl border border-border bg-card/90 p-4 shadow-sm backdrop-blur sm:p-6"
        >
          {!isStaff && mainBalance != null ? (
            <p className={`text-sm ${Number(mainBalance) < Number(amount || 0) ? "font-semibold text-red-700" : "text-muted-foreground"}`}>
              Main wallet: {money(mainBalance)}
              {Number(mainBalance) < Number(amount || 0) ? " — not enough balance" : ""}
            </p>
          ) : null}

          {isStaff ? (
            <>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={companyMint}
                  onChange={(e) => setCompanyMint(e.target.checked)}
                />
                Company mint (credit without debiting anyone)
              </label>
              {companyMint ? null : recipients.length > 0 ? (
                <RecipientPicker
                  label="From associate (wallet will reduce)"
                  recipients={recipients}
                  value={fromAssociateId}
                  onChange={setFromAssociateId}
                />
              ) : (
                <div className="space-y-1.5">
                  <Label>From associate (wallet will reduce)</Label>
                  <Input
                    value={fromAssociateId}
                    onChange={(e) => setFromAssociateId(e.target.value.toUpperCase())}
                    placeholder="JOY00000001"
                    required={!companyMint}
                  />
                </div>
              )}
            </>
          ) : null}

          {recipients.length > 0 ? (
            <RecipientPicker
              label={isStaff ? "To associate (wallet will increase)" : "Under-leg associate"}
              recipients={recipients}
              value={associateId}
              onChange={setAssociateId}
            />
          ) : (
            <div className="space-y-1.5">
              <Label>{isStaff ? "To associate" : "Under-leg associate"}</Label>
              <Input
                value={associateId}
                onChange={(e) => setAssociateId(e.target.value.toUpperCase())}
                placeholder={myId || "JOY00000001"}
                required
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label>Package amount</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={
                isStaff && !packageOptions.some((p) => p.amount === amount)
                  ? "__custom__"
                  : amount
              }
              onChange={(e) => {
                if (e.target.value === "__custom__") {
                  setAmount("");
                  return;
                }
                setAmount(e.target.value);
              }}
              required={!isStaff}
            >
              {packageOptions.map((p) => (
                <option key={p.amount} value={p.amount}>
                  {p.label} — {money(p.amount)}
                </option>
              ))}
              {isStaff ? <option value="__custom__">Custom amount…</option> : null}
            </select>
            {selectedPkg ? (
              <p className="text-xs text-muted-foreground">Selected: {selectedPkg.label}</p>
            ) : null}
            {isStaff && !packageOptions.some((p) => p.amount === amount) ? (
              <Input
                type="number"
                min={1}
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="Enter custom amount"
                required
              />
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label>Payment method</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              required
            >
              {(paymentMethods.length ? paymentMethods : FALLBACK_PAYMENT_METHODS).map((m) => (
                <option key={m.code} value={m.code}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {!isStaff ? (
            <>
              <div className="space-y-1.5">
                <Label>UTR / transaction ID</Label>
                <Input
                  value={utr}
                  onChange={(e) => setUtr(e.target.value.toUpperCase())}
                  placeholder="Bank / UPI UTR"
                  required
                  minLength={4}
                  maxLength={64}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Payment proof (image or PDF)</Label>
                <Input
                  key={proofKey}
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,.pdf,.heic,image/*"
                  onChange={(e) => setProof(e.target.files?.[0] ?? null)}
                  required
                />
                {proof ? (
                  <p className="text-xs text-muted-foreground">{proof.name}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">JPG, PNG, WEBP, or PDF · max 8 MB</p>
                )}
              </div>
            </>
          ) : null}

          {isStaff ? (
            <>
              <div className="space-y-1.5">
                <Label>Wallet</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={walletType}
                  onChange={(e) => setWalletType(e.target.value)}
                >
                  {["main", "personal", "income", "reward", "roi", "withdraw"].map((w) => (
                    <option key={w} value={w}>
                      {w}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={applyBusiness}
                  disabled={walletType !== "main"}
                  onChange={(e) => setApplyBusiness(e.target.checked)}
                />
                Apply business &amp; level income (main wallet + fixed package only)
              </label>
            </>
          ) : null}

          <div className="space-y-1.5">
            <Label>{isStaff ? "Narration" : "Note to admin"}</Label>
            <Input
              value={narration}
              onChange={(e) => setNarration(e.target.value)}
              placeholder={isStaff ? "Admin credit" : "Optional note"}
            />
          </div>

          <Button
            type="submit"
            disabled={
              loading ||
              (!isStaff && mainBalance != null && Number(mainBalance) < Number(amount || 0))
            }
          >
            {loading
              ? isStaff
                ? "Transferring…"
                : "Sending request…"
              : isStaff
                ? "Transfer funds"
                : "Send request to admin"}
          </Button>
        </form>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">
          {isStaff ? "Pending associate requests" : "My requests"}
        </h2>
        {shownRequests.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {isStaff ? "No pending requests." : "You have not sent a request yet."}
          </p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-border">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  {isStaff ? <th className="px-3 py-2">From</th> : null}
                  <th className="px-3 py-2">Credit to</th>
                  <th className="px-3 py-2">Amount</th>
                  <th className="px-3 py-2">Method</th>
                  <th className="px-3 py-2">UTR</th>
                  <th className="px-3 py-2">Proof</th>
                  <th className="px-3 py-2">Status</th>
                  {isStaff ? <th className="px-3 py-2">Action</th> : <th className="px-3 py-2">Note</th>}
                </tr>
              </thead>
              <tbody>
                {shownRequests.map((row) => (
                  <tr key={row.id} className="border-t border-border">
                    {isStaff ? (
                      <td className="px-3 py-2">
                        {row.requester_associate_id}
                        <div className="text-xs text-muted-foreground">{row.requester_name}</div>
                      </td>
                    ) : null}
                    <td className="px-3 py-2">
                      {row.beneficiary_associate_id}
                      <div className="text-xs text-muted-foreground">{row.beneficiary_name}</div>
                    </td>
                    <td className="px-3 py-2">{row.amount_label || money(row.amount)}</td>
                    <td className="px-3 py-2">{row.payment_method_label}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.utr || "—"}</td>
                    <td className="px-3 py-2">
                      <ProofLink url={row.proof_url} />
                    </td>
                    <td className={`px-3 py-2 capitalize ${statusClass(row.status)}`}>
                      {row.status}
                      {row.status === "rejected" && row.rejection_reason ? (
                        <div className="text-xs text-muted-foreground">{row.rejection_reason}</div>
                      ) : null}
                    </td>
                    {isStaff ? (
                      <td className="px-3 py-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                          <Button
                            size="sm"
                            disabled={actingId === row.id}
                            onClick={() => {
                              setApprovePassword("");
                              setApproveTarget(row);
                            }}
                          >
                            Approve
                          </Button>
                          <Input
                            value={rejectReasons[row.id] ?? ""}
                            onChange={(e) =>
                              setRejectReasons((prev) => ({ ...prev, [row.id]: e.target.value }))
                            }
                            placeholder="Reject reason"
                            className="h-8 w-40"
                          />
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={actingId === row.id}
                            onClick={() => void rejectRequest(row.id)}
                          >
                            Reject
                          </Button>
                        </div>
                      </td>
                    ) : (
                      <td className="px-3 py-2 text-muted-foreground">{row.note || "—"}</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Dialog
        open={!!approveTarget}
        onOpenChange={(open) => {
          if (!open) {
            setApproveTarget(null);
            setApprovePassword("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm approval</DialogTitle>
            <DialogDescription>
              Enter your admin password to credit this request. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {approveTarget ? (
            <div className="space-y-2 rounded-md border border-border bg-muted/40 p-3 text-sm">
              <p>
                {approveTarget.requester_associate_id} → {approveTarget.beneficiary_associate_id}
              </p>
              <p>{approveTarget.amount_label || money(approveTarget.amount)}</p>
              <p>
                UTR: <span className="font-mono">{approveTarget.utr || "—"}</span>
              </p>
              <ProofLink url={approveTarget.proof_url} />
            </div>
          ) : null}
          <div className="space-y-1.5">
            <Label htmlFor="approve-password">Confirm password</Label>
            <Input
              id="approve-password"
              type="password"
              autoComplete="current-password"
              value={approvePassword}
              onChange={(e) => setApprovePassword(e.target.value)}
              placeholder="Your login password"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void confirmApprove();
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setApproveTarget(null);
                setApprovePassword("");
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={actingId === approveTarget?.id}
              onClick={() => void confirmApprove()}
            >
              {actingId === approveTarget?.id ? "Approving…" : "Approve & credit"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
