import { Outlet, createFileRoute } from "@tanstack/react-router";

/** Layout for /genealogy and /genealogy/shift — child routes render via Outlet. */
export const Route = createFileRoute("/_app/genealogy")({
  ssr: false,
  component: () => <Outlet />,
});
