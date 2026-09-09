import { createFileRoute } from "@tanstack/react-router";
import { LiveKycTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/kyc/approved")({
  head: () => ({ meta: [{ title: "Approved KYC — JoyClub Associate" }] }),
  component: () => <LiveKycTable title="Approved KYC" subtitle="Verified associates." status="approved" />,
});
