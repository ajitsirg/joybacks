import { Outlet, createFileRoute } from "@tanstack/react-router";

/** Layout for /users/team, /users/team/levels, /users/team/level/$level */
export const Route = createFileRoute("/_app/users/team")({
  ssr: false,
  component: () => <Outlet />,
});
