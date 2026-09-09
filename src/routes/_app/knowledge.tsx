import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CmsAPI, resolveMediaUrl, unwrapList } from "@/lib/api";
import { useAuth } from "@/lib/rbac";

export const Route = createFileRoute("/_app/knowledge")({
  head: () => ({ meta: [{ title: "Knowledge Center — JoyClub Associate" }] }),
  component: KnowledgeCenter,
});

type Item = {
  id: string;
  title: string;
  body: string;
  audience: string;
  audience_label?: string;
  media_type: string;
  media_type_label?: string;
  file_url?: string | null;
  video_url?: string;
  is_published?: boolean;
  created_at?: string;
};

function embedUrl(raw: string) {
  try {
    const u = new URL(raw);
    if (u.hostname.includes("youtu.be")) return `https://www.youtube.com/embed/${u.pathname.replace("/", "")}`;
    if (u.hostname.includes("youtube.com")) {
      const id = u.searchParams.get("v");
      if (id) return `https://www.youtube.com/embed/${id}`;
    }
    if (u.hostname.includes("vimeo.com")) {
      const id = u.pathname.split("/").filter(Boolean).pop();
      if (id) return `https://player.vimeo.com/video/${id}`;
    }
  } catch {
    /* keep raw */
  }
  return raw;
}

function KnowledgeCenter() {
  const { session } = useAuth();
  const isStaff = !!(session?.isStaff || session?.isSuperuser);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState("all");
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await CmsAPI.knowledge({ page_size: 100 });
      setItems(unwrapList(data) as Item[]);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load tutorials");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      toast.error("Enter a title");
      return;
    }
    if (!file && !videoUrl.trim()) {
      toast.error("Upload a file or paste a video link");
      return;
    }
    const fd = new FormData();
    fd.append("title", title.trim());
    fd.append("body", body.trim());
    fd.append("audience", audience);
    fd.append("is_published", "true");
    if (file) {
      fd.append("file", file);
      const name = file.name.toLowerCase();
      const type = name.endsWith(".pdf")
        ? "pdf"
        : /\.(mp4|webm|mov|m4v)$/.test(name)
          ? "video"
          : "image";
      fd.append("media_type", type);
    } else {
      fd.append("media_type", "link");
      fd.append("video_url", videoUrl.trim());
    }
    setSaving(true);
    try {
      await CmsAPI.createKnowledge(fd);
      toast.success("Tutorial published");
      setTitle("");
      setBody("");
      setVideoUrl("");
      setFile(null);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    try {
      await CmsAPI.deleteKnowledge(id);
      toast.success("Removed");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Center"
        subtitle="Tutorials, PDFs, images, and videos for how to work on this panel."
      />

      {isStaff ? (
        <form
          onSubmit={upload}
          className="max-w-xl space-y-3 rounded-2xl border border-border bg-card/90 p-4"
        >
          <h2 className="text-sm font-semibold">Upload tutorial</h2>
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label>Steps / description</Label>
            <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Short steps" />
          </div>
          <div className="space-y-1.5">
            <Label>Who can see this</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            >
              <option value="all">Everyone</option>
              <option value="associate">Associates</option>
              <option value="staff">Admin / Staff</option>
              <option value="finance">Finance Manager</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>File (PDF, image, or video)</Label>
            <Input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp,.gif,.mp4,.webm,.mov,.m4v,image/*,video/*,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Or video link</Label>
            <Input
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://youtube.com/…"
            />
          </div>
          <Button type="submit" disabled={saving}>
            {saving ? "Publishing…" : "Publish tutorial"}
          </Button>
        </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading tutorials…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No tutorials yet.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((item) => {
            const href = resolveMediaUrl(item.file_url) || item.video_url;
            return (
              <article key={item.id} className="space-y-3 rounded-2xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">{item.title}</h3>
                    <p className="text-xs text-muted-foreground">
                      {item.media_type_label || item.media_type}
                      {isStaff ? ` · ${item.audience_label || item.audience}` : ""}
                    </p>
                  </div>
                  {isStaff ? (
                    <Button size="sm" variant="outline" onClick={() => void remove(item.id)}>
                      Remove
                    </Button>
                  ) : null}
                </div>
                {item.body ? <p className="whitespace-pre-wrap text-sm text-muted-foreground">{item.body}</p> : null}
                {item.media_type === "image" && href ? (
                  <img src={href} alt={item.title} className="max-h-72 w-full rounded-md object-contain" />
                ) : null}
                {item.media_type === "video" && href ? (
                  <video src={href} controls className="w-full rounded-md" />
                ) : null}
                {item.media_type === "link" && item.video_url ? (
                  <iframe
                    title={item.title}
                    src={embedUrl(item.video_url)}
                    className="aspect-video w-full rounded-md"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                ) : null}
                {item.media_type === "pdf" && href ? (
                  <a href={href} target="_blank" rel="noreferrer" className="text-sm underline">
                    Open PDF
                  </a>
                ) : null}
                {item.media_type !== "link" && item.media_type !== "image" && item.media_type !== "video" && href ? (
                  <a href={href} target="_blank" rel="noreferrer" className="text-sm underline">
                    Open file
                  </a>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
