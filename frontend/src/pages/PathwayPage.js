import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, BadgeCheck } from "lucide-react";
import { http, useApi, useCatalog } from "@/lib/api";
import { formatApiError, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, Container, ErrorState, Eyebrow, LINK_ARROW, Loading, ProgressBar, SectionTitle, levelRange } from "@/components/common";
import { StatusPill } from "@/pages/CourseReader";

const date = (iso) => new Date(iso).toLocaleDateString("fr-FR");
const TARGET_LABEL = { acquired: "Acquise", in_progress: "En cours", not_started: "À acquérir" };

export const RecognizedBadge = ({ testId }) => (
  <span className="inline-flex items-center gap-1 rounded-[10px] bg-[#EDF3F8] px-2 py-0.5 text-xs font-semibold text-[#254a98]" data-testid={testId}>
    <BadgeCheck size={12} aria-hidden="true" /> Acquis reconnu
  </span>
);

const CourseGroup = ({ title, courses, coursesInfo, progress }) => (
  <div>
    <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">{title}</h3>
    <ul className="mt-3 space-y-4">
      {courses.map((cid) => {
        const c = coursesInfo[cid];
        const p = progress?.find((x) => x.course_id === cid);
        const pmods = Object.fromEntries((p?.modules || []).map((m) => [m.module_id, m]));
        return (
          <li key={cid} className="border border-[#e5e9ef] bg-white" data-testid={`pathway-course-${cid}`}>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5e9ef] px-5 py-4">
              <Link to={`/courses/${cid}`} className="font-semibold hover:underline"><span className="mr-2 font-mono text-xs text-[#147c77]">{cid}</span>{c.title}</Link>
              <span className="flex items-center gap-3 text-xs">
                <span className="font-mono">{levelRange(c.levels)}</span>
                {p && <StatusPill status={p.status} testId={`pathway-course-status-${cid}`} />}
                {p && <span className="font-mono">{Math.round(p.percent * 100)} %</span>}
              </span>
            </div>
            <ol className="divide-y divide-[#e5e9ef]">
              {c.modules.map((m) => {
                const pm = pmods[m.id];
                return (
                  <li key={m.id} className="flex flex-wrap items-center gap-3 px-5 py-2.5 text-sm" data-testid={`pathway-${cid}-module-${m.id}`}>
                    <span className="font-mono text-xs font-semibold text-[#147c77]">{m.code}</span>
                    <Link to={`/modules/${m.id}`} className="flex-1 hover:underline">{m.title}</Link>
                    {pm?.recognized && (
                      <span className="flex items-center gap-2 text-xs text-[#627086]">
                        <RecognizedBadge testId={`recognized-module-${cid}-${m.id}`} />
                        validé le {date(pm.recognition.completed_at)}{pm.recognition.source_pathway_id ? ` (parcours ${pm.recognition.source_pathway_id})` : ""} · v{pm.recognition.module_version}
                      </span>
                    )}
                    {pm && !pm.recognized && <StatusPill status={pm.status} />}
                  </li>
                );
              })}
            </ol>
          </li>
        );
      })}
    </ul>
  </div>
);

