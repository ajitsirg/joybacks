import { createFileRoute } from "@tanstack/react-router";
import { LiveIncomePage } from "@/components/live-income";
import { RewardProgressBoard } from "@/components/reward-progress-board";

export const Route = createFileRoute("/_app/income/reward")({
  head: () => ({ meta: [{ title: "Reward Income — JoyClub Associate" }] }),
  component: Page,
});

function Page() {
  return (
    <div className="space-y-6">
      <LiveIncomePage
        title="Reward Income"
        subtitle="Milestone cash only — 9 levels from 0 (L1 ₹25,00,000 → ₹75,000). Not sale or ROI %."
        walletType="reward"
      />
      <RewardProgressBoard />
    </div>
  );
}
