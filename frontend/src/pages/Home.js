import { Link } from "react-router-dom";
import { Picto } from "@/components/Pictos";

const ROUTE = [["01", "◎", "Question et contexte"], ["02", "≡", "Analyse de la demande"], ["03", "▤", "Recherche documentaire"], ["04", "◇", "Traitement et génération"], ["05", "✓", "Réponse et références"]];

const AUDIENCES = [
  { id: "decouvrir", num: "01 — S'initier", title: "Découvrir les fondamentaux", text: "Comprendre les usages, les possibilités et les limites de l'IA sans prérequis technique.", to: "/pathways/P01" },
  { id: "utiliser", num: "02 — Utiliser", title: "Appliquer dans son métier", text: "Formuler ses besoins, exploiter des documents et fiabiliser ses méthodes de travail.", to: "/pathways/P-001" },
  { id: "concevoir", num: "03 — Concevoir", title: "Construire des solutions", text: "Maîtriser les données, modèles, architectures RAG, outils et évaluations.", to: "/pathways/P02" },
  { id: "piloter", num: "04 — Piloter", title: "Transformer une organisation", text: "Prioriser les cas d'usage, maîtriser les risques et mesurer la valeur créée.", to: "/parcours" },
];

const DIAGRAM = [["data", "Données", "Corpus, qualité, vecteurs"], ["mod", "Modèles", "Algorithmes, LLM"], ["infra", "Infrastructure", "CPU, GPU, stockage"], ["sec", "Gouvernance", "Accès, risques, audit"], ["", "Applications", "Services, interfaces"]];

const Hero = () => (
  <div className="shell hero" data-testid="home-hero">
    <div className="casa-reveal">
      <div className="eyebrow">Comprendre les systèmes d'IA, développer des compétences durables</div>
      <h1 data-testid="home-title">Comprendre ce qui se joue <em>entre la question et la réponse.</em></h1>
      <p className="lead">Une expérience de formation qui rend visible le fonctionnement de l'intelligence artificielle : les traitements, les données, les modèles et les choix technologiques mobilisés à chaque étape.</p>
      <div className="actions">
        <Link to="/demo" className="button" data-testid="hero-cta-demo">Explorer la démonstration&nbsp; →</Link>
        <a href="#parcours" className="button secondary" data-testid="hero-cta-parcours">Découvrir les parcours</a>
      </div>
      <div className="trust" data-testid="hero-reassurance"><span>Accessible sans inscription</span><span>Des cas appliqués aux métiers</span><span>Plusieurs niveaux d'approfondissement</span></div>
    </div>
    <div className="experience casa-reveal" style={{ animationDelay: "120ms" }} aria-label="Aperçu de la démonstration" data-testid="home-experience">
      <div className="exp-head"><strong>Une requête. Plusieurs mécanismes. Un résultat.</strong><span className="tag">Expérience guidée</span></div>
      <div className="promptbar"><span className="bubbleicon" aria-hidden="true">↗</span><span>« Quels textes régissent la commercialisation du café et du cacao ? »</span></div>
      <ol className="route">
        {ROUTE.map(([n, sym, label]) => (
          <li key={n} className="route-card" data-testid={`route-card-${n}`}><span className="route-num">{n}</span><span className="route-symbol" aria-hidden="true">{sym}</span><strong>{label}</strong></li>
        ))}
      </ol>
      <div className="exp-foot"><span>Chaque étape révèle les données, modèles, infrastructures et contrôles mobilisés.</span><Link to="/demo" data-testid="home-open-demo">Ouvrir la démonstration&nbsp; ↗</Link></div>
    </div>
  </div>
);

export default function Home() {
  return (
    <div data-testid="home-page">
      <Hero />
      <section id="parcours" className="section" aria-labelledby="parcours-title" data-testid="home-profiles">
        <div className="shell">
          <div className="section-head">
            <div><div className="eyebrow">À chacun sa progression</div><h2 id="parcours-title">Des compétences adaptées à votre rôle</h2></div>
            <p>Une même base de connaissances, plusieurs itinéraires d'apprentissage. Les acquis validés sont conservés d'un parcours à l'autre.</p>
          </div>
          <div className="audiences">
            {AUDIENCES.map((a) => (
              <article key={a.id} className="audience" data-testid={`profile-card-${a.id}`}>
                <span className="flex items-center justify-between"><span className="a-num">{a.num}</span><Picto id={a.id} size={20} /></span>
                <h3>{a.title}</h3>
                <p>{a.text}</p>
                <Link className="line-link" to={a.to} data-testid={`profile-link-${a.id}`}>Explorer un exemple →</Link>
              </article>
            ))}
          </div>
        </div>
      </section>
      <section id="architecture" className="section" aria-labelledby="archi-title" data-testid="home-architecture">
        <div className="shell premise">
          <div>
            <div className="eyebrow">Une architecture pédagogique commune</div>
            <div className="section-head"><div><h2 id="archi-title">Du parcours visible aux compétences mobilisées</h2></div></div>
            <p className="lead" style={{ fontSize: 15 }}>La plateforme associe deux dimensions : la succession des opérations réalisées par un système d'IA et les domaines techniques qui les rendent possibles. Chaque association mène vers des notions et ressources adaptées au niveau de l'apprenant.</p>
            <Link to="/demo?etape=3" className="button secondary mt-6" data-testid="home-architecture-cta">Explorer une étape →</Link>
          </div>
          <div className="diagram" data-testid="home-diagram">
            <div className="diagram-row">
              {DIAGRAM.map(([l, name, sub]) => <div key={name} className="diagram-block" data-l={l}><b>{name}</b>{sub}</div>)}
            </div>
            <p className="diagram-caption">Les couches sont transversales. Elles ne correspondent pas à cinq opérations exécutées les unes après les autres.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
