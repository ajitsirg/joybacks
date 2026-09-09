import { useMemo, useState, type ReactNode } from "react";
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Inbox, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type Column<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  className?: string;
  headerClassName?: string;
};

type Props<T> = {
  data: T[];
  columns: Column<T>[];
  searchable?: (row: T) => string;
  searchPlaceholder?: string;
  toolbar?: ReactNode;
  loading?: boolean;
  emptyTitle?: string;
  emptyHint?: string;
  rowActions?: (row: T) => ReactNode;
  onExport?: (kind: "csv" | "excel" | "pdf" | "print") => void;
  pageSize?: number;
};

export function DataTable<T extends { id: string | number }>({
  data,
  columns,
  searchable,
  searchPlaceholder = "Search…",
  toolbar,
  loading,
  emptyTitle = "Nothing here yet",
  emptyHint = "Try changing filters or come back later.",
  rowActions,
  onExport,
  pageSize: initialPageSize = 10,
}: Props<T>) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" } | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const filtered = useMemo(() => {
    let out = data;
    if (q && searchable) {
      const needle = q.toLowerCase();
      out = out.filter((r) => searchable(r).toLowerCase().includes(needle));
    }
    if (sort) {
      const col = columns.find((c) => c.key === sort.key);
      if (col?.sortValue) {
        out = [...out].sort((a, b) => {
          const av = col.sortValue!(a);
          const bv = col.sortValue!(b);
          if (av < bv) return sort.dir === "asc" ? -1 : 1;
          if (av > bv) return sort.dir === "asc" ? 1 : -1;
          return 0;
        });
      }
    }
    return out;
  }, [data, q, sort, columns, searchable]);

  const total = filtered.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, pageCount);
  const start = (currentPage - 1) * pageSize;
  const rows = filtered.slice(start, start + pageSize);

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex flex-col gap-3 border-b border-border p-3 sm:flex-row sm:items-center sm:justify-between sm:p-4">
        <div className="flex w-full flex-1 flex-col gap-2 sm:flex-row sm:items-center">
          {searchable && (
            <div className="relative w-full sm:max-w-sm">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setPage(1);
                }}
                placeholder={searchPlaceholder}
                className="h-10 pl-9"
              />
            </div>
          )}
          {toolbar}
        </div>
        {onExport && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="w-full gap-2 sm:w-auto">
                <Download className="h-4 w-4" /> Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onExport("csv")}>CSV</DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExport("excel")}>Excel</DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExport("pdf")}>PDF</DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExport("print")}>Print</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Mobile cards */}
      <div className="space-y-3 p-3 md:hidden">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)
        ) : rows.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
            <Inbox className="h-8 w-8 text-[color:var(--brand)]" />
            <div className="font-medium">{emptyTitle}</div>
            <div className="text-xs text-muted-foreground">{emptyHint}</div>
          </div>
        ) : (
          rows.map((row) => (
            <div key={String(row.id)} className="rounded-xl border border-border bg-[color:var(--hero)]/40 p-3">
              <div className="space-y-2">
                {columns.map((c) => (
                  <div key={c.key} className="flex items-start justify-between gap-3 text-sm">
                    <span className="shrink-0 text-xs font-medium uppercase tracking-wide text-muted-foreground">{c.header}</span>
                    <div className={cn("min-w-0 text-right text-foreground", c.className)}>{c.cell(row)}</div>
                  </div>
                ))}
              </div>
              {rowActions && (
                <div className="mt-3 flex flex-wrap justify-end gap-2 border-t border-border/70 pt-3">{rowActions(row)}</div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Desktop table */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="sticky top-0 z-10 bg-[color:var(--hero)] text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              {columns.map((c) => (
                <th key={c.key} className={cn("whitespace-nowrap px-4 py-3 font-medium", c.headerClassName)}>
                  {c.sortValue ? (
                    <button
                      onClick={() =>
                        setSort((s) =>
                          s?.key === c.key ? { key: c.key, dir: s.dir === "asc" ? "desc" : "asc" } : { key: c.key, dir: "asc" },
                        )
                      }
                      className="inline-flex items-center gap-1 hover:text-foreground"
                    >
                      {c.header}
                      <ArrowUpDown className="h-3 w-3" />
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              ))}
              {rowActions && <th className="px-4 py-3 text-right font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className="border-t border-border">
                  {columns.map((c) => (
                    <td key={c.key} className="px-4 py-3">
                      <Skeleton className="h-4 w-24" />
                    </td>
                  ))}
                  {rowActions && (
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-12" />
                    </td>
                  )}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (rowActions ? 1 : 0)} className="px-4 py-16">
                  <div className="flex flex-col items-center gap-2 text-center">
                    <div className="grid h-12 w-12 place-items-center rounded-full bg-[color:var(--hero)] text-[color:var(--brand)]">
                      <Inbox className="h-5 w-5" />
                    </div>
                    <div className="font-medium text-foreground">{emptyTitle}</div>
                    <div className="text-xs text-muted-foreground">{emptyHint}</div>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={String(row.id)} className="border-t border-border transition-colors hover:bg-[color:var(--muted)]">
                  {columns.map((c) => (
                    <td key={c.key} className={cn("px-4 py-3 align-middle text-foreground", c.className)}>
                      {c.cell(row)}
                    </td>
                  ))}
                  {rowActions && <td className="px-4 py-3 text-right">{rowActions(row)}</td>}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-border p-3 sm:flex-row sm:items-center sm:justify-between sm:p-4">
        <div className="text-xs text-muted-foreground">
          Showing {total === 0 ? 0 : start + 1}–{Math.min(start + pageSize, total)} of {total}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <Select
            value={String(pageSize)}
            onValueChange={(v) => {
              setPageSize(Number(v));
              setPage(1);
            }}
          >
            <SelectTrigger className="h-9 w-[110px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[10, 25, 50, 100].map((n) => (
                <SelectItem key={n} value={String(n)}>
                  {n} / page
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="icon" className="h-9 w-9" disabled={currentPage <= 1} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-[72px] text-center text-sm tabular-nums">
              {currentPage}/{pageCount}
            </div>
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9"
              disabled={currentPage >= pageCount}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    active: { bg: "var(--brand-tint)", text: "var(--brand-dark)", label: "Active" },
    approved: { bg: "var(--brand-tint)", text: "var(--brand-dark)", label: "Approved" },
    completed: { bg: "var(--brand-tint)", text: "var(--brand-dark)", label: "Completed" },
    paid: { bg: "var(--brand-tint)", text: "var(--brand-dark)", label: "Paid" },
    pending: { bg: "var(--warn-tint)", text: "var(--warn-text)", label: "Pending" },
    inactive: { bg: "var(--warn-tint)", text: "var(--warn-text)", label: "Inactive" },
    open: { bg: "var(--info-tint)", text: "var(--info-text)", label: "Open" },
    closed: { bg: "var(--brand-tint)", text: "var(--brand-dark)", label: "Closed" },
    blocked: { bg: "var(--danger-tint)", text: "var(--danger-text)", label: "Blocked" },
    rejected: { bg: "var(--danger-tint)", text: "var(--danger-text)", label: "Rejected" },
    suspended: { bg: "var(--danger-tint)", text: "var(--danger-text)", label: "Suspended" },
  };
  const key = (status ?? "").toString().toLowerCase();
  const s = map[key] ?? { bg: "var(--muted)", text: "var(--foreground)", label: status || "Unknown" };
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium" style={{ background: s.bg, color: s.text }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.text }} />
      {s.label}
    </span>
  );
}
