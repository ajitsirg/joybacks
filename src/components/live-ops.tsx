import { useCallback, useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Check, Loader2, X } from "lucide-react";
import { DataTable, StatusBadge, type Column } from "@/components/data-table";
import { DocThumb } from "@/components/doc-thumb";
import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OpsAPI, unwrapList } from "@/lib/api";

type Row = Record<string, unknown>;

function money(v: unknown) {
  const n = Number(v ?? 0);
  return `₹ ${n.toLocaleString("en-IN")}`;
}

function when(v: unknown) {
  if (!v) return "—";
  return new Date(String(v)).toLocaleString("en-IN");
}

export function LiveDepositTable({
  title,
  subtitle,
  status,
  showActions,
}: {
  title: string;
  subtitle: string;
  status: string;
  showActions?: boolean;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await OpsAPI.deposits({ status, page_size: 200 });
      setRows(unwrapList(data));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load deposits");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  const cols: Column<Row>[] = [
    { key: "associate_id", header: "Associate", cell: (r) => <span className="font-medium">{String(r.associate_id)}</span> },
    { key: "username", header: "User", cell: (r) => String(r.username ?? "") },
    { key: "amount", header: "Amount", cell: (r) => <span className="tabular-nums">{money(r.amount)}</span> },
    { key: "wallet_type", header: "Wallet", cell: (r) => String(r.wallet_type ?? "") },
    { key: "transaction_id", header: "Trnx ID", cell: (r) => <span className="font-mono text-xs">{String(r.transaction_id || "—")}</span> },
    { key: "created_at", header: "Applied", cell: (r) => when(r.created_at) },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={String(r.status)} /> },
  ];

  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined} />
      <DataTable
        data={rows}
        columns={cols}
        searchable={(r) => `${r.associate_id} ${r.username} ${r.transaction_id}`}
        rowActions={
          showActions
            ? (r) => (
                <div className="inline-flex w-full flex-wrap items-center justify-end gap-1">
                  <Button
                    size="sm"
                    className="h-8 flex-1 gap-1 sm:flex-none"
                    onClick={async () => {
                      try {
                        await OpsAPI.approveDeposit(String(r.id));
                        toast.success("Deposit approved — wallets & commissions updated");
                        void load();
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Approve failed");
                      }
                    }}
                  >
                    <Check className="h-3.5 w-3.5" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 flex-1 gap-1 text-[color:var(--danger)] sm:flex-none"
                    onClick={async () => {
                      try {
                        await OpsAPI.rejectDeposit(String(r.id), "Rejected by admin");
                        toast.message("Deposit rejected");
                        void load();
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Reject failed");
                      }
                    }}
                  >
                    <X className="h-3.5 w-3.5" /> Reject
                  </Button>
                </div>
              )
            : undefined
        }
      />
    </div>
  );
}

export function LiveWithdrawTable({
  title,
  subtitle,
  status,
  showActions,
}: {
  title: string;
  subtitle: string;
  status: string;
  showActions?: boolean;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await OpsAPI.withdrawals({ status, page_size: 200 });
      setRows(unwrapList(data));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load withdrawals");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  const cols: Column<Row>[] = [
    { key: "associate_id", header: "Associate", cell: (r) => <span className="font-medium">{String(r.associate_id)}</span> },
    { key: "username", header: "User", cell: (r) => String(r.username ?? "") },
    {
      key: "amount",
      header: "Amount",
      cell: (r) => (
        <span className="tabular-nums">
          {money(r.amount)}
          {r.requires_maker_checker ? (
            <span className="ml-1.5 rounded bg-[color:var(--warn-tint)] px-1.5 py-0.5 text-[10px] font-medium text-[color:var(--warn-text)]">
              Maker-Checker
            </span>
          ) : null}
        </span>
      ),
    },
    { key: "net_amount", header: "Net", cell: (r) => money(r.net_amount) },
    { key: "bank_detail", header: "Bank", cell: (r) => String(r.bank_detail || "—") },
    { key: "created_at", header: "Requested", cell: (r) => when(r.created_at) },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={String(r.status)} /> },
  ];

  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined} />
      <DataTable
        data={rows}
        columns={cols}
        searchable={(r) => `${r.associate_id} ${r.username}`}
        rowActions={
          showActions
            ? (r) => (
                <div className="inline-flex items-center gap-1">
                  <Button
                    size="sm"
                    className="h-8 gap-1"
                    onClick={async () => {
                      try {
                        await OpsAPI.approveWithdrawal(String(r.id));
                        toast.success("Withdrawal approved");
                        void load();
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Approve failed");
                      }
                    }}
                  >
                    <Check className="h-3.5 w-3.5" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 gap-1 text-[color:var(--danger)]"
                    onClick={async () => {
                      try {
                        await OpsAPI.rejectWithdrawal(String(r.id), "Rejected by admin");
                        toast.message("Withdrawal rejected & refunded");
                        void load();
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Reject failed");
                      }
                    }}
                  >
                    <X className="h-3.5 w-3.5" /> Reject
                  </Button>
                </div>
              )
            : undefined
        }
      />
    </div>
  );
}

