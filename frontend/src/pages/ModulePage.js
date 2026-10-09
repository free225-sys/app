import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Clock, FileText } from "lucide-react";
import { http, useApi } from "@/lib/api";
import { STATUS_LABEL, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, Container, ErrorState, Eyebrow, LINK_ARROW, LayerChip, Loading, Pill, SummaryCard, Tabs, Tag, minutes } from "@/components/common";
import { Picto } from "@/components/Pictos";

const STATUS_FR = { draft: "Brouillon", review: "En relecture", published: "Publié", retired: "Retiré" };

const ModuleCta = ({ moduleId }) => {
  const { user } = useAuth();
  const [prog, setProg] = useState(null);
  useEffect(() => {
    if (user) http.get(`/learners/me/modules/${moduleId}/progress`).then((r) => setProg(r.data)).catch(() => {});
  }, [user, moduleId]);
  const label = !prog || prog.status === "not_started" ? "Commencer le module" : prog.status === "completed" ? "Revoir le module" : "Reprendre le module";
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <Link to={`/modules/${moduleId}/learn`} className={BTN_PRIMARY} data-testid="module-start-button">{label} <ArrowRight size={16} aria-hidden="true" /></Link>
      {prog ? (
        <span className="text-sm text-[#505e75]" data-testid="module-progress-summary">
          {STATUS_LABEL[prog.status]} · {prog.resources_done}/{prog.resources_total} ressources · évaluation {prog.graded.passed ? "réussie" : "à passer"}
        </span>
      ) : user === false && <span className="text-sm text-[#627086]">Connexion requise pour suivre le module et passer l'évaluation notée.</span>}
    </div>
  );
};

