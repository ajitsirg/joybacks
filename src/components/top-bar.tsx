import { Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bell,
  ChevronDown,
  Globe,
  Loader2,
  LogOut,
  Menu,
  MessageCircle,
  Search,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/rbac";
import {
  AssociatesAPI,
  ConfigAPI,
  DashboardAPI,
  GenealogyAPI,
  NotificationsAPI,
  WalletsAPI,
  unwrapList,
} from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

function initials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

type SearchHit = {
  associate_id: string;
  name?: string;
  mobile?: string;
  status?: string;
};

type Notif = {
  id: string;
  title: string;
  body: string;
  is_read: boolean;
  link?: string;
  created_at?: string;
};

export function TopBar({
  onOpenMenu,
  primaryRole,
  showTeamApprovals = false,
}: {
  onOpenMenu: () => void;
  primaryRole: string;
  showTeamApprovals?: boolean;
}) {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [walletBalance, setWalletBalance] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const [supportEmail, setSupportEmail] = useState("");
  const [supportPhone, setSupportPhone] = useState("");
  const debounceRef = useRef<number | null>(null);
  const searchBoxRef = useRef<HTMLDivElement>(null);

  const loadWallet = useCallback(async () => {
    try {
      if (session?.isStaff) {
        const dash = await DashboardAPI.admin();
        const kpis = dash.kpis as Record<string, unknown> | undefined;
        setWalletBalance(Number(kpis?.wallet_balance ?? 0));
        return;
      }
      const wallets = await WalletsAPI.list({ page_size: 50 });
      const list = unwrapList(wallets as never);
      const total = list.reduce((s, w) => s + Number((w as { balance?: string }).balance ?? 0), 0);
      setWalletBalance(total);
    } catch {
      setWalletBalance(0);
    }
  }, [session?.isStaff]);

  const loadNotifs = useCallback(async () => {
    try {
      const res = await NotificationsAPI.list({ page_size: 30 });
      setNotifs(unwrapList(res) as Notif[]);
    } catch {
      setNotifs([]);
    }
  }, []);

  useEffect(() => {
    void loadWallet();
    void loadNotifs();
    ConfigAPI.runtime()
      .then((rt) => {
        const company = rt.company as Record<string, unknown> | undefined;
        setSupportEmail(String(company?.support_email || ""));
        setSupportPhone(String(company?.support_phone || ""));
      })
      .catch(() => undefined);
    const t = window.setInterval(() => {
      void loadNotifs();
      void loadWallet();
    }, 30000);
    return () => window.clearInterval(t);
  }, [loadNotifs, loadWallet]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!searchBoxRef.current?.contains(e.target as Node)) setSearchOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    const q = query.trim();
    if (q.length < 2) {
      setHits([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    debounceRef.current = window.setTimeout(async () => {
      try {
        let results: SearchHit[] = [];
        try {
          const geo = await GenealogyAPI.search(q);
          results = (geo as SearchHit[]).map((r) => ({
            associate_id: String(r.associate_id),
            name: String(r.name ?? ""),
            mobile: String(r.mobile ?? ""),
            status: String(r.status ?? ""),
          }));
        } catch {
          /* fall through */
        }
        if (results.length === 0) {
          const list = await AssociatesAPI.list({ search: q, page_size: 12 });
          results = unwrapList(list).map((r) => ({
            associate_id: String(r.associate_id ?? r.username ?? ""),
            name: String(r.name ?? ""),
            mobile: String(r.mobile ?? ""),
            status: String(r.status ?? ""),
          }));
        }
        setHits(results.filter((r) => r.associate_id));
        setSearchOpen(true);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Search failed");
        setHits([]);
      } finally {
        setSearching(false);
      }
    }, 280);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [query]);

  const unread = notifs.filter((n) => !n.is_read).length;

  async function openNotif(n: Notif) {
    try {
      if (!n.is_read) await NotificationsAPI.read(n.id);
    } catch {
      /* ignore */
    }
    setNotifs((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
    setNotifOpen(false);
    if (n.link) {
      try {
        await navigate({ to: n.link as never });
        return;
      } catch {
        /* fall through */
      }
    }
    if (showTeamApprovals && n.title.toLowerCase().includes("join")) {
      await navigate({ to: "/team/approvals" });
    }
  }

  async function markAllRead() {
    try {
      await NotificationsAPI.readAll();
      setNotifs((prev) => prev.map((n) => ({ ...n, is_read: true })));
      toast.success("All notifications marked read");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    }
  }

  function openHit(hit: SearchHit) {
    setSearchOpen(false);
    setQuery(hit.associate_id);
    void navigate({ to: "/genealogy", search: { focus: hit.associate_id } as never }).catch(() =>
      navigate({ to: "/genealogy" }),
    );
  }

  if (!session) return null;

  const roleLabel = session.associateId && !session.isStaff ? "Associate" : primaryRole;
  const subtitle = session.associateId || session.username || session.email;

  return (
    <header className="sticky top-0 z-20 border-b border-[color:var(--hero-border)] bg-[color:var(--hero)]/95 backdrop-blur supports-[backdrop-filter]:bg-[color:var(--hero)]/85">
      <div className="flex items-center gap-2 px-3 py-2.5 sm:gap-3 sm:px-6 sm:py-3">
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="shrink-0 rounded-xl border-[color:var(--sidebar-border)] bg-white md:hidden"
          onClick={onOpenMenu}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5 text-[color:var(--brand-dark)]" />
        </Button>

        <div className="relative min-w-0 flex-1 max-w-md" ref={searchBoxRef}>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => hits.length > 0 && setSearchOpen(true)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && hits[0]) openHit(hits[0]);
            }}
            placeholder="Search associate ID, name, mobile…"
            className="h-10 border-transparent bg-white pl-9 text-sm"
          />
          {searching && <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />}
          {searchOpen && (hits.length > 0 || query.trim().length >= 2) && (
            <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 overflow-hidden rounded-xl border border-[color:var(--hero-border)] bg-white shadow-lg">
              {hits.length === 0 ? (
                <div className="px-3 py-3 text-sm text-muted-foreground">No associates found</div>
              ) : (
                <ul className="max-h-72 overflow-y-auto py-1">
                  {hits.map((h) => (
                    <li key={h.associate_id}>
                      <button
                        type="button"
                        className="flex w-full flex-col gap-0.5 px-3 py-2 text-left hover:bg-[color:var(--brand-tint)]"
                        onClick={() => openHit(h)}
                      >
                        <span className="font-semibold text-[color:var(--brand-dark)]">{h.associate_id}</span>
                        <span className="truncate text-xs text-muted-foreground">
                          {h.name} · {h.mobile || "—"} · {h.status}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-2">
          <button
            type="button"
            onClick={() => void navigate({ to: session.isStaff ? "/fund/user-history" : "/fund/user-history" })}
            className="hidden items-center gap-2 rounded-full bg-[color:var(--brand)] px-3 py-1.5 text-white lg:inline-flex hover:opacity-95"
            title="Total wallet balance"
          >
            <Wallet className="h-4 w-4" />
            <span className="text-sm font-semibold tabular-nums">
              {walletBalance == null ? "…" : `₹ ${walletBalance.toLocaleString("en-IN")}`}
            </span>
          </button>

          <Button
            variant="ghost"
            size="icon"
            className="hidden rounded-full bg-white/60 sm:inline-flex"
            title={supportEmail || supportPhone ? "Contact support" : "Support contact"}
            onClick={() => {
              if (supportEmail) window.open(`mailto:${supportEmail}`);
              else if (supportPhone) window.open(`tel:${supportPhone}`);
              else toast.info("Support email/phone is set in Company settings");
            }}
          >
            <Globe className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="relative hidden rounded-full bg-white/60 sm:inline-flex"
            title="Help center"
            onClick={() => void navigate({ to: "/settings/help" })}
          >
            <MessageCircle className="h-4 w-4" />
          </Button>

          <Popover open={notifOpen} onOpenChange={setNotifOpen}>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="relative rounded-full bg-white/60" title="Notifications">
                <Bell className="h-4 w-4" />
                {unread > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-[color:var(--warn)] px-1 text-[10px] text-white">
                    {unread > 9 ? "9+" : unread}
                  </span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-80 p-0">
              <div className="flex items-center justify-between border-b px-3 py-2">
                <div className="text-sm font-semibold">Notifications</div>
                <button type="button" className="text-xs text-[color:var(--brand-dark)] underline" onClick={() => void markAllRead()}>
                  Mark all read
                </button>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifs.length === 0 ? (
                  <div className="px-3 py-6 text-center text-sm text-muted-foreground">No notifications</div>
                ) : (
                  notifs.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => void openNotif(n)}
                      className={cn(
                        "block w-full border-b px-3 py-2.5 text-left hover:bg-[color:var(--brand-tint)]",
                        !n.is_read && "bg-amber-50/60",
                      )}
                    >
                      <div className="text-sm font-medium">{n.title}</div>
                      <div className="line-clamp-2 text-xs text-muted-foreground">{n.body}</div>
                    </button>
                  ))
                )}
              </div>
            </PopoverContent>
          </Popover>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-xl bg-white/70 py-1 pl-1 pr-2 text-left hover:bg-white sm:pr-3">
                <Avatar key={session.photoUrl || "no-photo"} className="h-8 w-8 rounded-lg">
                  {session.photoUrl ? (
                    <img
                      src={session.photoUrl}
                      alt={session.name}
                      className="aspect-square h-full w-full object-cover"
                    />
                  ) : (
                    <AvatarFallback className="rounded-lg bg-[color:var(--brand)] text-xs text-white">
                      {initials(session.name)}
                    </AvatarFallback>
                  )}
                </Avatar>
                <div className="hidden leading-tight sm:block">
                  <div className="max-w-[8rem] truncate text-sm font-medium">{session.name}</div>
                  <div className="max-w-[8rem] truncate text-[10px] text-muted-foreground">
                    {roleLabel}
                    {session.associateId ? ` · ${session.associateId}` : ""}
                  </div>
                </div>
                <ChevronDown className="hidden h-4 w-4 text-muted-foreground sm:block" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="truncate font-medium">{session.name}</div>
                <div className="truncate text-xs font-normal text-muted-foreground">{subtitle}</div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/rbac/profile">My Profile</Link>
              </DropdownMenuItem>
              {showTeamApprovals ? (
                <DropdownMenuItem asChild>
                  <Link to="/team/approvals">Team Approvals</Link>
                </DropdownMenuItem>
              ) : null}
              <DropdownMenuItem asChild>
                <Link to="/genealogy">Associate Tree</Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="text-[color:var(--danger)]">
                <LogOut className="mr-2 h-4 w-4" /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
