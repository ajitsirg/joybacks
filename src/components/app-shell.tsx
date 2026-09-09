import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Shield } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard, FileBarChart, Users, TrendingUp, Wallet as WalletIcon, ArrowDownToLine,
  ShieldCheck, ArrowUpFromLine, Settings, KeyRound, UserCog, ScrollText, User as UserIcon,
  Trophy, LineChart, Layers, UserCheck, GitBranch, ArrowLeftRight, Network, Award, BookOpen, Percent,
} from "lucide-react";
import { useAuth, type Permission } from "@/lib/rbac";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { BrandMark } from "@/components/brand-mark";
import { TopBar } from "@/components/top-bar";
import { ConfigAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  perm?: Permission;
  badge?: number;
  /** Runtime menu key from /config/runtime/ menu object */
  menuKey?: "income_section" | "income_referral" | "income_sp_profit" | "team_approvals";
  /** Staff always; associates only if Django Admin enables the matching toggle */
  requireAdminHistory?: boolean;
  requireRewardAchievers?: boolean;
  /** Visible only to Django superusers */
  requireSuperuser?: boolean;
  /** Visible only to Django staff / superuser */
  requireStaff?: boolean;
  /** Visible only to associates (hidden from staff) */
  requireAssociate?: boolean;
};
type NavGroup = { label: string; items: NavItem[] };

type MenuFlags = {
  show_income_section: boolean;
  show_income_referral: boolean;
  show_income_sp_profit: boolean;
  show_team_approvals: boolean;
};

const DEFAULT_MENU: MenuFlags = {
  show_income_section: false,
  show_income_referral: false,
  show_income_sp_profit: false,
  show_team_approvals: false,
};

