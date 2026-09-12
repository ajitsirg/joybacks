/** Public site used in share / referral links. */
export const JOYCLUB_PUBLIC_URL = "https://joyclubs.in";
const REGISTER_PATH = `${import.meta.env.BASE_URL}register`;

export type ReferralShareInput = {
  associateId: string;
  referralCode?: string;
  mobile?: string;
  senderName?: string;
};

/** Prefer associate ID for lead_reference joins; fall back to referral_code. */
export function referralIdForJoin(input: ReferralShareInput): string {
  return (input.associateId || input.referralCode || "").trim().toUpperCase();
}

export function referralJoinUrl(input: ReferralShareInput): string {
  const id = referralIdForJoin(input);
  if (!id) return `${JOYCLUB_PUBLIC_URL}${REGISTER_PATH}`;
  return `${JOYCLUB_PUBLIC_URL}${REGISTER_PATH}?ref=${encodeURIComponent(id)}`;
}

export function formatShareMobile(mobile?: string): string {
  const digits = (mobile || "").replace(/\D/g, "");
  if (!digits) return "";
  if (digits.length === 10) return `+91 ${digits}`;
  if (digits.startsWith("91") && digits.length === 12) return `+${digits.slice(0, 2)} ${digits.slice(2)}`;
  return mobile?.trim() || "";
}

export function buildReferralWhatsAppMessage(input: ReferralShareInput): string {
  const id = referralIdForJoin(input);
  const joinUrl = referralJoinUrl(input);
  const mobile = formatShareMobile(input.mobile);
  const name = (input.senderName || "").trim();
  const greeter = name ? `I'm ${name} from JoyClub Associate.` : "I'm inviting you to JoyClub Associate.";

  const lines = [
    "🙏 Join JoyClub Associate with me!",
    "",
    greeter,
    "",
    "Earn More. Enjoy More. Live More.",
    "JoyClub is a smart membership & rewards platform — grow income, unlock benefits, and build with a trusted associate network.",
    "",
    `⭐ My Referral ID: ${id}`,
  ];
  if (mobile) lines.push(`📱 My Mobile: ${mobile}`);
  lines.push(
    "",
    `👉 Join with my referral: ${joinUrl}`,
    "",
    `🌐 Website: ${JOYCLUB_PUBLIC_URL}/`,
    "",
    "Register today and start your JoyClub journey!",
  );
  return lines.join("\n");
}

/** Opens WhatsApp with a prefilled message (user picks any contact). */
export function whatsAppShareUrl(message: string): string {
  return `https://wa.me/?text=${encodeURIComponent(message)}`;
}
