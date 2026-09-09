import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { ConfigAPI } from "@/lib/api";

export const Route = createFileRoute("/_app/plans/rewards")({
  head: () => ({ meta: [{ title: "Rewards — JoyClub Associate" }] }),
  component: Page,
});

function Page() {
  const [posterUrl, setPosterUrl] = useState<string | null>(null);

  useEffect(() => {
    ConfigAPI.runtime()
      .then((d) => {
        const company = d.company as { reward_poster_image_url?: string | null } | undefined;
        setPosterUrl(company?.reward_poster_image_url ?? null);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"));
  }, []);

  return (
    <div className="w-full max-w-full space-y-3 pb-6">
      <PageHeader
        title="Reward Achievement"
        subtitle="Poster managed in Django Admin → Company settings."
      />

      {posterUrl ? (
        <figure className="w-full overflow-hidden rounded-xl border border-border bg-card">
          <img
            src={posterUrl}
            alt="Reward Achievement plan"
            className="block h-auto w-full max-w-full object-contain object-top"
            loading="lazy"
          />
        </figure>
      ) : (
        <p className="text-sm text-muted-foreground">
          Upload the poster in Django Admin → Company settings → Reward Achievement poster
          (1200×675 or 1080×1350, under 800 KB).
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        Also see the schedule on{" "}
        <Link to="/dashboard" className="font-medium text-[color:var(--brand-dark)] underline">
          Dashboard
        </Link>{" "}
        or{" "}
        <Link to="/income/reward" className="font-medium text-[color:var(--brand-dark)] underline">
          Reward Income
        </Link>
        .
      </p>
    </div>
  );
}
