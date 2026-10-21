import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, ChevronDown } from "lucide-react";
import { http, useApi, useCatalog } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BTN_PRIMARY, ErrorState, Eyebrow, LINK_ARROW, Loading } from "@/components/common";
import { StepVisual } from "@/components/demo/StepVisual";
import { LayerPanel } from "@/components/demo/LayerPanel";
import { Quiz } from "@/components/demo/Quiz";
import { Picto } from "@/components/Pictos";

const MAIN_ID = "casa-jo-cafe-cacao";
const storeKey = (id) => (id === MAIN_ID ? "casa-demo-state" : `casa-demo-state-${id}`);
const readStore = (id) => {
  try {
    return JSON.parse(sessionStorage.getItem(storeKey(id))) || {};
  } catch {
    return {};
  }
};
const initialState = (id, params, total) => {
  const store = readStore(id);
  const urlStep = parseInt(params.get("etape"), 10);
  const step = urlStep >= 1 && urlStep <= total ? urlStep : store.step || 1;
  const perStep = { ...(store.perStep || {}) };
  if (params.get("couche") || params.get("detail")) {
    perStep[step] = { ...perStep[step], layer: params.get("couche") || perStep[step]?.layer, detail: params.get("detail") === "1" };
  }
  return { step, perStep, quiz: store.quiz || {}, maxStep: Math.max(store.maxStep || 1, step) };
};

const sessionId = () => {
  let id = sessionStorage.getItem("casa-session-id");
  if (!id) {
    id = Math.random().toString(36).slice(2, 14);
    sessionStorage.setItem("casa-session-id", id);
  }
  return id;
};
const trackEvent = (type, extra = {}) => http.post("/events", { type, session_id: sessionId(), ...extra }).catch(() => {});

