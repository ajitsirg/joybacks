import { createFileRoute } from "@tanstack/react-router";
import { LiveIncomePage } from "@/components/live-income";

export const Route = createFileRoute("/_app/income/roi")({
  head: () => ({ meta: [{ title: "ROI Income — JoyClub Associate" }] }),
  component: () => (
    <LiveIncomePage
      title="ROI / Monthly Return"
      subtitle="Upline only: ₹2,200 base ROI × level % (L1 5% = ₹110). Investor is not paid ₹2,200."
      walletType="roi"
    />
  ),
});
