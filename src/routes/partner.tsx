import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, type ComponentType } from "react";
import {
  ArrowRight,
  BadgePercent,
  ChartColumnIncreasing,
  ClipboardList,
  Crown,
  FileDown,
  Gift,
  Globe2,
  Handshake,
  IndianRupee,
  Mail,
  MapPin,
  Menu,
  Phone,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  UserPlus,
  Wallet,
  X,
} from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { useAuth } from "@/lib/rbac";
import { GooglePlayBadge } from "@/components/google-play-badge";
import {
  CmsAPI,
  type LandingBenefit,
  type LandingGalleryItem,
  type LandingPageSettings,
} from "@/lib/api";

const BROCHURE_PDF_HREF = "/downloads/JoyClubup.pdf";

export const Route = createFileRoute("/partner")({
  head: () => ({
    meta: [
      { title: "JoyClub Partner — Earn More. Enjoy More. Live More." },
      {
        name: "description",
        content:
          "JoyClub is a smart membership & rewards platform. Grow income, unlock exclusive benefits, and enjoy a better lifestyle.",
      },
    ],
  }),
  component: LandingPage,
});

const NAV = [
  { href: "#home", label: "Home" },
  { href: "#about", label: "About" },
  { href: "#membership", label: "Membership" },
  { href: "#benefits", label: "Benefits" },
  { href: "#contact", label: "Contact" },
] as const;

const FALLBACK_SETTINGS: LandingPageSettings = {
  eyebrow: "Exclusive Channel Partner Invitation",
  headline: "Join Our Resort Villa Partner Network",
  intro:
    "We invite brokers, consultants, and channel partners to join our Resort Villa Investment Project — designed for premium lifestyle assets and high appreciation potential.",
  investment_label: "Investment starts at just",
  investment_value: "₹ 2 Lakh",
  income_banner: "One Time & Regular Income",
  cta_title: "Join our channel partner network today and grow with us",
  cta_body: "Partner with us to grow your business with transparent payouts and long-term association.",
  slogan: "Build Wealth | Earn More | Grow Together",
  phone: "+91 800 0928 080",
  email: "info@joyadventureresort.com",
  website: "www.joyadventureresort.com",
  address: "Joy Adventure Resort, Jaipur, Rajasthan",
  banner_image_url: null,
  is_active: true,
};

const FALLBACK_BENEFITS: LandingBenefit[] = [
  {
    id: "fb-1",
    title: "High-Demand Investment Opportunity",
    body: "Premium resort villa assets with strong market interest.",
    icon_key: "trending",
    sort_order: 0,
  },
  {
    id: "fb-2",
    title: "Attractive Brokerage & Incentive Structure",
    body: "Earn real money with clear partner incentives.",
    icon_key: "money",
    sort_order: 1,
  },
  {
    id: "fb-3",
    title: "Dedicated Sales & Marketing Support",
    body: "Partner with a team that helps you close faster.",
    icon_key: "users",
    sort_order: 2,
  },
  {
    id: "fb-4",
    title: "Hassle-Free Booking Process",
    body: "Simple documentation and smooth booking flow.",
    icon_key: "clipboard",
    sort_order: 3,
  },
  {
    id: "fb-5",
    title: "Transparent Documentation & Timely Payouts",
    body: "Clear paperwork and reliable payout cycles.",
    icon_key: "shield",
    sort_order: 4,
  },
  {
    id: "fb-6",
    title: "Long-Term Business Association",
    body: "Grow together with a lasting partner relationship.",
    icon_key: "handshake",
    sort_order: 5,
  },
];

const BENEFIT_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  trending: TrendingUp,
  money: IndianRupee,
  users: Users,
  clipboard: ClipboardList,
  shield: ShieldCheck,
  handshake: Handshake,
};

