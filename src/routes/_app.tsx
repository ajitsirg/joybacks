import { createFileRoute, Navigate } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { WaitingApprovalGate } from "@/components/waiting-approval";
import { useAuth } from "@/lib/rbac";

export const Route = createFileRoute("/_app")({
  // Auth + localStorage session are client-only; skip SSR to avoid provider races.
  ssr: false,
  component: AppLayout,
});

function AppLayout() {
  const { session, hydrated } = useAuth();
  if (!hydrated) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">
        Loading JoyClub Associate…
      </div>
    );
  }
  if (!session) return <Navigate to="/login" />;
  return (
    <WaitingApprovalGate>
      <AppShell />
    </WaitingApprovalGate>
  );
}
