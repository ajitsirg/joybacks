import { Link, createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Check,
  Copy,
  IdCard,
  Mail,
  MapPin,
  Phone,
  Shield,
  UserRound,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";
import { ProfileAvatarEditor } from "@/components/avatar-picker";
import { LevelBadge } from "@/components/earning-level-badge";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { AuthAPI, AssociatesAPI, resolveMediaUrl, type ApiUser } from "@/lib/api";
import { useAuth, ALL_PERMISSIONS } from "@/lib/rbac";

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

const PERMISSION_GROUPS = Object.entries(
  ALL_PERMISSIONS.reduce<Record<string, typeof ALL_PERMISSIONS>>((acc, p) => {
    (acc[p.module] ??= []).push(p);
    return acc;
  }, {}),
);

export const Route = createFileRoute("/_app/rbac/profile")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "My Profile — JoyClub Associate" },
      { name: "description", content: "Your JoyClub account profile and access." },
      { property: "og:title", content: "My Profile — JoyClub Associate" },
      { property: "og:description", content: "Your JoyClub account profile and access." },
    ],
  }),
  component: ProfilePage,
});

function money(v: unknown) {
  return `₹ ${Number(v ?? 0).toLocaleString("en-IN")}`;
}

function flagLabel(flag?: string) {
  if (flag === "green") return "Has investment";
  return "No investment";
}

