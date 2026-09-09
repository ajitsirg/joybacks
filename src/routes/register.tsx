import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Lock,
  Shield,
  Star,
  Gem,
} from "lucide-react";
import { AvatarChoiceGrid } from "@/components/avatar-picker";
import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AssociatesAPI, AuthAPI, ConfigAPI, setTokens } from "@/lib/api";
import { useAuth } from "@/lib/rbac";
import { emailError, mobileError, normalizeEmail, normalizeMobile } from "@/lib/validation";

export const Route = createFileRoute("/register")({
  head: () => ({ meta: [{ title: "Join — JoyClub Associate" }] }),
  validateSearch: (search: Record<string, unknown>) => ({
    ref: typeof search.ref === "string" ? search.ref : typeof search.lead === "string" ? search.lead : "",
  }),
  component: JoinPage,
});

const PACKAGES = [
  {
    key: "platinum",
    amount: 220000,
    title: "Platinum",
    desc: "For serious investors seeking bespoke concierge service. The amount is paid and any rest amount will be deducted from incentives.",
    features: ["Dedicated Wealth Manager", "0.1% Trading Commissions"],
    badges: ["PREMIUM", "CHOICE", "MOST POPULAR"],
    recommended: true,
    icon: "gem" as const,
  },
  {
    key: "silver",
    amount: 22000,
    title: "Silver",
    desc: "₹ 22,000 insert amount, rest amount will deduct from incentives.",
    features: ["Advanced Portfolio Analytics", "Priority Support (24h)"],
    badges: [] as string[],
    recommended: false,
    icon: "star" as const,
  },
  {
    key: "gray",
    amount: 0,
    title: "Gray",
    desc: "Join with ₹ 0 (gray flag). Turns green after any investment is credited.",
    features: ["Basic Wealth Tracking", "Community Forum Access"],
    badges: ["ESSENTIAL"],
    recommended: false,
    icon: "shield" as const,
  },
] as const;

const STEPS = ["Membership", "Personal", "KYC Docs", "Verify"] as const;

function inr(n: number) {
  return `₹ ${n.toLocaleString("en-IN")}`;
}

type JoinKycReq = {
  pan: boolean;
  aadhaar: boolean;
  bank_name: boolean;
  account_number: boolean;
  ifsc: boolean;
  upi_id: boolean;
  profile_photo: boolean;
  aadhaar_document: boolean;
  pan_document: boolean;
  bank_document: boolean;
};

const DEFAULT_KYC_REQ: JoinKycReq = {
  pan: false,
  aadhaar: false,
  bank_name: false,
  account_number: false,
  ifsc: false,
  upi_id: false,
  profile_photo: false,
  aadhaar_document: false,
  pan_document: false,
  bank_document: false,
};

function JoinPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set(["gray"]));
  const [kycReq, setKycReq] = useState<JoinKycReq>(DEFAULT_KYC_REQ);
  const visiblePackages = useMemo(
    () => PACKAGES.filter((p) => visibleKeys.has(p.key)),
    [visibleKeys],
  );
  const [pkg, setPkg] = useState<(typeof PACKAGES)[number]>(PACKAGES[2]); // Gray default while Platinum/Silver hidden
  const [obscure, setObscure] = useState(true);
  const [country, setCountry] = useState("+91");
  const search = Route.useSearch();
  const { applyApiUser } = useAuth();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    mobile: "",
    password: "",
    lead_reference: (search.ref || "").toUpperCase(),
    otp: "",
    pan: "",
    aadhaar: "",
    bank_name: "",
    account_number: "",
    ifsc: "",
    upi_id: "",
  });
  const [files, setFiles] = useState<{
    profile_photo?: File;
    aadhaar_document?: File;
    aadhaar_back?: File;
    pan_document?: File;
    bank_document?: File;
  }>({});
  const [avatarId, setAvatarId] = useState<string | null>(null);
  const [otpSent, setOtpSent] = useState(false);
  const [requireJoinOtp, setRequireJoinOtp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState<Record<string, unknown> | null>(null);
  const lastStep = requireJoinOtp ? 3 : 2;
  const totalSteps = lastStep + 1;

  useEffect(() => {
    if (search.ref) {
      setForm((f) => ({ ...f, lead_reference: search.ref.trim().toUpperCase() }));
    }
  }, [search.ref]);

  useEffect(() => {
    ConfigAPI.runtime()
      .then((d) => {
        const jp = (d.join_packages as Record<string, boolean> | undefined) ?? {};
        const company = (d.company as Record<string, unknown> | undefined) ?? {};
        const joinFlow = (d.join_flow as { require_join_otp?: boolean } | undefined) ?? {};
        const req = (d.join_kyc_requirements as Partial<JoinKycReq> | undefined) ?? {};
        const keys = new Set<string>(["gray"]);
        if (jp.show_platinum ?? company.show_platinum_package) keys.add("platinum");
        if (jp.show_silver ?? company.show_silver_package) keys.add("silver");
        setVisibleKeys(keys);
        setKycReq({ ...DEFAULT_KYC_REQ, ...req });
        setRequireJoinOtp(joinFlow.require_join_otp === true);
        setPkg((current) => {
          if (keys.has(current.key)) return current;
          return PACKAGES.find((p) => keys.has(p.key)) ?? PACKAGES[2];
        });
      })
      .catch(() => {
        // Offline / API down: keep Gray only; KYC stays optional; OTP off
        setVisibleKeys(new Set(["gray"]));
        setPkg(PACKAGES[2]);
        setKycReq(DEFAULT_KYC_REQ);
        setRequireJoinOtp(false);
      });
  }, []);

  const set = (key: keyof typeof form, value: string) => setForm((f) => ({ ...f, [key]: value }));
  const progress = ((step + 1) / totalSteps) * 100;
  const digitsMobile = useMemo(() => normalizeMobile(form.mobile), [form.mobile]);

  function validateStep() {
    if (step === 1) {
      if (!form.lead_reference.trim()) return toast.error("Lead reference is required"), false;
      if (!form.first_name.trim()) return toast.error("Enter first name"), false;
      const em = emailError(form.email, { required: true });
      if (em) return toast.error(em), false;
      const mob = mobileError(form.mobile);
      if (mob) return toast.error(mob), false;
      if (form.password.length < 6) return toast.error("Password must be at least 6 characters"), false;
    }
    if (step === 2) {
      const textChecks: [keyof JoinKycReq, string, string][] = [
        ["pan", "PAN", form.pan],
        ["aadhaar", "Aadhaar", form.aadhaar],
        ["bank_name", "Bank name", form.bank_name],
        ["account_number", "Account number", form.account_number],
        ["ifsc", "IFSC", form.ifsc],
        ["upi_id", "UPI ID", form.upi_id],
      ];
      for (const [key, label, value] of textChecks) {
        if (kycReq[key] && !value.trim()) {
          return toast.error(`${label} is required`), false;
        }
      }
      const fileChecks: [keyof JoinKycReq, string, File | undefined][] = [
        ["profile_photo", "Profile photo", files.profile_photo],
        ["pan_document", "PAN card", files.pan_document],
        ["bank_document", "Bank proof", files.bank_document],
      ];
      for (const [key, label, value] of fileChecks) {
        if (kycReq[key] && !value) {
          return toast.error(`${label} is required`), false;
        }
      }
      if (kycReq.aadhaar_document) {
        if (!files.aadhaar_document) {
          return toast.error("Aadhaar front image is required"), false;
        }
        if (!files.aadhaar_back) {
          return toast.error("Aadhaar back image is required"), false;
        }
      }
    }
    if (requireJoinOtp && step === 3 && form.otp.trim().length < 4) {
      return toast.error("Enter the OTP sent to your mobile"), false;
    }
    return true;
  }

  async function sendOtp() {
    const mob = mobileError(form.mobile);
    if (mob) {
      toast.error(mob);
      return;
    }
    try {
      const res = await AssociatesAPI.registerOtp(digitsMobile);
      setOtpSent(true);
      if (res.debug_otp) {
        set("otp", res.debug_otp);
        toast.success(`OTP (dev): ${res.debug_otp}`);
      } else toast.success("OTP sent to mobile");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "OTP failed");
    }
  }

  async function submit() {
    setLoading(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (k === "otp" && !requireJoinOtp) return;
        fd.append(k, v);
      });
      fd.set("mobile", digitsMobile);
      fd.set("email", normalizeEmail(form.email));
      fd.set("lead_reference", form.lead_reference.trim().toUpperCase());
      fd.append("join_amount", String(pkg.amount));
      if (files.profile_photo) fd.append("profile_photo", files.profile_photo);
      if (files.aadhaar_document) fd.append("aadhaar_document", files.aadhaar_document);
      if (files.aadhaar_back) fd.append("aadhaar_back", files.aadhaar_back);
      if (files.pan_document) fd.append("pan_document", files.pan_document);
      if (files.bank_document) fd.append("bank_document", files.bank_document);
      const assoc = await AssociatesAPI.register(fd);
      const status = String(assoc.status ?? "").toLowerCase();
      const canEnter =
        assoc.auto_activated === true || status === "active" || status === "inactive";
      if (canEnter) {
        const username = String(assoc.associate_id ?? assoc.username ?? "");
        const result = await AuthAPI.loginPayload({
          username,
          password: form.password,
          remember_me: true,
        });
        setTokens({ access: result.access, refresh: result.refresh });
        applyApiUser(result.user);
        toast.success(
          status === "active"
            ? "Welcome! Opening your dashboard…"
            : "Welcome! Invest ₹2,20,000 to become Active.",
        );
        void navigate({ to: "/dashboard" });
        return;
      }
      setCreated(assoc);
      toast.success("Submitted — wait for your team lead approval");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Joining failed");
    } finally {
      setLoading(false);
    }
  }

  async function next() {
    if (!validateStep()) return;
    if (step < lastStep) {
      setStep((s) => s + 1);
      return;
    }
    await submit();
  }

  if (created) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F7FAF8] p-6">
        <div className="w-full max-w-md space-y-4 rounded-3xl border border-[#C5E2D1] bg-white p-8 shadow-xl">
          <BrandMark className="mx-auto h-16 w-16 rounded-2xl" />
          <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
            Wait for your admin approval
          </p>
          <h1 className="text-2xl font-semibold text-[color:var(--brand-dark)]">Request submitted</h1>
          <p className="text-sm text-muted-foreground">
            Documents sent to lead <strong>{String(created.lead_reference)}</strong>. Sign in after they approve for full access.
          </p>
          <div className="rounded-2xl bg-[color:var(--brand-tint)] p-4 text-sm">
            <div className="text-muted-foreground">Username</div>
            <div className="text-xl font-bold text-[color:var(--brand-dark)]">
              {String(created.username ?? created.associate_id)}
            </div>
            <div className="mt-2 text-muted-foreground">
              {pkg.title} · {inr(pkg.amount)} · {String(created.status)}
            </div>
          </div>
          <Button className="w-full" onClick={() => navigate({ to: "/login" })}>
            Go to login
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7FAF8]">
      <div className="mx-auto flex min-h-screen max-w-xl flex-col px-4 pb-28 pt-6 sm:px-6">
        <div className="mb-4 flex items-center gap-2">
          <button
            type="button"
            onClick={() => (step === 0 ? navigate({ to: "/login" }) : setStep((s) => s - 1))}
            className="grid h-9 w-9 place-items-center rounded-full text-[color:var(--brand-dark)] hover:bg-white"
            aria-label="Back"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <BrandMark className="h-9 w-9" />
          <h1 className="text-lg font-bold text-[color:var(--brand-dark)]">Join JoyClub</h1>
        </div>

        <div className="mb-5">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#6B7C72]">
              Step {step + 1} of {totalSteps}
            </span>
            {step === 0 ? (
              <span className="rounded-full bg-[#E8EEEA] px-2.5 py-1 text-[11px] font-semibold text-[#4A6B57]">
                {Math.round(progress)}% Complete
              </span>
            ) : (
              <span className="text-xs font-semibold text-[#4A6B57]">{STEPS[step]}</span>
            )}
          </div>
          {step === 0 && (
            <h2 className="mb-3 text-[1.65rem] font-extrabold leading-tight text-[color:var(--brand-dark)]">
              Choose Your Membership
            </h2>
          )}
          <div className="h-1.5 overflow-hidden rounded-full bg-[#DCE8E1]">
            <div className="h-full rounded-full bg-[color:var(--brand)] transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="flex-1 space-y-4">
          {step === 0 && (
            <>
              {visiblePackages.map((p) => (
                <MembershipCard key={p.key} pkg={p} selected={pkg.key === p.key} onSelect={() => setPkg(p)} />
              ))}
              <div className="rounded-2xl border border-dashed border-[#CDD9D2] bg-[#F0F4F2] px-4 py-5 text-center">
                <Lock className="mx-auto mb-2 h-5 w-5 text-[#6B7C72]" />
                <p className="text-xs leading-relaxed text-[#5A6F63]">
                  Your selection is secure. You can upgrade or downgrade your JoyClub tier at any time after the initial
                  30-day onboarding period.
                </p>
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <div>
                <h2 className="text-[1.65rem] font-extrabold leading-tight text-[color:var(--brand)]">Tell us about yourself</h2>
                <p className="mt-2 text-sm text-[#4A6B57]">
                  Please provide your legal details to ensure the security of your JoyClub account.
                </p>
              </div>
              <Field label="Lead Reference">
                <Input
                  value={form.lead_reference}
                  onChange={(e) => set("lead_reference", e.target.value.toUpperCase())}
                  placeholder="Enter lead username"
                  required
                  autoComplete="off"
                />
              </Field>
              <Field label="First Name">
                <Input value={form.first_name} onChange={(e) => set("first_name", e.target.value)} placeholder="Enter first name" required />
              </Field>
              <Field label="Last Name">
                <Input value={form.last_name} onChange={(e) => set("last_name", e.target.value)} placeholder="Enter last name" />
              </Field>
              <Field label="Email">
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  onBlur={() => {
                    const err = emailError(form.email, { required: true });
                    if (err && form.email.trim()) toast.error(err);
                  }}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </Field>
              <Field label="Mobile Number">
                <div className="flex gap-2">
                  <select
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="h-10 rounded-md border border-input bg-white px-2 text-sm"
                    disabled
                  >
                    <option value="+91">+91</option>
                  </select>
                  <Input
                    value={form.mobile}
                    onChange={(e) => set("mobile", e.target.value.replace(/\D/g, "").slice(0, 10))}
                    onBlur={() => {
                      const err = mobileError(form.mobile);
                      if (err && form.mobile.trim()) toast.error(err);
                    }}
                    placeholder="9876543210"
                    inputMode="numeric"
                    pattern="[6-9][0-9]{9}"
                    maxLength={10}
                    required
                  />
                </div>
                <p className="mt-1 text-xs text-[#5A6F63]">10-digit Indian mobile starting with 6–9.</p>
              </Field>
              <Field label="Password">
                <div className="relative">
                  <Input
                    type={obscure ? "password" : "text"}
                    value={form.password}
                    onChange={(e) => set("password", e.target.value)}
                    placeholder="Create a secure password"
                    minLength={6}
                    required
                    className="pr-10"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-[#8AA396]"
                    onClick={() => setObscure((v) => !v)}
                  >
                    {obscure ? "Show" : "Hide"}
                  </button>
                </div>
                <p className="mt-1 text-xs text-[#5A6F63]">Must be at least 6 characters.</p>
              </Field>
              <div className="flex gap-3 rounded-2xl bg-[color:var(--brand-tint)] p-4">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white">
                  <Shield className="h-4 w-4 text-[color:var(--brand-dark)]" />
                </div>
                <div>
                  <div className="text-sm font-bold text-[color:var(--brand-dark)]">Your data is secure</div>
                  <p className="mt-1 text-xs leading-relaxed text-[#4A6B57]">
                    JoyClub uses bank-grade encryption to protect your personal information. We never share your data with
                    third parties without your explicit consent.
                  </p>
                </div>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <h2 className="text-2xl font-extrabold text-[color:var(--brand-dark)]">KYC & bank details</h2>
                <p className="mt-2 text-sm text-[#4A6B57]">
                  Upload clear photos when available. Fields marked required depend on admin settings — others are optional.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label={kycReq.pan ? "PAN *" : "PAN"}>
                  <Input
                    value={form.pan}
                    onChange={(e) => set("pan", e.target.value.toUpperCase())}
                    required={kycReq.pan}
                  />
                </Field>
                <Field label={kycReq.aadhaar ? "Aadhaar *" : "Aadhaar"}>
                  <Input
                    value={form.aadhaar}
                    onChange={(e) => set("aadhaar", e.target.value)}
                    required={kycReq.aadhaar}
                  />
                </Field>
                <Field label={kycReq.bank_name ? "Bank name *" : "Bank name"} className="sm:col-span-2">
                  <Input
                    value={form.bank_name}
                    onChange={(e) => set("bank_name", e.target.value)}
                    required={kycReq.bank_name}
                  />
                </Field>
                <Field label={kycReq.account_number ? "Account number *" : "Account number"}>
                  <Input
                    value={form.account_number}
                    onChange={(e) => set("account_number", e.target.value)}
                    required={kycReq.account_number}
                  />
                </Field>
                <Field label={kycReq.ifsc ? "IFSC *" : "IFSC"}>
                  <Input
                    value={form.ifsc}
                    onChange={(e) => set("ifsc", e.target.value.toUpperCase())}
                    required={kycReq.ifsc}
                  />
                </Field>
                <Field label={kycReq.upi_id ? "UPI ID *" : "UPI ID"} className="sm:col-span-2">
                  <Input
                    value={form.upi_id}
                    onChange={(e) => set("upi_id", e.target.value)}
                    placeholder="name@upi"
                    required={kycReq.upi_id}
                  />
                </Field>
              </div>
              <div className="space-y-2">
                <FileField
                  label={kycReq.profile_photo ? "Profile photo *" : "Profile photo"}
                  accept="image/*"
                  required={kycReq.profile_photo && !files.profile_photo}
                  onChange={(f) => {
                    setAvatarId(null);
                    setFiles((x) => ({ ...x, profile_photo: f }));
                  }}
                />
                <div className="rounded-xl border border-border bg-muted/30 p-3">
                  <div className="mb-2 text-xs font-medium text-muted-foreground">
                    Or pick an avatar{files.profile_photo && avatarId ? " (selected)" : ""}
                  </div>
                  <AvatarChoiceGrid
                    value={avatarId}
                    onChange={(avatar, file) => {
                      setAvatarId(avatar.id);
                      setFiles((x) => ({ ...x, profile_photo: file }));
                      toast.success(`Avatar “${avatar.label}” selected`);
                    }}
                  />
                </div>
                <div className="rounded-xl border border-border bg-muted/20 p-3 space-y-2">
                  <div className="text-xs font-semibold text-[color:var(--brand-dark)]">
                    Aadhaar card{kycReq.aadhaar_document ? " *" : ""}
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Upload front and back. Aadhaar counts as attached only when both are present.
                  </p>
                  <FileField
                    label={kycReq.aadhaar_document ? "Aadhaar front *" : "Aadhaar front"}
                    accept="image/*,.pdf"
                    required={kycReq.aadhaar_document}
                    onChange={(f) => setFiles((x) => ({ ...x, aadhaar_document: f }))}
                  />
                  <FileField
                    label={kycReq.aadhaar_document ? "Aadhaar back *" : "Aadhaar back"}
                    accept="image/*,.pdf"
                    required={kycReq.aadhaar_document}
                    onChange={(f) => setFiles((x) => ({ ...x, aadhaar_back: f }))}
                  />
                </div>
                <FileField
                  label={kycReq.pan_document ? "PAN card *" : "PAN card"}
                  accept="image/*,.pdf"
                  required={kycReq.pan_document}
                  onChange={(f) => setFiles((x) => ({ ...x, pan_document: f }))}
                />
                <FileField
                  label={kycReq.bank_document ? "Bank proof *" : "Bank proof"}
                  accept="image/*,.pdf"
                  required={kycReq.bank_document}
                  onChange={(f) => setFiles((x) => ({ ...x, bank_document: f }))}
                />
              </div>
            </>
          )}

          {requireJoinOtp && step === 3 && (
            <>
              <div>
                <h2 className="text-2xl font-extrabold text-[color:var(--brand-dark)]">Verify your mobile</h2>
                <p className="mt-2 text-sm text-[#4A6B57]">
                  We will send an OTP to {country} {digitsMobile}
                </p>
              </div>
              <div className="rounded-2xl border border-[#C5E2D1] bg-white p-4 text-sm">
                <div className="font-semibold text-[color:var(--brand-dark)]">
                  {form.first_name} {form.last_name}
                </div>
                <div className="mt-1 text-muted-foreground">
                  {country} {digitsMobile} · Lead {form.lead_reference.toUpperCase()}
                </div>
                <div className="mt-2 font-semibold text-[color:var(--brand)]">
                  {pkg.title} · {inr(pkg.amount)}
                </div>
              </div>
              <Field label="One-time password">
                <div className="flex gap-2">
                  <Input value={form.otp} onChange={(e) => set("otp", e.target.value)} placeholder="Enter OTP" required />
                  <Button type="button" variant="outline" onClick={() => void sendOtp()}>
                    {otpSent ? "Resend" : "Send OTP"}
                  </Button>
                </div>
              </Field>
            </>
          )}
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 border-t border-[#E2EDE7] bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-xl items-center gap-3 px-4 py-3 sm:px-6">
          {step === 0 ? (
            <>
              <div className="min-w-0 flex-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#6B7C72]">Join amount</div>
                <div className="text-xl font-extrabold text-[color:var(--brand-dark)]">{inr(pkg.amount)}</div>
              </div>
              <Button onClick={() => void next()} className="gap-2 bg-[color:var(--brand-dark)] hover:bg-[color:var(--brand-dark)]/90">
                Continue to Step 2 <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Button type="button" variant="outline" className="gap-1" onClick={() => setStep((s) => s - 1)} disabled={loading}>
                <ChevronLeft className="h-4 w-4" /> Back
              </Button>
              <Button
                className="flex-1 gap-1 bg-[color:var(--brand-dark)] hover:bg-[color:var(--brand-dark)]/90"
                onClick={() => void next()}
                disabled={loading}
              >
                {loading
                  ? "Submitting…"
                  : step === lastStep
                    ? requireJoinOtp
                      ? "Submit for approval"
                      : "Complete & open dashboard"
                    : "Next Step"}
                {step < lastStep && <ChevronRight className="h-4 w-4" />}
              </Button>
            </>
          )}
        </div>
        <p className="pb-3 text-center text-xs text-muted-foreground">
          Already joined?{" "}
          <Link to="/login" className="font-medium text-[color:var(--brand-dark)] underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <Label className="text-[color:var(--brand)]">{label}</Label>
      {children}
    </div>
  );
}

