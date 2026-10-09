import { useState } from "react";
import { StatusBadge, fmtDate } from "./shared";

const Diff = ({ changes }) => (
  <table className="mt-3 w-full table-fixed text-left text-xs" data-testid="version-diff">
    <thead className="text-[#627086]"><tr><th scope="col" className="w-1/5 py-1 pr-2">Champ</th><th scope="col" className="py-1 pr-2">Avant</th><th scope="col" className="py-1">Après</th></tr></thead>
    <tbody className="divide-y divide-[#e5e9ef]">
      {changes.map((c) => (
        <tr key={c.field} data-testid={`diff-field-${c.field}`}>
          <td className="py-1.5 pr-2 font-mono align-top">{c.field}</td>
          <td className="break-words py-1.5 pr-2 align-top text-[#7E2828]">{c.before ?? "—"}</td>
          <td className="break-words py-1.5 align-top text-[#147c77]">{c.after ?? "—"}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

const VersionRow = ({ v }) => {
  const [open, setOpen] = useState(false);
  return (
    <li className="border border-[#e5e9ef] bg-white p-4" data-testid={`history-v${v.version}`}>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="font-mono font-semibold">v{v.version}</span>
        <StatusBadge status={v.status} approved={v.approved} testId={`history-status-v${v.version}`} />
        {v.superseded && v.status === "published" && <span className="text-xs text-[#627086]">remplacée par une version plus récente</span>}
        <span className="text-xs text-[#627086]">{v.changelog}</span>
      </div>
      <p className="mt-1 text-xs text-[#627086]">
        Créée le {fmtDate(v.created_at)}{v.created_by ? ` par ${v.created_by.name}` : ""}
        {v.published_at ? ` · publiée le ${fmtDate(v.published_at)}${v.published_by ? ` par ${v.published_by.name}` : ""}` : ""}
        {v.retired_at ? ` · retirée le ${fmtDate(v.retired_at)} (${v.retire_reason})` : ""}
      </p>
      {(v.reviews || []).length > 0 && (
        <ul className="mt-2 space-y-1 text-xs">
          {v.reviews.map((r, i) => (
            <li key={i} className="border-l-2 border-[#365ac8] pl-2"><strong>{r.decision === "approve" ? "Approuvée" : "Renvoyée"}</strong> par {r.by.name} le {fmtDate(r.at)}{r.comment ? ` — « ${r.comment} »` : ""}</li>
          ))}
        </ul>
      )}
      {v.changes.length > 0 && (
        <button type="button" className="mt-2 text-xs font-semibold text-[#147c77] underline underline-offset-4" aria-expanded={open} onClick={() => setOpen((o) => !o)} data-testid={`history-diff-toggle-v${v.version}`}>
          {open ? "Masquer" : "Voir"} les {v.changes.length} champ{v.changes.length > 1 ? "s" : ""} modifié{v.changes.length > 1 ? "s" : ""}
        </button>
      )}
      {open && <Diff changes={v.changes} />}
    </li>
  );
};

export const History = ({ history }) => (
  <section aria-labelledby="hist-title" className="mt-10" data-testid="version-history">
    <h3 id="hist-title" className="text-sm font-semibold">Historique des versions</h3>
    <ul className="mt-3 space-y-3">{history.map((v) => <VersionRow key={v.version} v={v} />)}</ul>
  </section>
);
