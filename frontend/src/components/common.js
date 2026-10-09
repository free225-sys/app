import { useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";

export const LAYER_STYLE = {
  "layer-application": { text: "#147c77", soft: "#eef5f3" },
  "layer-donnees": { text: "#254a98", soft: "#EDF3F8" },
  "layer-mathematiques": { text: "#67365F", soft: "#F5EDF3" },
  "layer-modeles": { text: "#8E4417", soft: "#FAEDE5" },
  "layer-infrastructure": { text: "#334155", soft: "#EEF2F6" },
  "layer-securite": { text: "#7E2828", soft: "#FBECEC" },
};

export const BTN_PRIMARY =
  "inline-flex items-center justify-center gap-2 rounded-[10px] border border-transparent bg-[#14243c] px-5 py-3 text-[13px] font-semibold text-white transition-[transform,box-shadow,background-color] duration-200 hover:-translate-y-px hover:shadow-[0_8px_18px_#14243c20] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0";
export const BTN_SECONDARY =
  "inline-flex items-center justify-center gap-2 rounded-[10px] border border-[#d9dfe8] bg-white px-5 py-3 text-[13px] font-semibold text-[#14243c] transition-[transform,box-shadow] duration-200 hover:-translate-y-px hover:shadow-[0_8px_18px_#14243c20] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0";
export const LINK_ARROW =
  "inline-flex items-center gap-1.5 text-sm font-semibold text-[#365ac8] underline-offset-4 hover:underline";

export const levelRange = (levels = []) =>
  levels.length > 1 ? `${levels[0]}–${levels[levels.length - 1]}` : levels[0] || "";

export const Container = ({ className = "", children, ...props }) => (
  <div className={`shell ${className}`} {...props}>
    {children}
  </div>
);

export const Eyebrow = ({ children, className = "" }) => (
  <p className={`eyebrow ${className}`}>{children}</p>
);

export const Tag = ({ children, className = "", ...props }) => (
  <span
    className={`inline-flex items-center rounded-[10px] border border-[#e5e9ef] bg-[#f1f4f7] px-2 py-0.5 text-xs font-medium text-[#505e75] ${className}`}
    {...props}
  >
    {children}
  </span>
);

export const LayerChip = ({ layer, ...props }) => {
  const s = LAYER_STYLE[layer.id] || {};
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-[10px] border px-2 py-0.5 text-xs font-medium"
      style={{ color: s.text, background: s.soft, borderColor: `${layer.color}4D` }}
      {...props}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: layer.color }} aria-hidden="true" />
      {layer.name}
    </span>
  );
};

export const ReadMore = ({ children, label = "En savoir plus", testId = "read-more" }) => {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="mt-4">
      <button type="button" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#365ac8] underline-offset-4 hover:underline" data-testid={`${testId}-toggle`}>
        {open ? "Réduire" : label}
        <ChevronDown size={15} className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      <div id={id} hidden={!open} className="casa-fade mt-4 space-y-4 text-[#505e75]" data-testid={`${testId}-content`}>{children}</div>
    </div>
  );
};

export const Tabs = ({ tabs, label, testId = "tabs" }) => {
  const [active, setActive] = useState(tabs[0].id);
  const refs = useRef({});
  const base = useId();
  const onKey = (e, i) => {
    const n = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (n === undefined) return;
    e.preventDefault();
    const t = tabs[(n + tabs.length) % tabs.length];
    setActive(t.id);
    refs.current[t.id]?.focus();
  };
  return (
    <div data-testid={testId}>
      <div role="tablist" aria-label={label} className="no-scrollbar flex gap-2 overflow-x-auto border-b border-[#e5e9ef]">
        {tabs.map((t, i) => (
          <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} type="button" role="tab" id={`${base}-${t.id}-tab`} aria-controls={`${base}-${t.id}`}
            aria-selected={active === t.id} tabIndex={active === t.id ? 0 : -1} onClick={() => setActive(t.id)} onKeyDown={(e) => onKey(e, i)}
            className={`-mb-px whitespace-nowrap border-b-2 px-4 py-3 text-sm font-semibold transition-colors duration-150 ${active === t.id ? "border-[#365ac8] text-[#14243c]" : "border-transparent text-[#627086] hover:text-[#14243c]"}`}
            data-testid={`${testId}-tab-${t.id}`}>{t.label}</button>
        ))}
      </div>
      {tabs.map((t) => (
        <div key={t.id} role="tabpanel" id={`${base}-${t.id}`} aria-labelledby={`${base}-${t.id}-tab`} hidden={active !== t.id} tabIndex={0}
          className="pt-10 outline-none" data-testid={`${testId}-panel-${t.id}`}>{t.content}</div>
      ))}
    </div>
  );
};

