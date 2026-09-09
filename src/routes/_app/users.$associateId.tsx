import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeft, Loader2, Pencil, Save, X } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { AttachmentGallery } from "@/components/doc-thumb";
import { DataTable, StatusBadge, type Column } from "@/components/data-table";
import { LevelBadge } from "@/components/earning-level-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AssociatesAPI,
  CommissionsAPI,
  OpsAPI,
  WalletsAPI,
  unwrapList,
} from "@/lib/api";
import { useAuth } from "@/lib/rbac";

export const Route = createFileRoute("/_app/users/$associateId")({
  ssr: false,
  head: ({ params }) => ({
    meta: [{ title: `${params.associateId} — JoyClub Associate` }],
  }),
  component: AssociateProfilePage,
});

type Row = Record<string, unknown>;

function money(v: unknown) {
  return `₹ ${Number(v ?? 0).toLocaleString("en-IN")}`;
}

type EditForm = {
  first_name: string;
  last_name: string;
  email: string;
  mobile: string;
  city: string;
  state: string;
  country: string;
  full_name: string;
  pan: string;
  aadhaar: string;
  bank_name: string;
  account_number: string;
  ifsc: string;
  upi_id: string;
  status: string;
  can_view_admin_history: boolean;
  can_view_reward_achievers: boolean;
  can_fund_transfer: boolean;
  password: string;
  confirm_password: string;
};

function formFromProfile(p: Row): EditForm {
  const kyc = (p.kyc as Row | null | undefined) ?? {};
  return {
    first_name: String(p.first_name ?? ""),
    last_name: String(p.last_name ?? ""),
    email: String(p.email ?? ""),
    mobile: String(p.mobile ?? ""),
    city: String(p.city ?? ""),
    state: String(p.state ?? ""),
    country: String(p.country ?? "India"),
    full_name: String(kyc.full_name ?? p.name ?? ""),
    pan: String(kyc.pan ?? ""),
    aadhaar: String(kyc.aadhaar ?? ""),
    bank_name: String(kyc.bank_name ?? ""),
    account_number: String(kyc.account_number ?? ""),
    ifsc: String(kyc.ifsc ?? ""),
    upi_id: String(kyc.upi_id ?? ""),
    status: String(p.status ?? "active"),
    can_view_admin_history: !!p.can_view_admin_history,
    can_view_reward_achievers: !!p.can_view_reward_achievers,
    can_fund_transfer: p.can_fund_transfer !== false,
    password: "",
    confirm_password: "",
  };
}

