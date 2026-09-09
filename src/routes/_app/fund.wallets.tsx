import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownToLine,
  ChevronRight,
  Gift,
  Landmark,
  Loader2,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { WalletsAPI, unwrapList } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/fund/wallets")({
  ssr: false,
  head: () => ({ meta: [{ title: "Wallets — JoyClub Associate" }] }),
  component: WalletsPage,
});

type WalletRow = {
  id: string;
  wallet_type?: string;
  balance?: string | number;
  associate_id?: string;
};

const ORDER = ["main", "personal", "income", "reward", "roi", "withdraw"] as const;

const META: Record<
  string,
  {
    label: string;
    hint: string;
    icon: LucideIcon;
    accent: string;
    soft: string;
    ring: string;
  }
> = {
  main: {
    label: "Main Fund",
    hint: "Transferable packages",
    icon: Landmark,
    accent: "#064E2A",
    soft: "#E6F5EC",
    ring: "ring-[#064E2A]/15",
  },
  personal: {
    label: "Personal Fund",
    hint: "Self-invested packages",
    icon: Wallet,
    accent: "#0F766E",
    soft: "#DDF7F3",
    ring: "ring-[#0F766E]/15",
  },
  income: {
    label: "Income",
    hint: "Level & referral",
    icon: TrendingUp,
    accent: "#0B6B3A",
    soft: "#DDF0E5",
    ring: "ring-[#0B6B3A]/15",
  },
  reward: {
    label: "Reward",
    hint: "Achievement rewards",
    icon: Gift,
    accent: "#B45309",
    soft: "#FFF4E5",
    ring: "ring-[#B45309]/15",
  },
  roi: {
    label: "ROI",
    hint: "Return income",
    icon: Wallet,
    accent: "#1D4ED8",
    soft: "#E8EEFF",
    ring: "ring-[#1D4ED8]/15",
  },
  withdraw: {
    label: "Withdraw",
    hint: "Ready to withdraw",
    icon: ArrowDownToLine,
    accent: "#BE123C",
    soft: "#FFE8EE",
    ring: "ring-[#BE123C]/15",
  },
};

function money(n: number) {
  return `₹ ${n.toLocaleString("en-IN")}`;
}

function WalletsPage() {
  const [rows, setRows] = useState<WalletRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    WalletsAPI.list({ page_size: 50 })
      .then((d) => {
        const list = unwrapList(d as never) as WalletRow[];
        const byType = new Map<string, WalletRow>();
        for (const w of list) {
          const key = String(w.wallet_type ?? "").toLowerCase();
          if (key && !byType.has(key)) byType.set(key, w);
        }
        setRows([...byType.values()]);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load wallets"))
      .finally(() => setLoading(false));
  }, []);

  const ordered = useMemo(() => {
    const by = new Map(rows.map((w) => [String(w.wallet_type ?? "").toLowerCase(), w]));
    const known = ORDER.map((t) => by.get(t)).filter(Boolean) as WalletRow[];
    const rest = rows.filter((w) => !ORDER.includes(String(w.wallet_type ?? "").toLowerCase() as (typeof ORDER)[number]));
    return [...known, ...rest];
  }, [rows]);

  const total = useMemo(
    () => ordered.reduce((s, w) => s + Number(w.balance ?? 0), 0),
    [ordered],
  );

  return (
    <div className="relative space-y-5">
      {/* Soft page atmosphere */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-3 -top-3 h-56 rounded-3xl bg-[radial-gradient(ellipse_at_top,_rgba(11,107,58,0.14),_transparent_65%)] sm:-inset-x-5"
      />

      <header className="relative overflow-hidden rounded-3xl border border-[color:var(--hero-border)] bg-gradient-to-br from-white via-[color:var(--hero)] to-[#d8efe3] p-5 sm:p-7">
        <div
          aria-hidden
          className="absolute -right-8 -top-10 h-36 w-36 rounded-full bg-[color:var(--brand)]/10 blur-2xl"
        />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--brand)]">
              Fund
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-[color:var(--brand-dark)] sm:text-3xl">
              Wallets
            </h1>
            <p className="mt-1.5 max-w-md text-sm text-slate-600">
              Your balances across fund wallets. Tap any wallet to open its history.
            </p>
          </div>
          {loading ? <Loader2 className="h-5 w-5 animate-spin text-[color:var(--brand)]" /> : null}
        </div>

        <div className="relative mt-6 overflow-hidden rounded-2xl bg-gradient-to-r from-[color:var(--brand-dark)] via-[#086338] to-[color:var(--brand)] p-4 text-white shadow-[0_12px_40px_-18px_rgba(6,78,42,0.65)] sm:p-5">
          <div
            aria-hidden
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.25), transparent 45%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.12), transparent 40%)",
            }}
          />
          <div className="relative flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="text-xs font-medium uppercase tracking-[0.16em] text-white/70">
                Total balance
              </div>
              <div className="mt-1 text-3xl font-bold tabular-nums tracking-tight sm:text-4xl">
                {money(total)}
              </div>
            </div>
            <div className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium backdrop-blur-sm">
              {ordered.length} wallet{ordered.length === 1 ? "" : "s"}
            </div>
          </div>
        </div>
      </header>

      {ordered.length === 0 && !loading ? (
        <div className="rounded-2xl border border-dashed border-[color:var(--hero-border)] bg-white/70 p-10 text-center text-sm text-muted-foreground">
          No wallets found
        </div>
      ) : (
        <div className="relative grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {ordered.map((w, i) => {
            const type = String(w.wallet_type ?? "main").toLowerCase();
            const meta = META[type] ?? META.main;
            const Icon = meta.icon;
            const bal = Number(w.balance ?? 0);
            const share = total > 0 ? Math.min(100, Math.round((bal / total) * 100)) : 0;
            return (
              <Link
                key={String(w.id)}
                to="/fund/user-history"
                search={{ wallet: type } as never}
                className={cn(
                  "group relative overflow-hidden rounded-2xl border border-white/80 bg-white p-4 shadow-[0_8px_30px_-20px_rgba(15,36,24,0.45)] transition duration-300",
                  "hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-22px_rgba(15,36,24,0.55)]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--brand)]",
                  meta.ring,
                )}
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div
                  aria-hidden
                  className="absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-80 transition duration-300 group-hover:scale-110"
                  style={{ background: meta.soft }}
                />
                <div className="relative flex items-start gap-3">
                  <div
                    className="grid h-11 w-11 shrink-0 place-items-center rounded-xl shadow-sm"
                    style={{ background: meta.soft, color: meta.accent }}
                  >
                    <Icon className="h-5 w-5" strokeWidth={2.1} />
                  </div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="flex items-center justify-between gap-2">
                      <div
                        className="text-[11px] font-bold uppercase tracking-[0.14em]"
                        style={{ color: meta.accent }}
                      >
                        {meta.label}
                      </div>
                      <ChevronRight
                        className="h-4 w-4 shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-slate-500"
                      />
                    </div>
                    <div className="mt-1 text-xl font-bold tabular-nums tracking-tight text-slate-900 sm:text-2xl">
                      {money(bal)}
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">{meta.hint}</p>
                  </div>
                </div>

                <div className="relative mt-4">
                  <div className="mb-1 flex items-center justify-between text-[10px] font-medium uppercase tracking-wider text-slate-400">
                    <span>Share of total</span>
                    <span className="tabular-nums">{share}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full transition-[width] duration-500"
                      style={{ width: `${share}%`, background: meta.accent }}
                    />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
