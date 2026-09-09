/**
 * JoyClub Associate — production API client (Django + JWT).
 */

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "joyclub.tokens.v1";

/** Turn relative /media/… paths into absolute URLs (API host or current origin). */
export function resolveMediaUrl(url?: string | null): string | null {
  if (!url) return null;
  if (/^(https?:|blob:|data:)/i.test(url)) return url;
  try {
    if (/^https?:/i.test(API_BASE)) {
      return new URL(url, new URL(API_BASE).origin).href;
    }
  } catch {
    /* fall through */
  }
  if (typeof window !== "undefined") {
    try {
      return new URL(url, window.location.origin).href;
    } catch {
      /* fall through */
    }
  }
  return url;
}

export type TokenPair = { access: string; refresh: string };

export type ApiAssociate = {
  associate_id: string;
  username?: string;
  mobile: string;
  referral_code?: string;
  card_tier: string;
  flag_color: string;
  join_amount: string;
  personal_business?: string;
  total_business?: string;
  earning_level?: number;
  earning_level_name?: string;
  reward_level?: number;
  reward_level_name?: string;
  performance_level?: number;
  performance_level_name?: string;
  lead_reference: string;
  status: string;
  kyc_verified?: boolean;
  can_view_admin_history?: boolean;
  can_view_reward_achievers?: boolean;
  can_fund_transfer?: boolean;
  rejection_reason?: string;
  waiting_message?: string;
  profile_photo_url?: string | null;
};

export type ApiUser = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  phone?: string;
  user_type: string;
  is_staff: boolean;
  is_superuser: boolean;
  last_login?: string | null;
  last_login_ip?: string | null;
  permissions: string[];
  roles: string[];
  associate?: ApiAssociate | null;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export function getTokens(): TokenPair | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    return null;
  }
}

export function setTokens(tokens: TokenPair | null) {
  if (!tokens) localStorage.removeItem(TOKEN_KEY);
  else localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

async function refreshAccess(): Promise<string | null> {
  const tokens = getTokens();
  if (!tokens?.refresh) return null;
  const res = await fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });
  if (!res.ok) {
    setTokens(null);
    return null;
  }
  const data = await res.json();
  setTokens({ access: data.access, refresh: data.refresh ?? tokens.refresh });
  return data.access as string;
}

function formatApiErrorBody(status: number, body: unknown): string {
  if (typeof body === "string" && body.trim()) return body;
  if (!body || typeof body !== "object") return `API ${status}`;
  const obj = body as Record<string, unknown>;
  if ("detail" in obj) {
    const d = obj.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map(String).join(" · ");
  }
  const parts: string[] = [];
  for (const [key, val] of Object.entries(obj)) {
    if (key === "detail") continue;
    if (Array.isArray(val)) parts.push(`${key}: ${val.map(String).join(", ")}`);
    else if (typeof val === "string") parts.push(`${key}: ${val}`);
    else if (val != null) parts.push(`${key}: ${String(val)}`);
  }
  return parts.length ? parts.join(" · ") : `API ${status}`;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(formatApiErrorBody(status, body));
    this.status = status;
    this.body = body;
  }
}

