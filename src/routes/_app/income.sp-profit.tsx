import { createFileRoute } from "@tanstack/react-router";
import { LiveIncomePage } from "@/components/live-income";

export const Route = createFileRoute("/_app/income/sp-profit")({
  head: () => ({ meta: [{ title: "S.P. / ROI Income — JoyClub Associate" }] }),
  component: () => (
    <LiveIncomePage
      title="S.P. / ROI Level Income"
      subtitle="ROI-on-ROI: Base ROI ₹2,200 × level % (not investment × %). Investor is not paid the ₹2,200."
      walletType="roi"
    />
  ),
});
