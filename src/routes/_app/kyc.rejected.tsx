import { createFileRoute } from "@tanstack/react-router";
import { LiveKycTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/kyc/rejected")({
  head: () => ({ meta: [{ title: "Rejected KYC — JoyClub Associate" }] }),
  component: () => <LiveKycTable title="Rejected KYC" subtitle="Declined submissions." status="rejected" />,
});