export async function api<T>(path: string, options: RequestInit & { auth?: boolean } = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (options.auth !== false) {
    let access = getTokens()?.access;
    if (!access) access = (await refreshAccess()) ?? undefined;
    if (access) headers.set("Authorization", `Bearer ${access}`);
  }

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401 && options.auth !== false) {
    const next = await refreshAccess();
    if (next) {
      headers.set("Authorization", `Bearer ${next}`);
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

function qs(params?: Record<string, string | number | undefined>) {
  if (!params) return "";
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const AuthAPI = {
  login: (email: string, password: string, remember_me = true) =>
    api<{ access: string; refresh: string; user: ApiUser }>("/auth/login/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password, remember_me }),
    }),
  loginPayload: (payload: Record<string, unknown>) =>
    api<{ access: string; refresh: string; user: ApiUser }>("/auth/login/", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    }),
  me: () => api<ApiUser>("/auth/me/"),
  /** Staff only — login as an associate (returns new JWT pair). */
  impersonate: (associateId: string) =>
    api<{ access: string; refresh: string; user: ApiUser }>("/auth/impersonate/", {
      method: "POST",
      body: JSON.stringify({ associate_id: associateId }),
    }),
  logoutLocal: () => setTokens(null),
};

export const DashboardAPI = {
  admin: () => api<Record<string, unknown>>("/dashboard/admin/"),
  businessReport: () => api<{ results: Record<string, unknown>[]; count: number }>("/dashboard/business-report/"),
};

export const AssociatesAPI = {
  list: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/associates/${qs(params)}`),
  levelSummary: (kind: "tree" | "leg" | "reward" | "performance" = "tree") =>
    api<{ kind: string; results: { level: number; name: string; count: number }[] }>(
      `/associates/level-summary/${qs({ kind })}`,
    ),
  get: (associateId: string) =>
    api<Record<string, unknown>>(`/associates/${encodeURIComponent(associateId)}/`),
  update: (associateId: string, body: FormData | Record<string, unknown>) =>
    api<Record<string, unknown>>(`/associates/${encodeURIComponent(associateId)}/`, {
      method: "PATCH",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  registerOtp: (mobile: string) =>
    api<{ detail: string; debug_otp?: string }>("/associates/register/otp/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ mobile }),
    }),
  register: (form: FormData) =>
    api<Record<string, unknown>>("/associates/register/", {
      method: "POST",
      auth: false,
      body: form,
    }),
  joinPreview: (join_amount: number) =>
    api<Record<string, unknown>>("/associates/join-preview/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ join_amount }),
    }),
  activate: (associateId: string) =>
    api(`/associates/${associateId}/activate/`, { method: "POST" }),
  pendingJoins: () =>
    api<{ count: number; results: Record<string, unknown>[] }>("/associates/pending-joins/"),
  leaderApprove: (associateId: string) =>
    api<Record<string, unknown>>(`/associates/${associateId}/leader-approve/`, { method: "POST" }),
  leaderReject: (associateId: string, reason = "") =>
    api<Record<string, unknown>>(`/associates/${associateId}/leader-reject/`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  rewardProgress: () => api<Record<string, unknown>>("/associates/reward-progress/"),
  assignRewardLegs: (body: { auto?: boolean; legs?: string[]; leg1?: string; leg2?: string; leg3?: string }) =>
    api<Record<string, unknown>>("/associates/reward-legs/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const GenealogyAPI = {
  tree: (associateId?: string) =>
    api<{
      node: Record<string, unknown>;
      children: Record<string, unknown>[];
      scoped_to?: string | null;
      is_company_root?: boolean;
    }>(
      associateId
        ? `/genealogy/tree/?associate_id=${encodeURIComponent(associateId)}`
        : `/genealogy/tree/`,
    ),
  /** Staff only — company top root(s) for full-network tree. */
  roots: () =>
    api<{ count: number; results: Record<string, unknown>[] }>("/genealogy/roots/"),
  search: (q: string) => api<Record<string, unknown>[]>(`/genealogy/search/?q=${encodeURIComponent(q)}`),
  upline: (associateId: string) =>
    api<{ depth: number; associate: Record<string, unknown> }[]>(`/genealogy/upline/${associateId}/`),
  /** Staff / super-admin — move associate (+ full leg) under a new sponsor. */
  shift: (associateId: string, newSponsorId: string) =>
    api<{
      detail: string;
      associate_id: string;
      old_sponsor_id: string | null;
      new_sponsor_id: string;
      moved_count: number;
      subtree_ids: string[];
    }>("/genealogy/shift/", {
      method: "POST",
      body: JSON.stringify({ associate_id: associateId, new_sponsor_id: newSponsorId }),
    }),
};

export const OpsAPI = {
  kyc: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/ops/kyc/${qs(params)}`),
  approveKyc: (id: string) => api(`/ops/kyc/${id}/approve/`, { method: "POST" }),
  rejectKyc: (id: string, reason = "") =>
    api(`/ops/kyc/${id}/reject/`, { method: "POST", body: JSON.stringify({ reason }) }),
  deposits: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/ops/deposits/${qs(params)}`),
  approveDeposit: (id: string) => api(`/ops/deposits/${id}/approve/`, { method: "POST" }),
  rejectDeposit: (id: string, reason = "") =>
    api(`/ops/deposits/${id}/reject/`, { method: "POST", body: JSON.stringify({ reason }) }),
  withdrawals: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/ops/withdrawals/${qs(params)}`),
  approveWithdrawal: (id: string) => api(`/ops/withdrawals/${id}/approve/`, { method: "POST" }),
  rejectWithdrawal: (id: string, reason = "") =>
    api(`/ops/withdrawals/${id}/reject/`, { method: "POST", body: JSON.stringify({ reason }) }),
};

