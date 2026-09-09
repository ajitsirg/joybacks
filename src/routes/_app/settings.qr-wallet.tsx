import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { CmsAPI, unwrapList } from "@/lib/api";

export const Route = createFileRoute("/_app/settings/qr-wallet")({
  head: () => ({ meta: [{ title: "QR & Wallet — JoyClub Associate" }] }),
  component: Page,
});

function Page() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    CmsAPI.qr()
      .then((d) => setItems(unwrapList(d as never)))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"));
  }, []);
  return (
    <div>
      <PageHeader title="QR & Wallet Settings" subtitle="Deposit QR / wallet addresses from admin CMS." />
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((q) => (
          <div key={String(q.id)} className="rounded-2xl border border-border bg-card p-5">
            <div className="font-semibold">{String(q.label)}</div>
            <div className="mt-2 font-mono text-sm text-muted-foreground">{String(q.wallet_address || "—")}</div>
            <div className="mt-2 text-xs">{q.is_active ? "Active" : "Inactive"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
