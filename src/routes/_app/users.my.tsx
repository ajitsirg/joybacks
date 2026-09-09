import { createFileRoute } from "@tanstack/react-router";
import { UserList } from "@/components/users-list";

export const Route = createFileRoute("/_app/users/my")({
  ssr: false,
  head: () => ({ meta: [{ title: "My Associates — JoyClub Associate" }] }),
  component: MyAssociatesPage,
});

function MyAssociatesPage() {
  return (
    <UserList
      scope="my"
      title="My Associates"
      subtitle="Only your under-leg — with relative level (Level 1 = direct)."
    />
  );
}