function MembershipCard({
  pkg,
  selected,
  onSelect,
}: {
  pkg: (typeof PACKAGES)[number];
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = pkg.icon === "gem" ? Gem : pkg.icon === "star" ? Star : Shield;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`relative w-full overflow-hidden rounded-[18px] border bg-white p-4 text-left shadow-sm transition ${
        selected ? "border-[color:var(--brand-dark)] ring-2 ring-[color:var(--brand)]/20" : "border-[#E2EDE7] hover:border-[#C5E2D1]"
      }`}
    >
      {pkg.recommended && (
        <span className="absolute right-0 top-0 rounded-bl-xl bg-[color:var(--brand-dark)] px-2.5 py-1 text-[10px] font-extrabold tracking-wide text-white">
          RECOMMENDED
        </span>
      )}
      <div className="flex items-start gap-3">
        <div
          className={`grid h-11 w-11 shrink-0 place-items-center ${
            pkg.key === "platinum" ? "rounded-xl bg-[color:var(--brand-dark)] text-white" : pkg.key === "silver" ? "rounded-full bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)]" : "rounded-full bg-[#EEF1EF] text-[color:var(--brand-dark)]"
          }`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-lg font-extrabold text-[color:var(--brand-dark)]">{pkg.title}</div>
              {pkg.badges.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {pkg.badges.map((b) => (
                    <span
                      key={b}
                      className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                        pkg.key === "gray" ? "bg-[#E8EEEA] text-[#5A6F63]" : "bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)]"
                      }`}
                    >
                      {b}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="shrink-0 text-xl font-extrabold tabular-nums text-[color:var(--brand-dark)]">{inr(pkg.amount)}</div>
          </div>
          <p className="mt-2 text-sm leading-snug text-[#5A6F63]">{pkg.desc}</p>
          <ul className="mt-2 space-y-1">
            {pkg.features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-[#3D5347]">
                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[color:var(--brand)]" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </button>
  );
}

function FileField({
  label,
  accept,
  onChange,
  required = false,
}: {
  label: string;
  accept: string;
  onChange: (f: File | undefined) => void;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[color:var(--brand)]">{label}</Label>
      <Input
        type="file"
        accept={accept}
        required={required}
        onChange={(e) => onChange(e.target.files?.[0])}
        className="cursor-pointer bg-white"
      />
    </div>
  );
}
