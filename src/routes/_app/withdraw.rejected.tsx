import { createFileRoute } from "@tanstack/react-router";
import { LiveWithdrawTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/withdraw/rejected")({
  head: () => ({ meta: [{ title: "Rejected Withdrawals — JoyClub Associate" }] }),
  component: () => <LiveWithdrawTable title="Rejected Withdrawals" subtitle="Rejected requests (balance refunded)." status="rejected" />,
});
