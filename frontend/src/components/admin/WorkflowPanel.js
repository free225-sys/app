import { useState } from "react";
import { http } from "@/lib/api";
import { formatApiError, useAuth } from "@/lib/auth";
import { BTN_DANGER, BTN_SMALL, INPUT, LABEL, Notice, PUBLISHERS, REVIEWERS, StatusBadge, hasRole } from "./shared";

export const WorkflowPanel = ({ type, item, canEdit, onUpdated, onDeleted }) => {
  const { user } = useAuth();
  const [comment, setComment] = useState("");
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const latest = item.latest;
  const base = `/admin/versions/${type}/${item.id}`;
  const act = async (path, body, ok) => {
    setBusy(true);
    try {
      const { data } = await http.post(`${base}/${path}`, body);
      setMsg({ kind: "ok", text: ok });
      setComment("");
      setReason("");
      onUpdated(data);
    } catch (e) {
      setMsg({ kind: "error", text: formatApiError(e) });
    } finally {
      setBusy(false);
    }
  };
  const isReviewer = hasRole(user, REVIEWERS);
  const isPublisher = hasRole(user, PUBLISHERS);
  return (
    <aside className="border border-[#e5e9ef] bg-white p-5" aria-labelledby="wf-title" data-testid="workflow-panel">
      <h3 id="wf-title" className="text-sm font-semibold">Cycle de publication</h3>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <span className="font-mono">v{latest.version}</span>
        <StatusBadge status={latest.status} approved={latest.approved} testId="workflow-status" />
      </div>
      <p className="mt-2 text-xs text-[#627086]" data-testid="workflow-published-version">
        Version publiée en ligne : {item.published_version ? `v${item.published_version}` : "aucune"}
      </p>
      <ol className="mt-4 flex flex-wrap gap-1 text-[11px] font-semibold uppercase tracking-wider text-[#627086]" aria-label="Étapes">
        {["Brouillon", "Relecture", "Publiée", "Retirée"].map((s, i) => <li key={s} className="flex items-center gap-1">{i > 0 && <span aria-hidden="true">→</span>}{s}</li>)}
      </ol>
      <div className="mt-5 space-y-4">
        {latest.status === "draft" && canEdit && (
          <div className="flex flex-wrap gap-2">
            <button type="button" className={BTN_SMALL} disabled={busy} onClick={() => act("submit", {}, "Version soumise à relecture.")} data-testid="workflow-submit">Soumettre à relecture</button>
            {(latest.created_by?.id === user.id || isPublisher) && (
              <button type="button" className={BTN_DANGER} disabled={busy} data-testid="workflow-delete-draft"
                onClick={async () => {
                  if (!window.confirm(`Supprimer définitivement le brouillon v${latest.version} ?`)) return;
                  try {
                    const { data } = await http.delete(`${base}/${latest.version}`);
                    if (data.deleted) onDeleted(); else { onUpdated(data); setMsg({ kind: "ok", text: "Brouillon supprimé." }); }
                  } catch (e) { setMsg({ kind: "error", text: formatApiError(e) }); }
                }}>Supprimer le brouillon</button>
            )}
          </div>
        )}
        {latest.status === "review" && isReviewer && (
          <div className="space-y-2">
            <label htmlFor="wf-comment" className={LABEL}>Commentaire de relecture</label>
            <textarea id="wf-comment" rows={3} className={INPUT} value={comment} onChange={(e) => setComment(e.target.value)} data-testid="workflow-comment" />
            <div className="flex flex-wrap gap-2">
              {!latest.approved && <button type="button" className={BTN_SMALL} disabled={busy} onClick={() => act("review", { decision: "approve", comment }, "Version approuvée.")} data-testid="workflow-approve">Approuver</button>}
              <button type="button" className={BTN_DANGER} disabled={busy} onClick={() => act("review", { decision: "return", comment }, "Version renvoyée à l'auteur.")} data-testid="workflow-return">Renvoyer à l'auteur</button>
            </div>
          </div>
        )}
        {latest.status === "review" && latest.approved && (isPublisher ? (
          <button type="button" className="inline-flex items-center rounded-[10px] bg-[#147c77] px-4 py-2 text-xs font-semibold text-white hover:bg-[#0f625e] disabled:opacity-40" disabled={busy}
            onClick={() => act("publish", {}, "Version publiée.")} data-testid="workflow-publish">Publier v{latest.version}</button>
        ) : <p className="text-xs text-[#627086]" data-testid="workflow-publish-restricted">Approuvée : en attente de publication par le responsable pédagogique ou l'administrateur.</p>)}
        {latest.status === "review" && !isReviewer && !latest.approved && <p className="text-xs text-[#627086]">En attente de relecture.</p>}
        {isPublisher && item.published_version && (
          <div className="space-y-2 border-t border-[#e5e9ef] pt-4">
            <label htmlFor="wf-reason" className={LABEL}>Retirer la version publiée v{item.published_version}</label>
            <input id="wf-reason" className={INPUT} placeholder="Motif (obligatoire)" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="workflow-retire-reason" />
            <button type="button" className={BTN_DANGER} disabled={busy || reason.trim().length < 3} onClick={() => act("retire", { version: item.published_version, reason }, "Version retirée.")} data-testid="workflow-retire">Retirer</button>
          </div>
        )}
        {msg && <Notice kind={msg.kind} testId="workflow-message">{msg.text}</Notice>}
      </div>
    </aside>
  );
};
