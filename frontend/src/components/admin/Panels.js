import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { downloadFile, http, useApi } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { Loading } from "@/components/common";
import { BTN_DANGER, BTN_SMALL, INPUT, LEGACY_ROLE_LABEL, Notice, StatusBadge, fmtDate, pct } from "./shared";

const ACTIONS = { create: "Création", update: "Modification", new_version: "Nouvelle version", submit: "Soumission", approve: "Approbation", return: "Renvoi",
  publish: "Publication", publish_blocked: "Publication bloquée", retire: "Retrait", revoke: "Révocation", allow_reclaim: "Autorisation de nouvelle demande", invalidate: "Invalidation", upload: "Téléversement" };

const ExportQueue = () => {
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const get = async (fmt) => {
    setBusy(fmt); setErr("");
    try { await downloadFile(`/admin/review-queue/export?format=${fmt}`, `file-de-relecture.${fmt}`); }
    catch (e) { setErr(formatApiError(e)); }
    finally { setBusy(""); }
  };
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Exporter la file de relecture">
      <span className="text-xs font-semibold text-[#627086]">Exporter la file de relecture :</span>
      <button type="button" className={BTN_SMALL} disabled={!!busy} onClick={() => get("pdf")} data-testid="review-export-pdf">{busy === "pdf" ? "Génération…" : "PDF"}</button>
      <button type="button" className={BTN_SMALL} disabled={!!busy} onClick={() => get("md")} data-testid="review-export-md">{busy === "md" ? "Génération…" : "Markdown"}</button>
      {err && <span role="alert" className="text-xs text-[#7E2828]">{err}</span>}
    </div>
  );
};

