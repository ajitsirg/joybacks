import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Pencil, Plus, Shield } from "lucide-react";
import { toast } from "sonner";
import { DataTable, StatusBadge, type Column } from "@/components/data-table";
import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  RolesAPI,
  StaffAPI,
  unwrapList,
  type ApiStaff,
  type ApiStaffRole,
} from "@/lib/api";

export const Route = createFileRoute("/_app/rbac/staff")({
  head: () => ({
    meta: [
      { title: "Staff Management — JoyClub Associate" },
      { name: "description", content: "Manage admin staff accounts and role assignments." },
      { property: "og:title", content: "Staff Management — JoyClub Associate" },
      { property: "og:description", content: "Manage admin staff accounts and role assignments." },
    ],
  }),
  component: StaffPage,
});

type FormState = {
  first_name: string;
  last_name: string;
  email: string;
  employee_code: string;
  department: string;
  password: string;
  is_suspended: boolean;
  role_ids: string[];
};

const emptyForm = (): FormState => ({
  first_name: "",
  last_name: "",
  email: "",
  employee_code: "",
  department: "",
  password: "",
  is_suspended: false,
  role_ids: [],
});

function StaffPage() {
  const [rows, setRows] = useState<ApiStaff[]>([]);
  const [roles, setRoles] = useState<ApiStaffRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ApiStaff | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [staffRes, rolesRes] = await Promise.all([
        StaffAPI.list({ page_size: 200 }),
        RolesAPI.list(),
      ]);
      setRows(unwrapList(staffRes));
      setRoles(unwrapList(rolesRes));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load staff");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm());
    setOpen(true);
  }

  function openEdit(s: ApiStaff) {
    setEditing(s);
    setForm({
      first_name: s.first_name || s.name?.split(/\s+/)[0] || "",
      last_name: s.last_name || s.name?.split(/\s+/).slice(1).join(" ") || "",
      email: s.email || "",
      employee_code: s.employee_code || "",
      department: s.department || "",
      password: "",
      is_suspended: !!s.is_suspended,
      role_ids: (s.roles || []).map((r) => String(r.id)),
    });
    setOpen(true);
  }

  function toggleRole(id: string) {
    setForm((f) => ({
      ...f,
      role_ids: f.role_ids.includes(id) ? f.role_ids.filter((x) => x !== id) : [...f.role_ids, id],
    }));
  }

  async function save() {
    if (!form.email.trim()) {
      toast.error("Email is required");
      return;
    }
    if (!editing && !form.password.trim()) {
      toast.error("Password is required for new staff");
      return;
    }
    setSaving(true);
    try {
      const body: Record<string, unknown> = {
        email: form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        employee_code: form.employee_code.trim() || undefined,
        department: form.department.trim(),
        is_suspended: form.is_suspended,
        role_ids: form.role_ids,
      };
      if (form.password.trim()) body.password = form.password.trim();

      if (editing) {
        await StaffAPI.update(editing.id, body);
        toast.success("Staff profile updated");
      } else {
        await StaffAPI.create(body);
        toast.success("Staff invited");
      }
      setOpen(false);
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function toggleSuspend(s: ApiStaff) {
    try {
      await StaffAPI.update(s.id, { is_suspended: !s.is_suspended });
      toast.success(`${s.name} ${!s.is_suspended ? "suspended" : "activated"}`);
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    }
  }

  const cols: Column<ApiStaff & { id: string }>[] = useMemo(
    () => [
      {
        key: "name",
        header: "Name",
        cell: (s) => <span className="font-medium">{s.name}</span>,
        sortValue: (s) => s.name,
      },
      {
        key: "email",
        header: "Email",
        cell: (s) => <span className="text-muted-foreground">{s.email}</span>,
      },
      {
        key: "roles",
        header: "Roles",
        cell: (s) => (
          <div className="flex flex-wrap gap-1">
            {(s.roles || []).length === 0 ? (
              <span className="text-xs text-muted-foreground">No roles</span>
            ) : (
              s.roles.map((r) => (
                <span
                  key={r.id}
                  className="rounded-full bg-[color:var(--brand-tint)] px-2 py-0.5 text-xs font-medium text-[color:var(--brand-dark)]"
                >
                  {r.name}
                </span>
              ))
            )}
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        cell: (s) => <StatusBadge status={s.is_suspended || s.is_active === false ? "suspended" : "active"} />,
      },
      {
        key: "last",
        header: "Last login",
        cell: (s) => (s.last_login_at ? new Date(s.last_login_at).toLocaleString("en-IN") : "—"),
      },
      {
        key: "ip",
        header: "IP",
        cell: (s) => s.last_login_ip ?? "—",
      },
    ],
    [],
  );

  const tableRows = rows.map((r) => ({ ...r, id: r.id }));

  return (
    <div>
      <PageHeader
        title="Staff Management"
        subtitle={`${rows.length} admin accounts`}
        actions={
          <div className="flex items-center gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
            <Button className="gap-2" onClick={openCreate}>
              <Plus className="h-4 w-4" /> Invite staff
            </Button>
          </div>
        }
      />

      <DataTable
        data={tableRows}
        columns={cols}
        loading={loading}
        searchable={(s) => `${s.name} ${s.email} ${s.employee_code} ${(s.roles || []).map((r) => r.name).join(" ")}`}
        rowActions={(s) => (
          <div className="flex flex-wrap justify-end gap-2">
            <Button size="sm" variant="outline" className="gap-1.5" onClick={() => openEdit(s)}>
              <Pencil className="h-3.5 w-3.5" /> Edit
            </Button>
            <Button size="sm" variant="outline" onClick={() => void toggleSuspend(s)}>
              {s.is_suspended ? "Activate" : "Suspend"}
            </Button>
          </div>
        )}
      />

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit staff profile" : "Invite staff"}</DialogTitle>
          </DialogHeader>

          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label>First name</Label>
                <Input
                  className="mt-1.5"
                  value={form.first_name}
                  onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
                />
              </div>
              <div>
                <Label>Last name</Label>
                <Input
                  className="mt-1.5"
                  value={form.last_name}
                  onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <Label>Email</Label>
              <Input
                className="mt-1.5"
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label>Employee code</Label>
                <Input
                  className="mt-1.5"
                  value={form.employee_code}
                  onChange={(e) => setForm((f) => ({ ...f, employee_code: e.target.value }))}
                  placeholder="Auto if blank"
                />
              </div>
              <div>
                <Label>Department</Label>
                <Input
                  className="mt-1.5"
                  value={form.department}
                  onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <Label>{editing ? "New password (optional)" : "Password"}</Label>
              <Input
                className="mt-1.5"
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                placeholder={editing ? "Leave blank to keep current" : "Min 6 characters"}
              />
            </div>

            <label className="flex items-center gap-2 rounded-lg border border-border p-3">
              <Checkbox
                checked={form.is_suspended}
                onCheckedChange={(v) => setForm((f) => ({ ...f, is_suspended: !!v }))}
              />
              <div>
                <div className="text-sm font-medium">Suspended</div>
                <div className="text-xs text-muted-foreground">Hide/deactivate login without deleting data</div>
              </div>
            </label>

            <div>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <Shield className="h-4 w-4 text-[color:var(--brand)]" />
                Allot roles / permissions
              </div>
              <p className="mb-2 text-xs text-muted-foreground">
                Roles carry permissions. Assign one or more roles to this staff member.
              </p>
              <div className="max-h-56 space-y-2 overflow-y-auto rounded-xl border border-border p-2">
                {roles.length === 0 ? (
                  <p className="p-2 text-sm text-muted-foreground">No roles found. Create roles first.</p>
                ) : (
                  roles.map((r) => {
                    const on = form.role_ids.includes(String(r.id));
                    const permCount = r.permissions?.length ?? 0;
                    return (
                      <label
                        key={r.id}
                        className="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3 hover:bg-muted"
                      >
                        <Checkbox checked={on} onCheckedChange={() => toggleRole(String(r.id))} />
                        <div className="min-w-0">
                          <div className="text-sm font-medium">{r.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {r.description || `${permCount} permissions`}
                          </div>
                        </div>
                      </label>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void save()} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : editing ? "Save changes" : "Invite"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