type KycRow = {
  id: string;
  associate_id?: string;
  associate_name?: string;
  associate_status?: string;
  kyc_verified?: boolean;
  full_name?: string;
  pan?: string;
  aadhaar?: string;
  bank_name?: string;
  account_number?: string;
  ifsc?: string;
  upi_id?: string;
  status?: string;
  rejection_reason?: string;
  aadhaar_attached?: boolean;
  profile_photo_url?: string | null;
  aadhaar_document_url?: string | null;
  aadhaar_front_url?: string | null;
  aadhaar_back_url?: string | null;
  pan_document_url?: string | null;
  bank_document_url?: string | null;
  created_at?: string;
};

export function LiveKycTable({
  title,
  subtitle,
  status,
  showActions,
}: {
  title: string;
  subtitle: string;
  status: string;
  showActions?: boolean;
}) {
  const [rows, setRows] = useState<KycRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await OpsAPI.kyc({ status, page_size: 200 });
      setRows(unwrapList(data) as KycRow[]);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load KYC");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = rows.filter((r) => {
    if (!q.trim()) return true;
    const hay = `${r.associate_id} ${r.associate_name} ${r.full_name} ${r.pan} ${r.aadhaar} ${r.upi_id}`.toLowerCase();
    return hay.includes(q.trim().toLowerCase());
  });

  async function approve(id: string) {
    setBusy(id);
    try {
      await OpsAPI.approveKyc(id);
      toast.success("KYC approved");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(null);
    }
  }

  async function reject(id: string) {
    const reason = (reasons[id] || "").trim() || "Documents mismatch / incomplete";
    setBusy(id);
    try {
      await OpsAPI.rejectKyc(id, reason);
      toast.message("KYC rejected");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search associate / name / PAN / Aadhaar"
          className="sm:max-w-md"
        />
        <p className="text-xs text-muted-foreground">{filtered.length} record{filtered.length === 1 ? "" : "s"}</p>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading KYC…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-sm text-muted-foreground">
          No KYC submissions in this queue.
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((row) => {
            const id = String(row.id);
            const aid = String(row.associate_id || "");
            return (
              <div key={id} className="rounded-2xl border border-border bg-card p-4 shadow-sm md:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-lg font-semibold text-[color:var(--brand-dark)]">
                      {row.full_name || row.associate_name || "—"}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {aid}
                      {row.associate_status ? ` · account ${row.associate_status}` : ""}
                      {row.kyc_verified ? " · verified" : " · not verified"}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={String(row.status || status)} />
                    <span
                      className={
                        row.aadhaar_attached
                          ? "rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-medium text-emerald-800"
                          : "rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-medium text-amber-900"
                      }
                    >
                      Aadhaar {row.aadhaar_attached ? "complete" : "incomplete"}
                    </span>
                    {aid ? (
                      <Button asChild size="sm" variant="outline" className="h-8">
                        <Link to="/users/$associateId" params={{ associateId: aid }}>
                          Open profile
                        </Link>
                      </Button>
                    ) : null}
                  </div>
                </div>

                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <dl className="grid gap-2 text-sm sm:grid-cols-2">
                    <div className="rounded-lg bg-muted/40 px-3 py-2">
                      <dt className="text-[11px] uppercase text-muted-foreground">PAN</dt>
                      <dd className="font-mono font-medium">{row.pan || "—"}</dd>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-3 py-2">
                      <dt className="text-[11px] uppercase text-muted-foreground">Aadhaar</dt>
                      <dd className="font-mono font-medium">{row.aadhaar || "—"}</dd>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-3 py-2">
                      <dt className="text-[11px] uppercase text-muted-foreground">Bank</dt>
                      <dd className="font-medium">{row.bank_name || "—"}</dd>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-3 py-2">
                      <dt className="text-[11px] uppercase text-muted-foreground">Account</dt>
                      <dd className="font-mono font-medium">{row.account_number || "—"}</dd>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-3 py-2">
                      <dt className="text-[11px] uppercase text-muted-foreground">IFSC</dt>
                      <dd className="font-mono font-medium">{row.ifsc || "—"}</dd>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-3 py-2">
                      <dt className="text-[11px] uppercase text-muted-foreground">UPI</dt>
                      <dd className="font-medium">{row.upi_id || "—"}</dd>
                    </div>
                  </dl>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    <DocThumb label="Profile" url={row.profile_photo_url} />
                    <DocThumb
                      label="Aadhaar front"
                      url={row.aadhaar_front_url || row.aadhaar_document_url}
                    />
                    <DocThumb label="Aadhaar back" url={row.aadhaar_back_url} />
                    <DocThumb label="PAN" url={row.pan_document_url} />
                    <DocThumb label="Bank proof" url={row.bank_document_url} />
                  </div>
                </div>

                {row.rejection_reason ? (
                  <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
                    Reason: {row.rejection_reason}
                  </p>
                ) : null}

                {showActions ? (
                  <div className="mt-4 flex flex-col gap-2 border-t border-border pt-4 sm:flex-row sm:items-center">
                    <Input
                      placeholder="Reject reason"
                      value={reasons[id] ?? ""}
                      onChange={(e) => setReasons((prev) => ({ ...prev, [id]: e.target.value }))}
                      className="sm:max-w-sm"
                    />
                    <div className="flex gap-2">
                      <Button
                        className="gap-1"
                        disabled={busy === id}
                        onClick={() => void approve(id)}
                      >
                        {busy === id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                        Approve
                      </Button>
                      <Button
                        variant="outline"
                        className="gap-1 text-[color:var(--danger)]"
                        disabled={busy === id}
                        onClick={() => void reject(id)}
                      >
                        <X className="h-3.5 w-3.5" /> Reject
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
