import { createFileRoute } from "@tanstack/react-router";
import { LiveDepositTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/deposit/complete")({
  head: () => ({ meta: [{ title: "Completed Deposits — JoyClub Associate" }] }),
  component: () => <LiveDepositTable title="Completed Deposits" subtitle="Successfully credited deposits." status="completed" />,
});
