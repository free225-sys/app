import { createContext, useContext } from "react";

export const ROLE_LABEL = { learner: "Apprenant", admin: "Administrateur" };
export const LEGACY_ROLE_LABEL = { ...ROLE_LABEL, author: "Auteur", reviewer: "Relecteur", evaluator: "Évaluateur", pedagogical_lead: "Responsable pédagogique" };
export const STAFF = ["admin"];
export const REVIEWERS = ["admin"];
export const PUBLISHERS = ["admin"];
export const hasRole = (user, roles) => !!user && user.roles.some((r) => roles.includes(r));

export const STATUS_META = {
  draft: { label: "Brouillon", cls: "bg-[#f1f4f7] text-[#505e75]" },
  review: { label: "En relecture", cls: "bg-[#EDF3F8] text-[#254a98]" },
  published: { label: "Publiée", cls: "bg-[#eef5f3] text-[#147c77]" },
  retired: { label: "Retirée", cls: "bg-[#FBECEC] text-[#7E2828]" },
};

export const StatusBadge = ({ status, approved, testId }) => {
  const m = STATUS_META[status] || { label: "Statut indisponible", cls: "bg-[#f1f4f7] text-[#505e75]" };
  return (
    <span className={`inline-flex items-center rounded-[10px] px-2 py-0.5 text-xs font-semibold ${m.cls}`} data-testid={testId}>
      {m.label}{status === "review" && approved ? " · approuvée" : ""}
    </span>
  );
};

export const INPUT = "w-full border border-[#e5e9ef] bg-white px-3 py-2 text-sm focus:border-[#147c77] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#147c77]/30";
export const LABEL = "block text-xs font-semibold uppercase tracking-[0.12em] text-[#627086]";
export const BTN_SMALL = "inline-flex items-center gap-1.5 rounded-[10px] border border-[#14243c]/25 px-3 py-1.5 text-xs font-semibold text-[#14243c] transition-colors duration-200 hover:border-[#14243c] hover:bg-white disabled:cursor-not-allowed disabled:opacity-40";
export const BTN_DANGER = "inline-flex items-center gap-1.5 rounded-[10px] border border-[#7E2828]/40 px-3 py-1.5 text-xs font-semibold text-[#7E2828] transition-colors duration-200 hover:bg-[#FBECEC] disabled:cursor-not-allowed disabled:opacity-40";

export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "—");
export const pct = (v) => `${Math.round((v || 0) * 100)} %`;

export const OptionsContext = createContext(null);
export const useOptions = () => useContext(OptionsContext);

export const Notice = ({ kind = "info", children, testId }) => (
  <p role={kind === "error" ? "alert" : "status"} data-testid={testId}
    className={`border-l-2 bg-white px-4 py-3 text-sm ${kind === "error" ? "border-[#A04444] text-[#7E2828]" : kind === "ok" ? "border-[#147c77] text-[#147c77]" : "border-[#365ac8] text-[#505e75]"}`}>
    {children}
  </p>
);
