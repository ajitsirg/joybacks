import { createFileRoute } from "@tanstack/react-router";
import { UserList } from "@/components/users-list";

export const Route = createFileRoute("/_app/users/active")({
  ssr: false,
  head: () => ({ meta: [{ title: "Active Associates — JoyClub Associate" }] }),
  component: ActiveUsersPage,
});

function ActiveUsersPage() {
  return <UserList status="active" title="Active Associates" subtitle="Live associates with status = active" />;
}
