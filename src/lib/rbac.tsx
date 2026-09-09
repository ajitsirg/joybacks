import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { AuthAPI, resolveMediaUrl, setTokens, type ApiUser } from "@/lib/api";

export type Permission =
  | "users.view" | "users.edit" | "users.block"
  | "withdrawal.view" | "withdrawal.approve" | "withdrawal.reject"
  | "deposit.view" | "deposit.approve" | "deposit.reject"
  | "fund.view" | "fund.transfer"
  | "kyc.view" | "kyc.approve" | "kyc.reject"
  | "income.view" | "income.adjust"
  | "reports.view" | "reports.export"
  | "settings.manage"
  | "rbac.manage" | "staff.manage" | "audit.view";

export const ALL_PERMISSIONS: { key: Permission; module: string; action: string }[] = [
  { key: "users.view", module: "Users", action: "View" },
  { key: "users.edit", module: "Users", action: "Edit" },
  { key: "users.block", module: "Users", action: "Block" },
  { key: "withdrawal.view", module: "Withdrawal", action: "View" },
  { key: "withdrawal.approve", module: "Withdrawal", action: "Approve" },
  { key: "withdrawal.reject", module: "Withdrawal", action: "Reject" },
  { key: "deposit.view", module: "Deposit", action: "View" },
  { key: "deposit.approve", module: "Deposit", action: "Approve" },
  { key: "deposit.reject", module: "Deposit", action: "Reject" },
  { key: "fund.view", module: "Fund", action: "View" },
  { key: "fund.transfer", module: "Fund", action: "Transfer" },
  { key: "kyc.view", module: "KYC", action: "View" },
  { key: "kyc.approve", module: "KYC", action: "Approve" },
  { key: "kyc.reject", module: "KYC", action: "Reject" },
  { key: "income.view", module: "Income", action: "View" },
  { key: "income.adjust", module: "Income", action: "Adjust" },
  { key: "reports.view", module: "Reports", action: "View" },
  { key: "reports.export", module: "Reports", action: "Export" },
  { key: "settings.manage", module: "Settings", action: "Manage" },
  { key: "rbac.manage", module: "RBAC", action: "Manage Roles" },
  { key: "staff.manage", module: "RBAC", action: "Manage Staff" },
  { key: "audit.view", module: "RBAC", action: "View Audit" },
];

export type Role = {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  system?: boolean;
};

export const DEFAULT_ROLES: Role[] = [
  { id: "super_admin", name: "Super Admin", description: "Full access to every module and setting.", permissions: ALL_PERMISSIONS.map(p => p.key), system: true },
  { id: "admin", name: "Admin", description: "Operational admin — most modules, no RBAC changes.", permissions: ALL_PERMISSIONS.map(p => p.key).filter(p => !p.startsWith("rbac") && p !== "staff.manage"), system: true },
  { id: "finance", name: "Finance Manager", description: "Handles money movement, withdrawals and deposits.", permissions: ["users.view","withdrawal.view","withdrawal.approve","withdrawal.reject","deposit.view","deposit.approve","deposit.reject","fund.view","fund.transfer","income.view","reports.view","reports.export"], system: true },
  { id: "kyc", name: "KYC Officer", description: "Reviews and approves KYC submissions.", permissions: ["users.view","kyc.view","kyc.approve","kyc.reject"], system: true },
  { id: "support", name: "Support Agent", description: "Answers tickets and views user data.", permissions: ["users.view","settings.manage"], system: true },
  { id: "viewer", name: "Viewer", description: "Read-only across the platform.", permissions: ["users.view","withdrawal.view","deposit.view","kyc.view","income.view","reports.view","fund.view"], system: true },
  {
    id: "associate",
    name: "Associate",
    description: "Associate portal — own downline, wallets, ops requests.",
    permissions: ["users.view", "withdrawal.view", "deposit.view", "kyc.view", "income.view", "fund.view", "fund.transfer"],
    system: true,
  },
];

export type Staff = {
  id: string;
  name: string;
  email: string;
  password: string;
  roleIds: string[];
  status: "active" | "suspended";
  lastLoginAt?: string;
  lastLoginIp?: string;
  createdAt: string;
  username?: string;
  associateId?: string;
  associateStatus?: string;
  waitingMessage?: string;
  isStaff?: boolean;
  /** Django is_superuser — required for tree shift power */
  isSuperuser?: boolean;
  /** Django Admin → Associate → can_view_admin_history */
  canViewAdminHistory?: boolean;
  /** Django Admin → Associate → can_view_reward_achievers */
  canViewRewardAchievers?: boolean;
  /** Staff-only: execute fund transfer. Associates request instead. */
  canFundTransfer?: boolean;
  /** Latest KYC profile photo (cache-busted URL from /me) */
  photoUrl?: string | null;
};

