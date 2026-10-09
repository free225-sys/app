import { Link } from "react-router-dom";
import { ArrowRight, Award } from "lucide-react";
import { useApi } from "@/lib/api";
import { RequireAuth, useAuth } from "@/lib/auth";
import { Container, ErrorState, Eyebrow, LINK_ARROW, Loading, ProgressBar, SectionTitle } from "@/components/common";
import { StatusPill, learnUrl } from "@/pages/CourseReader";
import { CertificatesSection, PathwaysSection, ProjectsSection } from "@/components/espace/Phase3Sections";

const pct = (v) => `${Math.round((v || 0) * 100)} %`;
const date = (iso) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });

const RECO_LINK = { demo: () => "/demo", diagnostic: () => "/diagnostic", module: (r) => `/modules/${r.module_id}/learn` };

const Recommendations = ({ items }) => (
  <section aria-labelledby="reco-title" data-testid="espace-recommendations">
    <SectionTitle id="reco-title" eyebrow="Recommandations" title="Votre prochaine étape" />
    <ul className="mt-6 grid gap-4 md:grid-cols-3">
      {items.map((r, i) => (
        <li key={i}>
          <Link to={RECO_LINK[r.kind](r)} className={`flex h-full flex-col border p-5 transition-colors duration-200 hover:border-[#14243c]/50 ${i === 0 ? "border-[#147c77] bg-[#eef5f3]" : "border-[#e5e9ef] bg-white"}`} data-testid={`reco-${r.kind}`}>
            <span className="text-base font-semibold">{r.label}</span>
            <span className="mt-1 flex-1 text-sm text-[#505e75]">{r.reason}</span>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#147c77]">Y aller <ArrowRight size={14} aria-hidden="true" /></span>
          </Link>
        </li>
      ))}
    </ul>
  </section>
);

const Courses = ({ courses }) => (
  <section aria-labelledby="courses-title" data-testid="espace-courses">
    <SectionTitle id="courses-title" eyebrow="Progression" title="Vos cours" />
    <ul className="mt-6 grid gap-4 md:grid-cols-2">
      {courses.map((c) => (
        <li key={c.course_id} className="border border-[#e5e9ef] bg-white p-5" data-testid={`espace-course-${c.course_id}`}>
          <div className="flex items-center justify-between gap-3">
            <Link to={`/courses/${c.course_id}`} className="font-semibold hover:underline"><span className="mr-2 font-mono text-xs text-[#147c77]">{c.code}</span>{c.title}</Link>
            <StatusPill status={c.status} />
          </div>
          <div className="mt-4 flex justify-between text-xs"><span>{c.completed_count}/{c.module_count} modules terminés</span><span className="font-mono" data-testid={`espace-course-percent-${c.course_id}`}>{pct(c.percent)}</span></div>
          <div className="mt-2"><ProgressBar value={c.percent} /></div>
          <ul className="mt-4 flex flex-wrap gap-1.5" aria-label="Modules du cours">
            {c.modules.map((m) => (
              <li key={m.module_id} title={`${m.code} — ${m.title}`}
                className={`rounded-[10px] px-1.5 py-0.5 font-mono text-[11px] ${m.status === "completed" ? "bg-[#147c77] text-white" : m.status === "in_progress" ? "bg-[#EDF3F8] text-[#254a98]" : "bg-[#f1f4f7] text-[#627086]"}`}>
                {m.code}<span className="sr-only"> : {m.status}</span>
              </li>
            ))}
          </ul>
          {c.resume && c.status !== "not_started" && (
            <Link to={learnUrl(c.resume)} className={`${LINK_ARROW} mt-4`} data-testid={`espace-course-resume-${c.course_id}`}>Reprendre <ArrowRight size={14} aria-hidden="true" /></Link>
          )}
        </li>
      ))}
    </ul>
  </section>
);

const groupByCompetency = (items) => {
  const groups = {};
  items.forEach((a) => { (groups[a.competency_id] ||= { id: a.competency_id, name: a.competency_name, items: [] }).items.push(a); });
  return Object.values(groups).map((g) => {
    const valid = g.items.filter((a) => a.status === "valid");
    const best = [...valid].sort((x, y) => y.level.localeCompare(x.level))[0];
    return { ...g, level: best?.level, valid: valid.length > 0 };
  });
};

const Evidence = ({ a }) => (
  <li className={`flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm ${a.status === "invalidated" ? "opacity-60" : ""}`} data-testid={`attainment-${a.competency_id}-${a.module_id}${a.evidence_type === "project" ? "-project" : ""}`}>
    <span className="font-mono text-xs text-[#147c77]">{a.module_id}</span>
    <span className="min-w-0 flex-1">{a.module_title}</span>
    <span className="font-mono text-xs">{a.level} · {pct(a.score_percent)}</span>
    {a.evidence_type === "project" ? (
      <Link to={`/modules/${a.module_id}/learn?etape=projet`} className="text-[#147c77] underline underline-offset-4" data-testid={`attainment-evidence-${a.competency_id}-${a.module_id}-project`}>Projet validé le {date(a.acquired_at)}</Link>
    ) : (
      <Link to={`/modules/${a.module_id}/learn?etape=evaluation`} className="text-[#147c77] underline underline-offset-4" data-testid={`attainment-evidence-${a.competency_id}-${a.module_id}`}>Tentative n° {a.evidence.attempt_number} du {date(a.acquired_at)}</Link>
    )}
    {a.status === "invalidated" && <span className="text-xs text-[#7E2828]">(preuve invalidée)</span>}
  </li>
);

