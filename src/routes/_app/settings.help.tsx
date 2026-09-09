import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { DataTable, StatusBadge, type Column } from "@/components/data-table";
import { CmsAPI, unwrapList } from "@/lib/api";

export const Route = createFileRoute("/_app/settings/help")({
  head: () => ({ meta: [{ title: "Help Center — JoyClub Associate" }] }),
  component: Page,
});

function Page() {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  useEffect(() => {
    CmsAPI.help()
      .then((d) => setRows(unwrapList(d as never)))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"));
  }, []);
  const cols: Column<Record<string, unknown>>[] = [
    { key: "subject", header: "Subject", cell: (r) => String(r.subject) },
    { key: "email", header: "Email", cell: (r) => String(r.email) },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={String(r.status)} /> },
    { key: "created_at", header: "Created", cell: (r) => new Date(String(r.created_at)).toLocaleString("en-IN") },
  ];
  return (
    <div>
      <PageHeader title="Help Center" subtitle="Support tickets from CMS." />
      <DataTable data={rows} columns={cols} searchable={(r) => `${r.subject} ${r.email}`} />
    </div>
  );
}