const NAV: NavGroup[] = [
  { label: "Overview", items: [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/knowledge", label: "Knowledge Center", icon: BookOpen },
    { to: "/team/approvals", label: "Team Approvals", icon: UserCheck, menuKey: "team_approvals" },
    { to: "/business-report", label: "Business Report", icon: FileBarChart, perm: "reports.view" },
    { to: "/genealogy", label: "Associate Tree", icon: Layers },
    {
      to: "/genealogy/shift",
      label: "Shift Associate",
      icon: GitBranch,
      // Visible to admin staff (API also allows is_staff / is_superuser)
      requireStaff: true,
    },
  ]},
  { label: "My Team", items: [
    { to: "/users/team", label: "All Team Member", icon: Users, perm: "users.view" },
    { to: "/users/my", label: "My Associates", icon: Network, perm: "users.view" },
  ]},
  { label: "Users", items: [
    // Staff: everyone. Associates use My Team / My Associates instead.
    { to: "/users/all", label: "All Associates", icon: Users, perm: "users.view", requireStaff: true },
    { to: "/users/active", label: "Active Users", icon: UserCheck, perm: "users.view", requireStaff: true },
    { to: "/users/inactive", label: "In-Active Users", icon: Users, perm: "users.view", requireStaff: true },
    { to: "/users/blocked", label: "Block Users", icon: Users, perm: "users.view", requireStaff: true },
    { to: "/users/levels", label: "By Level (Admin)", icon: Layers, perm: "users.view", requireStaff: true },
    {
      to: "/users/rewards",
      label: "Reward Achievers",
      icon: Trophy,
      perm: "users.view",
      requireRewardAchievers: true,
    },
  ]},
  { label: "Income", items: [
    { to: "/income/referral", label: "Referral Income", icon: TrendingUp, perm: "income.view", menuKey: "income_referral" },
    { to: "/income/sp-profit", label: "S.P. Profit", icon: TrendingUp, perm: "income.view", menuKey: "income_sp_profit", requireStaff: true },
    { to: "/income/roi", label: "ROI Level Income", icon: TrendingUp, perm: "income.view", menuKey: "income_section" },
    { to: "/income/reward", label: "Reward Income", icon: Award, perm: "income.view", menuKey: "income_section", requireAssociate: true },
    { to: "/income/admin-charges", label: "Admin Charges", icon: Percent, perm: "income.view", requireStaff: true },
  ]},
  { label: "Fund", items: [
    { to: "/fund/wallets", label: "Wallets", icon: WalletIcon, perm: "fund.view" },
    { to: "/fund/transfer", label: "Fund Transfer", icon: ArrowLeftRight, perm: "fund.view", requireStaff: true },
    { to: "/fund/transfer", label: "Request Fund Transfer", icon: ArrowLeftRight, perm: "fund.view", requireAssociate: true },
    { to: "/fund/user-history", label: "Users History", icon: LineChart, perm: "fund.view" },
    {
      to: "/fund/admin-history",
      label: "Admin History",
      icon: LineChart,
      perm: "fund.view",
      requireAdminHistory: true,
    },
  ]},
  { label: "Deposit", items: [
    { to: "/deposit/pending", label: "Pending Deposit", icon: ArrowDownToLine, perm: "deposit.view" },
    { to: "/deposit/complete", label: "Complete Deposit", icon: ArrowDownToLine, perm: "deposit.view" },
    { to: "/deposit/rejected", label: "Rejected Deposit", icon: ArrowDownToLine, perm: "deposit.view" },
  ]},
  { label: "KYC", items: [
    { to: "/kyc/approved", label: "Approved KYC", icon: ShieldCheck, perm: "kyc.view" },
    { to: "/kyc/pending", label: "Pending KYC", icon: ShieldCheck, perm: "kyc.view" },
    { to: "/kyc/rejected", label: "Rejected KYC", icon: ShieldCheck, perm: "kyc.view" },
  ]},
  { label: "Withdrawal", items: [
    { to: "/withdraw/pending", label: "Pending Withdraw", icon: ArrowUpFromLine, perm: "withdrawal.view" },
    { to: "/withdraw/completed", label: "Completed Withdraw", icon: ArrowUpFromLine, perm: "withdrawal.view" },
    { to: "/withdraw/rejected", label: "Rejected Withdraw", icon: ArrowUpFromLine, perm: "withdrawal.view" },
  ]},
  { label: "Plans", items: [
    { to: "/plans/direct", label: "Direct 5-Level Income", icon: Layers },
    { to: "/plans/performance", label: "Performance Levels", icon: Layers },
    { to: "/plans/rewards", label: "Reward Achievement", icon: Trophy },
  ]},
  { label: "Settings", items: [
    { to: "/settings/qr-wallet", label: "QR & Wallet", icon: Settings, perm: "settings.manage" },
    { to: "/settings/news", label: "News", icon: Settings, perm: "settings.manage" },
    { to: "/settings/help", label: "Help Center", icon: Settings, perm: "settings.manage" },
  ]},
  { label: "Administration", items: [
    { to: "/rbac/roles", label: "Role Management", icon: KeyRound, perm: "rbac.manage" },
    { to: "/rbac/staff", label: "Staff Management", icon: UserCog, perm: "staff.manage" },
    { to: "/rbac/audit", label: "Audit Log", icon: ScrollText, perm: "audit.view" },
    { to: "/rbac/profile", label: "My Profile", icon: UserIcon },
  ]},
];

function menuAllows(item: NavItem, menu: MenuFlags): boolean {
  if (item.menuKey === "income_section") return menu.show_income_section;
  if (item.menuKey === "income_referral") return menu.show_income_referral;
  if (item.menuKey === "income_sp_profit") return menu.show_income_sp_profit;
  if (item.menuKey === "team_approvals") return menu.show_team_approvals;
  return true;
}

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

