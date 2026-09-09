import { createFileRoute } from "@tanstack/react-router";
import { LiveDepositTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/deposit/pending")({
  head: () => ({ meta: [{ title: "Pending Deposits — JoyClub Associate" }] }),
  component: () => <LiveDepositTable title="Pending Deposits" subtitle="Approve to credit wallet, roll up business and pay level income." status="pending" showActions />,
});
