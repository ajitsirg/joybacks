import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { DataTable, StatusBadge, type Column } from "@/components/data-table";
import { LevelBadge } from "@/components/earning-level-badge";
import { DashboardAPI } from "@/lib/api";

export const Route = createFileRoute("/_app/business-report")({
  head: () => ({ meta: [{ title: "Business Report — JoyClub Associate" }] }),
  component: BusinessReport,
});

type Row = Record<string, unknown>;

function BusinessReport() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    DashboardAPI.businessReport()
      .then((d) => setRows(d.results))
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed"))
      .finally(() => setLoading(false));
  }, []);

  const cols: Column<Row>[] = [
    { key: "associate_id", header: "Associate", cell: (r) => <span className="font-semibold">{String(r.associate_id)}</span> },
    { key: "name", header: "Name", cell: (r) => String(r.name) },
    { key: "sponsor_id", header: "Sponsor", cell: (r) => String(r.sponsor_id || "—") },
    {
      key: "reward_level",
      header: "Reward level",
      sortValue: (r) => Number(r.reward_level ?? r.earning_level ?? 0),
      cell: (r) => (
        <LevelBadge
          kind="reward"
          level={r.reward_level ?? r.earning_level}
          name={r.reward_level_name ?? r.earning_level_name}
        />
      ),
    },
    {
      key: "performance_level",
      header: "Performance",
      sortValue: (r) => Number(r.performance_level ?? 0),
      cell: (r) => (
        <LevelBadge kind="performance" level={r.performance_level} name={r.performance_level_name} />
      ),
    },
    { key: "personal_business", header: "Personal", cell: (r) => `₹ ${Number(r.personal_business).toLocaleString("en-IN")}` },
    { key: "total_business", header: "Team", cell: (r) => `₹ ${Number(r.total_business).toLocaleString("en-IN")}` },
    { key: "income_total", header: "Income", cell: (r) => `₹ ${Number(r.income_total).toLocaleString("en-IN")}` },
    { key: "direct_count", header: "Directs", cell: (r) => String(r.direct_count) },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={String(r.status)} /> },
  ];

  return (
    <div>
      <PageHeader title="Business Report" subtitle="Live sponsor / business / income rollup" actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined} />
      <DataTable data={rows} columns={cols} searchable={(r) => `${r.associate_id} ${r.name} ${r.sponsor_id}`} />
    </div>
  );
}