const Timeline = ({ steps, current, onJump }) => {
  const onKey = (e) => {
    if (e.key === "ArrowRight" && current < steps.length) onJump(current + 1, true);
    if (e.key === "ArrowLeft" && current > 1) onJump(current - 1, true);
  };
  return (
    <nav aria-label="Étapes de la démonstration" data-testid="demo-stepper">
      <ol className="timeline no-scrollbar" onKeyDown={onKey}>
        {steps.map((s) => (
          <li key={s.number}>
            <button type="button" className={`step-tab ${s.number === current ? "active" : s.number < current ? "done" : ""}`} onClick={() => onJump(s.number)}
              aria-current={s.number === current ? "step" : undefined} aria-label={`Étape ${s.number} : ${s.label}`} data-testid={`stepper-step-${s.number}`}>
              <span className="flex items-center gap-2"><span className="n">{s.number}</span><Picto id={s.stage_id} size={14} className="mb-2 hidden min-[1130px]:block" /></span>{s.label}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
};

const FlowGraphic = ({ s, corpusNote }) => (
  <div className="visual" data-testid="demo-proto-visual">
    <span className="tag">Visualisation pédagogique · {s.label}</span>
    <div className="visual-graphic">
      {s.graphic.map((n, i) => (
        <span key={n} className="contents">
          <span className={`node ${i === 1 ? "primary" : i === 2 ? "purple" : ""}`}>{n}<small>{["Entrée", "Traitement", "Résultat"][i]}</small></span>
          {i < 2 && <span className="node arrow" aria-hidden="true">→</span>}
        </span>
      ))}
    </div>
    <p className="visual-note" data-testid="demo-visual-note">{s.number === 3 ? corpusNote : "Sélectionnez une autre étape pour suivre le traitement."}</p>
  </div>
);

const Details = ({ s, detail, toggle, conceptNames, generated, onGenerated }) => (
  <div className="detail-zone" data-testid="demo-visual-zone">
    <StepVisual step={s} generated={generated} onGenerated={onGenerated} />
    <button type="button" aria-expanded={detail} aria-controls="technical-detail" onClick={toggle}
      className="mt-8 flex w-full items-center justify-between gap-3 border-t border-[#e5e9ef] pt-5 text-left text-sm font-semibold text-[#365ac8]" data-testid="demo-technical-toggle">
      {detail ? "Masquer le mécanisme technique" : "Voir le mécanisme technique"}
      <ChevronDown size={18} className={`transition-transform duration-200 ${detail ? "rotate-180" : ""}`} aria-hidden="true" />
    </button>
    <div id="technical-detail" hidden={!detail} className="casa-fade mt-5 space-y-5" data-testid="demo-technical-detail">
      <p className="text-[15px] font-semibold leading-relaxed" data-testid="demo-step-headline">{s.headline}</p>
      <p className="text-sm leading-relaxed text-[#505e75]" data-testid="demo-step-explanation">{s.explanation}</p>
      <div className="rounded-[12px] border-l-[3px] border-[#365ac8] bg-[#f7f8fa] px-5 py-4">
        <p className="text-sm font-semibold">{s.technical.summary}</p>
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-[#505e75]">{s.technical.points.map((p) => <li key={p}>{p}</li>)}</ul>
      </div>
      <ul className="flex flex-wrap gap-2" aria-label="Notions mobilisées">
        {s.concept_ids.map((cid) => (
          <li key={cid}><Link to={`/concepts/${cid}`} className="chip inline-block" data-testid={`demo-concept-link-${cid}`}>{conceptNames[cid] || cid}</Link></li>
        ))}
      </ul>
    </div>
  </div>
);

const EndOfDemo = ({ quiz, answers, onAnswer, onReset }) => {
  const { user } = useAuth();
  return (
    <section className="mt-10 grid gap-8 lg:grid-cols-12" aria-label="Pour aller plus loin" data-testid="demo-end">
      <div className="rounded-[22px] border border-[#e5e9ef] bg-white p-6 lg:col-span-7"><Quiz questions={quiz} answers={answers} onAnswer={onAnswer} onReset={onReset} /></div>
      <div className="space-y-5 lg:col-span-5">
        <div className="rounded-[22px] border border-[#e5e9ef] bg-white p-6" data-testid="demo-free-module">
          <Eyebrow>Module gratuit</Eyebrow>
          <h3 className="mt-3 text-xl">M01 — Comprendre les usages, capacités et limites</h3>
          <p className="mt-2 text-sm leading-relaxed text-[#505e75]">Situer ce que l'IA générative sait faire, ce qu'elle ne sait pas faire et les précautions à prendre. Niveau L0, sans prérequis.</p>
          <Link to="/modules/M01" className={`${BTN_PRIMARY} mt-5`} data-testid="demo-free-module-link">Ouvrir le module M01 <ArrowRight size={16} aria-hidden="true" /></Link>
        </div>
        <div className="rounded-[22px] border border-dashed border-[#d9dfe8] p-6" data-testid="demo-account-placeholder">
          <p className="text-sm font-semibold">{user ? "Votre progression est enregistrée dans votre espace." : "Créez un compte pour sauvegarder votre progression."}</p>
          <Link to={user ? "/espace" : "/inscription?suite=%2Fespace"} className={`${LINK_ARROW} mt-3`} data-testid="demo-account-link">{user ? "Ouvrir mon espace" : "Créer un compte"} <ArrowRight size={14} aria-hidden="true" /></Link>
        </div>
      </div>
    </section>
  );
};

const DemoView = ({ scenario, scenarios, onCase, layers, conceptNames }) => {
  const total = scenario.steps.length;
  const [params, setParams] = useSearchParams();
  const [init] = useState(() => initialState(scenario.id, params, total));
  const [step, setStep] = useState(init.step);
  const [perStep, setPerStep] = useState(init.perStep);
  const [quiz, setQuiz] = useState(init.quiz);
  const [maxStep, setMaxStep] = useState(init.maxStep);
  const { user } = useAuth();
  const headingRef = useRef(null);
  const userNav = useRef(false);
  const s = scenario.steps[step - 1];
  const cur = perStep[step] || {};
  const selectedLayer = cur.layer || null;
  const detail = !!cur.detail;
  const patchStep = useCallback((n, patch) => setPerStep((p) => ({ ...p, [n]: { ...p[n], ...patch } })), []);
  const onGenerated = useCallback(() => patchStep(5, { generated: true }), [patchStep]);

  useEffect(() => setMaxStep((m) => Math.max(m, step)), [step]);
  useEffect(() => {
    if (!sessionStorage.getItem("casa-demo-started")) {
      sessionStorage.setItem("casa-demo-started", "1");
      trackEvent("demo_start");
    }
  }, []);
  useEffect(() => {
    if (maxStep >= total && !sessionStorage.getItem(`casa-demo-completed-${scenario.id}`)) {
      sessionStorage.setItem(`casa-demo-completed-${scenario.id}`, "1");
      trackEvent("demo_complete", { step: total });
    }
  }, [maxStep, total, scenario.id]);
  useEffect(() => {
    if (!user || user.role !== "learner" || scenario.id !== MAIN_ID) return undefined;
    const t = setTimeout(() => http.post("/learners/me/demo-progress", { max_step: maxStep, quiz_answers: quiz }).catch(() => {}), 600);
    return () => clearTimeout(t);
  }, [user, maxStep, quiz, scenario.id]);
  useEffect(() => {
    sessionStorage.setItem(storeKey(scenario.id), JSON.stringify({ step, perStep, quiz, maxStep }));
    setParams({ ...(scenario.id !== MAIN_ID ? { cas: scenario.id } : {}), etape: String(step), ...(selectedLayer ? { couche: selectedLayer } : {}), detail: detail ? "1" : "0" }, { replace: true });
  }, [step, perStep, quiz, maxStep, selectedLayer, detail, setParams, scenario.id]);
  useEffect(() => {
    if (!userNav.current) return;
    userNav.current = false;
    headingRef.current?.focus({ preventScroll: true });
  }, [step]);

  const goTo = (n, keepFocus = false) => {
    if (n < 1 || n > total) return;
    userNav.current = !keepFocus;
    setStep(n);
  };
  const last = step === total;

  return (
    <div className="shell demo-wrapper" data-testid="demo-page">
      <div className="demointro">
        <div>
          <div className="eyebrow">Expérience guidée • Prototype interactif</div>
          <h1 data-testid="demo-title">Suivre une demande, comprendre les mécanismes.</h1>
          <p>Avancez dans le parcours, sélectionnez une couche technologique et découvrez les notions et formations qui s'y rattachent.</p>
        </div>
        <Link to="/" className="button secondary" data-testid="demo-back-home">← Retour à l'accueil</Link>
      </div>
      <div className="demo-grid">
        <div className="workbench">
          <div className="bar">
            <div><strong>Cas de démonstration</strong><div className="case-title" data-testid="demo-case-title">{scenario.case_title}</div></div>
            <span className="pill" data-testid="demo-steps-pill">7 étapes</span>
          </div>
          <div className="bar" style={{ border: 0, paddingBottom: 2 }}>
            <div className="options" role="group" aria-label="Choisir un cas">
              {scenarios.map((c) => (
                <button key={c.id} type="button" className={`chip ${c.id === scenario.id ? "selected" : ""}`} aria-pressed={c.id === scenario.id} onClick={() => onCase(c.id)} data-testid={`demo-case-${c.id}`}>
                  {c.case_label}
                </button>
              ))}
            </div>
          </div>
          <Timeline steps={scenario.steps} current={step} onJump={goTo} />
          <section key={step} className="main-stage casa-fade" aria-labelledby="step-title" data-testid={`demo-step-${step}`}>
            <FlowGraphic s={s} corpusNote={scenario.corpus_note} />
            <div className="step-text">
              <div className="num" data-testid="demo-step-index">Étape {step} sur 7</div>
              <h2 id="step-title" ref={headingRef} tabIndex={-1} data-testid="demo-step-title">{s.title}</h2>
              <p data-testid="demo-step-description">{s.description}</p>
              <div className="micro" data-testid="demo-step-takeaway"><strong>Ce qu'il faut retenir</strong><br /><span>{s.takeaway}</span></div>
            </div>
          </section>
          <Details s={s} detail={detail} toggle={() => patchStep(step, { detail: !detail })} conceptNames={conceptNames}
            generated={!!perStep[5]?.generated} onGenerated={onGenerated} />
          <div className="controls">
            <div className="control-left">
              <button type="button" className="button secondary" onClick={() => goTo(step - 1)} disabled={step === 1} data-testid="demo-prev-button">← Précédent</button>
              <button type="button" className="button" onClick={() => (last ? goTo(1) : goTo(step + 1))} data-testid="demo-next-button">{last ? "Recommencer ↻" : "Étape suivante →"}</button>
            </div>
            <span className="quiet" aria-live="polite" data-testid="demo-step-indicator">{step} / 7</span>
          </div>
        </div>
        <LayerPanel layers={layers} activeIds={s.active_layer_ids} selectedId={selectedLayer}
          onSelect={(id) => { const next = id === selectedLayer ? null : id; patchStep(step, { layer: next }); if (next) trackEvent("demo_layer_click", { layer_id: id, step }); }} />
      </div>
      <div className="callout" data-testid="demo-callout">
        <div>
          <strong>Du mécanisme découvert à la compétence acquise</strong>
          <p>Chaque composante mène à une notion, un module, des exercices et un parcours. La plateforme conserve vos acquis lorsque vous changez de niveau ou de spécialité.</p>
        </div>
        <Link to="/pathways/P-001" className="button secondary" data-testid="demo-callout-pathway">Consulter un parcours type →</Link>
      </div>
      <p className="note" role="note" data-testid="demo-notice">{scenario.notice}</p>
      {last && <EndOfDemo quiz={scenario.quiz} answers={quiz} onAnswer={(id, i) => setQuiz((q) => ({ ...q, [id]: i }))} onReset={() => setQuiz({})} />}
    </div>
  );
};

export default function Demo() {
  const catalog = useCatalog();
  const [params, setParams] = useSearchParams();
  const caseId = params.get("cas") || MAIN_ID;
  const { data: scenarios } = useApi("/demo/scenarios");
  const { data: scenario, loading, error } = useApi(`/demo/scenarios/${caseId}`);
  const { data: concepts } = useApi("/concepts");
  const conceptNames = useMemo(() => Object.fromEntries((concepts || []).map((c) => [c.id, c.name])), [concepts]);
  if (error) return <ErrorState />;
  if (loading || !catalog || !scenarios || !scenario || scenario.id !== caseId) return <Loading />;
  return <DemoView key={scenario.id} scenario={scenario} scenarios={scenarios} onCase={(id) => setParams(id === MAIN_ID ? {} : { cas: id })} layers={catalog.layers} conceptNames={conceptNames} />;
}