const Attainments = ({ items }) => {
  const groups = groupByCompetency(items);
  return (
    <section aria-labelledby="att-title" data-testid="espace-attainments">
      <SectionTitle id="att-title" eyebrow="Compétences" title="Compétences acquises" lead="Chaque compétence est regroupée avec l'ensemble des preuves qui l'attestent : évaluations notées réussies et projets validés." />
      {groups.length === 0 ? (
        <p className="mt-6 border border-dashed border-[#e5e9ef] px-5 py-8 text-sm text-[#505e75]" data-testid="espace-attainments-empty">Aucune compétence validée pour l'instant. Réussissez l'évaluation notée d'un module pour en obtenir.</p>
      ) : (
        <ul className="mt-6 grid gap-4 lg:grid-cols-2">
          {groups.map((g) => (
            <li key={g.id} className="border border-[#e5e9ef] bg-white p-5" data-testid={`competency-group-${g.id}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="font-semibold"><Award size={14} className="mr-2 inline text-[#147c77]" aria-hidden="true" />{g.name}</p>
                <span className="font-mono text-sm" data-testid={`competency-level-${g.id}`}>{g.valid ? `Niveau ${g.level}` : "Preuves invalidées"}</span>
              </div>
              <p className="mt-1 text-xs text-[#627086]">{g.items.length} preuve{g.items.length > 1 ? "s" : ""}</p>
              <ul className="mt-2 divide-y divide-[#e5e9ef]">{g.items.map((a) => <Evidence key={a.id} a={a} />)}</ul>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

const Attempts = ({ items }) => (
  <section aria-labelledby="attempts-title" data-testid="espace-attempts">
    <SectionTitle id="attempts-title" eyebrow="Historique" title="Tentatives d'évaluation" />
    {items.length === 0 ? <p className="mt-6 text-sm text-[#505e75]">Aucune tentative pour l'instant.</p> : (
      <ol className="mt-6 divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]">
        {items.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm" data-testid={`attempt-row-${a.id}`}>
            <span><span className="font-semibold">{a.module_label}</span> · tentative {a.attempt_number}</span>
            <span className="flex items-center gap-4">
              <span className="font-mono">{a.score}/{a.max_score} · {pct(a.percent)}</span>
              <span className={`rounded-[10px] px-2 py-0.5 text-xs font-semibold ${a.passed ? "bg-[#eef5f3] text-[#147c77]" : "bg-[#FBECEC] text-[#7E2828]"}`}>{a.passed ? "Réussie" : "Non réussie"}</span>
              <span className="text-xs text-[#627086]">{date(a.created_at)}</span>
            </span>
          </li>
        ))}
      </ol>
    )}
  </section>
);

const Activity = ({ demo, diagnostic }) => (
  <section className="grid gap-4 md:grid-cols-2" aria-label="Activités" data-testid="espace-activity">
    <div className="border border-[#e5e9ef] bg-white p-5" data-testid="espace-demo">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Démonstration</p>
      {demo ? (
        <p className="mt-2 text-sm"><span className="font-semibold">{demo.completed ? "Terminée" : `Étape ${demo.max_step}/7 atteinte`}</span>
          {demo.quiz_done && ` · micro-activité : ${demo.quiz_score}/${demo.quiz_total}`}</p>
      ) : <p className="mt-2 text-sm">Non commencée.</p>}
      <Link to="/demo" className={`${LINK_ARROW} mt-3`} data-testid="espace-demo-link">{demo?.completed ? "Revoir" : "Explorer"} la démonstration</Link>
    </div>
    <div className="border border-[#e5e9ef] bg-white p-5" data-testid="espace-diagnostic">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Test de positionnement</p>
      {diagnostic ? <p className="mt-2 text-sm"><span className="font-semibold">Entrée {diagnostic.profile_name}</span> · cours {diagnostic.course_id} · niveau estimé {diagnostic.estimated_level}</p>
        : <p className="mt-2 text-sm">Non passé.</p>}
      <Link to="/diagnostic" className={`${LINK_ARROW} mt-3`} data-testid="espace-diagnostic-link">{diagnostic ? "Refaire" : "Passer"} le test</Link>
    </div>
  </section>
);

function Dashboard() {
  const { user } = useAuth();
  const { data, loading, error } = useApi("/learners/me/dashboard", { u: user.id });
  if (error) return <ErrorState />;
  if (loading) return <Loading />;
  return (
    <div data-testid="espace-page">
      <header className="border-b border-[#e5e9ef] pb-10 pt-14">
        <Container>
          <Eyebrow>Espace apprenant</Eyebrow>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl" data-testid="espace-title">Bonjour {data.user.first_name}.</h1>
          <p className="mt-4 text-base text-[#505e75]">{data.modules_completed.length} module{data.modules_completed.length > 1 ? "s" : ""} terminé{data.modules_completed.length > 1 ? "s" : ""} · {data.modules_in_progress.length} en cours · {groupByCompetency(data.attainments).filter((g) => g.valid).length} compétence{groupByCompetency(data.attainments).filter((g) => g.valid).length > 1 ? "s" : ""} validée{groupByCompetency(data.attainments).filter((g) => g.valid).length > 1 ? "s" : ""}</p>
        </Container>
      </header>
      <Container className="space-y-16 pt-12">
        {data.recommendations.length > 0 && <Recommendations items={data.recommendations} />}
        <Activity demo={data.demo} diagnostic={data.diagnostic} />
        <PathwaysSection />
        <Courses courses={data.courses} />
        <CertificatesSection />
        <Attainments items={data.attainments} />
        <ProjectsSection />
        <Attempts items={data.attempts} />
      </Container>
    </div>
  );
}

export default function Espace() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}
