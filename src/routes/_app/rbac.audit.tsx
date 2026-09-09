import { createFileRoute } from "@tanstack/react-router";
import { DataTable, type Column } from "@/components/data-table";
import { PageHeader } from "@/components/app-shell";
import { useAuth, type AuditEntry } from "@/lib/rbac";

export const Route = createFileRoute("/_app/rbac/audit")({
  head: () => ({ meta: [
    { title: "Audit Log — JoyClub Associate" },
    { name: "description", content: "Every privileged action, timestamped and attributed." },
    { property: "og:title", content: "Audit Log — JoyClub Associate" },
    { property: "og:description", content: "Every privileged action, timestamped and attributed." },
  ]}),
  component: AuditPage,
});

function AuditPage() {
  const { audit } = useAuth();
  const cols: Column<AuditEntry>[] = [
    { key: "at", header: "When", cell: e => new Date(e.at).toLocaleString("en-IN"), sortValue: e => e.at },
    { key: "actor", header: "Actor", cell: e => <span className="font-medium">{e.actor}</span> },
    { key: "action", header: "Action", cell: e => <span className="font-mono text-xs">{e.action}</span> },
    { key: "target", header: "Target", cell: e => e.target ?? "—" },
    { key: "before", header: "Before", cell: e => e.before ?? "—" },
    { key: "after", header: "After", cell: e => e.after ?? "—" },
    { key: "ip", header: "IP", cell: e => <span className="font-mono text-xs">{e.ip}</span> },
  ];
  return (
    <div>
      <PageHeader title="Audit Log" subtitle="Every privileged action performed by staff, with before/after values." />
      <DataTable data={audit} columns={cols} searchable={e => `${e.actor} ${e.action} ${e.target ?? ""}`} emptyTitle="No audit entries yet" emptyHint="Actions like approvals, blocks and role changes will appear here." />
    </div>
  );
}
