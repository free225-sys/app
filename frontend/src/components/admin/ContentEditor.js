import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { http } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { BTN_PRIMARY, Loading } from "@/components/common";
import { DEFAULTS, FIELDS, FieldInput, cleanContent } from "./fields";
import { History } from "./History";
import { WorkflowPanel } from "./WorkflowPanel";
import { INPUT, LABEL, Notice } from "./shared";

export const ContentEditor = ({ type, typeMeta, id, onBack, onCreated, reloadOptions }) => {
  const isNew = id === "nouveau";
  const [item, setItem] = useState(null);
  const [content, setContent] = useState(isNew ? DEFAULTS[type] : null);
  const [newId, setNewId] = useState("");
  const [changelog, setChangelog] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const apply = (data) => {
    setItem(data);
    setContent(data.latest.content);
    reloadOptions();
  };
  useEffect(() => {
    if (isNew) return;
    http.get(`/admin/content/${type}/${id}`).then((r) => apply(r.data)).catch((e) => setMsg({ kind: "error", text: formatApiError(e) }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, id]);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const body = { content: cleanContent(content), changelog: changelog || (isNew ? "Création" : "Modification") };
      if (isNew) {
        const { data } = await http.post(`/admin/content/${type}`, { ...body, id: newId || undefined });
        reloadOptions();
        onCreated(data.id);
        return;
      }
      const prev = item.latest;
      const { data } = await http.put(`/admin/content/${type}/${id}`, body);
      apply(data);
      setChangelog("");
      setMsg({ kind: "ok", text: data.latest.version !== prev.version ? `Version publiée non modifiée : nouvelle version brouillon v${data.latest.version} créée.` : `Brouillon v${data.latest.version} enregistré.` });
    } catch (err) {
      setMsg({ kind: "error", text: formatApiError(err) });
    } finally {
      setBusy(false);
    }
  };

  if (!content) return msg ? <Notice kind="error">{msg.text}</Notice> : <Loading />;
  const status = item?.latest.status;
  const locked = status === "review" || !typeMeta.can_edit;
  return (
    <div data-testid="content-editor">
      <button type="button" onClick={onBack} className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#147c77]" data-testid="editor-back"><ArrowLeft size={14} aria-hidden="true" />Retour à la liste</button>
      <h2 className="mt-4 text-2xl font-semibold tracking-tight" data-testid="editor-title">{isNew ? `Nouveau contenu — ${typeMeta.label}` : `${typeMeta.label} ${id}`}</h2>
      <div className="mt-8 grid gap-8 xl:grid-cols-[1fr_300px]">
        <form onSubmit={save} className="space-y-6" aria-label="Éditeur de contenu">
          {status === "published" || status === "retired" ? (
            <Notice testId="editor-immutable-notice">La version v{item.latest.version} est {status === "published" ? "publiée" : "retirée"} et immuable. Enregistrer vos modifications créera une nouvelle version brouillon v{item.latest.version + 1}.</Notice>
          ) : status === "review" ? <Notice testId="editor-review-notice">Version en relecture : modification impossible tant qu'elle n'est pas renvoyée en brouillon.</Notice> : null}
          {!typeMeta.can_edit && <Notice testId="editor-readonly-notice">Lecture seule : votre rôle ne permet pas de modifier ce type de contenu.</Notice>}
          {isNew && (
            <div>
              <label htmlFor="fld-new-id" className={LABEL}>Identifiant (facultatif)</label>
              <input id="fld-new-id" className={INPUT} value={newId} onChange={(e) => setNewId(e.target.value)} placeholder="Généré automatiquement si vide" data-testid="field-new-id" />
            </div>
          )}
          <div className="grid gap-6 sm:grid-cols-2">
            {FIELDS[type].map((f) => <FieldInput key={f.key} f={f} content={content} setContent={setContent} entityId={id} disabled={locked} />)}
          </div>
          {!locked && (
            <div className="flex flex-col gap-3 border-t border-[#e5e9ef] pt-6 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label htmlFor="fld-changelog" className={LABEL}>Note de version</label>
                <input id="fld-changelog" className={INPUT} value={changelog} onChange={(e) => setChangelog(e.target.value)} placeholder="Ce qui change dans cette version" data-testid="field-changelog" />
              </div>
              <button type="submit" className={BTN_PRIMARY} disabled={busy} data-testid="editor-save">{isNew ? "Créer le brouillon" : "Enregistrer"}</button>
            </div>
          )}
          {msg && <Notice kind={msg.kind} testId="editor-message">{msg.text}</Notice>}
        </form>
        {item && <div><WorkflowPanel type={type} item={item} canEdit={typeMeta.can_edit} onUpdated={apply} onDeleted={() => { reloadOptions(); onBack(); }} /></div>}
      </div>
      {item && <History history={item.history} />}
    </div>
  );
};
