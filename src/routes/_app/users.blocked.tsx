import { createFileRoute } from "@tanstack/react-router";
import { UserList } from "@/components/users-list";

export const Route = createFileRoute("/_app/users/blocked")({
  ssr: false,
  head: () => ({ meta: [{ title: "Blocked Users — JoyClub Associate" }] }),
  component: BlockedUsersPage,
});

function BlockedUsersPage() {
  return <UserList status="blocked" title="Blocked Users" subtitle="Associates with status = blocked" />;
}
