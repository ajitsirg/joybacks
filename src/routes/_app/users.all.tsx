import { createFileRoute } from "@tanstack/react-router";
import { UserList } from "@/components/users-list";

export const Route = createFileRoute("/_app/users/all")({
  ssr: false,
  head: () => ({ meta: [{ title: "All Associates — JoyClub Associate" }] }),
  component: AllUsersPage,
});

function AllUsersPage() {
  return (
    <UserList
      title="All Associates"
      subtitle="All associates with tree level, reward level and performance level."
    />
  );
}
