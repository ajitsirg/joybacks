import { createFileRoute } from "@tanstack/react-router";
import { UserList } from "@/components/users-list";

export const Route = createFileRoute("/_app/users/inactive")({
  ssr: false,
  head: () => ({ meta: [{ title: "In-Active Users — JoyClub Associate" }] }),
  component: InactiveUsersPage,
});

function InactiveUsersPage() {
  return <UserList status="inactive" title="In-Active Users" subtitle="Associates with status = inactive" />;
}
