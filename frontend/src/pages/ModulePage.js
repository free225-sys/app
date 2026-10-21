import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Clock, FileText } from "lucide-react";
import { http, useApi } from "@/lib/api";
import { statusLabel, useAuth, isAdmin } from "@/lib/auth";
import { BTN_PRIMARY, Container, ErrorState, Eyebrow, LINK_ARROW, LayerChip, Loading, Pill, SummaryCard, Tabs, Tag, minutes } from "@/components/common";
import { Picto } from "@/components/Pictos";

const STATUS_FR = { draft: "Brouillon", review: "En relecture", published: "Publié", retired: "Retiré" };

const ModuleCta = ({ moduleId }) => {
  const { user } = useAuth();
  const [prog, setProg] = useState(null);
  useEffect(() => {
    if (user && !isAdmin(user)) http.get(`/learners/me/modules/${moduleId}/progress`).then((r) => setProg(r.data)).catch(() => {});
  }, [user, moduleId]);
  if (isAdmin(user)) return <p className="text-sm text-[#505e75]" data-testid="module-admin-readonly">Mode administrateur : consultation en lecture seule, aucune progression n'est enregistrée.</p>;
  const label = !prog || prog.status === "not_started" ? "Commencer le module" : prog.status === "completed" ? "Revoir le module" : "Reprendre le module";
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <Link to={`/modules/${moduleId}/learn`} className={BTN_PRIMARY} data-testid="module-start-button">{label} <ArrowRight size={16} aria-hidden="true" /></Link>
      {prog ? (
        <span className="text-sm text-[#505e75]" data-testid="module-progress-summary">
          {statusLabel(prog.status)} · {prog.resources_done}/{prog.resources_total} ressources · évaluation {prog.graded.passed ? "réussie" : "à passer"}
        </span>
      ) : user === false && <span className="text-sm text-[#627086]">Connexion requise pour suivre le module et passer l'évaluation notée.</span>}
    </div>
  );
};

const pctTxt = (v) => `${Math.round(v * 100)} %`;

const ModuleEvaluation = ({ moduleId }) => {
  const { data: assessments } = useApi(`/modules/${moduleId}/assessments`);
  const [rubric, setRubric] = useState(null);
  useEffect(() => { http.get(`/projects/${moduleId}/rubric`).then((r) => setRubric(r.data)).catch(() => setRubric(false)); }, [moduleId]);
  if (!assessments || rubric === null) return <Loading />;
  const steps = assessments.map((a) => a.kind === "formative"
    ? { id: a.id, title: "Quiz formatif", text: `${a.question_count} questions, correction immédiate, essais illimités. Il n'entre pas dans la validation.` }
    : { id: a.id, title: "Quiz noté", text: `${a.question_count} questions, seuil de réussite ${pctTxt(a.pass_threshold)}, ${a.max_attempts} tentatives au plus.` });
  const total = rubric ? rubric.criteria.reduce((n, c) => n + c.weight, 0) : 0;
  return (
    <div className="space-y-8">
      <p>Chaque ressource est validée par l'action « J'ai terminé cette ressource ». Le module est terminé lorsque toutes les ressources sont lues et que l'évaluation notée est réussie{rubric ? " ; le projet final est évalué séparément." : "."}</p>
      <ol className="space-y-5">
        {steps.map((st, i) => (
          <li key={st.id} className="flex gap-4" data-testid={`module-evaluation-step-${st.id}`}>
            <span className="font-mono text-sm text-[#147c77]">{String(i + 1).padStart(2, "0")}</span>
            <div><h3 className="text-base">{st.title}</h3><p className="mt-1 text-sm text-[#505e75]">{st.text}</p></div>
          </li>
        ))}
        {rubric && (
          <li className="flex gap-4" data-testid="module-evaluation-project">
            <span className="font-mono text-sm text-[#147c77]">{String(steps.length + 1).padStart(2, "0")}</span>
            <div className="min-w-0 flex-1">
              <h3 className="text-base">Projet final</h3>
              <p className="mt-1 text-sm text-[#505e75]">Dépôt d'un livrable (description et fichier) depuis le lecteur du module. L'administrateur l'évalue critère par critère avec la grille « {rubric.title} ». Le projet est validé à partir de {pctTxt(rubric.pass_threshold)} du score pondéré. Vous suivez le statut (en attente, validé, à retravailler) et recevez un retour écrit.</p>
              <table className="mt-4 w-full text-left text-sm" data-testid="module-rubric-table">
                <caption className="sr-only">Critères de la grille et pondérations</caption>
                <thead><tr className="border-b border-[#e5e9ef] text-xs uppercase tracking-[0.1em] text-[#627086]"><th className="py-2 font-semibold">Critère</th><th className="py-2 text-right font-semibold">Pondération</th></tr></thead>
                <tbody>{rubric.criteria.map((c) => <tr key={c.id} className="border-b border-[#e5e9ef]"><td className="py-2 pr-4">{c.label}</td><td className="py-2 text-right font-mono">{c.weight} / {total}</td></tr>)}</tbody>
              </table>
              <p className="mt-3 text-xs text-[#627086]">Niveaux de la grille : {rubric.levels.map((l) => `${l.score} — ${l.label}`).join(" · ")}</p>
            </div>
          </li>
        )}
      </ol>
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
            { key: "duration", label: "Durée pédagogique estimée", value: <span className="font-semibold" data-testid="module-duration">{m.duration_hours} h</span> },
            { key: "reading", label: "Temps de lecture des ressources", value: <span className="font-semibold" data-testid="module-reading-time">{minutes(m.reading_minutes)}</span> },
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
            <section className="max-w-[72ch] space-y-8" data-testid="module-evaluation">
              <ModuleEvaluation moduleId={m.id} />
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
