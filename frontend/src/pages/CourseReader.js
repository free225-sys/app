import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { http, useApi } from "@/lib/api";
import { STATUS_LABEL, statusLabel, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, Container, ErrorState, Eyebrow, LINK_ARROW, Loading, ProgressBar, levelRange } from "@/components/common";

const STATUS_STYLE = { completed: "bg-[#eef5f3] text-[#147c77]", in_progress: "bg-[#EDF3F8] text-[#254a98]", not_started: "bg-[#f1f4f7] text-[#627086]" };

export const StatusPill = ({ status, testId }) => (
  <span className={`rounded-[10px] px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[status]}`} data-testid={testId}>{statusLabel(status)}</span>
);

export const learnUrl = (resume) => `/modules/${resume.module_id}/learn?etape=${resume.resource_id || "evaluation"}`;

export default function CourseReader() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: course, loading, error } = useApi(`/courses/${id}`);
  const [prog, setProg] = useState(null);
  useEffect(() => {
    if (user && user.role === "learner") http.get(`/learners/me/courses/${id}/progress`).then((r) => setProg(r.data)).catch(() => setProg(null));
  }, [user, id]);

  if (error) return <ErrorState message="Ce cours est introuvable." />;
  if (loading) return <Loading />;
  const byModule = Object.fromEntries((prog?.modules || []).map((m) => [m.module_id, m]));
  const first = course.modules[0];
  const cta = prog?.resume
    ? { to: learnUrl(prog.resume), label: prog.status === "not_started" ? "Commencer le cours" : "Reprendre" }
    : prog ? null : { to: `/modules/${first.id}/learn`, label: "Commencer le cours" };

  return (
    <div data-testid="course-page">
      <Container className="pt-10">
        <Link to="/parcours" className={LINK_ARROW} data-testid="course-back-link"><ArrowLeft size={14} aria-hidden="true" /> Tous les parcours</Link>
      </Container>
      <header className="border-b border-[#e5e9ef] pb-12 pt-8">
        <Container className="grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <Eyebrow>Cours {course.code} · {levelRange(course.levels)} · durée pédagogique {course.duration_hours} h · lecture ~ {course.reading_minutes} min</Eyebrow>
            <h1 className="mt-5 text-4xl sm:text-5xl" data-testid="course-title">{course.title}</h1>
            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#505e75] md:text-lg">{course.summary}</p>
          </div>
          <div className="self-end lg:col-span-4">
            {prog && (
              <div className="mb-5">
                <div className="flex justify-between text-sm">
                  <span className="font-semibold" data-testid="course-progress-label">{prog.completed_count}/{prog.module_count} modules terminés</span>
                  <span className="font-mono" data-testid="course-progress-percent">{Math.round(prog.percent * 100)} %</span>
                </div>
                <div className="mt-2"><ProgressBar value={prog.percent} testId="course-progress-bar" /></div>
              </div>
            )}
            {cta ? (
              <Link to={cta.to} className={`${BTN_PRIMARY} w-full`} data-testid="course-resume-button">{cta.label} <ArrowRight size={16} aria-hidden="true" /></Link>
            ) : prog && <p className="text-sm font-semibold text-[#147c77]" data-testid="course-completed">Cours terminé.</p>}
            {!user && <p className="mt-3 text-xs text-[#627086]">Une connexion est nécessaire pour suivre les modules et enregistrer votre progression.</p>}
          </div>
        </Container>
      </header>
      <Container className="pt-10">
        <ol className="divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]" data-testid="course-modules">
          {course.modules.map((m, i) => {
            const p = byModule[m.id];
            return (
              <li key={m.id} className="grid gap-3 py-5 md:grid-cols-[3rem_1fr_14rem] md:items-center" data-testid={`course-module-${m.id}`}>
                <span className="font-mono text-sm text-[#627086]">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <Link to={`/modules/${m.id}`} className="group" data-testid={`course-module-link-${m.id}`}>
                    <span className="font-mono text-xs font-semibold text-[#147c77]">{m.code}</span>
                    <span className="ml-2 text-base font-semibold group-hover:underline">{m.title}</span>
                  </Link>
                  <p className="mt-1 text-xs text-[#627086]">{levelRange(m.levels)} · {m.resource_count} ressources · durée pédagogique {m.duration_hours} h · lecture ~ {m.reading_minutes} min{m.optional ? " · optionnel" : ""}</p>
                </div>
                <div className="flex items-center gap-3 md:justify-end">
                  {p ? (
                    <>
                      <StatusPill status={p.status} testId={`course-module-status-${m.id}`} />
                      <span className="w-12 text-right font-mono text-xs">{Math.round(p.percent * 100)} %</span>
                    </>
                  ) : <span className="text-xs text-[#627086]">—</span>}
                </div>
              </li>
            );
          })}
        </ol>
      </Container>
    </div>
  );
}
