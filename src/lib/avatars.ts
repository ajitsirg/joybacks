/** Preset JoyClub avatars — rendered to PNG for upload (Django ImageField). */

export type PresetAvatar = {
  id: string;
  label: string;
  bg: string;
  accent: string;
  face: string;
};

export const PRESET_AVATARS: PresetAvatar[] = [
  { id: "grove", label: "Grove", bg: "#0B6B3A", accent: "#E6F5EC", face: "#FFFFFF" },
  { id: "mint", label: "Mint", bg: "#1FA971", accent: "#D8F0E2", face: "#064E2A" },
  { id: "forest", label: "Forest", bg: "#064E2A", accent: "#B7E0C8", face: "#EAF7F0" },
  { id: "jade", label: "Jade", bg: "#0E8F55", accent: "#FFFFFF", face: "#063D22" },
  { id: "sage", label: "Sage", bg: "#4A7C59", accent: "#E8F5EE", face: "#FFFFFF" },
  { id: "olive", label: "Olive", bg: "#6B8F3A", accent: "#F3F7E8", face: "#2A3D12" },
  { id: "teal", label: "Teal", bg: "#0F766E", accent: "#CCFBF1", face: "#FFFFFF" },
  { id: "sky", label: "Sky", bg: "#0369A1", accent: "#E0F2FE", face: "#FFFFFF" },
  { id: "indigo", label: "Indigo", bg: "#3730A3", accent: "#E0E7FF", face: "#FFFFFF" },
  { id: "rose", label: "Rose", bg: "#BE123C", accent: "#FFE4E6", face: "#FFFFFF" },
  { id: "amber", label: "Amber", bg: "#B45309", accent: "#FEF3C7", face: "#FFFFFF" },
  { id: "slate", label: "Slate", bg: "#334155", accent: "#E2E8F0", face: "#FFFFFF" },
];

function drawAvatar(ctx: CanvasRenderingContext2D, avatar: PresetAvatar, size: number) {
  const r = size / 2;
  ctx.clearRect(0, 0, size, size);

  // Circle background
  ctx.beginPath();
  ctx.arc(r, r, r, 0, Math.PI * 2);
  ctx.fillStyle = avatar.bg;
  ctx.fill();

  // Soft accent arc
  ctx.beginPath();
  ctx.arc(r, r * 1.15, r * 0.92, Math.PI * 1.05, Math.PI * 1.95);
  ctx.strokeStyle = avatar.accent;
  ctx.globalAlpha = 0.35;
  ctx.lineWidth = size * 0.08;
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Head
  ctx.beginPath();
  ctx.arc(r, r * 0.78, r * 0.28, 0, Math.PI * 2);
  ctx.fillStyle = avatar.face;
  ctx.fill();

  // Shoulders
  ctx.beginPath();
  ctx.ellipse(r, r * 1.45, r * 0.42, r * 0.32, 0, Math.PI, 0, true);
  ctx.fillStyle = avatar.face;
  ctx.fill();

  // Accent collar ring
  ctx.beginPath();
  ctx.arc(r, r * 1.12, r * 0.18, 0, Math.PI * 2);
  ctx.fillStyle = avatar.accent;
  ctx.globalAlpha = 0.55;
  ctx.fill();
  ctx.globalAlpha = 1;
}

export function avatarDataUrl(avatar: PresetAvatar, size = 256): string {
  if (typeof document === "undefined") return "";
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";
  drawAvatar(ctx, avatar, size);
  return canvas.toDataURL("image/png");
}

export async function avatarToPngFile(avatar: PresetAvatar, size = 256): Promise<File> {
  if (typeof document === "undefined") throw new Error("Canvas not available");
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas not available");
  drawAvatar(ctx, avatar, size);
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Failed to create image"))), "image/png");
  });
  return new File([blob], `avatar-${avatar.id}.png`, { type: "image/png" });
}
