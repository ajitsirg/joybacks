import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { useAuth, ALL_PERMISSIONS, type Permission, type Role } from "@/lib/rbac";
import { Plus, Shield } from "lucide-react";

export const Route = createFileRoute("/_app/rbac/roles")({
  head: () => ({ meta: [
    { title: "Role Management — JoyClub Associate" },
    { name: "description", content: "Create roles and toggle granular permissions." },
    { property: "og:title", content: "Role Management — JoyClub Associate" },
    { property: "og:description", content: "Create roles and toggle granular permissions." },
  ]}),
  component: RolesPage,
});

function RolesPage() {
  const { roles, updateRoles, logAudit } = useAuth();
  const [selectedId, setSelectedId] = useState(roles[0]?.id);
  const [newOpen, setNewOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const selected = roles.find(r => r.id === selectedId) ?? roles[0];
  const grouped = Object.entries(ALL_PERMISSIONS.reduce<Record<string, typeof ALL_PERMISSIONS>>((acc, p) => { (acc[p.module] ??= []).push(p); return acc; }, {}));

  function toggle(perm: Permission) {
    if (!selected) return;
    const has = selected.permissions.includes(perm);
    const next = has ? selected.permissions.filter(p => p !== perm) : [...selected.permissions, perm];
    updateRoles(roles.map(r => r.id === selected.id ? { ...r, permissions: next } : r));
    logAudit({ action: has ? "role.permission.revoke" : "role.permission.grant", target: `${selected.name}:${perm}` });
  }

  function createRole() {
    if (!newName.trim()) return;
    const role: Role = { id: `custom_${Date.now()}`, name: newName.trim(), description: newDesc.trim() || "Custom role", permissions: [] };
    updateRoles([...roles, role]);
    logAudit({ action: "role.create", target: role.name });
    toast.success(`Role "${role.name}" created`);
    setSelectedId(role.id); setNewName(""); setNewDesc(""); setNewOpen(false);
  }

  return (
    <div>
      <PageHeader title="Role Management" subtitle="Define roles and grant fine-grained permissions." actions={
        <Dialog open={newOpen} onOpenChange={setNewOpen}>
          <DialogTrigger asChild><Button className="gap-2"><Plus className="h-4 w-4" /> New role</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create a role</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label>Name</Label><Input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Regional Manager" className="mt-1.5" /></div>
              <div><Label>Description</Label><Input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="What this role can do" className="mt-1.5" /></div>
            </div>
            <DialogFooter><Button onClick={createRole}>Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      } />

      <div className="grid gap-4 lg:grid-cols-[280px,1fr]">
        <div className="rounded-2xl border border-border bg-card p-3">
          {roles.map(r => (
            <button key={r.id} onClick={() => setSelectedId(r.id)} className={`flex w-full items-start gap-3 rounded-xl p-3 text-left ${selected?.id === r.id ? "bg-[color:var(--brand-tint)]" : "hover:bg-muted"}`}>
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white text-[color:var(--brand-dark)]"><Shield className="h-4 w-4" /></div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2"><span className="truncate font-medium">{r.name}</span>{r.system && <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">system</span>}</div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground">{r.permissions.length} permissions</div>
              </div>
            </button>
          ))}
        </div>

        <div className="rounded-2xl border border-border bg-card p-6">
          {selected && (
            <>
              <div>
                <h3 className="text-lg font-semibold">{selected.name}</h3>
                <p className="text-sm text-muted-foreground">{selected.description}</p>
              </div>
              <div className="mt-6 space-y-6">
                {grouped.map(([module, perms]) => (
                  <div key={module}>
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{module}</div>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {perms.map(p => (
                        <label key={p.key} className="flex items-center gap-2 rounded-lg border border-border p-3 hover:bg-muted">
                          <Checkbox checked={selected.permissions.includes(p.key)} onCheckedChange={() => toggle(p.key)} />
                          <div className="min-w-0"><div className="text-sm font-medium">{p.action}</div><div className="truncate text-xs text-muted-foreground">{p.key}</div></div>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
