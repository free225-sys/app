import { useEffect, useState } from "react";
import { http } from "@/lib/api";
import { formatApiError, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, Loading } from "@/components/common";
import { BTN_DANGER, BTN_SMALL, INPUT, LABEL, Notice, ROLE_LABEL, fmtDate } from "./shared";

const ROLES = Object.keys(ROLE_LABEL);

const RoleBoxes = ({ value, onChange, prefix }) => (
  <div className="flex flex-wrap gap-3" role="group" aria-label="Rôles">
    {ROLES.map((r) => (
      <label key={r} className="inline-flex items-center gap-1.5 text-xs">
        <input type="checkbox" checked={value.includes(r)} onChange={(e) => onChange(e.target.checked ? [...value, r] : value.filter((x) => x !== r))} data-testid={`${prefix}-role-${r}`} />
        {ROLE_LABEL[r]}
      </label>
    ))}
  </div>
);

const CreateUser = ({ onCreated }) => {
  const [f, setF] = useState({ email: "", first_name: "", last_name: "", password: "", roles: ["learner"] });
  const [msg, setMsg] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    try {
      await http.post("/admin/users", f);
      setMsg({ kind: "ok", text: `Compte ${f.email} créé.` });
      setF({ email: "", first_name: "", last_name: "", password: "", roles: ["learner"] });
      onCreated();
    } catch (err) {
      setMsg({ kind: "error", text: formatApiError(err) });
    }
  };
  const field = (k, label, type = "text") => (
    <div><label htmlFor={`nu-${k}`} className={LABEL}>{label}</label>
      <input id={`nu-${k}`} type={type} className={`${INPUT} mt-1`} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} required data-testid={`new-user-${k}`} /></div>
  );
  return (
    <form onSubmit={submit} className="space-y-4 border border-[#e5e9ef] bg-white p-5" aria-label="Créer un compte" data-testid="new-user-form">
      <h3 className="text-sm font-semibold">Créer un compte</h3>
      <div className="grid gap-4 sm:grid-cols-2">{field("first_name", "Prénom")}{field("last_name", "Nom")}{field("email", "E-mail", "email")}{field("password", "Mot de passe initial (8 car. min.)", "password")}</div>
      <RoleBoxes value={f.roles} onChange={(roles) => setF({ ...f, roles })} prefix="new-user" />
      <button type="submit" className={BTN_PRIMARY} data-testid="new-user-submit">Créer le compte</button>
      {msg && <Notice kind={msg.kind} testId="new-user-message">{msg.text}</Notice>}
    </form>
  );
};

const UserRow = ({ u, me, onChange }) => {
  const [roles, setRoles] = useState(u.roles);
  const [msg, setMsg] = useState(null);
  const patch = async (body, ok) => {
    try {
      await http.patch(`/admin/users/${u.id}`, body);
      setMsg({ kind: "ok", text: ok });
      onChange();
    } catch (e) {
      setMsg({ kind: "error", text: formatApiError(e) });
    }
  };
  const dirty = [...roles].sort().join() !== [...u.roles].sort().join();
  return (
    <li className={`border border-[#e5e9ef] bg-white p-4 ${u.active ? "" : "opacity-70"}`} data-testid={`user-row-${u.email}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm"><strong>{u.first_name} {u.last_name}</strong> · <span className="font-mono text-xs">{u.email}</span>{me && " (vous)"}</p>
        <span className={`rounded-[10px] px-2 py-0.5 text-xs font-semibold ${u.active ? "bg-[#eef5f3] text-[#147c77]" : "bg-[#FBECEC] text-[#7E2828]"}`} data-testid={`user-active-${u.email}`}>{u.active ? "Actif" : "Désactivé"}</span>
      </div>
      <p className="mt-1 text-xs text-[#627086]">Créé le {fmtDate(u.created_at)}</p>
      <div className="mt-3"><RoleBoxes value={roles} onChange={setRoles} prefix={`user-${u.email}`} /></div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className={BTN_SMALL} disabled={!dirty || roles.length === 0} onClick={() => patch({ roles }, "Rôles mis à jour.")} data-testid={`user-save-roles-${u.email}`}>Enregistrer les rôles</button>
        {!me && (u.active
          ? <button type="button" className={BTN_DANGER} onClick={() => patch({ active: false }, "Compte désactivé.")} data-testid={`user-deactivate-${u.email}`}>Désactiver</button>
          : <button type="button" className={BTN_SMALL} onClick={() => patch({ active: true }, "Compte réactivé.")} data-testid={`user-activate-${u.email}`}>Réactiver</button>)}
      </div>
      {msg && <div className="mt-2"><Notice kind={msg.kind}>{msg.text}</Notice></div>}
    </li>
  );
};

export const Users = () => {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    const t = setTimeout(() => http.get("/admin/users", { params: { q: q || undefined, role: role || undefined } }).then((r) => alive && setItems(r.data)).catch((e) => alive && setError(e)), 200);
    return () => { alive = false; clearTimeout(t); };
  }, [q, role, tick]);
  const reload = () => setTick((t) => t + 1);
  return (
    <section aria-labelledby="users-title" className="space-y-6" data-testid="admin-users">
      <h2 id="users-title" className="text-2xl font-semibold tracking-tight">Utilisateurs</h2>
      <CreateUser onCreated={reload} />
      <div className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="users-q" className="sr-only">Rechercher</label>
        <input id="users-q" className={INPUT} placeholder="Rechercher par nom ou e-mail" value={q} onChange={(e) => setQ(e.target.value)} data-testid="users-search" />
        <label htmlFor="users-role" className="sr-only">Rôle</label>
        <select id="users-role" className={`${INPUT} sm:w-56`} value={role} onChange={(e) => setRole(e.target.value)} data-testid="users-role-filter">
          <option value="">Tous les rôles</option>
          {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
        </select>
      </div>
      {error ? <Notice kind="error">{formatApiError(error)}</Notice> : !items ? <Loading /> : (
        <ul className="space-y-3" data-testid="users-list">{items.map((u) => <UserRow key={`${u.id}-${u.roles.join()}-${u.active}`} u={u} me={u.id === user.id} onChange={reload} />)}</ul>
      )}
    </section>
  );
};
