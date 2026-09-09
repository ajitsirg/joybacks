import { createFileRoute } from "@tanstack/react-router";
import { LiveWithdrawTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/withdraw/completed")({
  head: () => ({ meta: [{ title: "Completed Withdrawals — JoyClub Associate" }] }),
  component: () => <LiveWithdrawTable title="Completed Withdrawals" subtitle="Settled payouts." status="completed" />,
});
