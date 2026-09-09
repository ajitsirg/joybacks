import { createFileRoute } from "@tanstack/react-router";
import { LiveKycTable } from "@/components/live-ops";

export const Route = createFileRoute("/_app/kyc/pending")({
  head: () => ({ meta: [{ title: "Pending KYC — JoyClub Associate" }] }),
  component: () => <LiveKycTable title="Pending KYC" subtitle="Verify identity documents." status="pending" showActions />,
});
