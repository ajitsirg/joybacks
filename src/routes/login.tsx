import { createFileRoute, Link, Navigate, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { BadgeCheck, Eye, EyeOff, Lock, Mail, UserRound } from "lucide-react";
import { useAuth } from "@/lib/rbac";
import { ApiError, AuthAPI, setTokens } from "@/lib/api";
import { emailError, normalizeEmail } from "@/lib/validation";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

const assetUrl = (asset: string) => `${import.meta.env.BASE_URL}${asset}`;

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [{ title: "Sign in — JoyClub Associate" }],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { session, hydrated, applyApiUser } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"associate" | "staff">("associate");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [obscure, setObscure] = useState(true);
  const [loading, setLoading] = useState(false);

  if (!hydrated) return null;
  if (session) return <Navigate to="/dashboard" />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (mode === "staff") {
      const err = emailError(email, { required: true });
      if (err) {
        toast.error(err);
        return;
      }
    }
    if (mode === "associate" && !username.trim()) {
      toast.error("Enter your associate username");
      return;
    }
    setLoading(true);
    try {
      const payload =
        mode === "associate"
          ? { username: username.trim().toUpperCase(), password: password.trim(), remember_me: true }
          : { email: normalizeEmail(email), password: password.trim(), remember_me: true };
      const result = await AuthAPI.loginPayload(payload);
      setTokens({ access: result.access, refresh: result.refresh });
      applyApiUser(result.user);
      toast.success("Welcome to JoyClub Associate");
      navigate({ to: "/dashboard" });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-[color:var(--brand-dark)]">
      <div className="flex flex-col items-center px-6 pb-6 pt-10 text-center sm:pt-14">
        <img
          src={`${assetUrl("logo-full.png")}?v=20260911`}
          alt="Joy Hospitality and Real Estate Group"
          className="h-36 w-36 object-contain sm:h-40 sm:w-40"
        />
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-white">JoyClub Associate</h1>
        <p className="mt-2 text-sm text-white/75">Secure access to your wealth dashboard</p>
      </div>

      <div className="flex flex-1 items-center justify-center overflow-y-auto rounded-t-[1.75rem] bg-white px-5 py-8 shadow-[0_-8px_30px_rgba(0,0,0,0.12)] sm:px-8 sm:py-10">
        <div className="my-auto w-full max-w-md">
          <div className="grid grid-cols-2 gap-1 rounded-2xl bg-[#EAF7F0] p-1">
            <button
              type="button"
              onClick={() => {
                setMode("associate");
                setUsername("");
                setPassword("");
              }}
              className={`inline-flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-bold transition ${
                mode === "associate" ? "bg-white text-[color:var(--brand-dark)] shadow-sm" : "text-[#6B7C72]"
              }`}
            >
              <UserRound className="h-4 w-4" /> Associate
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("staff");
                setEmail("");
                setPassword("");
              }}
              className={`inline-flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-bold transition ${
                mode === "staff" ? "bg-white text-[color:var(--brand-dark)] shadow-sm" : "text-[#6B7C72]"
              }`}
            >
              <BadgeCheck className="h-4 w-4" /> Staff
            </button>
          </div>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {mode === "associate" ? (
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-[#3D5347]">
                  Username
                </Label>
                <div className="relative">
                  <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6B7C72]" />
                  <Input
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toUpperCase())}
                    placeholder="Enter username"
                    className="h-11 bg-[#F7FAF8] pl-10"
                    required
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-[#3D5347]">
                  Staff email
                </Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6B7C72]" />
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@joyclub.associate"
                    className="h-11 bg-[#F7FAF8] pl-10"
                    required
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-[#3D5347]">
                  Password
                </Label>
                <button
                  type="button"
                  className="text-xs font-bold text-[color:var(--brand)]"
                  onClick={() => toast.info("Ask your lead or admin to reset your password")}
                >
                  Forgot?
                </button>
              </div>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6B7C72]" />
                <Input
                  id="password"
                  type={obscure ? "password" : "text"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="h-11 bg-[#F7FAF8] pl-10 pr-10"
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8AA396]"
                  onClick={() => setObscure((v) => !v)}
                  aria-label={obscure ? "Show password" : "Hide password"}
                >
                  {obscure ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="h-12 w-full rounded-xl bg-[color:var(--brand-dark)] text-base font-bold hover:bg-[color:var(--brand-dark)]/90"
              disabled={loading}
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            New associate?{" "}
            <Link to="/register" className="font-extrabold text-[color:var(--brand-dark)]">
              Join now
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