export const ReviewQueue = ({ open }) => {
  const { data, error } = useApi("/admin/review-queue");
  if (error) return <Notice kind="error">{formatApiError(error)}</Notice>;
  if (!data) return <Loading />;
  return (
    <section aria-labelledby="rq-title" data-testid="admin-review-queue">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="rq-title" className="text-2xl font-semibold tracking-tight">À relire et à publier</h2>
        <ExportQueue />
      </div>
      {data.length === 0 ? <p className="mt-6 text-sm" data-testid="review-queue-empty">Aucune version en relecture.</p> : (
        <ul className="mt-6 divide-y divide-[#e5e9ef] border border-[#e5e9ef] bg-white">
          {data.map((v) => (
            <li key={`${v.type}-${v.entity_id}`}>
              <button type="button" onClick={() => open(v.type, v.entity_id)} className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left text-sm hover:bg-[#f7f8fa]" data-testid={`review-item-${v.type}-${v.entity_id}`}>
                <span className="w-28 text-xs font-semibold uppercase text-[#627086]">{v.label}</span>
                <span className="font-mono text-xs text-[#147c77]">{v.entity_id} v{v.version}</span>
                <span className="min-w-0 flex-1 truncate">{v.title}</span>
                <span className="text-xs text-[#627086]">soumise le {fmtDate(v.submitted_at)}{v.submitted_by ? ` par ${v.submitted_by.name}` : ""}</span>
                <StatusBadge status={v.status} approved={v.approved} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

const CODE_LABEL = { ...LEGACY_ROLE_LABEL, draft: "brouillon", review: "relecture", published: "publiée", retired: "retirée" };
const humanize = (t) => (t || "").replace(/\b(learner|admin|author|reviewer|evaluator|pedagogical_lead|draft|review|published|retired)\b/g, (m) => CODE_LABEL[m].toLowerCase());

export const ChangeLog = ({ types }) => {
  const [f, setF] = useState({ entity_type: "", action: "", user_email: "", entity_id: "" });
  const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
  const { data, error } = useApi("/admin/changelog", params);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <section aria-labelledby="log-title" data-testid="admin-changelog">
      <h2 id="log-title" className="text-2xl font-semibold tracking-tight">Journal des modifications</h2>
      <div className="mt-6 grid gap-3 sm:grid-cols-4">
        <select aria-label="Type" className={INPUT} value={f.entity_type} onChange={set("entity_type")} data-testid="log-filter-type">
          <option value="">Tous les types</option>
          {types.map((t) => <option key={t.type} value={t.type}>{t.label}</option>)}
          <option value="user">Utilisateur</option><option value="certificate">Certificat</option><option value="attainment">Preuve</option>
        </select>
        <select aria-label="Action" className={INPUT} value={f.action} onChange={set("action")} data-testid="log-filter-action">
          <option value="">Toutes les actions</option>
          {Object.entries(ACTIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input aria-label="E-mail de l'auteur" className={INPUT} placeholder="E-mail de l'auteur" value={f.user_email} onChange={set("user_email")} data-testid="log-filter-user" />
        <input aria-label="Identifiant" className={INPUT} placeholder="Identifiant (ex. M09)" value={f.entity_id} onChange={set("entity_id")} data-testid="log-filter-entity" />
      </div>
      {error ? <Notice kind="error">{formatApiError(error)}</Notice> : !data ? <Loading /> : data.length === 0 ? <p className="mt-6 text-sm" data-testid="log-empty">Aucune entrée.</p> : (
        <div className="mt-6 overflow-x-auto border border-[#e5e9ef] bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-[#e5e9ef] text-xs text-[#627086]"><tr>{["Date", "Qui", "Contenu", "Action", "Détails"].map((h) => <th key={h} scope="col" className="px-4 py-2 font-semibold">{h}</th>)}</tr></thead>
            <tbody className="divide-y divide-[#e5e9ef]">
              {data.map((e) => (
                <tr key={e.id} data-testid={`log-row-${e.id}`}>
                  <td className="whitespace-nowrap px-4 py-2 font-mono text-xs">{fmtDate(e.at)}</td>
                  <td className="px-4 py-2 text-xs">{e.user_name}<br /><span className="text-[#627086]">{e.user_email}</span></td>
                  <td className="px-4 py-2 font-mono text-xs">{e.entity_type} · {e.entity_id}{e.version ? ` v${e.version}` : ""}</td>
                  <td className="px-4 py-2 text-xs font-semibold">{ACTIONS[e.action] || e.action}</td>
                  <td className="px-4 py-2 text-xs">{humanize(e.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

const AwardRow = ({ a, onChange }) => {
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState("");
  const act = async (path) => {
    try {
      const { data } = await http.post(path, { reason });
      setMsg(data.revoked_certificates ? `Preuve invalidée. Certificats révoqués : ${data.revoked_certificates.join(", ") || "aucun"}.`
        : path.endsWith("allow-reclaim") ? "Nouvelle demande autorisée (valable une fois)." : "Certificat révoqué.");
      onChange();
    } catch (e) {
      setMsg(formatApiError(e));
    }
  };
  return (
    <li className="border border-[#e5e9ef] bg-white p-5" data-testid={`admin-award-${a.code}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-semibold">{a.credential_title} — {a.holder_name}</p>
        <span className={`rounded-[10px] px-2 py-0.5 text-xs font-semibold ${a.status === "valid" ? "bg-[#eef5f3] text-[#147c77]" : "bg-[#FBECEC] text-[#7E2828]"}`} data-testid={`admin-award-status-${a.code}`}>{a.status === "valid" ? "Valide" : "Révoqué"}</span>
      </div>
      <p className="mt-1 font-mono text-xs"><Link to={`/verifier/${a.code}`} className="underline">{a.code}</Link> · délivré le {new Date(a.issued_at).toLocaleDateString("fr-FR")}{a.revoke_reason ? ` · ${a.revoke_reason}` : ""}</p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label htmlFor={`reason-${a.code}`} className="sr-only">Motif</label>
        <input id={`reason-${a.code}`} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Motif (obligatoire)" className={`${INPUT} flex-1`} data-testid={`admin-reason-${a.code}`} />
        {a.status === "valid" && <button type="button" className={BTN_DANGER} disabled={reason.trim().length < 3} onClick={() => act(`/admin/certificates/${a.code}/revoke`)} data-testid={`admin-revoke-${a.code}`}>Révoquer</button>}
        {a.reclaim?.can_authorize && <button type="button" className={BTN_SMALL} disabled={reason.trim().length < 3} onClick={() => act(`/admin/certificates/${a.code}/allow-reclaim`)} data-testid={`admin-allow-reclaim-${a.code}`}>Autoriser une nouvelle demande</button>}
        {a.reclaim?.authorized && <span className="text-xs font-semibold text-[#147c77]" data-testid={`admin-reclaim-authorized-${a.code}`}>Nouvelle demande autorisée</span>}
      </div>
      <ul className="mt-3 space-y-1 text-xs">
        {a.evidence_refs.map((e) => (
          <li key={e.rule_id} className="flex flex-wrap items-center gap-3">
            <span>{e.label}</span>
            <button type="button" className="font-semibold text-[#7E2828] underline disabled:opacity-40" disabled={reason.trim().length < 3}
              onClick={() => act(`/admin/attainments/${e.attainment_id}/invalidate`)} data-testid={`admin-invalidate-${a.code}-${e.rule_id}`}>Invalider la preuve</button>
          </li>
        ))}
      </ul>
      {msg && <p role="status" className="mt-3 text-sm" data-testid={`admin-award-msg-${a.code}`}>{msg}</p>}
    </li>
  );
};

const EvidenceRow = ({ a, onChange }) => {
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState("");
  const invalidate = async () => {
    try {
      const { data } = await http.post(`/admin/attainments/${a.id}/invalidate`, { reason });
      setMsg(`Invalidée. Certificats révoqués : ${data.revoked_certificates.join(", ") || "aucun"}.`);
      onChange();
    } catch (e) {
      setMsg(formatApiError(e));
    }
  };
  return (
    <tr data-testid={`evidence-row-${a.id}`}>
      <td className="px-3 py-2 text-xs">{a.learner}</td>
      <td className="px-3 py-2 font-mono text-xs">{a.competency_id} · {a.level}</td>
      <td className="px-3 py-2 font-mono text-xs">{a.module_id} · {a.evidence_type === "project" ? "projet" : "évaluation"} · {pct(a.score_percent)}</td>
      <td className="px-3 py-2 text-xs">{a.status === "valid" ? "Valide" : "Invalidée"}</td>
      <td className="px-3 py-2">
        {a.status === "valid" ? (
          <div className="flex gap-2">
            <input aria-label="Motif" className={`${INPUT} py-1 text-xs`} placeholder="Motif" value={reason} onChange={(e) => setReason(e.target.value)} data-testid={`evidence-reason-${a.id}`} />
            <button type="button" className={BTN_SMALL} disabled={reason.trim().length < 3} onClick={invalidate} data-testid={`evidence-invalidate-${a.id}`}>Invalider</button>
          </div>
        ) : <span className="text-xs text-[#627086]">{a.invalidation_reason}</span>}
        {msg && <p role="status" className="mt-1 text-xs">{msg}</p>}
      </td>
    </tr>
  );
};

export const Certificates = () => {
  const [awards, setAwards] = useState(null);
  const [atts, setAtts] = useState(null);
  const [error, setError] = useState(null);
  const load = () => {
    http.get("/admin/certificates").then((r) => setAwards(r.data)).catch(setError);
    http.get("/admin/attainments").then((r) => setAtts(r.data)).catch(setError);
  };
  useEffect(load, []);
  if (error) return <Notice kind="error">{formatApiError(error)}</Notice>;
  return (
    <section aria-labelledby="cert-title" className="space-y-10" data-testid="admin-page">
      <div>
        <h2 id="cert-title" className="text-2xl font-semibold tracking-tight">Certificats délivrés</h2>
        <p className="mt-2 text-sm text-[#627086]">Révoquer un certificat, ou invalider une preuve : les certificats qui en dépendent sont alors révoqués.</p>
        {!awards ? <Loading /> : awards.length === 0 ? <p className="mt-6 text-sm" data-testid="admin-empty">Aucun certificat délivré.</p> : (
          <ul className="mt-6 space-y-4">{awards.map((a) => <AwardRow key={a.id} a={a} onChange={load} />)}</ul>
        )}
      </div>
      <div>
        <h3 className="text-lg font-semibold">Preuves de compétences</h3>
        {!atts ? <Loading /> : (
          <div className="mt-4 max-h-[480px] overflow-auto border border-[#e5e9ef] bg-white">
            <table className="w-full min-w-[760px] text-left text-sm" data-testid="evidence-table">
              <thead className="sticky top-0 bg-white text-xs text-[#627086]"><tr>{["Apprenant", "Compétence", "Source", "Statut", "Action"].map((h) => <th key={h} scope="col" className="px-3 py-2 font-semibold">{h}</th>)}</tr></thead>
              <tbody className="divide-y divide-[#e5e9ef]">{atts.map((a) => <EvidenceRow key={`${a.id}-${a.status}`} a={a} onChange={load} />)}</tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};
