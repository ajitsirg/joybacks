import { useEffect, useMemo, useState } from "react";
import { Check, Copy, MessageCircle, Share2 } from "lucide-react";
import { toast } from "sonner";
import { AuthAPI } from "@/lib/api";
import { useAuth } from "@/lib/rbac";
import {
  buildReferralWhatsAppMessage,
  referralIdForJoin,
  referralJoinUrl,
  whatsAppShareUrl,
} from "@/lib/referral";

export function ReferralShareCard() {
  const { session } = useAuth();
  const [associateId, setAssociateId] = useState(session?.associateId ?? "");
  const [referralCode, setReferralCode] = useState("");
  const [mobile, setMobile] = useState("");
  const [senderName, setSenderName] = useState(session?.name ?? "");
  const [copied, setCopied] = useState<"id" | "link" | "msg" | null>(null);

  useEffect(() => {
    AuthAPI.me()
      .then((me) => {
        const a = me.associate;
        if (!a?.associate_id) return;
        setAssociateId(a.associate_id);
        setReferralCode(a.referral_code ?? "");
        setMobile(a.mobile ?? me.phone ?? "");
        setSenderName([me.first_name, me.last_name].filter(Boolean).join(" ") || me.username || session?.name || "");
      })
      .catch(() => {
        /* keep session fallback */
      });
  }, [session?.name]);

  const shareInput = useMemo(
    () => ({ associateId, referralCode, mobile, senderName }),
    [associateId, referralCode, mobile, senderName],
  );
  const refId = referralIdForJoin(shareInput);
  const joinUrl = referralJoinUrl(shareInput);
  const message = useMemo(() => buildReferralWhatsAppMessage(shareInput), [shareInput]);
  const waUrl = whatsAppShareUrl(message);

  if (!refId) return null;

  async function copy(text: string, kind: "id" | "link" | "msg") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      toast.success(kind === "id" ? "Referral ID copied" : kind === "link" ? "Join link copied" : "Message copied");
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      toast.error("Could not copy");
    }
  }

  return (
    <section className="rounded-2xl bg-gradient-to-br from-[#0B3D24] via-[#062A18] to-[#04180F] p-5 text-white shadow-[0_1px_0_rgba(15,36,24,0.04)] ring-1 ring-[#F5D56A]/25">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#F5D56A]">Referral</p>
          <h3 className="mt-1 text-lg font-extrabold tracking-tight">Invite on WhatsApp</h3>
          <p className="mt-1 max-w-xl text-sm text-white/70">
            Share JoyClub with your referral ID, join link, and mobile — message opens ready to send.
          </p>
        </div>
        <Share2 className="h-6 w-6 shrink-0 text-[#F5D56A]" />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-white/45">Your referral ID</p>
          <div className="mt-1 flex items-center justify-between gap-2">
            <p className="font-mono text-lg font-extrabold text-[#F5D56A]">{refId}</p>
            <button
              type="button"
              onClick={() => void copy(refId, "id")}
              className="grid h-8 w-8 place-items-center rounded-lg border border-white/15 text-white/80 hover:border-[#F5D56A] hover:text-[#F5D56A]"
              aria-label="Copy referral ID"
            >
              {copied === "id" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
          {referralCode && referralCode.toUpperCase() !== refId ? (
            <p className="mt-1 text-xs text-white/50">Code: {referralCode}</p>
          ) : null}
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-white/45">Join link</p>
          <div className="mt-1 flex items-start justify-between gap-2">
            <p className="break-all text-sm font-medium text-white/90">{joinUrl}</p>
            <button
              type="button"
              onClick={() => void copy(joinUrl, "link")}
              className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/15 text-white/80 hover:border-[#F5D56A] hover:text-[#F5D56A]"
              aria-label="Copy join link"
            >
              {copied === "link" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <a
          href={waUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#25D366] px-5 text-sm font-extrabold text-white transition hover:bg-[#1ebe57]"
        >
          <MessageCircle className="h-4 w-4" />
          Share on WhatsApp
        </a>
        <button
          type="button"
          onClick={() => void copy(message, "msg")}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#F5D56A]/50 bg-white/5 px-5 text-sm font-bold text-[#F5D56A] transition hover:bg-white/10"
        >
          {copied === "msg" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          Copy full message
        </button>
      </div>

      <pre className="mt-4 max-h-40 overflow-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-black/25 p-3 text-[11px] leading-relaxed text-white/65">
        {message}
      </pre>
    </section>
  );
}