const DEFAULT_STAFF: Staff[] = [
  { id: "u_1", name: "Aarav Mehta", email: "super@atmpay.io", password: "admin123", roleIds: ["super_admin"], status: "active", lastLoginAt: new Date().toISOString(), lastLoginIp: "10.0.0.1", createdAt: "2025-01-04" },
  { id: "u_2", name: "Priya Shah", email: "finance@atmpay.io", password: "admin123", roleIds: ["finance"], status: "active", lastLoginAt: new Date(Date.now()-86400000).toISOString(), lastLoginIp: "10.0.0.3", createdAt: "2025-02-11" },
  { id: "u_3", name: "Rohit Verma", email: "kyc@atmpay.io", password: "admin123", roleIds: ["kyc"], status: "active", lastLoginAt: new Date(Date.now()-3600_000).toISOString(), lastLoginIp: "10.0.0.5", createdAt: "2025-03-20" },
  { id: "u_4", name: "Neha Kapoor", email: "support@atmpay.io", password: "admin123", roleIds: ["support"], status: "active", createdAt: "2025-04-02" },
  { id: "u_5", name: "Kabir Singh", email: "viewer@atmpay.io", password: "admin123", roleIds: ["viewer"], status: "suspended", createdAt: "2025-05-14" },
];

export type AuditEntry = {
  id: string;
  actor: string;
  action: string;
  target?: string;
  before?: string;
  after?: string;
  ip: string;
  at: string;
};

type StoreShape = {
  roles: Role[];
  staff: Staff[];
  audit: AuditEntry[];
};

const API_ROLE_IDS: Record<string, string> = {
  "super admin": "super_admin",
  admin: "admin",
  "finance manager": "finance",
  finance: "finance",
  "kyc officer": "kyc",
  kyc: "kyc",
  "support agent": "support",
  support: "support",
  viewer: "viewer",
  associate: "associate",
};

function apiRoleIds(user: ApiUser): string[] {
  const mapped = (user.roles ?? [])
    .map((name) => API_ROLE_IDS[String(name).toLowerCase()] || String(name).toLowerCase().replace(/\s+/g, "_"))
    .filter(Boolean);
  if (mapped.length) return mapped;
  if (user.is_superuser) return ["super_admin"];
  if (user.is_staff) return ["admin"];
  if (user.associate) return ["associate"];
  return ["viewer"];
}

const KEY = "atmpay.rbac.v1";
function loadStore(): StoreShape {
  if (typeof window === "undefined") return { roles: DEFAULT_ROLES, staff: DEFAULT_STAFF, audit: [] };
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as StoreShape;
      // Ensure system roles (incl. associate) always exist
      const byId = new Map(parsed.roles?.map((r) => [r.id, r]));
      for (const role of DEFAULT_ROLES) byId.set(role.id, role);
      return {
        roles: [...byId.values()],
        staff: parsed.staff?.length ? parsed.staff : DEFAULT_STAFF,
        audit: parsed.audit ?? [],
      };
    }
  } catch {}
  return { roles: DEFAULT_ROLES, staff: DEFAULT_STAFF, audit: [] };
}
function saveStore(s: StoreShape) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(s));
}

type AuthCtx = {
  session: Staff | null;
  hydrated: boolean;
  roles: Role[];
  staff: Staff[];
  audit: AuditEntry[];
  permissions: Set<Permission>;
  can: (p: Permission) => boolean;
  login: (email: string, password: string) => { ok: boolean; error?: string };
  loginWithApi: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  applyApiUser: (user: ApiUser) => void;
  logout: () => void;
  updateRoles: (roles: Role[]) => void;
  updateStaff: (staff: Staff[]) => void;
  logAudit: (entry: Omit<AuditEntry, "id" | "at" | "actor" | "ip">) => void;
};

