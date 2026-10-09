import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useApi, useCatalog } from "@/lib/api";
import { Container, ErrorState, Eyebrow, LINK_ARROW, LayerChip, Loading, levelRange } from "@/components/common";

const Block = ({ title, children, testId }) => (
  <section className="border-t border-[#e5e9ef] pt-6" data-testid={testId}>
    <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">{title}</h2>
    <div className="mt-4">{children}</div>
  </section>
);

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
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl" data-testid="concept-title">{c.name}</h1>
          <p className="mt-5 max-w-3xl text-base text-[#505e75] md:text-lg">{c.short}</p>
        </Container>
      </header>
      <Container className="grid gap-14 pt-12 lg:grid-cols-12">
        <div className="space-y-10 lg:col-span-8">
          <section data-testid="concept-definition">
            <h2 className="text-2xl font-semibold tracking-tight">Définition</h2>
            <p className="mt-4 text-base leading-relaxed">{c.definition}</p>
            <div className="mt-6 border-l-2 border-[#365ac8] bg-white px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Exemple — cas CASA</p>
              <p className="mt-1.5 text-sm leading-relaxed text-[#505e75]">{c.example}</p>
            </div>
          </section>
          <section data-testid="concept-treatment">
            <h2 className="text-2xl font-semibold tracking-tight">Traitement par niveau</h2>
            <p className="mt-2 text-sm text-[#505e75]">Ce que l'on attend de vous sur cette notion, du niveau découverte au niveau expertise.</p>
            <ol className="mt-6 divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]">
              {catalog.levels.map((lv) => (
                <li key={lv.id} className={`grid gap-2 py-4 sm:grid-cols-[10rem_1fr] sm:gap-6 ${c.levels.includes(lv.id) ? "" : "opacity-70"}`} data-testid={`concept-level-${lv.id}`}>
                  <div>
                    <span className="font-mono text-sm font-semibold text-[#147c77]">{lv.id}</span>
                    <span className="ml-2 text-sm font-medium">{lv.name}</span>
                  </div>
                  <p className="text-sm leading-relaxed">{c.treatment[lv.id]}</p>
                </li>
              ))}
            </ol>
          </section>
        </div>
        <aside className="space-y-8 lg:col-span-4">
          <Block title="Étapes associées" testId="concept-stages">
            <ul className="space-y-2">
              {c.stages.map((s) => (
                <li key={s.id} className="flex items-baseline gap-3 text-sm">
                  <span className="font-mono text-xs text-[#147c77]">{s.code}</span>
                  <Link to={`/demo?etape=${parseInt(s.code, 10)}`} className="font-medium hover:underline" data-testid={`concept-stage-link-${s.id}`}>{s.name}</Link>
                  <span className="text-xs text-[#627086]">{s.subtitle}</span>
                </li>
              ))}
            </ul>
          </Block>
          <Block title="Couches associées" testId="concept-layers">
            <div className="flex flex-wrap gap-2">{c.layers.map((l) => <LayerChip key={l.id} layer={l} />)}</div>
          </Block>
          <Block title="Prérequis" testId="concept-prerequisites">
            {c.prerequisites.length ? (
              <ul className="space-y-2">
                {c.prerequisites.map((p) => (
                  <li key={p.id}><Link to={`/concepts/${p.id}`} className="text-sm font-medium text-[#147c77] hover:underline" data-testid={`concept-prereq-link-${p.id}`}>{p.name}</Link></li>
                ))}
              </ul>
            ) : <p className="text-sm text-[#505e75]">Aucun prérequis.</p>}
          </Block>
          <Block title="Modules liés" testId="concept-modules">
            <ul className="space-y-3">
              {c.modules.map((m) => (
                <li key={m.id}>
                  <Link to={`/modules/${m.id}`} className="group flex items-start gap-3 text-sm" data-testid={`concept-module-link-${m.id}`}>
                    <span className="font-mono text-xs font-semibold text-[#147c77]">{m.code}</span>
                    <span className="flex-1 font-medium group-hover:underline">{m.title}</span>
                    <span className="font-mono text-xs text-[#627086]">{levelRange(m.levels)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Block>
          {c.dependents.length > 0 && (
            <Block title="Notions qui s'appuient sur celle-ci" testId="concept-dependents">
              <ul className="flex flex-wrap gap-2">
                {c.dependents.map((d) => (
                  <li key={d.id}><Link to={`/concepts/${d.id}`} className="inline-flex border border-[#e5e9ef] bg-white px-2.5 py-1 text-sm hover:border-[#147c77]" data-testid={`concept-dependent-link-${d.id}`}>{d.name}</Link></li>
                ))}
              </ul>
            </Block>
          )}
          <Link to="/demo" className={LINK_ARROW} data-testid="concept-demo-link">Voir la notion dans la démonstration <ArrowRight size={14} aria-hidden="true" /></Link>
        </aside>
      </Container>
    </article>
  );
}
