import { createFileRoute } from "@tanstack/react-router";
import { LiveDepositTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/deposit/rejected")({
  head: () => ({ meta: [{ title: "Rejected Deposits — JoyClub Associate" }] }),
  component: () => <LiveDepositTable title="Rejected Deposits" subtitle="Declined deposit requests." status="rejected" />,
});
