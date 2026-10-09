import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useCatalog } from "@/lib/api";
import { BTN_PRIMARY, Container, LayerChip, Loading, PageHeader, SectionTitle } from "@/components/common";

const MODEL = [
  { name: "Ressource", text: "Un contenu élémentaire : texte, schéma commenté, étude de cas, exercice guidé, fiche de synthèse." },
  { name: "Module", text: "Un ensemble cohérent de ressources autour d'objectifs, de couches, de niveaux et de compétences." },
  { name: "Cours", text: "Une sélection ordonnée de modules pour un public. Un même module peut appartenir à plusieurs cours." },
  { name: "Parcours", text: "Un enchaînement de cours qui conduit un profil d'un niveau de départ à un niveau visé." },
];

const STATUSES = [["Brouillon", "En cours de rédaction"], ["Relecture", "Validation pédagogique"], ["Publié", "Visible des apprenants"], ["Retiré", "Conservé pour l'historique"]];

export default function Approche() {
  const catalog = useCatalog();
  if (!catalog) return <Loading />;
  const axes = [
    { n: "01", title: "Le processus", lead: "Sept étapes, de la demande à la restitution.",
      body: <ol className="space-y-1 text-sm">{catalog.stages.map((s) => <li key={s.id}><span className="mr-2 font-mono text-xs text-[#147c77]">{s.code}</span>{s.name}</li>)}</ol> },
    { n: "02", title: "Les couches", lead: "Six couches transverses mobilisées à chaque étape.",
      body: <div className="flex flex-wrap gap-1.5">{catalog.layers.map((l) => <LayerChip key={l.id} layer={l} />)}</div> },
    { n: "03", title: "La profondeur", lead: "Cinq niveaux, de la découverte à l'expertise.",
      body: <ol className="space-y-1 text-sm">{catalog.levels.map((l) => <li key={l.id}><span className="mr-2 font-mono text-xs text-[#147c77]">{l.id}</span>{l.name} — <span className="text-[#505e75]">{l.description}</span></li>)}</ol> },
    { n: "04", title: "Les compétences", lead: "Cinq types de compétences visées.",
      body: <ul className="space-y-1 text-sm">{catalog.competencies.map((c) => <li key={c.id}><span className="font-semibold">{c.name}</span> — <span className="text-[#505e75]">{c.description}</span></li>)}</ul> },
  ];
  return (
    <div data-testid="approche-page">
      <PageHeader eyebrow="Notre approche" title="Rendre visible ce qui est habituellement caché."
        lead="Nous partons d'un fait simple : entre une question et une réponse, plusieurs traitements, données, modèles et choix technologiques interviennent. Les comprendre permet de mieux utiliser, concevoir et piloter l'IA." />
      <section className="py-16 sm:py-24" aria-labelledby="axes-title">
        <Container>
          <SectionTitle id="axes-title" eyebrow="Quatre axes" title="Chaque contenu est situé sur quatre axes."
            lead="Une notion ou un module est toujours rattaché à une ou plusieurs étapes, à des couches, à des niveaux de profondeur et à des compétences. C'est ce qui permet de filtrer le catalogue et de composer des parcours cohérents." />
          <div className="mt-12 grid gap-px border border-[#e5e9ef] bg-[#e5e9ef] md:grid-cols-2">
            {axes.map((a) => (
              <section key={a.n} className="bg-[#f7f8fa] p-7 sm:p-9" data-testid={`axis-${a.n}`}>
                <span className="font-mono text-sm text-[#627086]">{a.n}</span>
                <h3 className="mt-2 text-2xl font-semibold">{a.title}</h3>
                <p className="mt-1 text-sm text-[#505e75]">{a.lead}</p>
                <div className="mt-6">{a.body}</div>
              </section>
            ))}
          </div>
        </Container>
      </section>
      <section className="border-y border-[#e5e9ef] bg-white py-16 sm:py-24" aria-labelledby="model-title">
        <Container>
          <SectionTitle id="model-title" eyebrow="Organisation des contenus" title="Ressource, module, cours, parcours."
            lead="Les contenus s'emboîtent à quatre niveaux. Un module est rédigé une seule fois et réutilisé dans plusieurs cours : une correction profite immédiatement à tous les parcours concernés." />
          <ol className="mt-12 grid gap-4 md:grid-cols-4" data-testid="content-model">
            {MODEL.map((m, i) => (
              <li key={m.name} className="relative border border-[#14243c]/20 p-6">
                <span className="font-mono text-xs text-[#627086]">Niveau {i + 1}</span>
                <h3 className="mt-2 text-xl font-semibold">{m.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[#505e75]">{m.text}</p>
                {i < MODEL.length - 1 && <ArrowRight size={16} className="absolute -right-3 top-1/2 hidden -translate-y-1/2 bg-white text-[#147c77] md:block" aria-hidden="true" />}
              </li>
            ))}
          </ol>
          <div className="mt-14 grid gap-8 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <h3 className="text-xl font-semibold">Des contenus versionnés</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#505e75]">Modules, cours et parcours existent en versions successives. Seule la version publiée est visible ; les précédentes restent consultables pour l'historique et la traçabilité des certifications.</p>
            </div>
            <ol className="grid gap-px border border-[#e5e9ef] bg-[#e5e9ef] sm:grid-cols-4 lg:col-span-7">
              {STATUSES.map(([s, d]) => <li key={s} className="bg-white p-4"><p className="text-sm font-semibold">{s}</p><p className="mt-1 text-xs text-[#627086]">{d}</p></li>)}
            </ol>
          </div>
        </Container>
      </section>
      <Container className="pt-16">
        <Link to="/demo" className={BTN_PRIMARY} data-testid="approche-demo-cta">Explorer la démonstration <ArrowRight size={16} aria-hidden="true" /></Link>
      </Container>
    </div>
  );
}