function LandingPage() {
  const { session } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [partnerActive, setPartnerActive] = useState(true);
  const [settings, setSettings] = useState<LandingPageSettings>(FALLBACK_SETTINGS);
  const [benefits, setBenefits] = useState<LandingBenefit[]>(FALLBACK_BENEFITS);
  const [gallery, setGallery] = useState<LandingGalleryItem[]>([]);

  useEffect(() => {
    CmsAPI.landing()
      .then((data) => {
        if (!data.active || !data.settings) {
          setPartnerActive(false);
          return;
        }
        setPartnerActive(true);
        setSettings(data.settings);
        setBenefits(data.benefits?.length ? data.benefits : FALLBACK_BENEFITS);
        setGallery(data.gallery ?? []);
      })
      .catch(() => {
        setPartnerActive(true);
        setSettings(FALLBACK_SETTINGS);
        setBenefits(FALLBACK_BENEFITS);
        setGallery([]);
      });
  }, []);

  const websiteHref = settings.website
    ? settings.website.startsWith("http")
      ? settings.website
      : `https://${settings.website.replace(/^\/\//, "")}`
    : "";

  return (
    <div className="landing min-h-screen bg-[#04180F] text-white">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#04180F]/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:h-[4.25rem] sm:px-6">
          <a href="#home" className="flex items-center gap-2.5">
            <BrandMark className="h-9 w-9 sm:h-10 sm:w-10" plate="none" />
            <div className="leading-tight">
              <div className="text-sm font-extrabold tracking-[0.18em] text-[#F5D56A] sm:text-base">JOYCLUB</div>
              <div className="hidden text-[10px] font-medium tracking-wide text-white/55 sm:block">Associate</div>
            </div>
          </a>

          <nav className="hidden items-center gap-6 lg:flex">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-xs font-semibold uppercase tracking-[0.14em] text-white/75 transition hover:text-[#F5D56A]"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {session ? (
              <Link
                to="/dashboard"
                className="rounded-full bg-[#F5D56A] px-4 py-2 text-xs font-extrabold uppercase tracking-wide text-[#04180F] transition hover:bg-[#ffe08a]"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link
                  to="/register"
                  className="rounded-full border border-[#F5D56A]/70 px-3.5 py-2 text-xs font-extrabold uppercase tracking-wide text-[#F5D56A] transition hover:bg-[#F5D56A]/10 sm:px-4"
                >
                  Register
                </Link>
                <Link
                  to="/login"
                  className="rounded-full bg-[#F5D56A] px-3.5 py-2 text-xs font-extrabold uppercase tracking-wide text-[#04180F] transition hover:bg-[#ffe08a] sm:px-4"
                >
                  Login
                </Link>
              </>
            )}
            <button
              type="button"
              className="grid h-10 w-10 place-items-center rounded-full border border-white/15 text-white lg:hidden"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {menuOpen ? (
          <div className="border-t border-white/10 bg-[#062016] px-4 py-3 lg:hidden">
            <div className="mx-auto flex max-w-6xl flex-col gap-1">
              {NAV.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-lg px-3 py-2.5 text-sm font-semibold uppercase tracking-wide text-white/80 hover:bg-white/5 hover:text-[#F5D56A]"
                >
                  {item.label}
                </a>
              ))}
            </div>
          </div>
        ) : null}
      </header>

      <main>
        <section
          id="home"
          className="relative overflow-hidden border-b border-white/10"
          style={{
            backgroundImage:
              "linear-gradient(105deg, rgba(4,24,15,0.92) 0%, rgba(4,24,15,0.78) 42%, rgba(4,24,15,0.55) 100%), radial-gradient(ellipse at 70% 40%, rgba(245,213,106,0.18), transparent 55%), linear-gradient(160deg, #063822 0%, #04180F 55%, #0a2f1c 100%)",
          }}
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.14]"
            style={{
              backgroundImage:
                "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23F5D56A' fill-opacity='0.35'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
            }}
          />

          <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-12 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-[1.15fr_0.85fr] lg:gap-8 lg:pt-20">
            <div className="text-center lg:text-left">
              <p className="text-sm font-semibold tracking-wide text-white/70 sm:text-base">
                Earn More. <span className="text-[#F5D56A]">Enjoy</span> More.{" "}
                <span className="text-[#7ED9B0]">Live</span> More.
              </p>
              <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-[3.35rem] lg:leading-[1.08]">
                WELCOME TO <span className="text-[#F5D56A]">JoyClub</span>
              </h1>
              <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-white/75 sm:text-base lg:mx-0">
                JoyClub is a smart membership &amp; rewards platform that helps you grow your income, unlock exclusive
                benefits and enjoy a better lifestyle.
              </p>

              <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:flex-wrap lg:justify-start">
                <GooglePlayBadge href="/downloads/joyclub.apk" className="scale-110" />
                <Link
                  to="/register"
                  className="inline-flex h-12 items-center gap-2 rounded-xl bg-[#F5D56A] px-6 text-sm font-extrabold uppercase tracking-wide text-[#04180F] transition hover:bg-[#ffe08a]"
                >
                  Join JoyClub Now <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href={BROCHURE_PDF_HREF}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-12 items-center gap-2 rounded-xl border border-white/25 bg-white/5 px-6 text-sm font-extrabold uppercase tracking-wide text-white transition hover:border-[#F5D56A]/60 hover:bg-white/10 hover:text-[#F5D56A]"
                >
                  <FileDown className="h-4 w-4" />
                  Download brochure
                </a>
              </div>

              <div className="mx-auto mt-10 grid max-w-lg grid-cols-2 gap-3 text-left sm:max-w-none sm:grid-cols-4 lg:mx-0">
                {[
                  { icon: Wallet, label: "Extra Income Opportunities" },
                  { icon: Sparkles, label: "Exclusive Benefits" },
                  { icon: Users, label: "Trusted Community" },
                  { icon: ShieldCheck, label: "100% Secure & Transparent" },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl border border-white/10 bg-white/5 px-3 py-3 backdrop-blur-sm">
                    <item.icon className="h-5 w-5 text-[#F5D56A]" />
                    <p className="mt-2 text-[11px] font-semibold leading-snug text-white/85">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-sm lg:max-w-md">
              <div className="absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#F5D56A]/15 blur-3xl" />
              <div className="relative mx-auto aspect-[4/5] w-[88%] max-w-[280px] rounded-[1.75rem] border-2 border-[#F5D56A] bg-gradient-to-br from-[#0B3D24] via-[#062A18] to-[#04180F] p-5 shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
                <div className="flex items-center justify-between">
                  <BrandMark className="h-12 w-12" plate="none" />
                </div>
                <div className="mt-8">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-white/50">Membership</p>
                  <p className="mt-1 text-2xl font-extrabold tracking-wide text-[#F5D56A]">ASSOCIATE</p>
                  <p className="mt-3 text-xs leading-relaxed text-white/65">
                    Tradition meets technology. Grow with JoyClub Associate.
                  </p>
                </div>
                <div className="absolute bottom-5 left-5 right-5 flex items-end justify-between border-t border-white/10 pt-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-white/45">Status</p>
                    <p className="text-sm font-bold text-white">Active</p>
                  </div>
                  <Crown className="h-7 w-7 text-[#F5D56A]" />
                </div>
              </div>
              <div className="mx-auto mt-4 h-3 w-3/4 rounded-full bg-[#F5D56A]/35 blur-[1px]" />
              <div className="mx-auto h-2 w-1/2 rounded-full bg-[#F5D56A]/20" />
            </div>
          </div>
        </section>

        <section id="about" className="scroll-mt-20 border-b border-white/10 bg-[#062016] py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#F5D56A]">About JoyClub</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">Built for ambitious associates</h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-white/70 sm:text-base">
              JoyClub Associate connects membership, rewards, and transparent earnings in one secure platform — so you
              can focus on growing your network and lifestyle.
            </p>
          </div>
        </section>

        <section id="membership" className="scroll-mt-20 border-b border-white/10 bg-[#04180F] py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="text-center">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#F5D56A]">Simple &amp; Easy</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">How to Become a Member</h2>
            </div>
            <div className="relative mx-auto mt-12 grid max-w-4xl gap-8 md:grid-cols-3 md:gap-6">
              <div className="pointer-events-none absolute left-[16%] right-[16%] top-10 hidden border-t border-dashed border-[#F5D56A]/35 md:block" />
              {[
                {
                  icon: UserPlus,
                  title: "Register",
                  text: "Sign up with your basic details and create your account.",
                },
                {
                  icon: Crown,
                  title: "Choose Membership",
                  text: "Choose the membership plan that suits you best.",
                },
                {
                  icon: Wallet,
                  title: "Start Earning & Enjoy",
                  text: "Refer, earn, unlock benefits and grow with JoyClub.",
                },
              ].map((step, i) => (
                <div key={step.title} className="relative text-center">
                  <div className="mx-auto grid h-20 w-20 place-items-center rounded-full border-2 border-[#F5D56A] bg-[#0B3D24] shadow-[0_0_0_6px_rgba(245,213,106,0.08)]">
                    <step.icon className="h-8 w-8 text-[#F5D56A]" />
                  </div>
                  <p className="mt-4 text-xs font-bold uppercase tracking-[0.18em] text-[#F5D56A]">Step {i + 1}</p>
                  <h3 className="mt-1 text-lg font-extrabold">{step.title}</h3>
                  <p className="mt-2 text-sm text-white/65">{step.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="benefits" className="scroll-mt-20 border-b border-white/10 bg-[#062016] py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="text-center">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#F5D56A]">Rewards</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">Best Benefits for You</h2>
            </div>
            <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { icon: ChartColumnIncreasing, title: "Unlimited Income", text: "Scale your earnings with referrals and performance rewards." },
                { icon: Gift, title: "Attractive Rewards", text: "Unlock gifts, milestones, and recognition as you grow." },
                { icon: BadgePercent, title: "Exclusive Discounts", text: "Member-only offers that add real everyday value." },
                { icon: Globe2, title: "Global Community", text: "Connect with associates building together worldwide." },
                { icon: Sparkles, title: "Personal Growth", text: "Tools and guidance to level up your journey." },
                { icon: IndianRupee, title: "Financial Freedom", text: "Transparent wallets and income tracking you can trust." },
              ].map((item) => (
                <div
                  key={item.title}
                  className="rounded-2xl border border-[#F5D56A]/35 bg-[#04180F]/60 px-5 py-6 transition hover:border-[#F5D56A] hover:bg-[#0B3D24]/40"
                >
                  <item.icon className="h-8 w-8 text-[#F5D56A]" />
                  <h3 className="mt-4 text-lg font-extrabold text-white">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-white/65">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {partnerActive ? (
          <>
            <section className="scroll-mt-20 border-b border-white/10 bg-[#04180F] py-16 sm:py-20">
              <div className="mx-auto max-w-6xl px-4 sm:px-6">
                <div className="text-center">
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#F5D56A]">{settings.eyebrow}</p>
                  <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">{settings.headline}</h2>
                  {settings.intro ? (
                    <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-white/70 sm:text-base">
                      {settings.intro}
                    </p>
                  ) : null}
                </div>

                {settings.banner_image_url ? (
                  <img
                    src={settings.banner_image_url}
                    alt=""
                    className="mt-10 w-full max-h-72 object-cover object-center"
                  />
                ) : null}

                <div className="mt-10 grid gap-4 sm:grid-cols-2">
                  <div className="border border-[#F5D56A]/40 bg-[#0B3D24]/50 px-6 py-7 text-center sm:text-left">
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/55">
                      {settings.investment_label}
                    </p>
                    <p className="mt-2 text-3xl font-extrabold text-[#F5D56A] sm:text-4xl">
                      {settings.investment_value}
                    </p>
                  </div>
                  <div className="flex items-center justify-center border border-[#F5D56A]/40 bg-gradient-to-r from-[#0B3D24] to-[#062A18] px-6 py-7 text-center">
                    <p className="text-xl font-extrabold tracking-tight text-white sm:text-2xl">
                      {settings.income_banner}
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {benefits.length ? (
              <section className="border-b border-white/10 bg-[#062016] py-16 sm:py-20">
                <div className="mx-auto max-w-6xl px-4 sm:px-6">
                  <div className="text-center">
                    <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#F5D56A]">Why partner with us?</p>
                    <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">Partner advantages</h2>
                  </div>
                  <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {benefits.map((item) => {
                      const Icon = BENEFIT_ICONS[item.icon_key] ?? Sparkles;
                      return (
                        <div key={item.id} className="text-left">
                          <Icon className="h-8 w-8 text-[#F5D56A]" />
                          <h3 className="mt-4 text-lg font-extrabold text-white">{item.title}</h3>
                          {item.body ? (
                            <p className="mt-2 text-sm leading-relaxed text-white/65">{item.body}</p>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </section>
            ) : null}

            {gallery.length ? (
              <section className="border-b border-white/10 bg-[#04180F] py-16 sm:py-20">
                <div className="mx-auto max-w-6xl px-4 sm:px-6">
                  <div className="text-center">
                    <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#F5D56A]">What you get</p>
                    <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">Lifestyle &amp; growth</h2>
                  </div>
                  <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {gallery.map((item) => (
                      <figure key={item.id} className="overflow-hidden border border-[#F5D56A]/25 bg-[#062016]">
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={item.title}
                            className="aspect-[8/5] w-full object-cover"
                          />
                        ) : (
                          <div className="flex aspect-[8/5] items-center justify-center bg-gradient-to-br from-[#0B3D24] to-[#04180F] px-4">
                            <Sparkles className="h-8 w-8 text-[#F5D56A]/70" />
                          </div>
                        )}
                        <figcaption className="px-3 py-3 text-center text-sm font-semibold text-white/85">
                          {item.title}
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                </div>
              </section>
            ) : null}

            <section id="contact" className="scroll-mt-20 border-b border-white/10 bg-[#062016] py-14 sm:py-16">
              <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
                <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{settings.cta_title}</h2>
                {settings.cta_body ? (
                  <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-white/70">{settings.cta_body}</p>
                ) : null}
                {settings.slogan ? (
                  <p className="mt-5 text-sm font-bold uppercase tracking-[0.16em] text-[#F5D56A]">{settings.slogan}</p>
                ) : null}
                <div className="mx-auto mt-8 grid max-w-3xl gap-4 text-left sm:grid-cols-2">
                  {settings.phone ? (
                    <a
                      href={`tel:${settings.phone.replace(/\s+/g, "")}`}
                      className="flex items-start gap-3 text-sm text-white/80 transition hover:text-[#F5D56A]"
                    >
                      <Phone className="mt-0.5 h-4 w-4 shrink-0 text-[#F5D56A]" />
                      <span>{settings.phone}</span>
                    </a>
                  ) : null}
                  {settings.email ? (
                    <a
                      href={`mailto:${settings.email}`}
                      className="flex items-start gap-3 text-sm text-white/80 transition hover:text-[#F5D56A]"
                    >
                      <Mail className="mt-0.5 h-4 w-4 shrink-0 text-[#F5D56A]" />
                      <span>{settings.email}</span>
                    </a>
                  ) : null}
                  {settings.website ? (
                    <a
                      href={websiteHref}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-start gap-3 text-sm text-white/80 transition hover:text-[#F5D56A]"
                    >
                      <Globe2 className="mt-0.5 h-4 w-4 shrink-0 text-[#F5D56A]" />
                      <span>{settings.website}</span>
                    </a>
                  ) : null}
                  {settings.address ? (
                    <p className="flex items-start gap-3 text-sm text-white/80">
                      <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#F5D56A]" />
                      <span>{settings.address}</span>
                    </p>
                  ) : null}
                </div>
              </div>
            </section>
          </>
        ) : null}

        <section className="border-b border-white/10 bg-gradient-to-r from-[#0B3D24] via-[#062A18] to-[#0B3D24] py-12">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-4 text-center sm:px-6 md:flex-row md:text-left">
            <p className="max-w-xl text-lg font-semibold text-white/90 sm:text-xl">
              Join thousands of smart people who are already growing with JoyClub…
            </p>
            <div className="flex flex-col items-center gap-3 sm:flex-row">
              <GooglePlayBadge href="/downloads/joyclub.apk" />
              <Link
                to="/register"
                className="inline-flex h-12 items-center gap-2 rounded-xl bg-[#F5D56A] px-6 text-sm font-extrabold uppercase tracking-wide text-[#04180F] transition hover:bg-[#ffe08a]"
              >
                Join JoyClub Now <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href={BROCHURE_PDF_HREF}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center gap-2 rounded-xl border border-white/25 bg-white/5 px-6 text-sm font-extrabold uppercase tracking-wide text-white transition hover:border-[#F5D56A]/60 hover:bg-white/10 hover:text-[#F5D56A]"
              >
                <FileDown className="h-4 w-4" />
                Download brochure
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer id={partnerActive ? undefined : "contact"} className="scroll-mt-20 bg-[#020E09] py-12">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 sm:px-6 md:grid-cols-[1.2fr_1fr]">
          <div>
            <div className="flex items-center gap-3">
              <BrandMark className="h-12 w-12" plate="none" />
              <div>
                <div className="text-lg font-extrabold tracking-[0.16em] text-[#F5D56A]">JOYCLUB</div>
                <p className="text-sm text-white/55">Earn More. Enjoy More. Live More.</p>
              </div>
            </div>
            <p className="mt-4 max-w-md text-sm text-white/60">
              Tradition meets technology — your membership, rewards, and associate dashboard in one place.
            </p>
          </div>
          <div className="md:text-right">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#F5D56A]">Get started</p>
            {!partnerActive ? (
              <>
                {settings.website ? <p className="mt-3 text-sm text-white/75">{settings.website}</p> : null}
                {settings.email ? <p className="mt-1 text-sm text-white/75">{settings.email}</p> : null}
              </>
            ) : null}
            <div className="mt-5 flex gap-3 md:justify-end">
              {session ? (
                <Link to="/dashboard" className="text-sm font-bold text-[#F5D56A] hover:underline">
                  Open dashboard
                </Link>
              ) : (
                <>
                  <Link to="/register" className="text-sm font-bold text-[#F5D56A] hover:underline">
                    Register
                  </Link>
                  <span className="text-white/30">·</span>
                  <Link to="/login" className="text-sm font-bold text-[#F5D56A] hover:underline">
                    Login
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
        <p className="mx-auto mt-10 max-w-6xl px-4 text-center text-xs text-white/35 sm:px-6">
          © {new Date().getFullYear()} JoyClub Associate. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
