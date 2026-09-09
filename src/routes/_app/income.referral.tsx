import { createFileRoute } from "@tanstack/react-router";
import { LiveIncomePage } from "@/components/live-income";

export const Route = createFileRoute("/_app/income/referral")({
  head: () => ({ meta: [{ title: "Level Income — JoyClub Associate" }] }),
  component: () => (
    <LiveIncomePage
      title="Level / Referral Income"
      subtitle="Sale commission on ₹2,20,000 farmhouse (L1 5% = ₹11,000). Unlock level N only when you have N immediate members with a sale."
      walletType="income"
    />
  ),
});