function ProfilePage() {
  const { session, roles, permissions, applyApiUser } = useAuth();
  const [me, setMe] = useState<ApiUser | null>(null);
  const [city, setCity] = useState("");
  const [stateName, setStateName] = useState("");
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [rewardLevelName, setRewardLevelName] = useState("");
  const [rewardLevel, setRewardLevel] = useState(0);
  const [performanceLevelName, setPerformanceLevelName] = useState("");
  const [performanceLevel, setPerformanceLevel] = useState(0);
  const [totalBusiness, setTotalBusiness] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [showDenied, setShowDenied] = useState(false);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const user = await AuthAPI.me();
      setMe(user);
      applyApiUser(user);
      setRewardLevelName(
        user.associate?.reward_level_name || user.associate?.earning_level_name || "",
      );
      setRewardLevel(
        Number(user.associate?.reward_level ?? user.associate?.earning_level ?? 0),
      );
      setPerformanceLevelName(user.associate?.performance_level_name || "");
      setPerformanceLevel(Number(user.associate?.performance_level ?? 0));
      setTotalBusiness(user.associate?.total_business);
      setPhotoUrl(resolveMediaUrl(user.associate?.profile_photo_url ?? null));
      const aid = user.associate?.associate_id;
      if (aid) {
        try {
          const detail = await AssociatesAPI.get(aid);
          setCity(String(detail.city ?? ""));
          setStateName(String(detail.state ?? ""));
          setRewardLevelName(
            String(
              detail.reward_level_name ??
                detail.earning_level_name ??
                user.associate?.reward_level_name ??
                user.associate?.earning_level_name ??
                "",
            ),
          );
          setRewardLevel(
            Number(
              detail.reward_level ??
                detail.earning_level ??
                user.associate?.reward_level ??
                user.associate?.earning_level ??
                0,
            ),
          );
          setPerformanceLevelName(
            String(detail.performance_level_name ?? user.associate?.performance_level_name ?? ""),
          );
          setPerformanceLevel(
            Number(detail.performance_level ?? user.associate?.performance_level ?? 0),
          );
          setTotalBusiness(String(detail.total_business ?? user.associate?.total_business ?? "0"));
          const kyc = detail.kyc as Record<string, unknown> | null | undefined;
          const fromKyc = resolveMediaUrl(
            kyc?.profile_photo_url ? String(kyc.profile_photo_url) : null,
          );
          if (fromKyc) setPhotoUrl(fromKyc);
        } catch {
          /* optional enrich */
        }
      }
    } catch {
      toast.error("Could not load profile");
    } finally {
      setLoading(false);
    }
  }, [applyApiUser]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  if (!session) return null;

  const name =
    [me?.first_name, me?.last_name].filter(Boolean).join(" ") ||
    session.name ||
    me?.username ||
    "—";
  const email = me?.email || session.email || "—";
  const username = me?.username || session.username || "—";
  const associate = me?.associate ?? null;
  const myRoles = roles.filter((r) => session.roleIds.includes(r.id));
  const primaryRole = myRoles[0]?.name ?? (session.isStaff ? "Staff" : "Associate");
  const grantedCount = ALL_PERMISSIONS.filter((p) => permissions.has(p.key)).length;

  async function copyText(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(`${label} copied`);
    } catch {
      toast.error("Copy failed");
    }
  }

  async function savePhoto(file: File) {
    const aid = associate?.associate_id;
    if (!aid) throw new Error("Associate profile required to save a photo");
    const fd = new FormData();
    fd.append("profile_photo", file);
    const updated = await AssociatesAPI.update(aid, fd);
    const kyc = updated.kyc as Record<string, unknown> | null | undefined;
    const nextUrl = resolveMediaUrl(
      kyc?.profile_photo_url ? String(kyc.profile_photo_url) : null,
    );
    if (!nextUrl) {
      throw new Error("Photo uploaded but the server did not return a URL. Please try again.");
    }
    setPhotoUrl(nextUrl);
    // Refresh session so header / sidebar show the new photo immediately
    try {
      const user = await AuthAPI.me();
      applyApiUser({
        ...user,
        associate: user.associate
          ? { ...user.associate, profile_photo_url: nextUrl }
          : user.associate,
      });
    } catch {
      if (me?.associate) {
        applyApiUser({
          ...me,
          associate: { ...me.associate, profile_photo_url: nextUrl },
        });
      }
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 sm:space-y-5">
      <PageHeader
        title="My Profile"
        subtitle="Your account identity, associate details, and access."
        actions={
          associate?.associate_id ? (
            <Button asChild size="sm">
              <Link to="/users/$associateId" params={{ associateId: associate.associate_id }}>
                Edit full profile
              </Link>
            </Button>
          ) : null
        }
      />

      {/* Identity band */}
      <section className="overflow-hidden rounded-2xl border border-[color:var(--hero-border)] bg-[color:var(--hero)]">
        <div className="h-1.5 w-full bg-[color:var(--brand)]" />
        <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
          {associate?.associate_id ? (
            <ProfileAvatarEditor
              name={name}
              photoUrl={photoUrl || session.photoUrl}
              onPickFile={savePhoto}
            />
          ) : (
            <div className="h-28 w-28 overflow-hidden rounded-xl border-2 border-white bg-[color:var(--brand)] shadow-sm sm:h-32 sm:w-32">
              {photoUrl || session.photoUrl ? (
                <img
                  src={String(photoUrl || session.photoUrl)}
                  alt={name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="grid h-full w-full place-items-center text-2xl font-semibold text-white">
                  {initials(name)}
                </div>
              )}
            </div>
          )}
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
                {loading ? "Loading…" : name}
              </h2>
              {associate?.status ? (
                <StatusBadge status={associate.status} />
              ) : (
                <StatusBadge status={session.status} />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Mail className="h-3.5 w-3.5" />
                {email}
              </span>
              {(associate?.mobile || me?.phone) && (
                <span className="inline-flex items-center gap-1.5">
                  <Phone className="h-3.5 w-3.5" />
                  {associate?.mobile || me?.phone}
                </span>
              )}
              {(city || stateName) && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" />
                  {[city, stateName].filter(Boolean).join(", ")}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 text-xs font-medium text-[color:var(--brand-dark)] ring-1 ring-[color:var(--hero-border)]">
                <Shield className="h-3 w-3" />
                {primaryRole}
              </span>
              {associate?.card_tier && (
                <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 text-xs font-medium text-foreground ring-1 ring-[color:var(--hero-border)]">
                  <IdCard className="h-3 w-3" />
                  {associate.card_tier} card
                </span>
              )}
              <LevelBadge kind="reward" level={rewardLevel} name={rewardLevelName} />
              <LevelBadge
                kind="performance"
                level={performanceLevel}
                name={performanceLevelName}
              />
              {associate?.flag_color && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/80 px-2.5 py-1 text-xs font-medium text-foreground ring-1 ring-[color:var(--hero-border)]">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{
                      background:
                        associate.flag_color === "green" ? "var(--brand)" : "#9CA3AF",
                    }}
                  />
                  {flagLabel(associate.flag_color)}
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {associate?.waiting_message && associate.status !== "active" && (
        <div className="rounded-xl border border-[color:var(--warn)]/30 bg-[color:var(--warn-tint)] px-4 py-3 text-sm text-[color:var(--warn-text)]">
          {associate.waiting_message}
        </div>
      )}

      {/* Account + associate */}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2">
            <UserRound className="h-4 w-4 text-[color:var(--brand)]" />
            <h3 className="text-sm font-semibold">Account</h3>
          </div>
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Display name" value={name} />
            <Field label="Username" value={username} mono />
            <Field label="Email" value={email} />
            <Field label="User type" value={me?.user_type || (session.isStaff ? "staff" : "associate")} />
            <Field
              label="Last login"
              value={
                session.lastLoginAt
                  ? new Date(session.lastLoginAt).toLocaleString("en-IN")
                  : "—"
              }
            />
            <Field label="Last IP" value={session.lastLoginIp || "—"} mono />
          </dl>
          {myRoles.length > 0 && (
            <div className="mt-4 border-t border-border pt-4">
              <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Roles
              </div>
              <div className="flex flex-wrap gap-1.5">
                {myRoles.map((r) => (
                  <span
                    key={r.id}
                    className="rounded-md bg-[color:var(--brand-tint)] px-2.5 py-1 text-xs font-medium text-[color:var(--brand-dark)]"
                  >
                    {r.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2">
            <Wallet className="h-4 w-4 text-[color:var(--brand)]" />
            <h3 className="text-sm font-semibold">Associate</h3>
          </div>
          {associate ? (
            <dl className="grid gap-3 sm:grid-cols-2">
              <Field
                label="Associate ID"
                value={associate.associate_id}
                mono
                onCopy={() => copyText("Associate ID", associate.associate_id)}
              />
              <Field label="Status" value={<StatusBadge status={associate.status} />} />
              <Field label="Mobile" value={associate.mobile || "—"} />
              <Field
                label="Referral code"
                value={associate.referral_code || "—"}
                mono
                onCopy={
                  associate.referral_code
                    ? () => copyText("Referral code", associate.referral_code!)
                    : undefined
                }
              />
              <Field label="Lead reference" value={associate.lead_reference || "—"} />
              <Field label="KYC" value={associate.kyc_verified ? "Verified" : "Not verified"} />
              <Field
                label="Reward level"
                value={<LevelBadge kind="reward" level={rewardLevel} name={rewardLevelName} />}
              />
              <Field
                label="Performance level"
                value={
                  <LevelBadge
                    kind="performance"
                    level={performanceLevel}
                    name={performanceLevelName}
                  />
                }
              />
              <Field label="Join amount" value={money(associate.join_amount)} />
              <Field label="Personal business" value={money(associate.personal_business)} />
              <Field label="Team business" value={money(totalBusiness ?? associate.total_business)} />
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">
              Staff account — no associate membership linked.
            </p>
          )}
        </section>
      </div>

      {/* Permissions — staff only */}
      {session.isStaff && (
        <section className="rounded-2xl border border-border bg-card p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-[color:var(--brand)]" />
                <h3 className="text-sm font-semibold">Access</h3>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {grantedCount} of {ALL_PERMISSIONS.length} permissions granted
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowDenied((v) => !v)}
            >
              {showDenied ? "Hide denied" : "Show denied"}
            </Button>
          </div>

          <div className="mt-5 space-y-5">
            {PERMISSION_GROUPS.map(([mod, perms]) => {
              const visible = showDenied ? perms : perms.filter((p) => permissions.has(p.key));
              if (visible.length === 0) return null;
              return (
                <div key={mod}>
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {mod}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {visible.map((p) => {
                      const on = permissions.has(p.key);
                      return (
                        <span
                          key={p.key}
                          className={
                            on
                              ? "inline-flex items-center gap-1 rounded-md bg-[color:var(--brand-tint)] px-2.5 py-1 text-xs font-medium text-[color:var(--brand-dark)]"
                              : "inline-flex items-center gap-1 rounded-md bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                          }
                          title={p.key}
                        >
                          {on ? <Check className="h-3 w-3" /> : null}
                          {p.action}
                        </span>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  mono,
  onCopy,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
  onCopy?: () => void;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 flex min-w-0 items-center gap-1.5 text-sm font-medium text-foreground">
        <span className={`min-w-0 truncate ${mono ? "font-mono text-xs sm:text-sm" : ""}`}>
          {value}
        </span>
        {onCopy && (
          <button
            type="button"
            onClick={onCopy}
            className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={`Copy ${label}`}
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
        )}
      </dd>
    </div>
  );
}
