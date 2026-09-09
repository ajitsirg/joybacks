import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { TeamMemberTable } from "@/components/team-member-table";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_app/users/team/level/$level")({
  ssr: false,
  head: ({ params }) => ({
    meta: [{ title: `Level ${params.level} Team — JoyClub Associate` }],
  }),
  component: TeamLevelMembersPage,
});

function TeamLevelMembersPage() {
  const { level: levelParam } = Route.useParams();
  const level = Math.max(1, Number.parseInt(levelParam, 10) || 1);

  return (
    <div className="space-y-3">
      <Button asChild type="button" variant="outline" size="sm" className="gap-1.5">
        <Link to="/users/team">
          <ArrowLeft className="h-3.5 w-3.5" />
          All Team
        </Link>
      </Button>
      <TeamMemberTable
        title="All Team"
        subtitle={`LEVEL ${level} members only`}
        legLevel={level}
      />
    </div>
  );
}
