import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import logo from "../../Asets/leaf logo.png";

const NAV = [
  { label: "Home", href: "#home" },
  { label: "Stay", href: "#stay" },
  { label: "Adventure", href: "#adventure" },
  { label: "Wellness", href: "#wellness" },
  { label: "Weddings", href: "#weddings" },
  { label: "Gallery", href: "#gallery" },
  { label: "Contact", href: "#contact" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <header
        className={cn(
          "fixed inset-x-0 top-0 z-50 transition-all duration-300",
          scrolled
            ? "bg-forest-deep/95 shadow-[0_10px_30px_-18px_rgba(0,0,0,0.8)] backdrop-blur"
            : "bg-forest-deep/45 shadow-[0_8px_24px_-14px_rgba(0,0,0,0.7)] backdrop-blur-sm",
        )}
      >
        <div className="mx-auto flex h-20 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
          <a href="#home" className="flex min-w-0 items-center gap-3">
            <span className="border-gold/60 grid size-11 shrink-0 place-items-center overflow-hidden rounded-full border">
              <img
                src={logo}
                alt="Joy Club Adventure Resort logo"
                className="size-full object-cover"
              />
            </span>
            <span className="min-w-0 leading-tight">
              <span className="text-cream font-display block truncate text-lg tracking-wide">
                JOY CLUB
              </span>
              <span className="text-gold/90 block truncate text-[0.6rem] tracking-[0.3em]">
                ADVENTURE RESORT
              </span>
            </span>
          </a>

          <nav className="mx-auto hidden items-center gap-7 lg:flex" aria-label="Primary">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-cream/85 hover:text-gold text-[0.8rem] font-medium tracking-[0.12em] uppercase transition-colors"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-2 lg:ml-0 lg:gap-3">
            <Link
              to="/login"
              className="text-cream/90 hover:text-gold hidden border-cream/25 rounded-btn border px-3 py-2 text-[0.68rem] font-bold tracking-[0.14em] uppercase transition-colors sm:inline-flex"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="bg-gold hover:bg-gold-light text-forest-deep btn-glow rounded-btn hidden px-4 py-2 text-[0.68rem] font-bold tracking-[0.14em] uppercase transition-colors sm:inline-flex"
            >
              Join
            </Link>
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-label="Open menu"
              className="text-cream border-cream/25 grid size-10 place-items-center rounded-full border lg:hidden"
            >
              <Menu className="size-5" strokeWidth={1.5} />
            </button>
          </div>
        </div>
      </header>

      <div
        className={cn(
          "fixed inset-0 z-50 lg:hidden",
          open ? "pointer-events-auto" : "pointer-events-none",
        )}
        aria-hidden={!open}
      >
        <div
          onClick={() => setOpen(false)}
          className={cn(
            "absolute inset-0 bg-black/60 transition-opacity duration-300",
            open ? "opacity-100" : "opacity-0",
          )}
        />
        <aside
          className={cn(
            "bg-forest-deep absolute inset-y-0 right-0 flex w-[82%] max-w-sm flex-col gap-2 p-6 shadow-2xl transition-transform duration-300",
            open ? "translate-x-0" : "translate-x-full",
          )}
        >
          <div className="mb-4 flex items-center justify-between">
            <span className="text-gold eyebrow">Menu</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
              className="text-cream border-cream/25 grid size-9 place-items-center rounded-full border"
            >
              <X className="size-4" />
            </button>
          </div>
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="text-cream/90 hover:text-gold border-cream/10 border-b py-3 text-sm tracking-[0.14em] uppercase"
            >
              {item.label}
            </a>
          ))}
          <Link
            to="/login"
            onClick={() => setOpen(false)}
            className="border-cream/30 text-cream rounded-btn mt-4 border py-3 text-center text-xs font-bold tracking-[0.16em] uppercase"
          >
            Login
          </Link>
          <Link
            to="/register"
            onClick={() => setOpen(false)}
            className="bg-gold text-forest-deep rounded-btn py-3 text-center text-xs font-bold tracking-[0.16em] uppercase"
          >
            Join
          </Link>
        </aside>
      </div>
    </>
  );
}