export const Pill = ({ children, className = "", ...props }) => (
  <span className={`inline-flex items-center gap-1.5 rounded-full border border-[#e5e9ef] bg-white px-3 py-1 text-xs font-medium text-[#14243c] ${className}`} {...props}>{children}</span>
);

export const SummaryCard = ({ items, children, testId = "summary-card" }) => (
  <div className="mt-10 rounded-[20px] border border-[#e5e9ef] bg-white p-7 sm:p-8" data-testid={testId}>
    <dl className="grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
      {items.filter((it) => it.value).map((it) => (
        <div key={it.label} data-testid={`${testId}-${it.key || it.label}`}>
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-[#627086]">{it.label}</dt>
          <dd className="mt-2.5 flex flex-wrap gap-2 text-sm">{it.value}</dd>
        </div>
      ))}
    </dl>
    {children && <div className="mt-8 border-t border-[#e5e9ef] pt-6">{children}</div>}
  </div>
);

export const minutes = (m) => (m ? `~ ${m} min` : null);

export const PageHeader = ({ eyebrow, title, lead, more, children, testId }) => (
  <header className="border-b border-[#e5e9ef] bg-white pb-14 pt-16 sm:pb-20 sm:pt-24" data-testid={testId}>
    <Container>
      {eyebrow && <Eyebrow className="casa-reveal">{eyebrow}</Eyebrow>}
      <h1 className="casa-reveal mt-5 max-w-4xl text-4xl leading-[1.08] sm:text-5xl lg:text-[58px]">
        {title}
      </h1>
      {lead && (
        <p className="casa-reveal mt-6 max-w-3xl text-base leading-relaxed text-[#505e75] md:text-lg" style={{ animationDelay: "80ms" }}>
          {lead}
        </p>
      )}
      {more && <ReadMore testId="header-more">{more}</ReadMore>}
      {children}
    </Container>
  </header>
);

export const ProgressBar = ({ value, testId }) => (
  <div className="h-1.5 w-full bg-[#edf1f5]" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)} data-testid={testId}>
    <div className="h-full bg-[#147c77] transition-[width] duration-500" style={{ width: `${value * 100}%` }} />
  </div>
);

export const SectionTitle = ({ eyebrow, title, lead, more, id }) => (
  <div className="max-w-3xl">
    {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
    <h2 id={id} className="mt-3 text-3xl sm:text-[39px] sm:leading-tight">
      {title}
    </h2>
    {lead && <p className="mt-4 text-base leading-relaxed text-[#505e75] md:text-lg">{lead}</p>}
    {more && <ReadMore testId={`${id}-more`}>{more}</ReadMore>}
  </div>
);

export const Loading = () => (
  <Container>
    <p role="status" className="py-28 text-sm text-[#627086]" data-testid="loading-state">
      Chargement…
    </p>
  </Container>
);

export const ErrorState = ({ message = "Le contenu n'a pas pu être chargé. Veuillez réessayer." }) => (
  <Container>
    <div role="alert" className="my-20 border-l-2 border-[#A04444] bg-white px-6 py-5 text-sm" data-testid="error-state">
      {message}
      <div className="mt-3">
        <Link to="/" className={LINK_ARROW}>
          Retour à l'accueil
        </Link>
      </div>
    </div>
  </Container>
);
