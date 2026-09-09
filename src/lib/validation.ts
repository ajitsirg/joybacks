/** Shared client-side email / mobile checks (India-first). */

const MOBILE_RE = /^[6-9]\d{9}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i;

export function normalizeMobile(value: string): string {
  let digits = (value || "").replace(/\D/g, "");
  if (digits.length > 10 && digits.startsWith("91")) digits = digits.slice(2);
  if (digits.length === 11 && digits.startsWith("0")) digits = digits.slice(1);
  if (digits.length > 10) digits = digits.slice(-10);
  return digits;
}

export function isValidMobile(value: string): boolean {
  return MOBILE_RE.test(normalizeMobile(value));
}

export function mobileError(value: string): string | null {
  const m = normalizeMobile(value);
  if (!m) return "Mobile number is required";
  if (m.length !== 10) return "Enter a valid 10-digit mobile number";
  if (!MOBILE_RE.test(m)) return "Indian mobile must start with 6, 7, 8, or 9";
  return null;
}

export function normalizeEmail(value: string): string {
  return (value || "").trim().toLowerCase();
}

export function isValidEmail(value: string, { required = false } = {}): boolean {
  const email = normalizeEmail(value);
  if (!email) return !required;
  return EMAIL_RE.test(email);
}

export function emailError(value: string, { required = false } = {}): string | null {
  const email = normalizeEmail(value);
  if (!email) return required ? "Email is required" : null;
  if (!EMAIL_RE.test(email)) return "Enter a valid email address";
  return null;
}
