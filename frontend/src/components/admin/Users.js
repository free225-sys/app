import { useEffect, useState } from "react";
import { http } from "@/lib/api";
import { formatApiError, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, Loading } from "@/components/common";
import { BTN_DANGER, BTN_SMALL, INPUT, LABEL, LEGACY_ROLE_LABEL, Notice, ROLE_LABEL, fmtDate } from "./shared";

const ROLES = Object.keys(ROLE_LABEL);

const CreateUser = ({ onCreated }) => {
  const [f, setF] = useState({ email: "", first_name: "", last_name: "", password: "" });
  const [msg, setMsg] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    try {
      await http.post("/admin/users", f);
      setMsg({ kind: "ok", text: `Compte ${f.email} créé.` });
      setF({ email: "", first_name: "", last_name: "", password: "" });
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
    <form onSubmit={submit} className="space-y-4 border border-[#e5e9ef] bg-white p-5" aria-label="Créer un compte apprenant" data-testid="new-user-form">
      <h3 className="text-sm font-semibold">Créer un compte apprenant</h3>
      <div className="grid gap-4 sm:grid-cols-2">{field("first_name", "Prénom")}{field("last_name", "Nom")}{field("email", "E-mail", "email")}{field("password", "Mot de passe initial (8 car. min.)", "password")}</div>
      <button type="submit" className={BTN_PRIMARY} data-testid="new-user-submit">Créer le compte</button>
      {msg && <Notice kind={msg.kind} testId="new-user-message">{msg.text}</Notice>}
    </form>
  );
};

const TempPassword = ({ onSave, email }) => {
  const [open, setOpen] = useState(false);
  const [pwd, setPwd] = useState("");
  if (!open) return <button type="button" className={BTN_SMALL} onClick={() => setOpen(true)} data-testid={`user-temp-password-${email}`}>Définir un mot de passe provisoire</button>;
  return (
    <form className="flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); onSave(pwd).then((ok) => ok && (setPwd(""), setOpen(false))); }}>
      <label htmlFor={`tp-${email}`} className="sr-only">Mot de passe provisoire</label>
      <input id={`tp-${email}`} type="password" autoComplete="new-password" minLength={8} required className={`${INPUT} w-56`} placeholder="8 caractères minimum" value={pwd} onChange={(e) => setPwd(e.target.value)} data-testid={`user-temp-password-input-${email}`} />
      <button type="submit" className={BTN_SMALL} data-testid={`user-temp-password-save-${email}`}>Enregistrer</button>
      <button type="button" className={BTN_SMALL} onClick={() => setOpen(false)}>Annuler</button>
    </form>
  );
};

const UserRow = ({ u, me, onChange }) => {
  const [msg, setMsg] = useState(null);
  const patch = async (body, ok) => {
    try {
      await http.patch(`/admin/users/${u.id}`, body);
      setMsg({ kind: "ok", text: ok });
      onChange();
      return true;
    } catch (e) {
      setMsg({ kind: "error", text: formatApiError(e) });
      return false;
    }
  };
  const legacy = (u.legacy_roles || []).filter((r) => r !== "learner" && r !== u.role);
  return (
    <li className={`border border-[#e5e9ef] bg-white p-4 ${u.active ? "" : "opacity-70"}`} data-testid={`user-row-${u.email}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm"><strong>{u.first_name} {u.last_name}</strong> · <span className="font-mono text-xs">{u.email}</span>{me && " (vous)"}</p>
        <span className="flex gap-2">
          <span className="rounded-[10px] bg-[#f1f4f7] px-2 py-0.5 text-xs font-semibold" data-testid={`user-role-${u.email}`}>{ROLE_LABEL[u.role] || "Rôle inconnu"}</span>
          <span className={`rounded-[10px] px-2 py-0.5 text-xs font-semibold ${u.active ? "bg-[#eef5f3] text-[#147c77]" : "bg-[#FBECEC] text-[#7E2828]"}`} data-testid={`user-active-${u.email}`}>{u.active ? "Actif" : "Désactivé"}</span>
        </span>
      </div>
      <p className="mt-1 text-xs text-[#627086]">Créé le {fmtDate(u.created_at)}{legacy.length > 0 && ` · rôles hérités (historique) : ${legacy.map((r) => LEGACY_ROLE_LABEL[r] || r).join(", ")}`}</p>
      {u.role !== "admin" && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {u.active
            ? <button type="button" className={BTN_DANGER} onClick={() => patch({ active: false }, "Compte désactivé.")} data-testid={`user-deactivate-${u.email}`}>Désactiver</button>
            : <button type="button" className={BTN_SMALL} onClick={() => patch({ active: true }, "Compte réactivé.")} data-testid={`user-activate-${u.email}`}>Réactiver</button>}
          <TempPassword email={u.email} onSave={(password) => patch({ password }, "Mot de passe provisoire enregistré. Les sessions ouvertes de ce compte sont fermées.")} />
        </div>
      )}
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
      <h2 id="users-title" className="text-2xl font-semibold tracking-tight">Apprenants et comptes</h2>
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
        <ul className="space-y-3" data-testid="users-list">{items.map((u) => <UserRow key={`${u.id}-${u.role}-${u.active}`} u={u} me={u.id === user.id} onChange={reload} />)}</ul>
      )}
    </section>
  );
};