export const WalletsAPI = {
  list: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>> | Record<string, unknown>[]>(`/wallets/${qs(params)}`),
  ledger: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/wallets/ledger/${qs(params)}`),
  packages: () =>
    api<{
      packages: { amount: string; label: string; amount_number: number }[];
      payment_methods?: { code: string; label: string }[];
      recipients?: {
        associate_id: string;
        name: string;
        is_self: boolean;
        status?: string;
      }[];
      can_fund_transfer: boolean;
      can_request_fund_transfer?: boolean;
      associate_id: string | null;
      main_balance: string | null;
      personal_balance?: string | null;
      personal_business?: string | null;
      min_package?: string;
    }>("/wallets/transfer/packages/"),
  transfer: (payload: {
    associate_id: string;
    from_associate_id?: string;
    company_mint?: boolean;
    wallet_type?: string;
    amount: number;
    narration?: string;
    apply_business?: boolean;
    payment_method: string;
  }) => api("/wallets/transfer/", { method: "POST", body: JSON.stringify(payload) }),
  transferRequests: (params?: Record<string, string | number | undefined>) =>
    api<
      Paginated<{
        id: string;
        requester_associate_id: string;
        requester_name: string;
        beneficiary_associate_id: string;
        beneficiary_name: string;
        amount: string;
        amount_label: string;
        wallet_type: string;
        payment_method: string;
        payment_method_label: string;
        utr: string;
        proof_url: string | null;
        note: string;
        status: string;
        rejection_reason: string;
        reviewed_by_email: string;
        reviewed_at: string | null;
        created_at: string;
      }>
    >(`/wallets/transfer/requests/${qs(params)}`),
  requestTransfer: (payload: {
    associate_id: string;
    amount: number;
    payment_method: string;
    note?: string;
    utr: string;
    proof: File;
  }) => {
    const fd = new FormData();
    fd.append("associate_id", payload.associate_id);
    fd.append("amount", String(payload.amount));
    fd.append("payment_method", payload.payment_method);
    if (payload.note) fd.append("note", payload.note);
    fd.append("utr", payload.utr);
    fd.append("proof", payload.proof);
    return api("/wallets/transfer/requests/", { method: "POST", body: fd });
  },
  approveTransferRequest: (id: string, applyBusiness = true, password: string) =>
    api(`/wallets/transfer/requests/${id}/approve/`, {
      method: "POST",
      body: JSON.stringify({ apply_business: applyBusiness, password }),
    }),
  rejectTransferRequest: (id: string, reason = "") =>
    api(`/wallets/transfer/requests/${id}/reject/`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};

export const ConfigAPI = {
  runtime: () => api<Record<string, unknown>>("/config/runtime/", { auth: false }),
};

export type ApiStaffRole = {
  id: string;
  name: string;
  description?: string;
  is_system?: boolean;
  permissions?: { id: string; code: string; name: string; module: string }[];
};

export type ApiStaff = {
  id: string;
  employee_code: string;
  email: string;
  first_name?: string;
  last_name?: string;
  name: string;
  department?: string;
  is_suspended: boolean;
  is_active?: boolean;
  roles: ApiStaffRole[];
  role_ids?: string[];
  last_login_at?: string | null;
  last_login_ip?: string | null;
  created_at?: string;
};

export const StaffAPI = {
  list: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<ApiStaff> | ApiStaff[]>(`/auth/staff/${qs(params)}`),
  get: (id: string) => api<ApiStaff>(`/auth/staff/${encodeURIComponent(id)}/`),
  create: (body: Record<string, unknown>) =>
    api<ApiStaff>("/auth/staff/", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: Record<string, unknown>) =>
    api<ApiStaff>(`/auth/staff/${encodeURIComponent(id)}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};

export const RolesAPI = {
  list: () => api<Paginated<ApiStaffRole> | ApiStaffRole[]>("/auth/roles/"),
};

export const CommissionsAPI = {
  entries: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/commissions/entries/${qs(params)}`),
  runs: () => api<Paginated<Record<string, unknown>>>("/commissions/runs/"),
  adminCharges: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/commissions/admin-charges/${qs(params)}`),
};

export type LandingBenefit = {
  id: string;
  title: string;
  body: string;
  icon_key: string;
  sort_order: number;
};

export type LandingGalleryItem = {
  id: string;
  title: string;
  image_url: string | null;
  sort_order: number;
};

export type LandingPageSettings = {
  eyebrow: string;
  headline: string;
  intro: string;
  investment_label: string;
  investment_value: string;
  income_banner: string;
  cta_title: string;
  cta_body: string;
  slogan: string;
  phone: string;
  email: string;
  website: string;
  address: string;
  banner_image_url: string | null;
  is_active: boolean;
};

export type LandingPagePayload = {
  active: boolean;
  settings?: LandingPageSettings;
  benefits?: LandingBenefit[];
  gallery?: LandingGalleryItem[];
};

export const CmsAPI = {
  news: () => api<Paginated<Record<string, unknown>> | Record<string, unknown>[]>("/cms/news/"),
  help: () => api<Paginated<Record<string, unknown>> | Record<string, unknown>[]>("/cms/help/"),
  qr: () => api<Paginated<Record<string, unknown>> | Record<string, unknown>[]>("/cms/qr-wallets/"),
  landing: () => api<LandingPagePayload>("/cms/landing/", { auth: false }),
  knowledge: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>> | Record<string, unknown>[]>(`/cms/knowledge/${qs(params)}`),
  createKnowledge: (form: FormData) =>
    api<Record<string, unknown>>("/cms/knowledge/", { method: "POST", body: form }),
  deleteKnowledge: (id: string) =>
    api(`/cms/knowledge/${id}/`, { method: "DELETE" }),
};

export const NotificationsAPI = {
  list: (params?: Record<string, string | number | undefined>) =>
    api<Paginated<Record<string, unknown>>>(`/notifications/${qs(params)}`),
  read: (id: string) => api(`/notifications/${id}/read/`, { method: "POST" }),
  readAll: () => api("/notifications/read_all/", { method: "POST" }),
};

export function unwrapList<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results ?? [];
}
