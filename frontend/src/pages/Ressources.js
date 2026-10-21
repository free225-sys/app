import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, X } from "lucide-react";
import { useApi, useCatalog } from "@/lib/api";
import { Container, ErrorState, LayerChip, Loading, PageHeader, levelRange } from "@/components/common";

const FILTERS = [
  { key: "etape", api: "stage", label: "Étape", source: "stages", fmt: (s) => `${s.code} — ${s.name}` },
  { key: "couche", api: "layer", label: "Couche", source: "layers", fmt: (l) => l.name },
  { key: "niveau", api: "level", label: "Niveau", source: "levels", fmt: (l) => `${l.id} — ${l.name}` },
  { key: "competence", api: "competency", label: "Compétence", source: "competencies", fmt: (c) => c.name },
];

const FilterBar = ({ catalog, params, setParam, query, setQuery, onReset, hasFilters }) => (
  <div className="grid gap-4 border border-[#e5e9ef] bg-white p-5 md:grid-cols-2 lg:grid-cols-6" data-testid="catalogue-filter-bar">
    <div className="md:col-span-2">
      <label htmlFor="f-q" className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Recherche</label>
      <div className="mt-2 flex items-center border border-[#e5e9ef] bg-[#f7f8fa] px-3 focus-within:border-[#147c77]">
        <Search size={16} className="text-[#627086]" aria-hidden="true" />
        <input id="f-q" type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ex. : RAG, token, GPU…"
          className="w-full bg-transparent px-2 py-2.5 text-sm outline-none placeholder:text-[#627086]" data-testid="filter-search-input" />
      </div>
    </div>
    {FILTERS.map((f) => (
      <div key={f.key}>
        <label htmlFor={`f-${f.key}`} className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">{f.label}</label>
        <select id={`f-${f.key}`} value={params.get(f.key) || ""} onChange={(e) => setParam(f.key, e.target.value)}
          className="mt-2 w-full border border-[#e5e9ef] bg-[#f7f8fa] px-2 py-2.5 text-sm focus:border-[#147c77]" data-testid={`filter-${f.key}-select`}>
          <option value="">Tous</option>
          {catalog[f.source].map((o) => <option key={o.id} value={o.id}>{f.fmt(o)}</option>)}
        </select>
      </div>
    ))}
    {hasFilters && (
      <div className="lg:col-span-6">
        <button type="button" onClick={onReset} className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#147c77] underline-offset-4 hover:underline" data-testid="filter-reset">
          <X size={14} aria-hidden="true" /> Réinitialiser les filtres
        </button>
      </div>
    )}
  </div>
);

