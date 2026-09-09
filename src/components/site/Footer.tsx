import { useState } from "react";
import { Facebook, Instagram, Twitter, Youtube } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import logo from "../../Asets/Joy Club Adventure Resort Logo.png";

const QUICK_LINKS = [
  { label: "Home", href: "#home" },
  { label: "Stay", href: "#stay" },
  { label: "Wellness", href: "#wellness" },
  { label: "Weddings", href: "#weddings" },
  { label: "Gallery", href: "#gallery" },
  { label: "Corporate", href: "#weddings" },
  { label: "Packages", href: "#stay" },
  { label: "About Us", href: "#about" },
  { label: "Contact", href: "#contact" },
];

const emailSchema = z
  .string()
  .trim()
  .min(1, { message: "Please enter your email address." })
  .email({ message: "Please enter a valid email address." })
  .max(255, { message: "Email must be less than 255 characters." });

function Newsletter() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        const result = emailSchema.safeParse(email);
        if (!result.success) {
          setError(result.error.issues[0].message);
          setDone(false);
          return;
        }
        setError(null);
        setDone(true);
        setEmail("");
        toast.success("You're subscribed!", {
          description: "Offers and seasonal packages are on their way to your inbox.",
        });
      }}
      className="space-y-3"
    >
      <label htmlFor="newsletter-email" className="text-cream/70 block text-sm">
        Get seasonal offers and packages.
      </label>
      <input
        id="newsletter-email"
        type="email"
        value={email}
        onChange={(e) => {
          setEmail(e.target.value);
          setError(null);
        }}
        placeholder="Your email address"
        aria-invalid={!!error}
        className="border-cream/20 text-cream placeholder:text-cream/40 focus:border-gold rounded-btn w-full border bg-white/5 px-4 py-3 text-sm outline-none"
      />
      {error ? (
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : null}
      {done ? <p className="text-gold text-xs">Thank you for subscribing!</p> : null}
      <button
        type="submit"
        className="bg-gold hover:bg-gold-light text-forest-deep btn-glow rounded-btn w-full py-3 text-xs font-bold tracking-[0.18em] uppercase transition-colors"
      >
        Subscribe
      </button>
    </form>
  );
}

export function Footer() {
  return (
    <footer id="contact" className="bg-forest-deep text-cream">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-2 lg:grid-cols-3 lg:px-8 lg:py-12">
        <div>
          <img
            src={logo}
            alt="Joy Club Adventure Resort"
            className="h-16 w-16 rounded-full object-cover"
          />
          <p className="text-cream/70 mt-4 text-sm leading-relaxed">
            Relax, Refresh, Reconnect. A luxury adventure and wellness retreat in the Aravalli
            Hills.
          </p>
        </div>

        <nav aria-label="Quick links">
          <h3 className="font-display text-lg">Quick Links</h3>
          <ul className="mt-5 grid grid-cols-2 gap-x-4 gap-y-2.5">
            {QUICK_LINKS.map((link) => (
              <li key={link.label}>
                <a href={link.href} className="text-cream/70 hover:text-gold text-sm">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div>
          <h3 className="font-display text-lg">Newsletter</h3>
          <div className="mt-5">
            <Newsletter />
          </div>
        </div>
      </div>

      <div className="border-cream/10 border-t">
        <div className="text-cream/60 mx-auto flex max-w-7xl flex-col items-center gap-4 px-4 py-6 text-xs sm:px-6 md:flex-row md:justify-between lg:px-8">
          <p>© 2026 Joy Club Adventure Resort. All Rights Reserved.</p>
          <div className="flex items-center gap-4">
            {[Facebook, Instagram, Twitter, Youtube].map((Icon, i) => (
              <a
                key={i}
                href="https://instagram.com"
                target="_blank"
                rel="noreferrer"
                aria-label="Joy Club social profile"
                className="text-gold hover:text-gold-light"
              >
                <Icon className="size-4" strokeWidth={1.5} />
              </a>
            ))}
          </div>
          <div className="flex gap-5">
            <a href="#contact" className="hover:text-gold">
              Privacy Policy
            </a>
            <a href="#contact" className="hover:text-gold">
              Terms &amp; Conditions
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
