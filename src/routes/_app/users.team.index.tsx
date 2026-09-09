import { createFileRoute } from "@tanstack/react-router";
import { TeamMemberTable } from "@/components/team-member-table";

export const Route = createFileRoute("/_app/users/team/")({
  ssr: false,
  head: () => ({ meta: [{ title: "All Team — JoyClub Associate" }] }),
  component: AllTeamPage,
});

function AllTeamPage() {
  return (
    <TeamMemberTable
      title="All Team"
      subtitle="Your under-leg team — click View to see only that level"
      showView
    />
  );
}
