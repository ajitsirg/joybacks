import { useEffect, useState } from "react";
import { AuthAPI, type ApiUser } from "@/lib/api";
import { useAuth } from "@/lib/rbac";

/**
 * Loads / refreshes associate status for banners — does NOT block dashboard access.
 * Active / Inactive / Pending / Rejected can all use the app; status is display-only.
 */
export function WaitingApprovalGate({ children }: { children: React.ReactNode }) {
  const { session, applyApiUser } = useAuth();
  const [, setUser] = useState<ApiUser | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const me = await AuthAPI.me();
        if (!alive) return;
        setUser(me);
        applyApiUser(me);
      } catch {
        if (alive) setUser(null);
      }
    })();
    const t = window.setInterval(async () => {
      try {
        const me = await AuthAPI.me();
        if (!alive) return;
        setUser(me);
        applyApiUser(me);
      } catch {
        /* ignore */
      }
    }, 30000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [session?.id, applyApiUser]);

  // Never lock the shell — status changes do not restrict access.
  return <>{children}</>;
}
