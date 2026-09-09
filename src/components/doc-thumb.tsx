import { FileText, ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

function isImageUrl(url: string) {
  return /\.(jpe?g|png|gif|webp|bmp|svg)(\?|$)/i.test(url);
}

type DocThumbProps = {
  label: string;
  url?: string | null;
  className?: string;
};

/** Small clickable attachment preview (image thumbnail or file icon). */
export function DocThumb({ label, url, className }: DocThumbProps) {
  if (!url) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-border bg-muted/30 p-2 text-center",
          className,
        )}
      >
        <div className="grid h-20 w-full place-items-center rounded-lg bg-muted/40 text-muted-foreground">
          <ImageIcon className="h-6 w-6 opacity-50" />
        </div>
        <span className="text-[11px] text-muted-foreground">{label}: missing</span>
      </div>
    );
  }

  const image = isImageUrl(url);

  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className={cn(
        "group flex flex-col gap-1.5 rounded-xl border border-[color:var(--hero-border)] bg-white p-2 shadow-sm transition hover:border-[color:var(--brand)] hover:shadow-md",
        className,
      )}
      title={`Open ${label}`}
    >
      <div className="relative h-24 w-full overflow-hidden rounded-lg bg-[color:var(--brand-tint)]">
        {image ? (
          <img
            src={url}
            alt={label}
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
            loading="lazy"
          />
        ) : (
          <div className="grid h-full place-items-center text-[color:var(--brand-dark)]">
            <FileText className="h-8 w-8" />
          </div>
        )}
      </div>
      <span className="truncate text-center text-xs font-medium text-[color:var(--brand-dark)]">{label}</span>
    </a>
  );
}

type KycDocs = {
  profile_photo_url?: string | null;
  aadhaar_document_url?: string | null;
  aadhaar_front_url?: string | null;
  aadhaar_back_url?: string | null;
  aadhaar_attached?: boolean;
  pan_document_url?: string | null;
  bank_document_url?: string | null;
  full_name?: string;
  pan?: string;
  aadhaar?: string;
  bank_name?: string;
  account_number?: string;
  ifsc?: string;
  upi_id?: string;
  status?: string;
};

export function AttachmentGallery({
  kyc,
  title = "Attachments",
}: {
  kyc?: KycDocs | null;
  title?: string;
}) {
  if (!kyc) {
    return (
      <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
        <h2 className="mb-2 text-sm font-semibold text-[color:var(--brand-dark)]">{title}</h2>
        <p className="text-sm text-muted-foreground">No KYC documents uploaded yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <h2 className="text-sm font-semibold text-[color:var(--brand-dark)]">{title}</h2>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span
            className={
              kyc.aadhaar_attached
                ? "rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800"
                : "rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800"
            }
          >
            Aadhaar: {kyc.aadhaar_attached ? "attached" : "incomplete (need front + back)"}
          </span>
          {kyc.status ? (
            <span className="capitalize text-muted-foreground">KYC: {kyc.status}</span>
          ) : null}
        </div>
      </div>
      {(kyc.full_name || kyc.pan || kyc.aadhaar) && (
        <dl className="mb-4 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {kyc.full_name ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">KYC name</dt>
              <dd className="font-medium">{kyc.full_name}</dd>
            </div>
          ) : null}
          {kyc.pan ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">PAN</dt>
              <dd className="font-medium">{kyc.pan}</dd>
            </div>
          ) : null}
          {kyc.aadhaar ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">Aadhaar</dt>
              <dd className="font-medium">{kyc.aadhaar}</dd>
            </div>
          ) : null}
          {kyc.bank_name ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">Bank</dt>
              <dd className="font-medium">{kyc.bank_name}</dd>
            </div>
          ) : null}
          {kyc.account_number ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">Account</dt>
              <dd className="font-medium">{kyc.account_number}</dd>
            </div>
          ) : null}
          {kyc.ifsc ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">IFSC</dt>
              <dd className="font-medium">{kyc.ifsc}</dd>
            </div>
          ) : null}
          {kyc.upi_id ? (
            <div className="rounded-lg bg-[color:var(--hero)]/50 px-3 py-2">
              <dt className="text-[11px] uppercase text-muted-foreground">UPI</dt>
              <dd className="font-medium">{kyc.upi_id}</dd>
            </div>
          ) : null}
        </dl>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <DocThumb label="Profile photo" url={kyc.profile_photo_url} />
        <DocThumb
          label="Aadhaar front"
          url={kyc.aadhaar_front_url || kyc.aadhaar_document_url}
        />
        <DocThumb label="Aadhaar back" url={kyc.aadhaar_back_url} />
        <DocThumb label="PAN" url={kyc.pan_document_url} />
        <DocThumb label="Bank proof" url={kyc.bank_document_url} />
      </div>
    </section>
  );
}