function AssociateProfilePage() {
  const { associateId } = Route.useParams();
  const id = associateId.toUpperCase();
  const navigate = useNavigate();
  const { session } = useAuth();
  const isStaff = !!(session?.isStaff);

  const [profile, setProfile] = useState<Row | null>(null);
  const [wallets, setWallets] = useState<Row[]>([]);
  const [ledger, setLedger] = useState<Row[]>([]);
  const [income, setIncome] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"ledger" | "income">("ledger");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<EditForm | null>(null);
  const [files, setFiles] = useState<{
    profile_photo?: File;
    aadhaar_document?: File;
    aadhaar_back?: File;
    pan_document?: File;
    bank_document?: File;
  }>({});
  const [kycBusy, setKycBusy] = useState(false);
  const [kycRejectReason, setKycRejectReason] = useState("");

  async function loadAll() {
    setLoading(true);
    try {
      const [p, w, l, c] = await Promise.all([
        AssociatesAPI.get(id),
        WalletsAPI.list({ "associate__associate_id": id, page_size: 50 }),
        WalletsAPI.ledger({ "wallet__associate__associate_id": id, page_size: 200 }),
        CommissionsAPI.entries({ "beneficiary__associate_id": id, page_size: 200 }),
      ]);
      setProfile(p);
      setForm(formFromProfile(p));
      setWallets(unwrapList(w as never).map((r, i) => ({ ...r, id: (r.id as string) ?? `w-${i}` })));
      setLedger(unwrapList(l).map((r, i) => ({ ...r, id: (r.id as string) ?? `l-${i}` })));
      setIncome(unwrapList(c).map((r, i) => ({ ...r, id: (r.id as string) ?? `c-${i}` })));
    } catch (e) {
      setProfile(null);
      toast.error(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAll();
    setEditing(false);
    setFiles({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const canEdit = !!profile?.can_edit;

  async function save() {
    if (!form) return;
    setSaving(true);
    try {
      const fd = new FormData();
      const textFields: (keyof EditForm)[] = [
        "first_name",
        "last_name",
        "email",
        "mobile",
        "city",
        "state",
        "country",
        "full_name",
        "pan",
        "aadhaar",
        "bank_name",
        "account_number",
        "ifsc",
        "upi_id",
      ];
      for (const key of textFields) {
        fd.append(key, String(form[key] ?? ""));
      }
      if (form.password || form.confirm_password) {
        if (!form.password || form.password.length < 6) {
          toast.error("Password must be at least 6 characters");
          setSaving(false);
          return;
        }
        if (form.password !== form.confirm_password) {
          toast.error("Password and confirm password do not match");
          setSaving(false);
          return;
        }
        fd.append("password", form.password);
        fd.append("confirm_password", form.confirm_password);
      }
      if (isStaff) {
        fd.append("status", form.status);
        fd.append("can_view_admin_history", form.can_view_admin_history ? "true" : "false");
        fd.append("can_view_reward_achievers", form.can_view_reward_achievers ? "true" : "false");
      }
      if (files.profile_photo) fd.append("profile_photo", files.profile_photo);
      if (files.aadhaar_document) fd.append("aadhaar_document", files.aadhaar_document);
      if (files.aadhaar_back) fd.append("aadhaar_back", files.aadhaar_back);
      if (files.pan_document) fd.append("pan_document", files.pan_document);
      if (files.bank_document) fd.append("bank_document", files.bank_document);

      const updated = await AssociatesAPI.update(id, fd);
      const newId = String(updated.associate_id ?? updated.username ?? id).toUpperCase();
      setFiles({});
      setEditing(false);
      if (newId !== id) {
        toast.success(`Details updated. Username is now ${newId}`);
        void navigate({ to: "/users/$associateId", params: { associateId: newId } });
        return;
      }
      setProfile(updated);
      setForm({ ...formFromProfile(updated), password: "", confirm_password: "" });
      toast.success(form.password ? "Details and password updated" : "Details updated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  const ledgerCols: Column<Row>[] = [
    { key: "wallet_type", header: "Wallet", cell: (r) => String(r.wallet_type ?? "").toUpperCase() },
    { key: "entry_type", header: "Type", cell: (r) => <span className="capitalize">{String(r.entry_type)}</span> },
    {
      key: "amount",
      header: "Amount",
      cell: (r) => <span className="tabular-nums">{money(r.amount)}</span>,
      sortValue: (r) => Number(r.amount ?? 0),
    },
    { key: "reference", header: "Reference", cell: (r) => String(r.reference || "—") },
    { key: "narration", header: "Narration", cell: (r) => String(r.narration || "—") },
    {
      key: "created_at",
      header: "Date",
      cell: (r) => (r.created_at ? new Date(String(r.created_at)).toLocaleString("en-IN") : "—"),
      sortValue: (r) => String(r.created_at ?? ""),
    },
  ];

  const incomeCols: Column<Row>[] = [
    { key: "level", header: "Level", cell: (r) => String(r.level ?? "—") },
    { key: "wallet_type", header: "Wallet", cell: (r) => String(r.wallet_type ?? "").toUpperCase() },
    {
      key: "amount",
      header: "Amount",
      cell: (r) => <span className="tabular-nums">{money(r.amount)}</span>,
      sortValue: (r) => Number(r.amount ?? 0),
    },
    { key: "source_id", header: "From", cell: (r) => String(r.source_id || "—") },
    { key: "narration", header: "Narration", cell: (r) => String(r.narration || "—") },
    {
      key: "created_at",
      header: "Date",
      cell: (r) => (r.created_at ? new Date(String(r.created_at)).toLocaleString("en-IN") : "—"),
      sortValue: (r) => String(r.created_at ?? ""),
    },
  ];

  const walletTotal = wallets.reduce((s, w) => s + Number(w.balance ?? 0), 0);
  const set = (key: keyof EditForm, value: string | boolean) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  return (
    <div>
      <PageHeader
        title={profile ? String(profile.name || id) : id}
        subtitle={loading ? "Loading profile…" : "Associate profile & history"}
        actions={
          <div className="flex items-center gap-2">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {canEdit && !editing ? (
              <Button
                size="sm"
                className="gap-1.5 bg-[color:var(--brand-dark)]"
                onClick={() => {
                  if (profile) setForm(formFromProfile(profile));
                  setEditing(true);
                }}
              >
                <Pencil className="h-4 w-4" /> Update details
              </Button>
            ) : null}
            {editing ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  disabled={saving}
                  onClick={() => {
                    setEditing(false);
                    setFiles({});
                    if (profile) setForm(formFromProfile(profile));
                  }}
                >
                  <X className="h-4 w-4" /> Cancel
                </Button>
                <Button
                  size="sm"
                  className="gap-1.5 bg-[color:var(--brand-dark)]"
                  disabled={saving}
                  onClick={() => void save()}
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  Save
                </Button>
              </>
            ) : null}
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link to="/users/all">
                <ArrowLeft className="h-4 w-4" /> Back
              </Link>
            </Button>
          </div>
        }
      />

      {!loading && !profile ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Profile details are private. Only the associate or an admin can open this page.
        </div>
      ) : (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <InfoCard label="Username" value={String(profile?.username ?? profile?.associate_id ?? id)} />
            <InfoCard label="Status" value={<StatusBadge status={String(profile?.status ?? "pending")} />} />
            <InfoCard
              label="Reward level"
              value={
                <LevelBadge
                  kind="reward"
                  level={profile?.reward_level ?? profile?.earning_level}
                  name={profile?.reward_level_name ?? profile?.earning_level_name}
                />
              }
            />
            <InfoCard
              label="Performance"
              value={
                <LevelBadge
                  kind="performance"
                  level={profile?.performance_level}
                  name={profile?.performance_level_name}
                />
              }
            />
            <InfoCard label="Mobile" value={String(profile?.mobile || "—")} />
            <InfoCard label="Wallet total" value={money(walletTotal)} />
          </div>

          {editing && form ? (
            <section className="mb-4 rounded-2xl border border-border bg-card p-4 sm:p-5">
              <h2 className="mb-1 text-sm font-semibold text-[color:var(--brand-dark)]">Update all details</h2>
              <p className="mb-4 text-xs text-muted-foreground">
                Editable by the associate, their team lead, admin, or superadmin. Associate ID stays fixed.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="First name">
                  <Input value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
                </Field>
                <Field label="Last name">
                  <Input value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
                </Field>
                <Field label="Email">
                  <Input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />
                </Field>
                <Field label="Mobile (username becomes JOY + mobile)">
                  <Input value={form.mobile} onChange={(e) => set("mobile", e.target.value)} />
                </Field>
                <Field label="City">
                  <Input value={form.city} onChange={(e) => set("city", e.target.value)} />
                </Field>
                <Field label="State">
                  <Input value={form.state} onChange={(e) => set("state", e.target.value)} />
                </Field>
                <Field label="Country">
                  <Input value={form.country} onChange={(e) => set("country", e.target.value)} />
                </Field>
                <Field label="KYC full name">
                  <Input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} />
                </Field>
                <Field label="PAN">
                  <Input value={form.pan} onChange={(e) => set("pan", e.target.value.toUpperCase())} />
                </Field>
                <Field label="Aadhaar">
                  <Input value={form.aadhaar} onChange={(e) => set("aadhaar", e.target.value)} />
                </Field>
                <Field label="Bank name">
                  <Input value={form.bank_name} onChange={(e) => set("bank_name", e.target.value)} />
                </Field>
                <Field label="Account number">
                  <Input value={form.account_number} onChange={(e) => set("account_number", e.target.value)} />
                </Field>
                <Field label="IFSC">
                  <Input value={form.ifsc} onChange={(e) => set("ifsc", e.target.value.toUpperCase())} />
                </Field>
                <Field label="UPI ID">
                  <Input value={form.upi_id} onChange={(e) => set("upi_id", e.target.value)} />
                </Field>
              </div>

              <div className="mt-4 grid gap-3 border-t border-border pt-4 sm:grid-cols-2">
                <Field label="New password">
                  <Input
                    type="password"
                    autoComplete="new-password"
                    value={form.password}
                    onChange={(e) => set("password", e.target.value)}
                    placeholder="Leave blank to keep current"
                  />
                </Field>
                <Field label="Confirm password">
                  <Input
                    type="password"
                    autoComplete="new-password"
                    value={form.confirm_password}
                    onChange={(e) => set("confirm_password", e.target.value)}
                    placeholder="Re-enter new password"
                  />
                </Field>
                {isStaff && profile?.login_password ? (
                  <p className="sm:col-span-2 text-xs text-muted-foreground">
                    Admin-visible password on file:{" "}
                    <span className="font-mono font-semibold text-foreground">
                      {String(profile.login_password)}
                    </span>
                  </p>
                ) : null}
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {(
                  [
                    ["profile_photo", "Profile photo (square)"],
                    ["aadhaar_document", "Aadhaar front"],
                    ["aadhaar_back", "Aadhaar back"],
                    ["pan_document", "PAN document"],
                    ["bank_document", "Bank proof"],
                  ] as const
                ).map(([key, label]) => (
                  <Field key={key} label={label}>
                    <Input
                      type="file"
                      accept="image/*,.pdf"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        setFiles((prev) => ({ ...prev, [key]: f }));
                      }}
                    />
                  </Field>
                ))}
              </div>

              {isStaff ? (
                <div className="mt-4 grid gap-3 border-t border-border pt-4 sm:grid-cols-2">
                  <Field label="Status (staff)">
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                      value={form.status}
                      onChange={(e) => set("status", e.target.value)}
                    >
                      {["pending", "active", "inactive", "blocked", "rejected"].map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <div className="flex flex-col justify-end gap-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.can_view_admin_history}
                        onChange={(e) => set("can_view_admin_history", e.target.checked)}
                      />
                      Can view admin history
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.can_view_reward_achievers}
                        onChange={(e) => set("can_view_reward_achievers", e.target.checked)}
                      />
                      Can view reward achievers
                    </label>
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}

          <div className="mb-4">
            <AttachmentGallery
              title="Uploaded attachments"
              kyc={(profile?.kyc as Record<string, unknown> | null | undefined) as never}
            />
            {isStaff && String((profile?.kyc as Row | null | undefined)?.status || "") === "pending" ? (
              <div className="mt-3 flex flex-col gap-2 rounded-2xl border border-amber-200 bg-amber-50/60 p-3 sm:flex-row sm:items-center">
                <Input
                  placeholder="Reject reason"
                  value={kycRejectReason}
                  onChange={(e) => setKycRejectReason(e.target.value)}
                  className="sm:max-w-sm"
                />
                <div className="flex gap-2">
                  <Button
                    disabled={kycBusy}
                    onClick={async () => {
                      const kycId = String((profile?.kyc as Row | null | undefined)?.id || "");
                      if (!kycId) {
                        toast.error("No KYC submission id");
                        return;
                      }
                      setKycBusy(true);
                      try {
                        await OpsAPI.approveKyc(kycId);
                        toast.success("KYC approved");
                        await loadAll();
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Approve failed");
                      } finally {
                        setKycBusy(false);
                      }
                    }}
                  >
                    Approve KYC
                  </Button>
                  <Button
                    variant="outline"
                    className="text-[color:var(--danger)]"
                    disabled={kycBusy}
                    onClick={async () => {
                      const kycId = String((profile?.kyc as Row | null | undefined)?.id || "");
                      if (!kycId) {
                        toast.error("No KYC submission id");
                        return;
                      }
                      setKycBusy(true);
                      try {
                        await OpsAPI.rejectKyc(
                          kycId,
                          kycRejectReason.trim() || "Documents mismatch / incomplete",
                        );
                        toast.message("KYC rejected");
                        setKycRejectReason("");
                        await loadAll();
                      } catch (e) {
                        toast.error(e instanceof Error ? e.message : "Reject failed");
                      } finally {
                        setKycBusy(false);
                      }
                    }}
                  >
                    Reject KYC
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

          <div className="mb-4 grid gap-4 lg:grid-cols-2">
            <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
              <h2 className="mb-3 text-sm font-semibold text-[color:var(--brand-dark)]">Profile details</h2>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <Detail label="Email" value={String(profile?.email || "—")} />
                <Detail label="Lead ref" value={String(profile?.lead_reference || profile?.sponsor_id || "—")} />
                <Detail
                  label="Last login"
                  value={
                    profile?.last_login_at
                      ? new Date(String(profile.last_login_at)).toLocaleString("en-IN")
                      : "—"
                  }
                />
                <Detail label="Last IP" value={String(profile?.last_login_ip || "—")} />
                <Detail label="Card" value={String(profile?.card_tier || "—")} />
                <Detail label="Flag" value={String(profile?.flag_color || "—")} />
                <Detail
                  label="Reward level"
                  value={
                    <LevelBadge
                      kind="reward"
                      level={profile?.reward_level ?? profile?.earning_level}
                      name={profile?.reward_level_name ?? profile?.earning_level_name}
                    />
                  }
                />
                <Detail
                  label="Performance level"
                  value={
                    <LevelBadge
                      kind="performance"
                      level={profile?.performance_level}
                      name={profile?.performance_level_name}
                    />
                  }
                />
                <Detail label="Join amount" value={money(profile?.join_amount)} />
                <Detail label="Team business" value={money(profile?.total_business)} />
                <Detail label="Directs" value={String(profile?.direct_count ?? 0)} />
                <Detail label="Active directs" value={String(profile?.direct_active_count ?? 0)} />
                <Detail label="City" value={String(profile?.city || "—")} />
                <Detail label="State" value={String(profile?.state || "—")} />
                <Detail
                  label="Joined"
                  value={
                    profile?.created_at
                      ? new Date(String(profile.created_at)).toLocaleString("en-IN")
                      : "—"
                  }
                />
                <Detail
                  label="Activated"
                  value={
                    profile?.activated_at
                      ? new Date(String(profile.activated_at)).toLocaleString("en-IN")
                      : "—"
                  }
                />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
              <h2 className="mb-3 text-sm font-semibold text-[color:var(--brand-dark)]">Wallets</h2>
              {wallets.length === 0 ? (
                <p className="text-sm text-muted-foreground">No wallets yet.</p>
              ) : (
                <ul className="space-y-2">
                  {wallets.map((w) => (
                    <li
                      key={String(w.id)}
                      className="flex items-center justify-between rounded-xl border border-border/70 bg-[color:var(--hero)]/40 px-3 py-2.5 text-sm"
                    >
                      <span className="font-medium uppercase tracking-wide text-muted-foreground">
                        {String(w.wallet_type)}
                      </span>
                      <span className="tabular-nums font-semibold text-[color:var(--brand-dark)]">
                        {money(w.balance)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="mb-3 flex gap-2">
            <TabButton active={tab === "ledger"} onClick={() => setTab("ledger")}>
              Fund history
            </TabButton>
            <TabButton active={tab === "income"} onClick={() => setTab("income")}>
              Income history
            </TabButton>
          </div>

          {tab === "ledger" ? (
            <DataTable
              data={ledger}
              columns={ledgerCols}
              searchable={(r) => `${r.wallet_type} ${r.reference} ${r.narration}`}
              emptyTitle="No fund history"
              emptyHint="Ledger entries for this associate will appear here."
            />
          ) : (
            <DataTable
              data={income}
              columns={incomeCols}
              searchable={(r) => `${r.source_id} ${r.narration} ${r.wallet_type}`}
              emptyTitle="No income history"
              emptyHint="Commission entries for this associate will appear here."
            />
          )}
        </>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1.5 text-base font-semibold text-foreground">{value}</div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-[color:var(--brand)] text-white"
          : "bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)] hover:opacity-90"
      }`}
    >
      {children}
    </button>
  );
}
