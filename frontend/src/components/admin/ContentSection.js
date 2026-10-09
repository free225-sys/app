import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { http } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { Loading } from "@/components/common";
import { ContentEditor } from "./ContentEditor";
import { BTN_SMALL, INPUT, Notice, STATUS_META, StatusBadge } from "./shared";

const List = ({ type, typeMeta, onOpen }) => {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let alive = true;
    setItems(null);
    const t = setTimeout(() => http.get(`/admin/content/${type}`, { params: { q: q || undefined, status: status || undefined } })
      .then((r) => alive && setItems(r.data)).catch((e) => alive && setError(e)), 200);
    return () => { alive = false; clearTimeout(t); };
  }, [type, q, status]);
  return (
    <div data-testid={`content-list-${type}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label htmlFor="content-q" className="sr-only">Rechercher</label>
        <input id="content-q" className={INPUT} placeholder="Rechercher par identifiant ou titre" value={q} onChange={(e) => setQ(e.target.value)} data-testid="content-search" />
        <label htmlFor="content-status" className="sr-only">Statut</label>
        <select id="content-status" className={`${INPUT} sm:w-48`} value={status} onChange={(e) => setStatus(e.target.value)} data-testid="content-status-filter">
          <option value="">Tous les statuts</option>
          {Object.entries(STATUS_META).map(([k, m]) => <option key={k} value={k}>{m.label}</option>)}
        </select>
        {typeMeta.can_edit && <button type="button" className={BTN_SMALL} onClick={() => onOpen("nouveau")} data-testid="content-new"><Plus size={12} aria-hidden="true" />Nouveau</button>}
      </div>
      {error ? <Notice kind="error">{formatApiError(error)}</Notice> : !items ? <Loading /> : items.length === 0 ? <p className="mt-6 text-sm" data-testid="content-empty">Aucun contenu.</p> : (
        <ul className="mt-6 divide-y divide-[#e5e9ef] border border-[#e5e9ef] bg-white">
          {items.map((i) => (
            <li key={i.id}>
              <button type="button" onClick={() => onOpen(i.id)} className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left text-sm transition-colors duration-150 hover:bg-[#f7f8fa] focus-visible:bg-[#f7f8fa]" data-testid={`content-row-${i.id}`}>
                <span className="w-40 shrink-0 truncate font-mono text-xs text-[#147c77]">{i.id}</span>
                <span className="min-w-0 flex-1 truncate">{i.title}</span>
                <span className="font-mono text-xs text-[#627086]">v{i.latest_version}{i.published_version ? ` · en ligne v${i.published_version}` : " · non publié"}</span>
                <StatusBadge status={i.latest_status} approved={i.approved} testId={`content-status-${i.id}`} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const ContentSection = ({ types, type, id, setParams, reloadOptions }) => {
  const typeMeta = types.find((t) => t.type === type) || types[0];
  const open = (eid) => setParams({ onglet: "contenus", type: typeMeta.type, ...(eid ? { id: eid } : {}) });
  return (
    <section aria-labelledby="content-title" data-testid="admin-content">
      <h2 id="content-title" className="sr-only">Contenus pédagogiques</h2>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Types de contenus">
        {types.map((t) => (
          <button key={t.type} type="button" role="tab" aria-selected={t.type === typeMeta.type} onClick={() => setParams({ onglet: "contenus", type: t.type })}
            className={`rounded-[10px] border px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${t.type === typeMeta.type ? "border-[#14243c] bg-[#14243c] text-white" : "border-[#e5e9ef] bg-white hover:border-[#14243c]/40"}`}
            data-testid={`content-type-${t.type}`}>{t.label}</button>
        ))}
      </div>
      <div className="mt-8">
        {id ? <ContentEditor key={`${typeMeta.type}-${id}`} type={typeMeta.type} typeMeta={typeMeta} id={id} onBack={() => open(null)} onCreated={open} reloadOptions={reloadOptions} />
          : <List type={typeMeta.type} typeMeta={typeMeta} onOpen={open} />}
      </div>
    </section>
  );
};