export default function PathwayPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const catalog = useCatalog();
  const { data: pathway, loading, error } = useApi(`/pathways/${id}`);
  const [prog, setProg] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (user) http.get(`/learners/me/pathways/${id}/progress`).then((r) => setProg(r.data)).catch(() => {});
  }, [user, id]);

  if (error) return <ErrorState message="Ce parcours est introuvable." />;
  if (loading || !catalog) return <Loading />;
  const compNames = Object.fromEntries(catalog.competencies.map((c) => [c.id, c.name]));
  const coursesInfo = Object.fromEntries(pathway.courses.map((c) => [c.id, c]));
  const group = (g) => pathway.pathway_courses.filter((pc) => pc.group === g).map((pc) => pc.course_id);
  const enroll = async () => {
    if (!user) return navigate(`/connexion?suite=${encodeURIComponent(`/pathways/${id}`)}`);
    try {
      const { data } = await http.post(`/pathways/${id}/enroll`);
      setProg(data);
    } catch (e) {
      setErr(formatApiError(e));
    }
  };
  const targets = Object.fromEntries((prog?.targets || []).map((t) => [t.competency_id, t]));

  return (
    <div data-testid="pathway-page">
      <Container className="pt-10"><Link to="/parcours" className={LINK_ARROW} data-testid="pathway-back-link"><ArrowLeft size={14} aria-hidden="true" /> Tous les parcours</Link></Container>
      <header className="border-b border-[#e5e9ef] pb-12 pt-8">
        <Container className="grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <Eyebrow>Parcours {pathway.code} · version {prog?.pathway_version || pathway.version}</Eyebrow>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl" data-testid="pathway-title">{pathway.title}</h1>
            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#505e75] md:text-lg">{pathway.summary}</p>
          </div>
          <div className="self-end lg:col-span-4">
            {prog?.enrolled ? (
              <div data-testid="pathway-enrolled">
                <p className="text-sm font-semibold">Inscrit depuis le {date(prog.enrolled_at)}</p>
                <div className="mt-3 flex justify-between text-xs"><span>Cours obligatoires</span><span className="font-mono" data-testid="pathway-percent">{Math.round(prog.percent * 100)} %</span></div>
                <div className="mt-2"><ProgressBar value={prog.percent} testId="pathway-progress-bar" /></div>
                {(prog.recognized_counts.modules > 0 || prog.recognized_counts.competencies > 0) && (
                  <p className="mt-3 text-xs text-[#254a98]" data-testid="pathway-recognized-summary">
                    {prog.recognized_counts.modules} module(s) et {prog.recognized_counts.competencies} compétence(s) reconnus automatiquement à l'inscription.
                  </p>
                )}
              </div>
            ) : (
              <>
                <button type="button" className={`${BTN_PRIMARY} w-full`} onClick={enroll} data-testid="pathway-enroll-button">S'inscrire à ce parcours <ArrowRight size={16} aria-hidden="true" /></button>
                <p className="mt-3 text-xs text-[#627086]">Les modules et compétences déjà validés sont reconnus automatiquement, sans nouvelle évaluation.</p>
                {err && <p role="alert" className="mt-3 text-sm text-[#7E2828]">{err}</p>}
              </>
            )}
          </div>
        </Container>
      </header>
      <Container className="grid gap-14 pt-12 lg:grid-cols-12">
        <div className="space-y-10 lg:col-span-8">
          <CourseGroup title="Cours obligatoires" courses={group("mandatory")} coursesInfo={coursesInfo} progress={prog?.groups.mandatory} />
          {group("optional").length > 0 && <CourseGroup title="Cours optionnels" courses={group("optional")} coursesInfo={coursesInfo} progress={prog?.groups.optional} />}
        </div>
        <aside className="lg:col-span-4" data-testid="pathway-targets">
          <SectionTitle eyebrow="Objectifs" title="Compétences visées" />
          <ul className="mt-6 divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]">
            {pathway.target_competencies.map((t) => {
              const s = targets[t.competency_id];
              return (
                <li key={t.competency_id} className="py-4" data-testid={`pathway-target-${t.competency_id}`}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold">{compNames[t.competency_id]}</span>
                    <span className="font-mono text-xs">niveau requis {t.level}</span>
                  </div>
                  {s && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[#505e75]">
                      {s.recognized ? <RecognizedBadge testId={`recognized-competency-${t.competency_id}`} /> : (
                        <span className="font-semibold" data-testid={`pathway-target-status-${t.competency_id}`}>{TARGET_LABEL[s.status]}</span>
                      )}
                      {s.current_level && <span>niveau atteint {s.current_level}</span>}
                      {s.evidence && <span>· preuve : {s.evidence.evidence_type === "project" ? "projet" : "évaluation notée"} {s.evidence.module_id}</span>}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </aside>
      </Container>
    </div>
  );
}
