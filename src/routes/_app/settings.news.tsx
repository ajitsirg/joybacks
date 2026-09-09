import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { CmsAPI, unwrapList } from "@/lib/api";

export const Route = createFileRoute("/_app/settings/news")({
  head: () => ({ meta: [{ title: "News — JoyClub Associate" }] }),
  component: Page,
});

function Page() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    CmsAPI.news()
      .then((d) => setItems(unwrapList(d as never)))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"));
  }, []);
  return (
    <div>
      <PageHeader title="News & Announcements" subtitle="Published from CMS API / Django Admin." />
      <div className="space-y-3">
        {items.map((n) => (
          <article key={String(n.id)} className="rounded-2xl border border-border bg-card p-5">
            <h3 className="font-semibold">{String(n.title)}</h3>
            <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">{String(n.body)}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