const ModuleCard = ({ m, layers }) => (
  <li>
    <Link to={`/modules/${m.id}`} className="group flex h-full flex-col border border-[#e5e9ef] bg-white p-6 transition-colors duration-200 hover:border-[#14243c]/50" data-testid={`module-card-${m.id}`}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono font-semibold text-[#147c77]">{m.code}</span>
        <span className="font-mono text-[#627086]">{levelRange(m.levels)}</span>
      </div>
      <h3 className="mt-3 text-lg font-semibold leading-snug group-hover:underline group-hover:underline-offset-4">{m.title}</h3>
      <p className="mt-2 line-clamp-3 flex-1 text-sm leading-relaxed text-[#505e75]">{m.summary}</p>
      <div className="mt-5 flex flex-wrap gap-1.5">
        {m.layer_ids.map((id) => { const l = layers.find((x) => x.id === id); return l && <LayerChip key={id} layer={l} />; })}
      </div>
      <p className="mt-4 text-xs text-[#627086]">{m.resource_count} ressources · durée pédagogique {m.duration_hours} h</p>
    </Link>
  </li>
);

const ConceptCard = ({ c, layers, stages }) => (
  <li>
    <Link to={`/concepts/${c.id}`} className="group flex h-full flex-col border border-[#e5e9ef] bg-white p-5 transition-colors duration-200 hover:border-[#14243c]/50" data-testid={`concept-card-${c.id}`}>
      <h3 className="text-base font-semibold group-hover:underline group-hover:underline-offset-4">{c.name}</h3>
      <p className="mt-1.5 flex-1 text-sm leading-relaxed text-[#505e75]">{c.short}</p>
      <div className="mt-4 flex flex-wrap gap-1.5">
        {c.layer_ids.map((id) => { const l = layers.find((x) => x.id === id); return l && <LayerChip key={id} layer={l} />; })}
      </div>
      <p className="mt-3 font-mono text-xs text-[#627086]">
        Étapes {c.stage_ids.map((id) => stages.find((s) => s.id === id)?.code).join(" · ")} · Modules {c.module_ids.join(", ")}
      </p>
    </Link>
  </li>
);

export default function Ressources() {
  const catalog = useCatalog();
  const [params, setParams] = useSearchParams();
  const view = params.get("vue") === "notions" ? "notions" : "modules";
  const [query, setQuery] = useState(params.get("q") || "");

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const t = setTimeout(() => {
      if ((params.get("q") || "") !== query) setParam("q", query.trim());
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const apiParams = useMemo(() => {
    const p = {};
    FILTERS.forEach((f) => { if (params.get(f.key)) p[f.api] = params.get(f.key); });
    if (params.get("q")) p.q = params.get("q");
    return p;
  }, [params]);

  const { data, loading, error } = useApi(view === "modules" ? "/modules" : "/concepts", apiParams);
  const hasFilters = Object.keys(apiParams).length > 0;
  const reset = () => { setQuery(""); setParams(view === "notions" ? { vue: "notions" } : {}, { replace: true }); };

  return (
    <div data-testid="ressources-page">
      <PageHeader eyebrow="Ressources" title="Catalogue des modules et des notions."
        lead="Modules et notions, à filtrer par étape, couche, niveau ou compétence."
        more={<p>Une vingtaine de modules et une trentaine de notions, organisés selon les sept étapes du traitement, les six couches, cinq niveaux de profondeur et cinq types de compétences.</p>} />
      <Container className="pt-10">
        <div role="tablist" aria-label="Type de contenu" className="flex gap-8 border-b border-[#e5e9ef]">
          {[["modules", "Modules"], ["notions", "Notions"]].map(([key, label]) => (
            <button key={key} type="button" role="tab" aria-selected={view === key}
              onClick={() => setParam("vue", key === "notions" ? "notions" : "")}
              className={`-mb-px border-b-2 pb-3 text-sm font-semibold transition-colors duration-200 ${view === key ? "border-[#147c77] text-[#14243c]" : "border-transparent text-[#627086] hover:text-[#14243c]"}`}
              data-testid={`tab-${key}`}>
              {label}
            </button>
          ))}
        </div>
        {catalog && (
          <div className="mt-8">
            <FilterBar catalog={catalog} params={params} setParam={setParam} query={query} setQuery={setQuery} onReset={reset} hasFilters={hasFilters} />
          </div>
        )}
        <p className="mt-8 text-sm text-[#505e75]" aria-live="polite" data-testid="results-count">
          {data && !loading ? `${data.length} ${view === "modules" ? "module" : "notion"}${data.length > 1 ? "s" : ""}` : ""}
        </p>
        {error && <ErrorState />}
        {(loading || !catalog) && !error && <Loading />}
        {data && catalog && !loading && data.length === 0 && (
          <div className="mt-6 border border-dashed border-[#e5e9ef] px-6 py-12 text-center text-sm text-[#505e75]" data-testid="results-empty">
            Aucun résultat ne correspond à ces critères. <button type="button" onClick={reset} className="font-semibold text-[#147c77] underline">Réinitialiser</button>
          </div>
        )}
        {data && catalog && !loading && data.length > 0 && (
          <ul className={`mt-6 grid gap-5 sm:grid-cols-2 ${view === "modules" ? "lg:grid-cols-3" : "lg:grid-cols-3 xl:grid-cols-4"}`} data-testid="results-list">
            {view === "modules"
              ? data.map((m) => <ModuleCard key={m.id} m={m} layers={catalog.layers} />)
              : data.map((c) => <ConceptCard key={c.id} c={c} layers={catalog.layers} stages={catalog.stages} />)}
          </ul>
        )}
        {view === "notions" && data && <p className="mt-6 text-xs text-[#627086]">Les niveaux et compétences d'une notion sont ceux des modules qui la traitent.</p>}
      </Container>
    </div>
  );
}
