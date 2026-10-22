import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Check, ClipboardCheck, FolderKanban, PenLine } from "lucide-react";
import { http, useApi, useCatalog } from "@/lib/api";
import { RequireAuth, statusLabel } from "@/lib/auth";
import { Container, ErrorState, LINK_ARROW, Loading, ProgressBar } from "@/components/common";
import { ResourceView } from "@/components/learn/ResourceView";
import { FormativeQuiz } from "@/components/learn/FormativeQuiz";
import { GradedQuiz } from "@/components/learn/GradedQuiz";
import { ProjectPanel } from "@/components/learn/ProjectPanel";
import { PreviousCompletion } from "@/pages/ModulePage";


const SideItem = ({ active, done, icon, label, sub, onClick, testId }) => (
  <li>
    <button type="button" onClick={onClick} aria-current={active ? "step" : undefined}
      className={`flex w-full items-start gap-3 px-4 py-3 text-left text-sm transition-colors duration-200 ${active ? "bg-[#f1f4f7]" : "hover:bg-[#f7f8fa]"}`} data-testid={testId}>
      <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${done ? "border-[#147c77] bg-[#147c77] text-white" : "border-[#14243c]/30 text-[#627086]"}`} aria-hidden="true">
        {done ? <Check size={12} /> : icon}
      </span>
      <span className="flex-1">
        <span className={`block ${active ? "font-semibold" : ""}`}>{label}</span>
        {sub && <span className="block text-xs text-[#627086]">{sub}</span>}
      </span>
      <span className="sr-only">{done ? "terminé" : "à faire"}</span>
    </button>
  </li>
);

function LearnView() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const catalog = useCatalog();
  const { data: mod, error } = useApi(`/modules/${id}`);
  const { data: rubric } = useApi(`/projects/${id}/rubric`);
  const [progress, setProgress] = useState(null);
  const [busy, setBusy] = useState(false);
  const reload = useCallback(() => http.get(`/learners/me/modules/${id}/progress`).then((r) => setProgress(r.data)), [id]);
  useEffect(() => { reload(); }, [reload]);
  const compNames = useMemo(() => Object.fromEntries((catalog?.competencies || []).map((c) => [c.id, c.name])), [catalog]);

  if (error) return <ErrorState message="Ce module est introuvable." />;
  if (!mod || !progress || !catalog) return <Loading />;

  const g = progress.graded;
  const hasFormative = !mod.assessment_ids || mod.assessment_ids.includes(`A-${id}-F`);
  const current = params.get("etape") || progress.next_resource_id || (g ? "evaluation" : rubric ? "projet" : "formatif");
  const go = (e) => { setParams({ etape: e }); window.scrollTo({ top: 0 }); };
  const done = Object.fromEntries(progress.resources.map((r) => [r.id, r.completed]));
  const idx = mod.resources.findIndex((r) => r.id === current);
  const resource = mod.resources[idx];
  const complete = async () => {
    setBusy(true);
    const { data } = await http.post(`/learners/me/resources/${resource.id}/complete`).finally(() => setBusy(false));
    setProgress(data);
  };
  const nextKey = idx >= 0 && idx < mod.resources.length - 1 ? mod.resources[idx + 1].id : hasFormative ? "formatif" : g ? "evaluation" : rubric ? "projet" : null;

  return (
    <div data-testid="module-learn-page">
      <div className="border-b border-[#e5e9ef] bg-white">
        <Container className="py-8">
          <Link to={`/modules/${id}`} className={LINK_ARROW} data-testid="learn-back-link"><ArrowLeft size={14} aria-hidden="true" /> Fiche du module</Link>
          <div className="mt-5 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="font-mono text-sm font-semibold text-[#147c77]">{mod.code}</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl" data-testid="learn-module-title">{mod.title}</h1>
            </div>
            <div className="w-full md:w-72">
              <div className="flex justify-between text-xs">
                <span className="font-semibold" data-testid="learn-module-status">{statusLabel(progress.status)}</span>
                <span className="font-mono" data-testid="learn-module-percent">{Math.round(progress.percent * 100)} %</span>
              </div>
              <div className="mt-2"><ProgressBar value={progress.percent} testId="learn-progress-bar" /></div>
              {progress.previous_completion && <div className="mt-3"><PreviousCompletion moduleId={id} prev={progress.previous_completion} onGo={() => go("evaluation")} /></div>}
            </div>
          </div>
          {progress.status === "completed" && (
            <p className="mt-6 border-l-2 border-[#147c77] bg-[#eef5f3] px-4 py-3 text-sm font-semibold" role="status" data-testid="learn-module-completed">
              Module terminé. Vos compétences validées sont visibles dans <Link to="/espace" className="underline">votre espace</Link>.
            </p>
          )}
        </Container>
      </div>
      <Container className="grid gap-10 pt-10 lg:grid-cols-12">
        <nav aria-label="Contenu du module" className="lg:col-span-4">
          <div className="border border-[#e5e9ef] bg-white lg:sticky lg:top-24">
            <p className="border-b border-[#e5e9ef] px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">
              Ressources · {progress.resources_done}/{progress.resources_total}
            </p>
            <ul className="divide-y divide-[#e5e9ef]">
              {mod.resources.map((r, i) => (
                <SideItem key={r.id} active={current === r.id} done={done[r.id]} icon={<span className="font-mono text-[10px]">{i + 1}</span>}
                  label={r.title} sub={`${r.type} · ${r.duration_min} min`} onClick={() => go(r.id)} testId={`learn-nav-${r.id}`} />
              ))}
            </ul>
            <p className="border-y border-[#e5e9ef] px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Évaluations</p>
            <ul className="divide-y divide-[#e5e9ef]">
              {hasFormative && <SideItem active={current === "formatif"} done={false} icon={<PenLine size={11} />} label="Quiz formatif" sub="Entraînement, essais illimités"
                onClick={() => go("formatif")} testId="learn-nav-formatif" />}
              {g && <SideItem active={current === "evaluation"} done={g.passed} icon={<ClipboardCheck size={11} />} label="Évaluation notée"
                sub={`${g.attempts_used}/${g.max_attempts ?? 3} tentatives${g.best_percent != null ? ` · meilleur score ${Math.round(g.best_percent * 100)} %` : ""}`}
                onClick={() => go("evaluation")} testId="learn-nav-evaluation" />}
              {rubric && (
                <SideItem active={current === "projet"} done={false} icon={<FolderKanban size={11} />} label="Projet appliqué" sub="Dépôt et évaluation par grille"
                  onClick={() => go("projet")} testId="learn-nav-projet" />
              )}
            </ul>
          </div>
        </nav>
        <div className="lg:col-span-8">
          {resource ? (
            <ResourceView key={resource.id} resource={resource} index={idx} total={mod.resources.length} completed={done[resource.id]} busy={busy}
              onComplete={complete} onNext={nextKey ? () => go(nextKey) : null} nextLabel={{ formatif: "Passer au quiz formatif", evaluation: "Passer à l'évaluation notée", projet: "Passer au projet" }[nextKey] || "Ressource suivante"} />
          ) : current === "formatif" ? (
            <>
              <FormativeQuiz moduleId={id} compNames={compNames} />
              {g && <button type="button" className="mt-12 text-sm font-semibold text-[#147c77] underline underline-offset-4" onClick={() => go("evaluation")} data-testid="formative-to-graded">
                Passer à l'évaluation notée
              </button>}
            </>
          ) : current === "projet" && rubric ? (
            <ProjectPanel moduleId={id} rubric={rubric} />
          ) : !g ? (
            <FormativeQuiz moduleId={id} compNames={compNames} />
          ) : (
            <GradedQuiz key={id} moduleId={id} compNames={compNames} onSubmitted={setProgress} />
          )}
        </div>
      </Container>
    </div>
  );
}

export default function ModuleLearn() {
  return (
    <RequireAuth learner>
      <LearnView />
    </RequireAuth>
  );
}
