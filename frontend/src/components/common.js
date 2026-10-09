import { Link } from "react-router-dom";

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

export const PageHeader = ({ eyebrow, title, lead, children, testId }) => (
  <header className="border-b border-[#e5e9ef] bg-white pb-12 pt-14 sm:pt-16" data-testid={testId}>
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
      {children}
    </Container>
  </header>
);

export const ProgressBar = ({ value, testId }) => (
  <div className="h-1.5 w-full bg-[#edf1f5]" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)} data-testid={testId}>
    <div className="h-full bg-[#147c77] transition-[width] duration-500" style={{ width: `${value * 100}%` }} />
  </div>
);

export const SectionTitle = ({ eyebrow, title, lead, id }) => (
  <div className="max-w-3xl">
    {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
    <h2 id={id} className="mt-3 text-3xl sm:text-[39px] sm:leading-tight">
      {title}
    </h2>
    {lead && <p className="mt-4 text-base leading-relaxed text-[#505e75] md:text-lg">{lead}</p>}
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
