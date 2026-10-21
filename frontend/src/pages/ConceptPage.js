import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useApi, useCatalog } from "@/lib/api";
import { Container, ErrorState, Eyebrow, LINK_ARROW, LayerChip, Loading, Pill, SummaryCard, Tabs, levelRange, minutes } from "@/components/common";
import { Picto } from "@/components/Pictos";

export default function ConceptPage() {
  const { id } = useParams();
  const catalog = useCatalog();
  const { data: c, loading, error } = useApi(`/concepts/${id}`);
  if (error) return <ErrorState message="Cette notion est introuvable." />;
  if (loading || !catalog) return <Loading />;
  return (
    <article data-testid="concept-page">
      <Container className="pt-10">
        <Link to="/ressources?vue=notions" className={LINK_ARROW} data-testid="concept-back-link"><ArrowLeft size={14} aria-hidden="true" /> Toutes les notions</Link>
      </Container>
      <header className="border-b border-[#e5e9ef] pb-12 pt-8">
        <Container>
          <Eyebrow>Fiche notion</Eyebrow>
          <h1 className="mt-5 text-4xl sm:text-5xl lg:text-6xl" data-testid="concept-title">{c.name}</h1>
          <p className="mt-5 text-base text-[#505e75] md:text-lg">{c.short}</p>
          <SummaryCard testId="concept-summary" items={[
            { key: "levels", label: "Niveaux", value: <span className="font-mono font-semibold">{levelRange(c.levels) || "L0–L4"}</span> },
            { key: "duration", label: "Temps de lecture", value: <span className="font-semibold" data-testid="concept-duration">{minutes(c.estimated_minutes)}</span> },
            { key: "layers", label: "Couches", value: c.layers.map((l) => <LayerChip key={l.id} layer={l} />) },
            { key: "competencies", label: "Compétences visées", value: c.competencies.length ? c.competencies.map((k) => <Pill key={k.id}><Picto id={k.id} category={k.category_id} size={13} />{k.name}</Pill>) : null },
            { key: "prerequisites", label: "Prérequis", value: c.prerequisites.length ? c.prerequisites.map((p) => (
              <Link key={p.id} to={`/concepts/${p.id}`} data-testid={`concept-prereq-link-${p.id}`}><Pill className="hover:border-[#365ac8]">{p.name}</Pill></Link>
            )) : <Pill>Aucun</Pill> },
          ]} />
        </Container>
      </header>
      <Container className="py-16 sm:py-20">
        <Tabs label="Fiche notion" testId="concept-tabs" tabs={[
          { id: "definition", label: "Définition", content: (
            <section className="max-w-[68ch]" data-testid="concept-definition">
              <p className="text-base leading-relaxed">{c.definition}</p>
              <div className="mt-8 rounded-[14px] border-l-[3px] border-[#365ac8] bg-white px-6 py-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Exemple — cas CASA</p>
                <p className="mt-2 text-sm leading-relaxed text-[#505e75]">{c.example}</p>
              </div>
            </section>
          ) },
          { id: "niveaux", label: "Par niveau (L0-L4)", content: (
            <ol className="max-w-[80ch] divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]" data-testid="concept-treatment">
              {catalog.levels.map((lv) => (
                <li key={lv.id} className={`grid gap-2 py-5 sm:grid-cols-[10rem_1fr] sm:gap-6 ${c.levels.includes(lv.id) ? "" : "opacity-70"}`} data-testid={`concept-level-${lv.id}`}>
                  <div><span className="font-mono text-sm font-semibold text-[#147c77]">{lv.id}</span><span className="ml-2 text-sm font-medium">{lv.name}</span></div>
                  <p className="text-sm leading-relaxed">{c.treatment[lv.id]}</p>
                </li>
              ))}
            </ol>
          ) },
          { id: "liens", label: "Liens", content: (
            <div className="grid gap-12 md:grid-cols-2">
              <section data-testid="concept-stages"><h3 className="text-lg">Étapes associées</h3>
                <ul className="mt-4 space-y-3">{c.stages.map((st) => (
                  <li key={st.id} className="flex items-center gap-3 text-sm"><Picto id={st.id} />
                    <Link to={`/demo?etape=${parseInt(st.code, 10)}`} className="font-medium hover:underline" data-testid={`concept-stage-link-${st.id}`}>{st.name}</Link>
                    <span className="text-xs text-[#627086]">{st.subtitle}</span></li>))}</ul>
              </section>
              <section data-testid="concept-modules"><h3 className="text-lg">Modules liés</h3>
                <ul className="mt-4 space-y-3">{c.modules.map((m) => (
                  <li key={m.id}><Link to={`/modules/${m.id}`} className="group flex items-start gap-3 text-sm" data-testid={`concept-module-link-${m.id}`}>
                    <span className="font-mono text-xs font-semibold text-[#147c77]">{m.code}</span><span className="flex-1 font-medium group-hover:underline">{m.title}</span>
                    <span className="font-mono text-xs text-[#627086]">{levelRange(m.levels)}</span></Link></li>))}</ul>
              </section>
              <section data-testid="concept-layers"><h3 className="text-lg">Couches associées</h3>
                <ul className="mt-4 space-y-3">{c.layers.map((l) => <li key={l.id} className="flex items-center gap-3 text-sm"><Picto id={l.id} /><span className="font-medium">{l.name}</span><span className="text-xs text-[#627086]">{l.short}</span></li>)}</ul>
              </section>
              {c.dependents.length > 0 && (
                <section data-testid="concept-dependents"><h3 className="text-lg">Notions qui s'appuient sur celle-ci</h3>
                  <ul className="mt-4 flex flex-wrap gap-2">{c.dependents.map((d) => <li key={d.id}><Link to={`/concepts/${d.id}`} data-testid={`concept-dependent-link-${d.id}`}><Pill className="hover:border-[#365ac8]">{d.name}</Pill></Link></li>)}</ul>
                </section>
              )}
              <Link to="/demo" className={LINK_ARROW} data-testid="concept-demo-link">Voir la notion dans la démonstration <ArrowRight size={14} aria-hidden="true" /></Link>
            </div>
          ) },
        ]} />
      </Container>
    </article>
  );
}
