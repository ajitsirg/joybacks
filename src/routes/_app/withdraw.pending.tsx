import { createFileRoute } from "@tanstack/react-router";
import { LiveWithdrawTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/withdraw/pending")({
  head: () => ({ meta: [{ title: "Pending Withdrawals — JoyClub Associate" }] }),
  component: () => <LiveWithdrawTable title="Pending Withdrawals" subtitle="Review and settle payout requests." status="pending" showActions />,
});
