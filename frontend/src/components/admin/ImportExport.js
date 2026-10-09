import { useState } from "react";
import { http } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { BTN_PRIMARY } from "@/components/common";
import { BTN_SMALL, Notice } from "./shared";

const ACTION = { create: "Création", update: "Mise à jour", unchanged: "Inchangé" };

export const ImportExport = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const exportJson = async () => {
    try {
      const { data } = await http.get("/admin/catalog/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = Object.assign(document.createElement("a"), { href: url, download: `casa-catalogue-${data.catalogue_version}.json` });
      a.click();
      URL.revokeObjectURL(url);
      setMsg({ kind: "ok", text: "Catalogue publié exporté." });
    } catch (e) {
      setMsg({ kind: "error", text: formatApiError(e) });
    }
  };
  const run = async (confirm) => {
    setBusy(true);
    setMsg(null);
    try {
      const { data } = await http.post(`/admin/catalog/import${confirm ? "?confirm=true" : ""}`, file.data);
      setPreview(data);
      if (confirm) setMsg({ kind: "ok", text: "Import effectué : les contenus créés ou modifiés sont en brouillon et doivent passer en relecture." });
    } catch (e) {
      setPreview(null);
      setMsg({ kind: "error", text: formatApiError(e) });
    } finally {
      setBusy(false);
    }
  };
  const pick = async (f) => {
    setPreview(null);
    setMsg(null);
    try {
      setFile({ name: f.name, data: JSON.parse(await f.text()) });
    } catch {
      setFile(null);
      setMsg({ kind: "error", text: "Fichier JSON illisible." });
    }
  };
  const s = preview?.summary;
  return (
    <section aria-labelledby="io-title" className="space-y-8" data-testid="admin-import-export">
      <div>
        <h2 id="io-title" className="text-3xl">Import / Export JSON</h2>
        <p className="mt-2 max-w-3xl text-sm text-[#627086]">L'export contient le catalogue publié au format du catalogue exemple. L'import ne publie jamais directement : il crée des brouillons qui suivent le circuit de relecture et de publication.</p>
      </div>
      <div className="rounded-[17px] border border-[#e5e9ef] bg-white p-6">
        <h3 className="text-xl">Exporter</h3>
        <button type="button" className={`${BTN_PRIMARY} mt-4`} onClick={exportJson} data-testid="catalog-export-button">Télécharger le catalogue publié (JSON)</button>
      </div>
      <div className="rounded-[17px] border border-[#e5e9ef] bg-white p-6">
        <h3 className="text-xl">Importer</h3>
        <label htmlFor="catalog-file" className="mt-4 block text-sm font-semibold">Fichier catalogue (.json)</label>
        <input id="catalog-file" type="file" accept=".json,application/json" className="mt-2 text-sm" onChange={(e) => e.target.files[0] && pick(e.target.files[0])} data-testid="catalog-import-file" />
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" className={BTN_SMALL} disabled={!file || busy} onClick={() => run(false)} data-testid="catalog-import-preview">Prévisualiser</button>
          <button type="button" className={BTN_SMALL} disabled={!preview || preview.imported || s?.errors > 0 || busy} onClick={() => run(true)} data-testid="catalog-import-confirm">Confirmer l'import en brouillons</button>
        </div>
        {preview && (
          <div className="mt-6 space-y-4" data-testid="catalog-import-result">
            <p className="text-sm" data-testid="catalog-import-summary">
              {s.create} création(s) · {s.update} mise(s) à jour · {s.unchanged} inchangé(s) · {s.new_competencies} compétence(s) nouvelle(s) · <strong className={s.errors ? "text-[#7E2828]" : "text-[#147c77]"}>{s.errors} erreur(s)</strong>
            </p>
            {preview.errors.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-sm text-[#7E2828]" role="alert" data-testid="catalog-import-errors">{preview.errors.map((e) => <li key={e}>{e}</li>)}</ul>
            )}
            {preview.warnings.length > 0 && <ul className="list-disc pl-5 text-sm text-[#a85e34]" data-testid="catalog-import-warnings">{preview.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
            <div className="max-h-[420px] overflow-auto rounded-[12px] border border-[#e5e9ef]">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="sticky top-0 bg-white text-xs text-[#627086]"><tr>{["Type", "Identifiant", "Source", "Action", "Champs modifiés"].map((h) => <th key={h} scope="col" className="px-3 py-2 font-semibold">{h}</th>)}</tr></thead>
                <tbody className="divide-y divide-[#e5e9ef]">
                  {preview.items.filter((i) => i.action !== "unchanged").concat(preview.items.filter((i) => i.action === "unchanged")).map((i) => (
                    <tr key={`${i.type}-${i.id}`} data-testid={`import-item-${i.type}-${i.id}`}>
                      <td className="px-3 py-2 text-xs">{i.label}</td><td className="px-3 py-2 font-mono text-xs">{i.id}</td><td className="px-3 py-2 font-mono text-xs">{i.source_id}</td>
                      <td className="px-3 py-2 text-xs font-semibold">{ACTION[i.action]}</td><td className="px-3 py-2 text-xs">{i.changes.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
      {msg && <Notice kind={msg.kind} testId="catalog-import-message">{msg.text}</Notice>}
    </section>
  );
};
