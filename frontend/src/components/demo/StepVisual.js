import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Cpu, Lock, RotateCcw, FastForward } from "lucide-react";
import { Link } from "react-router-dom";
import { usePrefersReducedMotion } from "@/lib/api";

const Label = ({ children }) => (
  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">{children}</p>
);

const DefList = ({ items, testId }) => (
  <dl className="divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]" data-testid={testId}>
    {items.map((it) => (
      <div key={it.label} className="grid gap-1 py-2.5 sm:grid-cols-[11rem_1fr] sm:gap-4">
        <dt className="text-xs font-medium text-[#627086]">{it.label}</dt>
        <dd className="text-sm font-medium">{it.value}</dd>
      </div>
    ))}
  </dl>
);

const StatusIcon = ({ status }) =>
  status === "ok" ? (
    <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[#147c77]" aria-label="Conforme" />
  ) : (
    <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[#A0662B]" aria-label="Point d'attention" />
  );

const RequestVisual = ({ v }) => (
  <div className="space-y-6" data-testid="visual-request">
    <div>
      <Label>Question saisie</Label>
      <div className="mt-2 flex items-start gap-3 border border-[#14243c]/30 bg-white p-4">
        <p className="flex-1 text-sm leading-relaxed sm:text-base" data-testid="visual-request-question">{v.question}</p>
        <Lock size={14} className="mt-1 shrink-0 text-[#627086]" aria-hidden="true" />
      </div>
    </div>
    <div>
      <Label>Contexte associé par l'application</Label>
      <div className="mt-2"><DefList items={v.context} testId="visual-request-context" /></div>
    </div>
    <div>
      <Label>Contrôles d'entrée</Label>
      <ul className="mt-2 grid gap-2 sm:grid-cols-2">
        {v.checks.map((c) => (
          <li key={c.label} className="flex items-start gap-2 text-sm"><StatusIcon status={c.status} />{c.label}</li>
        ))}
      </ul>
    </div>
  </div>
);

const TokensVisual = ({ v }) => (
  <div className="space-y-6" data-testid="visual-tokens">
    <div>
      <div className="flex items-baseline justify-between">
        <Label>Question découpée en tokens</Label>
        <span className="font-mono text-xs text-[#627086]" data-testid="token-count">{v.token_count} tokens</span>
      </div>
      <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Tokens">
        {v.tokens.map((t, i) => (
          <li key={i} className="casa-reveal flex flex-col items-center border border-[#365ac8]/40 bg-[#EDF3F8] px-1.5 py-1"
            style={{ animationDelay: `${i * 25}ms` }} data-testid={`token-${i}`}>
            <span className="whitespace-pre font-mono text-[13px] text-[#14243c]">{t.replace(/^ /, "·")}</span>
            <span className="font-mono text-[10px] text-[#627086]">{v.token_ids[i]}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-[#627086]">Le point « · » signale un espace intégré au token. Les nombres sont les identifiants transmis au modèle.</p>
    </div>
    <div className="grid gap-6 sm:grid-cols-2">
      <div>
        <Label>Intention détectée</Label>
        <p className="mt-2 border-l-2 border-[#147c77] pl-3 text-sm font-semibold" data-testid="token-intent">{v.intent}</p>
        <div className="mt-4"><DefList items={v.entities} testId="token-entities" /></div>
      </div>
      <div>
        <Label>Filtres déduits</Label>
        <ul className="mt-2 space-y-2">
          {v.filters.map((f) => <li key={f} className="border border-[#e5e9ef] bg-white px-3 py-2 text-sm">{f}</li>)}
        </ul>
      </div>
    </div>
  </div>
);

const ScoreBar = ({ label, value, strong }) => (
  <div className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-2 text-xs">
    <span className="text-[#627086]">{label}</span>
    <span className="h-1.5 bg-[#edf1f5]" aria-hidden="true">
      <span className="block h-full" style={{ width: `${value * 100}%`, background: strong ? "#147c77" : "#365ac8" }} />
    </span>
    <span className={`text-right font-mono ${strong ? "font-semibold" : ""}`}>{value.toFixed(2).replace(".", ",")}</span>
  </div>
);

const RetrievalVisual = ({ v }) => (
  <div className="space-y-8" data-testid="visual-retrieval">
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Label>1 · Documents présélectionnés</Label>
        <span className="text-xs text-[#627086]">{v.corpus_size} — seuil {String(v.threshold).replace(".", ",")}</span>
      </div>
      <ol className="mt-3 space-y-2">
        {v.documents.map((d) => (
          <li key={d.id} className={`grid gap-3 border p-4 md:grid-cols-[1fr_15rem] ${d.retained ? "border-[#147c77]/40 bg-white" : "border-[#e5e9ef] bg-[#f1f4f7]/60 text-[#627086]"}`}
            data-testid={`candidate-doc-${d.id}`}>
            <div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-mono">{d.id}</span>
                <span className="font-semibold">{d.type}</span>
                <span>JO du {d.date}</span>
                <span className={`rounded-[10px] px-1.5 py-0.5 font-semibold ${d.retained ? "bg-[#eef5f3] text-[#147c77]" : "bg-[#edf1f5] text-[#627086]"}`}>
                  {d.retained ? "Retenu" : "Écarté"}
                </span>
              </div>
              <p className={`mt-1.5 text-sm font-medium ${d.retained ? "text-[#14243c]" : ""}`}>{d.title}</p>
              <p className="mt-1 text-xs">{d.reason}</p>
            </div>
            <div className="space-y-1.5 self-center">
              <ScoreBar label="Lexical" value={d.lexical} />
              <ScoreBar label="Sémantique" value={d.semantic} />
              <ScoreBar label="Combiné" value={d.score} strong />
            </div>
          </li>
        ))}
      </ol>
    </div>
    <div>
      <Label>2 · Extraits retenus et transmis au modèle</Label>
      <ol className="mt-3 space-y-2">
        {v.extracts.map((e) => (
          <li key={e.n} className="border-l-2 border-[#365ac8] bg-white px-4 py-3" data-testid={`extract-${e.n}`}>
            <p className="font-mono text-xs text-[#254a98]">[{e.n}] {e.ref}</p>
            <p className="mt-1 text-sm leading-relaxed">« {e.text} »</p>
          </li>
        ))}
      </ol>
    </div>
  </div>
);

const InferenceVisual = ({ v }) => {
  const total = v.prompt_blocks.reduce((a, b) => a + b.tokens, 0);
  return (
    <div className="space-y-8" data-testid="visual-inference">
      <div>
        <div className="flex items-baseline justify-between"><Label>Prompt assemblé</Label><span className="font-mono text-xs text-[#627086]">{total.toLocaleString("fr-FR")} tokens</span></div>
        <div className="mt-3 flex h-2 w-full" aria-hidden="true">
          {v.prompt_blocks.map((b, i) => (
            <span key={b.label} style={{ width: `${(b.tokens / total) * 100}%`, background: ["#14243c", "#365ac8", "#147c77"][i] }} />
          ))}
        </div>
        <ol className="mt-3 space-y-2">
          {v.prompt_blocks.map((b, i) => (
            <li key={b.label} className="border border-[#e5e9ef] bg-white p-4" data-testid={`prompt-block-${i}`}>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="flex items-center gap-2 font-semibold"><span className="h-2 w-2" style={{ background: ["#14243c", "#365ac8", "#147c77"][i] }} aria-hidden="true" />{b.label}</span>
                <span className="font-mono text-[#627086]">{b.tokens} tokens</span>
              </div>
              <p className="mt-2 font-mono text-xs leading-relaxed text-[#505e75]">{b.content}</p>
            </li>
          ))}
        </ol>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div><Label>Paramètres d'inférence</Label><div className="mt-2"><DefList items={v.parameters} testId="inference-parameters" /></div></div>
        <div>
          <Label><span className="inline-flex items-center gap-1.5"><Cpu size={12} aria-hidden="true" /> Infrastructure</span></Label>
          <div className="mt-2"><DefList items={v.infrastructure} testId="inference-infrastructure" /></div>
        </div>
      </div>
    </div>
  );
};

const GenerationVisual = ({ v, done, onDone }) => {
  const reduced = usePrefersReducedMotion();
  const total = v.chunks.length;
  const [count, setCount] = useState(done || reduced ? total : 0);
  useEffect(() => {
    if (count >= total) {
      if (!done) onDone();
      return undefined;
    }
    const t = setTimeout(() => setCount((c) => c + 1), 700);
    return () => clearTimeout(t);
  }, [count, total, done, onDone]);
  const finished = count >= total;
  return (
    <div className="space-y-8" data-testid="visual-generation">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Label>Réponse candidate</Label>
          <div className="flex gap-2">
            <button type="button" onClick={() => setCount(0)} className="inline-flex items-center gap-1.5 border border-[#e5e9ef] bg-white px-2.5 py-1.5 text-xs font-medium hover:border-[#14243c]" data-testid="generation-replay">
              <RotateCcw size={12} aria-hidden="true" /> Rejouer
            </button>
            <button type="button" onClick={() => setCount(total)} disabled={finished} className="inline-flex items-center gap-1.5 border border-[#e5e9ef] bg-white px-2.5 py-1.5 text-xs font-medium hover:border-[#14243c] disabled:opacity-40" data-testid="generation-show-all">
              <FastForward size={12} aria-hidden="true" /> Tout afficher
            </button>
          </div>
        </div>
        <div className="mt-3 min-h-[11rem] border border-[#e5e9ef] bg-white p-5 text-sm leading-7 sm:text-base" data-testid="generation-text">
          {v.chunks.slice(0, count).map((c, i) => (
            <span key={i} className={`casa-fade ${i === v.unsourced_index && finished ? "bg-[#FBF1E4] underline decoration-[#A0662B] decoration-dashed underline-offset-4" : ""}`}>{c}</span>
          ))}
          {!finished && <span className="casa-caret" aria-hidden="true" />}
        </div>
        <p className="mt-2 text-xs text-[#627086]" role="status" data-testid="generation-status">
          {finished ? `Génération terminée — ${total} phrases produites. La phrase soulignée ne cite aucune source.` : `Génération en cours… phrase ${count + 1} sur ${total}`}
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <Label>Prédiction du token suivant</Label>
          <p className="mt-2 font-mono text-xs text-[#505e75]">« {v.next_token.context} … »</p>
          <ul className="mt-3 space-y-1.5" data-testid="next-token-candidates">
            {v.next_token.candidates.map((c, i) => (
              <li key={c.token} className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-2 text-xs">
                <span className={`font-mono ${i === 0 ? "font-semibold text-[#147c77]" : ""}`}>{c.token.trim()}</span>
                <span className="h-1.5 bg-[#edf1f5]" aria-hidden="true"><span className="block h-full" style={{ width: `${c.p * 100}%`, background: i === 0 ? "#147c77" : "#365ac8" }} /></span>
                <span className="text-right font-mono">{Math.round(c.p * 100)} %</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <Label>Contraintes de format</Label>
          <ul className="mt-2 space-y-2">{v.constraints.map((c) => <li key={c} className="border border-[#e5e9ef] bg-white px-3 py-2 text-sm">{c}</li>)}</ul>
        </div>
      </div>
    </div>
  );
};

const ControlsVisual = ({ v }) => (
  <div className="space-y-8" data-testid="visual-controls">
    <div>
      <Label>Contrôles appliqués par l'application</Label>
      <ul className="mt-3 divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]">
        {v.checks.map((c, i) => (
          <li key={c.label} className="flex items-start gap-3 py-3" data-testid={`control-check-${i}`}>
            <StatusIcon status={c.status} />
            <div><p className="text-sm font-semibold">{c.label}</p><p className="text-sm text-[#505e75]">{c.detail}</p></div>
          </li>
        ))}
      </ul>
    </div>
    <div className="border-l-2 border-[#A0662B] bg-[#FBF1E4] px-4 py-3" data-testid="control-removed-sentence">
      <Label>Phrase retirée</Label>
      <p className="mt-1 text-sm line-through decoration-[#A0662B]">{v.removed_sentence}</p>
      <p className="mt-1 text-sm text-[#505e75]">{v.removed_reason}</p>
    </div>
  </div>
);

const AnswerVisual = ({ v }) => (
  <div className="space-y-8" data-testid="visual-answer">
    <article className="border border-[#14243c]/20 bg-white p-5 sm:p-7">
      <Label>Réponse restituée</Label>
      <p className="mt-3 text-base font-medium leading-relaxed sm:text-lg" data-testid="answer-summary">{v.summary}</p>
      <ul className="mt-5 space-y-3">
        {v.points.map((p, i) => (
          <li key={i} className="flex gap-3 text-sm leading-relaxed sm:text-base">
            <span className="mt-2.5 h-1 w-3 shrink-0 bg-[#147c77]" aria-hidden="true" />
            <span>
              {p.text}{" "}
              {p.refs.map((r) => (
                <a key={r} href={`#source-${r}`} className="font-mono text-sm font-semibold text-[#147c77] hover:underline" aria-label={`Voir la source ${r}`} data-testid={`answer-ref-${i}-${r}`}>[{r}]</a>
              ))}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-5 font-mono text-xs text-[#627086]">Trace {v.trace_id}</p>
    </article>
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <Label>Preuves</Label>
        <ol className="mt-3 space-y-2">
          {v.sources.map((s) => (
            <li key={s.n} id={`source-${s.n}`} className="scroll-mt-24 border-l-2 border-[#365ac8] bg-white px-3 py-2" data-testid={`answer-source-${s.n}`}>
              <p className="font-mono text-xs text-[#254a98]">[{s.n}] {s.ref}</p>
              <p className="mt-1 text-xs leading-relaxed text-[#505e75]">« {s.text} »</p>
            </li>
          ))}
        </ol>
      </div>
      <div className="space-y-8">
        <div>
          <Label>Limites</Label>
          <ul className="mt-3 space-y-2" data-testid="answer-limits">
            {v.limits.map((l) => <li key={l} className="flex gap-2 text-sm"><AlertTriangle size={14} className="mt-1 shrink-0 text-[#A0662B]" aria-hidden="true" />{l}</li>)}
          </ul>
        </div>
        <div>
          <Label>Suite proposée</Label>
          <ul className="mt-3 space-y-2">
            {v.next_steps.map((n) => (
              <li key={n.label}>
                <Link to={`/modules/${n.module_id}`} className="group flex items-start justify-between gap-3 border border-[#e5e9ef] bg-white px-3 py-2.5 text-sm hover:border-[#147c77]" data-testid={`answer-next-${n.module_id}`}>
                  <span>{n.label}</span><span className="font-mono text-xs text-[#147c77]">{n.module_id}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  </div>
);

const FlowVisual = ({ v }) => (
  <div className="rounded-[16px] border border-[#e5edf1] bg-[#f7f8fa] p-5" data-testid="visual-flow">
    <div className="visual-graphic">
      {v.nodes.map((n, i) => (
        <span key={n} className="contents">
          <span className={`node ${i === 1 ? "primary" : i === 2 ? "purple" : ""}`}>{n}</span>
          {i < v.nodes.length - 1 && <span className="node arrow" aria-hidden="true">→</span>}
        </span>
      ))}
    </div>
    <p className="visual-note mx-auto mt-4">{v.note}</p>
  </div>
);

export const StepVisual = ({ step, generated, onGenerated }) => {
  const v = step.visual;
  switch (v.kind) {
    case "flow": return <FlowVisual v={v} />;
    case "request": return <RequestVisual v={v} />;
    case "tokens": return <TokensVisual v={v} />;
    case "retrieval": return <RetrievalVisual v={v} />;
    case "inference": return <InferenceVisual v={v} />;
    case "generation": return <GenerationVisual v={v} done={generated} onDone={onGenerated} />;
    case "controls": return <ControlsVisual v={v} />;
    default: return <AnswerVisual v={v} />;
  }
};