const Ctx = createContext<AuthCtx | null>(null);
const SESSION_KEY = "atmpay.session.v1";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [store, setStore] = useState<StoreShape>({ roles: DEFAULT_ROLES, staff: DEFAULT_STAFF, audit: [] });
  const [session, setSession] = useState<Staff | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setStore(loadStore());
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    saveStore(store);
  }, [store, hydrated]);
  useEffect(() => {
    if (!hydrated || typeof window === "undefined") return;
    if (session) window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else window.localStorage.removeItem(SESSION_KEY);
  }, [session, hydrated]);

  const permissions = useMemo(() => {
    if (!session) return new Set<Permission>();
    const set = new Set<Permission>();
    for (const rid of session.roleIds) {
      const role = store.roles.find(r => r.id === rid);
      if (role) role.permissions.forEach(p => set.add(p));
    }
    return set;
  }, [session, store.roles]);

  const can = useCallback((p: Permission) => permissions.has(p), [permissions]);

  const applyApiUser = useCallback((user: ApiUser) => {
    const isStaff = !!(user.is_superuser || user.is_staff);
    const roleIds = apiRoleIds(user);
    const apiPerms = user.permissions ?? [];
    const canFundTransfer = !!(
      user.is_superuser ||
      (isStaff &&
        (apiPerms.includes("fund.transfer") ||
          apiPerms.includes("wallets.transfer") ||
          roleIds.some((id) => ["finance", "admin", "super_admin"].includes(id))))
    );
    const staffUser: Staff = {
      id: `api_${user.id}`,
      name: [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username || user.email,
      email: user.email,
      password: "",
      roleIds,
      status: "active",
      lastLoginAt: user.last_login || new Date().toISOString(),
      lastLoginIp: user.last_login_ip || undefined,
      createdAt: new Date().toISOString().slice(0, 10),
      username: user.username,
      associateId: user.associate?.associate_id,
      associateStatus: user.associate?.status,
      waitingMessage: user.associate?.waiting_message,
      isStaff,
      isSuperuser: !!user.is_superuser,
      canViewAdminHistory: isStaff || !!user.associate?.can_view_admin_history,
      canViewRewardAchievers: isStaff || !!user.associate?.can_view_reward_achievers,
      canFundTransfer,
      photoUrl: resolveMediaUrl(user.associate?.profile_photo_url ?? null),
    };
    setSession(staffUser);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const { getTokens } = await import("@/lib/api");
        const tokens = getTokens();
        if (tokens?.access) {
          const me = await AuthAPI.me();
          applyApiUser(me);
        } else {
          // Drop legacy mock local sessions (e.g. Aarav Mehta)
          window.localStorage.removeItem(SESSION_KEY);
          setSession(null);
        }
      } catch {
        window.localStorage.removeItem(SESSION_KEY);
        setSession(null);
      } finally {
        setHydrated(true);
      }
    })();
  }, [applyApiUser]);

  const login = useCallback((email: string, password: string) => {
    const user = store.staff.find(s => s.email.toLowerCase() === email.toLowerCase());
    if (!user) return { ok: false, error: "No account with that email." };
    if (user.status !== "active") return { ok: false, error: "Account is suspended." };
    if (user.password !== password) return { ok: false, error: "Incorrect password." };
    const updated: Staff = { ...user, lastLoginAt: new Date().toISOString(), lastLoginIp: "127.0.0.1" };
    setStore(s => ({ ...s, staff: s.staff.map(u => u.id === updated.id ? updated : u) }));
    setSession(updated);
    return { ok: true };
  }, [store.staff]);

  const loginWithApi = useCallback(async (email: string, password: string) => {
    try {
      const result = await AuthAPI.login(email, password, true);
      setTokens({ access: result.access, refresh: result.refresh });
      applyApiUser(result.user);
      return { ok: true };
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Sign in failed";
      return { ok: false, error: msg };
    }
  }, [applyApiUser]);

  const logout = useCallback(() => {
    AuthAPI.logoutLocal();
    setSession(null);
  }, []);

  const updateRoles = useCallback((roles: Role[]) => setStore(s => ({ ...s, roles })), []);
  const updateStaff = useCallback((staff: Staff[]) => setStore(s => ({ ...s, staff })), []);

  const logAudit = useCallback((entry: Omit<AuditEntry, "id" | "at" | "actor" | "ip">) => {
    setStore(s => ({
      ...s,
      audit: [
        { id: crypto.randomUUID(), at: new Date().toISOString(), actor: session?.name ?? "system", ip: "127.0.0.1", ...entry },
        ...s.audit,
      ].slice(0, 500),
    }));
  }, [session]);

  const value: AuthCtx = {
    session,
    hydrated,
    roles: store.roles,
    staff: store.staff,
    audit: store.audit,
    permissions,
    can,
    login,
    loginWithApi,
    applyApiUser,
    logout,
    updateRoles,
    updateStaff,
    logAudit,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

const EMPTY_AUTH: AuthCtx = {
  session: null,
  hydrated: false,
  roles: DEFAULT_ROLES,
  staff: DEFAULT_STAFF,
  audit: [],
  permissions: new Set(),
  can: () => false,
  login: () => ({ ok: false, error: "Auth not ready" }),
  loginWithApi: async () => ({ ok: false, error: "Auth not ready" }),
  applyApiUser: () => undefined,
  logout: () => undefined,
  updateRoles: () => undefined,
  updateStaff: () => undefined,
  logAudit: () => undefined,
};

export function useAuth() {
  // Soft fallback avoids white-screen crashes during SSR/HMR edge cases
  // where a route briefly renders outside AuthProvider.
  return useContext(Ctx) ?? EMPTY_AUTH;
}

export function usePermission(p: Permission) {
  return useAuth().can(p);
}