export default function ModulePage() {
  const { id } = useParams();
  const { data: m, loading, error } = useApi(`/modules/${id}`);
  if (error) return <ErrorState message="Ce module est introuvable." />;
  if (loading) return <Loading />;
  return (
    <article data-testid="module-page">
      <Container className="pt-10">
        <Link to="/ressources" className={LINK_ARROW} data-testid="module-back-link"><ArrowLeft size={14} aria-hidden="true" /> Tous les modules</Link>
      </Container>
      <header className="border-b border-[#e5e9ef] pb-12 pt-8">
        <Container>
          <div className="flex flex-wrap items-center gap-3">
            <Eyebrow>Module {m.code}</Eyebrow>
            <Tag data-testid="module-version">Version {m.version} · {STATUS_FR[m.status]}</Tag>
          </div>
          <h1 className="mt-5 max-w-4xl text-4xl leading-[1.12] sm:text-5xl" data-testid="module-title">{m.title}</h1>
          <p className="mt-6 text-base leading-relaxed text-[#505e75] md:text-lg">{m.summary}</p>
          <SummaryCard testId="module-summary" items={[
            { key: "levels", label: "Niveaux", value: <span className="font-mono font-semibold" data-testid="module-levels">{m.levels.join(" · ")}</span> },
            { key: "duration", label: "Durée estimée", value: <span className="font-semibold" data-testid="module-duration">{minutes(m.estimated_minutes)}</span> },
            { key: "layers", label: "Couches", value: m.layers.map((l) => <LayerChip key={l.id} layer={l} />) },
            { key: "competencies", label: "Compétences visées", value: m.competencies.map((c) => <Pill key={c.id}><Picto id={c.id} category={c.category_id} size={13} />{c.name}</Pill>) },
            { key: "prerequisites", label: "Prérequis", value: m.prerequisite_modules.length ? m.prerequisite_modules.map((p) => (
              <Link key={p.id} to={`/modules/${p.id}`} data-testid={`module-prereq-link-${p.id}`}><Pill className="hover:border-[#365ac8]"><span className="font-mono">{p.code}</span>{p.title}</Pill></Link>
            )) : <Pill>Aucun</Pill> },
          ]}>
            <ModuleCta moduleId={m.id} />
          </SummaryCard>
        </Container>
      </header>
      <Container className="py-16 sm:py-20">
        <Tabs label="Contenu du module" testId="module-tabs" tabs={[
          { id: "objectifs", label: "Objectifs", content: (
            <section data-testid="module-objectives">
              <ol className="max-w-[68ch] space-y-4">
                {m.objectives.map((o, i) => <li key={o} className="flex gap-4 text-base leading-relaxed"><span className="font-mono text-sm text-[#147c77]">{String(i + 1).padStart(2, "0")}</span>{o}</li>)}
              </ol>
              {m.prerequisites.length > 0 && <p className="mt-8 text-sm text-[#627086]" data-testid="module-prerequisites">Prérequis : {m.prerequisites.join(" · ")}</p>}
            </section>
          ) },
          { id: "contenu", label: "Contenu", content: (
            <section data-testid="module-resources">
              <ol className="grid gap-6 md:grid-cols-2">
                {m.resources.map((r, i) => (
                  <li key={r.id} className="rounded-[17px] border border-[#e5e9ef] bg-white p-7" data-testid={`module-resource-${r.id}`}>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-[#627086]">
                      <span className="font-mono">{String(i + 1).padStart(2, "0")}</span>
                      <span className="inline-flex items-center gap-1 font-semibold text-[#14243c]"><FileText size={12} aria-hidden="true" />{r.type}</span>
                      <span className="inline-flex items-center gap-1"><Clock size={12} aria-hidden="true" />{r.duration_min} min</span>
                    </div>
                    <h3 className="mt-3 text-lg">{r.title}</h3>
                    <ul className="mt-3 space-y-1">{(r.sections || []).map((sec) => <li key={sec.heading} className="text-sm text-[#505e75]">— {sec.heading}</li>)}</ul>
                  </li>
                ))}
              </ol>
              <div className="mt-12 grid gap-10 md:grid-cols-2">
                <div data-testid="module-concepts"><h3 className="text-lg">Notions traitées</h3>
                  <ul className="mt-4 flex flex-wrap gap-2">{m.concepts.map((c) => <li key={c.id}><Link to={`/concepts/${c.id}`} data-testid={`module-concept-link-${c.id}`}><Pill className="hover:border-[#365ac8]">{c.name}</Pill></Link></li>)}</ul></div>
                <div data-testid="module-stages"><h3 className="text-lg">Étapes du traitement</h3>
                  <ul className="mt-4 flex flex-wrap gap-2">{m.stages.map((st) => <li key={st.id}><Pill><Picto id={st.id} size={13} />{st.name}</Pill></li>)}</ul></div>
              </div>
            </section>
          ) },
          { id: "evaluation", label: "Évaluation", content: (
            <section className="max-w-[68ch] space-y-6" data-testid="module-evaluation">
              <p>Chaque ressource est validée par l'action « J'ai terminé cette ressource ». Le module est terminé lorsque toutes les ressources sont lues et l'évaluation réussie.</p>
              <ul className="space-y-3 text-sm">
                <li className="flex gap-3"><Picto id="comp-utiliser" />Quiz formatif : correction immédiate, essais illimités.</li>
                <li className="flex gap-3"><Picto id="comp-evaluer" />Évaluation notée : seuil de réussite, trois tentatives au plus.</li>
              </ul>
              <div data-testid="module-courses"><h3 className="text-lg">Présent dans les cours</h3>
                {m.courses.length ? <ul className="mt-3 space-y-2">{m.courses.map((c) => <li key={c.id}><Link to={`/courses/${c.id}`} className="text-sm font-medium text-[#147c77] hover:underline" data-testid={`module-course-link-${c.id}`}><span className="font-mono">{c.code}</span> {c.title}</Link></li>)}</ul>
                  : <p className="mt-3 text-sm text-[#505e75]">Module complémentaire, accessible hors cours.</p>}
              </div>
            </section>
          ) },
        ]} />
      </Container>
    </article>
  );
}
