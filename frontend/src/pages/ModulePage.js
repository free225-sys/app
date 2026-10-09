import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Clock, FileText } from "lucide-react";
import { http, useApi } from "@/lib/api";
import { STATUS_LABEL, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, Container, ErrorState, Eyebrow, LINK_ARROW, LayerChip, Loading, Tag } from "@/components/common";

const STATUS_FR = { draft: "Brouillon", review: "En relecture", published: "Publié", retired: "Retiré" };

const Side = ({ title, children, testId }) => (
  <section className="border-t border-[#e5e9ef] pt-5" data-testid={testId}>
    <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">{title}</h2>
    <div className="mt-3">{children}</div>
  </section>
);

const ModuleCta = ({ moduleId }) => {
  const { user } = useAuth();
  const [prog, setProg] = useState(null);
  useEffect(() => {
    if (user) http.get(`/learners/me/modules/${moduleId}/progress`).then((r) => setProg(r.data)).catch(() => {});
  }, [user, moduleId]);
  const label = !prog || prog.status === "not_started" ? "Commencer le module" : prog.status === "completed" ? "Revoir le module" : "Reprendre le module";
  return (
    <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
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
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-[1.12] tracking-tight sm:text-5xl" data-testid="module-title">{m.title}</h1>
          <p className="mt-6 max-w-3xl text-base leading-relaxed text-[#505e75] md:text-lg">{m.summary}</p>
          <dl className="mt-8 flex flex-wrap gap-x-10 gap-y-3 text-sm">
            <div><dt className="text-xs text-[#627086]">Niveaux</dt><dd className="font-mono font-semibold" data-testid="module-levels">{m.levels.join(" · ")}</dd></div>
            <div><dt className="text-xs text-[#627086]">Durée indicative</dt><dd className="font-semibold">{m.duration_hours} h</dd></div>
            <div><dt className="text-xs text-[#627086]">Ressources</dt><dd className="font-semibold">{m.resources.length}</dd></div>
          </dl>
          <ModuleCta moduleId={m.id} />
        </Container>
      </header>
      <Container className="grid gap-14 pt-12 lg:grid-cols-12">
        <div className="space-y-12 lg:col-span-8">
          <section data-testid="module-objectives">
            <h2 className="text-2xl font-semibold tracking-tight">Objectifs</h2>
            <ol className="mt-5 space-y-3">
              {m.objectives.map((o, i) => (
                <li key={o} className="flex gap-4 text-base leading-relaxed">
                  <span className="font-mono text-sm text-[#147c77]">{String(i + 1).padStart(2, "0")}</span>{o}
                </li>
              ))}
            </ol>
          </section>
          <section data-testid="module-resources">
            <h2 className="text-2xl font-semibold tracking-tight">Ressources du module</h2>
            <p className="mt-2 text-sm text-[#505e75]">Chaque ressource est validée par l'action « J'ai terminé cette ressource » dans le lecteur du module.</p>
            <ol className="mt-6 space-y-3">
              {m.resources.map((r, i) => (
                <li key={r.id} className="border border-[#e5e9ef] bg-white p-5" data-testid={`module-resource-${r.id}`}>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-[#627086]">
                    <span className="font-mono">{String(i + 1).padStart(2, "0")}</span>
                    <span className="inline-flex items-center gap-1 font-semibold text-[#14243c]"><FileText size={12} aria-hidden="true" />{r.type}</span>
                    <span className="inline-flex items-center gap-1"><Clock size={12} aria-hidden="true" />{r.duration_min} min</span>
                  </div>
                  <h3 className="mt-2 text-lg font-semibold">{r.title}</h3>
                  <ul className="mt-2 space-y-1">
                    {r.sections.map((s) => <li key={s.heading} className="text-sm text-[#505e75]">— {s.heading}</li>)}
                  </ul>
                </li>
              ))}
            </ol>
          </section>
        </div>
        <aside className="space-y-7 lg:col-span-4">
          <Side title="Prérequis" testId="module-prerequisites">
            <ul className="space-y-1.5 text-sm">{m.prerequisites.map((p) => <li key={p}>{p}</li>)}</ul>
            {m.prerequisite_modules.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {m.prerequisite_modules.map((p) => (
                  <li key={p.id}><Link to={`/modules/${p.id}`} className="text-sm font-medium text-[#147c77] hover:underline" data-testid={`module-prereq-link-${p.id}`}><span className="font-mono">{p.code}</span> {p.title}</Link></li>
                ))}
              </ul>
            )}
          </Side>
          <Side title="Couches" testId="module-layers"><div className="flex flex-wrap gap-2">{m.layers.map((l) => <LayerChip key={l.id} layer={l} />)}</div></Side>
          <Side title="Compétences visées" testId="module-competencies">
            <ul className="space-y-2">{m.competencies.map((c) => <li key={c.id} className="text-sm"><span className="font-semibold">{c.name}</span> — <span className="text-[#505e75]">{c.description}</span></li>)}</ul>
          </Side>
          <Side title="Étapes du traitement" testId="module-stages">
            <ul className="flex flex-wrap gap-2">{m.stages.map((s) => <li key={s.id}><Tag><span className="mr-1 font-mono">{s.code}</span>{s.name}</Tag></li>)}</ul>
          </Side>
          <Side title="Notions traitées" testId="module-concepts">
            <ul className="flex flex-wrap gap-2">
              {m.concepts.map((c) => <li key={c.id}><Link to={`/concepts/${c.id}`} className="inline-flex border border-[#e5e9ef] bg-white px-2.5 py-1 text-sm hover:border-[#147c77]" data-testid={`module-concept-link-${c.id}`}>{c.name}</Link></li>)}
            </ul>
          </Side>
          <Side title="Présent dans les cours" testId="module-courses">
            {m.courses.length ? (
              <ul className="space-y-1.5">{m.courses.map((c) => <li key={c.id}><Link to={`/courses/${c.id}`} className="text-sm font-medium text-[#147c77] hover:underline" data-testid={`module-course-link-${c.id}`}><span className="font-mono">{c.code}</span> {c.title}</Link></li>)}</ul>
            ) : <p className="text-sm text-[#505e75]">Module complémentaire, accessible hors cours.</p>}
          </Side>
        </aside>
      </Container>
    </article>
  );
}