function SidebarNav({
  pathname,
  can,
  menu,
  canViewAdminHistory,
  canViewRewardAchievers,
  isSuperuser,
  isStaff,
  onNavigate,
}: {
  pathname: string;
  can: (p: Permission) => boolean;
  menu: MenuFlags;
  canViewAdminHistory: boolean;
  canViewRewardAchievers: boolean;
  isSuperuser: boolean;
  isStaff: boolean;
  onNavigate?: () => void;
}) {
  const allNavItems = NAV.flatMap((g) => g.items);

  return (
    <nav className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-6">
      {NAV.map((group) => {
        const visible = group.items.filter(
          (it) =>
            (!it.perm || can(it.perm)) &&
            menuAllows(it, menu) &&
            (!it.requireAdminHistory || canViewAdminHistory) &&
            (!it.requireRewardAchievers || canViewRewardAchievers) &&
            (!it.requireSuperuser || isSuperuser) &&
            (!it.requireStaff || isStaff || isSuperuser) &&
            (!it.requireAssociate || (!isStaff && !isSuperuser)),
        );
        if (visible.length === 0) return null;
        return (
          <div key={group.label} className="mb-4">
            <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
              {group.label}
            </div>
            <div className="flex flex-col gap-0.5">
              {visible.map((it) => {
                // Exact match, or prefix — but not when a more-specific sibling owns the path
                // (e.g. /genealogy should not stay active on /genealogy/shift).
                const siblingOwns =
                  pathname !== it.to &&
                  allNavItems.some(
                    (other) =>
                      other.to !== it.to &&
                      (pathname === other.to || pathname.startsWith(`${other.to}/`)),
                  );
                const active =
                  pathname === it.to ||
                  (pathname.startsWith(`${it.to}/`) && !siblingOwns);
                return (
                  <Link
                    key={it.to}
                    to={it.to}
                    onClick={onNavigate}
                    className={cn(
                      "group flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors",
                      active
                        ? "bg-[color:var(--brand)] text-white shadow-sm"
                        : "text-[color:var(--foreground)] hover:bg-[color:var(--sidebar-accent)] hover:text-[color:var(--brand-dark)]",
                    )}
                  >
                    <it.icon className={cn("h-4 w-4 shrink-0", active ? "text-white" : "text-[color:var(--brand)]/70")} />
                    <span className="flex-1 truncate">{it.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        );
      })}
    </nav>
  );
}

function BrandBlock() {
  return (
    <div className="flex shrink-0 items-center gap-2 px-5 py-5">
      <BrandMark className="h-10 w-10" />
      <div className="min-w-0">
        <div className="truncate text-base font-semibold leading-tight text-[color:var(--brand-dark)]">JoyClub Associate</div>
        <div className="text-[10px] uppercase tracking-widest text-[color:var(--muted-foreground)]">Associate Portal</div>
      </div>
    </div>
  );
}

export function AppShell() {
  const { session, roles, can, hydrated } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menu, setMenu] = useState<MenuFlags>(DEFAULT_MENU);
  const [menuReady, setMenuReady] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    ConfigAPI.runtime()
      .then((d) => {
        const m = (d.menu as Partial<MenuFlags> | undefined) ?? {};
        const joinFlow = (d.join_flow as { require_leader_approval?: boolean } | undefined) ?? {};
        setMenu({
          show_income_section: !!m.show_income_section,
          show_income_referral: !!m.show_income_referral,
          show_income_sp_profit: !!m.show_income_sp_profit,
          show_team_approvals: !!(m.show_team_approvals ?? joinFlow.require_leader_approval),
        });
      })
      .catch(() => setMenu(DEFAULT_MENU))
      .finally(() => setMenuReady(true));
  }, []);

  const canViewAdminHistory = !!(session?.isStaff || session?.canViewAdminHistory);
  const canViewRewardAchievers = !!(session?.isStaff || session?.canViewRewardAchievers);
  const isSuperuser = !!session?.isSuperuser;
  const isStaff = !!(session?.isStaff || session?.isSuperuser);

  const blockedPath = useMemo(() => {
    if (pathname.startsWith("/team/approvals") && !menu.show_team_approvals) return true;
    if (pathname.startsWith("/income/referral") && !menu.show_income_referral) return true;
    if (pathname.startsWith("/income/sp-profit") && (!menu.show_income_sp_profit || (hydrated && session && !isStaff))) {
      return true;
    }
    if (pathname.startsWith("/income/admin-charges") && hydrated && session && !isStaff) {
      return true;
    }
    if (
      (pathname.startsWith("/income/roi") || pathname.startsWith("/income/reward")) &&
      !menu.show_income_section
    ) {
      return true;
    }
    if (pathname.startsWith("/fund/admin-history") && !canViewAdminHistory) return true;
    if (pathname.startsWith("/users/rewards") && !canViewRewardAchievers) return true;
    // Wait for auth hydrate — session is null on first paint, which would
    // falsely bounce away from Shift before staff/superuser is known.
    if (pathname.startsWith("/genealogy/shift") && hydrated && session && !isStaff) {
      return true;
    }
    // Staff-only user directory pages
    if (
      hydrated &&
      session &&
      !isStaff &&
      (pathname.startsWith("/users/all") ||
        pathname.startsWith("/users/active") ||
        pathname.startsWith("/users/inactive") ||
        pathname.startsWith("/users/blocked"))
    ) {
      return true;
    }
    return false;
  }, [pathname, menu, canViewAdminHistory, canViewRewardAchievers, isStaff, hydrated, session]);

  useEffect(() => {
    if (menuReady && blockedPath) {
      void navigate({ to: "/dashboard" });
    }
  }, [menuReady, blockedPath, navigate]);

  if (!hydrated || !session) return null;

  const activeRoles = roles.filter((r) => session.roleIds.includes(r.id));
  const primaryRole = activeRoles[0]?.name ?? "Staff";

  const profileCard = (
    <div className="mx-4 mb-3 shrink-0 rounded-xl border border-[color:var(--sidebar-border)] bg-[color:var(--sidebar-accent)] p-3">
      <div className="flex items-center gap-3">
        <Avatar key={session.photoUrl || "no-photo"} className="h-9 w-9 rounded-lg">
          {session.photoUrl ? (
            <img
              src={session.photoUrl}
              alt={session.name}
              className="aspect-square h-full w-full object-cover"
            />
          ) : (
            <AvatarFallback className="rounded-lg bg-[color:var(--brand)] text-white text-xs">
              {initials(session.name)}
            </AvatarFallback>
          )}
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-[color:var(--brand-dark)]">{session.name}</div>
          <div className="truncate text-xs text-[color:var(--muted-foreground)]">{session.email || session.id}</div>
        </div>
      </div>
      <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-[color:var(--brand-tint)] px-2 py-0.5 text-[10px] font-medium text-[color:var(--brand-dark)]">
        <Shield className="h-3 w-3" /> {primaryRole}
      </div>
    </div>
  );

  const navProps = {
    pathname,
    can,
    menu,
    canViewAdminHistory,
    canViewRewardAchievers,
    isSuperuser,
    isStaff,
  };

  return (
    <div className="flex min-h-dvh w-full max-w-[100vw] overflow-x-hidden bg-background">
      <aside className="sticky top-0 z-20 hidden h-dvh w-64 shrink-0 flex-col overflow-hidden border-r border-[color:var(--sidebar-border)] bg-[color:var(--sidebar)] md:flex">
        <BrandBlock />
        {profileCard}
        <SidebarNav {...navProps} />
      </aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          side="left"
          className="flex w-[min(100vw-2rem,20rem)] flex-col gap-0 overflow-hidden border-[color:var(--sidebar-border)] bg-[color:var(--sidebar)] p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <BrandBlock />
          {profileCard}
          <SidebarNav {...navProps} onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          onOpenMenu={() => setMobileOpen(true)}
          primaryRole={primaryRole}
          showTeamApprovals={menu.show_team_approvals}
        />

        <main className="min-w-0 flex-1 overflow-x-hidden p-3 sm:p-5 lg:p-6">
          {blockedPath ? (
            <div className="rounded-xl border border-dashed p-8 text-sm text-muted-foreground">
              This page is currently disabled by admin.
            </div>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  );
}

export { PageHeader } from "@/components/page-header";
