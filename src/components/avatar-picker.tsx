import { useEffect, useState } from "react";
import { Camera, ImagePlus, Loader2, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PRESET_AVATARS, avatarDataUrl, avatarToPngFile, type PresetAvatar } from "@/lib/avatars";
import { cn } from "@/lib/utils";

function useAvatarPreviews(size = 128) {
  const [previews, setPreviews] = useState<{ avatar: PresetAvatar; src: string }[]>([]);
  useEffect(() => {
    setPreviews(PRESET_AVATARS.map((a) => ({ avatar: a, src: avatarDataUrl(a, size) })));
  }, [size]);
  return previews;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

type Props = {
  name: string;
  photoUrl?: string | null;
  /** Called with a PNG/JPEG file from upload or preset avatar */
  onPickFile: (file: File) => Promise<void> | void;
  size?: "md" | "lg";
  disabled?: boolean;
  className?: string;
};

/** Square profile photo frame (upload / avatar picker). */
export function ProfileAvatarEditor({
  name,
  photoUrl,
  onPickFile,
  size = "lg",
  disabled,
  className,
}: Props) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<PresetAvatar | null>(PRESET_AVATARS[0] ?? null);
  const [saving, setSaving] = useState(false);
  const [localPreview, setLocalPreview] = useState<string | null>(null);
  const previews = useAvatarPreviews(128);

  const displayUrl = localPreview || photoUrl || undefined;
  const dim = size === "lg" ? "h-28 w-28 sm:h-32 sm:w-32" : "h-16 w-16";

  async function applyFile(file: File) {
    setSaving(true);
    try {
      const preview = URL.createObjectURL(file);
      setLocalPreview(preview);
      await onPickFile(file);
      setOpen(false);
      toast.success("Profile photo updated");
    } catch (e) {
      setLocalPreview(null);
      toast.error(e instanceof Error ? e.message : "Could not update photo");
    } finally {
      setSaving(false);
    }
  }

  async function onUpload(fileList: FileList | null) {
    const file = fileList?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Please choose an image file");
      return;
    }
    await applyFile(file);
  }

  async function onConfirmAvatar() {
    if (!selected) return;
    const file = await avatarToPngFile(selected);
    await applyFile(file);
  }

  return (
    <div className={cn("relative inline-flex", className)}>
      <button
        type="button"
        disabled={disabled || saving}
        onClick={() => setOpen(true)}
        className={cn(
          dim,
          "relative overflow-hidden rounded-xl border-2 border-dashed border-[color:var(--hero-border)] bg-white shadow-sm transition hover:border-[color:var(--brand)]",
          displayUrl && "border-solid border-white",
        )}
        aria-label="Change profile photo"
      >
        {displayUrl ? (
          <img src={displayUrl} alt={name} className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full flex-col items-center justify-center gap-1 bg-[color:var(--brand-tint)] text-[color:var(--brand-dark)]">
            {initials(name) ? (
              <span className="text-2xl font-semibold">{initials(name)}</span>
            ) : (
              <UserRound className="h-8 w-8 opacity-60" />
            )}
            <span className="text-[10px] font-medium uppercase tracking-wide opacity-70">Square photo</span>
          </span>
        )}
      </button>

      <Button
        type="button"
        size="icon"
        variant="secondary"
        disabled={disabled || saving}
        className="absolute -bottom-1 -right-1 h-9 w-9 rounded-lg border border-border bg-white shadow-sm"
        onClick={() => setOpen(true)}
        aria-label="Change profile photo"
      >
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Profile photo</DialogTitle>
            <DialogDescription>
              Upload a clear square photo, or pick an avatar if you don’t have one.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted/40 px-4 py-5 text-center hover:bg-muted/70">
              <div className="grid h-20 w-20 place-items-center overflow-hidden rounded-xl border border-border bg-white">
                {displayUrl ? (
                  <img src={displayUrl} alt="" className="h-full w-full object-cover" />
                ) : (
                  <ImagePlus className="h-6 w-6 text-[color:var(--brand)]" />
                )}
              </div>
              <span className="text-sm font-medium">Upload square photo</span>
              <span className="text-xs text-muted-foreground">JPG, PNG — face centered</span>
              <input
                type="file"
                accept="image/*"
                className="sr-only"
                disabled={saving}
                onChange={(e) => void onUpload(e.target.files)}
              />
            </label>

            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Or choose an avatar
              </div>
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                {previews.map(({ avatar, src }) => {
                  const on = selected?.id === avatar.id;
                  return (
                    <button
                      key={avatar.id}
                      type="button"
                      disabled={saving}
                      title={avatar.label}
                      onClick={() => setSelected(avatar)}
                      className={cn(
                        "rounded-xl p-0.5 ring-2 transition",
                        on ? "ring-[color:var(--brand)]" : "ring-transparent hover:ring-[color:var(--hero-border)]",
                      )}
                    >
                      <img
                        src={src}
                        alt={avatar.label}
                        className="h-12 w-12 rounded-lg object-cover sm:h-14 sm:w-14"
                      />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" disabled={saving} onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="button" disabled={saving || !selected} onClick={() => void onConfirmAvatar()}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Use selected avatar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** Compact square avatar grid for register (no dialog). */
export function AvatarChoiceGrid({
  value,
  onChange,
  disabled,
}: {
  value?: string | null;
  onChange: (avatar: PresetAvatar, file: File) => void;
  disabled?: boolean;
}) {
  const previews = useAvatarPreviews(96);

  return (
    <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
      {previews.map(({ avatar, src }) => {
        const on = value === avatar.id;
        return (
          <button
            key={avatar.id}
            type="button"
            disabled={disabled}
            title={avatar.label}
            onClick={() => {
              void avatarToPngFile(avatar).then((file) => onChange(avatar, file));
            }}
            className={cn(
              "rounded-xl p-0.5 ring-2 transition",
              on ? "ring-[color:var(--brand)]" : "ring-transparent hover:ring-[color:var(--hero-border)]",
            )}
          >
            {src ? (
              <img src={src} alt={avatar.label} className="h-12 w-12 rounded-lg object-cover" />
            ) : (
              <span
                className="block h-12 w-12 rounded-lg"
                style={{ background: avatar.bg }}
                aria-hidden
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
