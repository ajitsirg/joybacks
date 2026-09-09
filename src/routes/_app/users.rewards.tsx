import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { DataTable, type Column } from "@/components/data-table";
import { PageHeader } from "@/components/app-shell";
import { REWARD_ACHIEVEMENT_ROWS } from "@/components/reward-achievement-table";
import { WalletsAPI, unwrapList } from "@/lib/api";

export const Route = createFileRoute("/_app/users/rewards")({
  head: () => ({
    meta: [
      { title: "Reward Achievers — JoyClub Associate" },
      { name: "description", content: "Reward plans and reward-wallet credits from live API." },
    ],
  }),
  component: RewardAchievers,
});

type Row = Record<string, unknown>;

function RewardAchievers() {
  const [plans, setPlans] = useState<Row[]>([]);
  const [credits, setCredits] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    WalletsAPI.ledger({ page_size: 200, "wallet__wallet_type": "reward" })
      .catch(() => WalletsAPI.ledger({ page_size: 200 }))
      .then((ledger) => {
        setPlans(
          REWARD_ACHIEVEMENT_ROWS.map((row) => ({
            name: `Milestone ${row.sno}`,
            business_target: row.total,
            leg1_target: row.leg1,
            leg2_target: row.leg2,
            leg3_target: row.leg3,
            reward_amount: row.reward,
            is_active: true,
          })),
        );
        const list = unwrapList(ledger).filter((r) => String(r.wallet_type) === "reward");
        setCredits(list);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load rewards"))
      .finally(() => setLoading(false));
  }, []);

  const planCols: Column<Row>[] = [
    { key: "name", header: "Reward", cell: (r) => <span className="font-medium">{String(r.name ?? "—")}</span> },
    {
      key: "business_target",
      header: "Total target",
      cell: (r) => `₹ ${Number(r.business_target ?? 0).toLocaleString("en-IN")}`,
    },
    {
      key: "leg1_target",
      header: "Leg 1",
      cell: (r) => `₹ ${Number(r.leg1_target ?? 0).toLocaleString("en-IN")}`,
    },
    {
      key: "leg2_target",
      header: "Leg 2",
      cell: (r) => `₹ ${Number(r.leg2_target ?? 0).toLocaleString("en-IN")}`,
    },
    {
      key: "leg3_target",
      header: "Leg 3",
      cell: (r) => `₹ ${Number(r.leg3_target ?? 0).toLocaleString("en-IN")}`,
    },
    {
      key: "reward_amount",
      header: "Reward amount",
      cell: (r) => `₹ ${Number(r.reward_amount ?? 0).toLocaleString("en-IN")}`,
    },
    { key: "is_active", header: "Active", cell: (r) => (r.is_active === false ? "No" : "Yes") },
  ];

  const creditCols: Column<Row>[] = [
    { key: "associate_id", header: "Associate", cell: (r) => String(r.associate_id ?? "—") },
    {
      key: "amount",
      header: "Credit",
      cell: (r) => <span className="tabular-nums font-semibold text-[color:var(--brand-dark)]">₹ {Number(r.amount ?? 0).toLocaleString("en-IN")}</span>,
    },
    { key: "narration", header: "Narration", cell: (r) => String(r.narration || "—") },
    {
      key: "created_at",
      header: "Date",
      cell: (r) => (r.created_at ? new Date(String(r.created_at)).toLocaleString("en-IN") : "—"),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reward Achievers"
        subtitle="Official 9-level table (each level from 0) + live reward-wallet ledger"
        actions={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
      />
      <div>
        <h2 className="mb-2 text-sm font-semibold text-[color:var(--brand-dark)]">Official milestone rewards</h2>
        <DataTable data={plans} columns={planCols} searchable={(r) => `${r.name} ${r.title}`} />
      </div>
      <div>
        <h2 className="mb-2 text-sm font-semibold text-[color:var(--brand-dark)]">Reward wallet credits (live)</h2>
        <DataTable data={credits} columns={creditCols} searchable={(r) => `${r.associate_id} ${r.narration}`} />
      </div>
    </div>
  );
}
