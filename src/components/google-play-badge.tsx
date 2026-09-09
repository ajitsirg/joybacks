import { cn } from "@/lib/utils";

type Props = {
  href: string;
  className?: string;
};

/** Stylized Google Play badge that triggers APK download (sideload). */
export function GooglePlayBadge({ href, className }: Props) {
  return (
    <a
      href={href}
      download="joyclub.apk"
      className={cn(
        "inline-flex h-14 items-center gap-3 rounded-xl border border-white/20 bg-black px-4 text-left text-white shadow-lg transition hover:border-[#F5D56A]/50 hover:bg-[#111]",
        className,
      )}
      aria-label="Download JoyClub Android app"
    >
      <svg viewBox="0 0 24 24" className="h-8 w-8 shrink-0" aria-hidden>
        <path
          fill="#EA4335"
          d="M3.6 1.8c-.4.2-.7.7-.7 1.3v17.8c0 .6.3 1.1.7 1.3l10.1-10.2L3.6 1.8z"
        />
        <path fill="#FBBC04" d="M16.4 14.7l-2.7-2.7-10.1 10.2c.4.3 1 .3 1.6 0l11.2-6.5v-.1z" />
        <path fill="#4285F4" d="M20.4 10.7l-4-2.3-2.8 2.8 2.8 2.8 4-2.3c1.1-.6 1.1-1.9 0-2.9v-.1z" />
        <path fill="#34A853" d="M13.7 12l2.7-2.7L5.2 1.7c-.6-.3-1.2-.2-1.6.1L13.7 12z" />
      </svg>
      <span className="leading-tight">
        <span className="block text-[10px] font-medium uppercase tracking-wider text-white/70">Get it on</span>
        <span className="block text-base font-bold tracking-wide">Google Play</span>
      </span>
    </a>
  );
}
