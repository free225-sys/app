import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Download } from "lucide-react";
import { downloadFile, http, useApi } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { BTN_PRIMARY, LINK_ARROW, ProgressBar, SectionTitle } from "@/components/common";
import { SubmissionStatus } from "@/components/learn/ProjectPanel";

export const PathwaysSection = () => {
  const { data } = useApi("/learners/me/pathways");
  return (
    <section aria-labelledby="my-pathways-title" data-testid="espace-pathways">
      <SectionTitle id="my-pathways-title" eyebrow="Parcours" title="Mes parcours" />
      {!data ? null : data.length === 0 ? (
        <p className="mt-6 text-sm text-[#505e75]" data-testid="espace-pathways-empty">Vous n'êtes inscrit à aucun parcours. <Link to="/parcours" className="font-semibold text-[#147c77] underline">Choisir un parcours</Link></p>
      ) : (
        <ul className="mt-6 grid gap-4 md:grid-cols-2">
          {data.map((p) => (
            <li key={p.pathway_id} className="border border-[#e5e9ef] bg-white p-5" data-testid={`espace-pathway-${p.pathway_id}`}>
              <Link to={`/pathways/${p.pathway_id}`} className="font-semibold hover:underline"><span className="mr-2 font-mono text-xs text-[#147c77]">{p.pathway_id}</span>{p.title}</Link>
              <div className="mt-3 flex justify-between text-xs"><span>Version {p.pathway_version}</span><span className="font-mono">{Math.round(p.percent * 100)} %</span></div>
              <div className="mt-2"><ProgressBar value={p.percent} /></div>
              <p className="mt-3 text-xs text-[#505e75]">
                {p.targets.filter((t) => t.status === "acquired").length}/{p.targets.length} compétences visées acquises
                {p.recognized_counts.modules + p.recognized_counts.competencies > 0 && ` · acquis reconnus : ${p.recognized_counts.modules} module(s), ${p.recognized_counts.competencies} compétence(s)`}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

export const ProjectsSection = () => {
  const { data } = useApi("/learners/me/submissions", { k: "espace" });
  return (
    <section aria-labelledby="my-projects-title" data-testid="espace-projects">
      <SectionTitle id="my-projects-title" eyebrow="Projets" title="Projets appliqués" />
      {!data ? null : data.length === 0 ? (
        <p className="mt-6 text-sm text-[#505e75]">Aucun projet soumis. <Link to="/modules/M16/learn?etape=projet" className="font-semibold text-[#147c77] underline">Découvrir le projet M16</Link></p>
      ) : (
        <ul className="mt-6 divide-y divide-[#e5e9ef] border-y border-[#e5e9ef]">
          {data.map((s) => (
            <li key={s.id} className="py-4" data-testid={`espace-submission-${s.id}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="font-semibold">{s.module_id} — {s.title}</span>
                <SubmissionStatus status={s.status} testId={`espace-submission-status-${s.id}`} />
              </div>
              {s.review && <p className="mt-2 text-sm text-[#505e75]"><span className="font-mono">{Math.round(s.review.percent * 100)} %</span> — {s.review.comment}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

const CredentialCard = ({ c, onClaim }) => {
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);
  const award = c.award;
  const claim = async () => {
    setErr("");
    try {
      await http.post(`/credentials/${c.credential.id}/claim`);
      onClaim();
    } catch (e) {
      setErr(formatApiError(e));
    }
  };
  return (
    <li className="flex flex-col border border-[#e5e9ef] bg-white p-5" data-testid={`credential-${c.credential.id}`}>
      <p className="font-semibold">{c.credential.title}</p>
      <p className="mt-1 text-xs text-[#505e75]">{c.credential.summary}</p>
      <p className="mt-4 text-sm font-semibold" data-testid={`credential-progress-${c.credential.id}`}>{c.met_count}/{c.total} preuves</p>
      <div className="mt-2"><ProgressBar value={c.met_count / c.total} /></div>
      <ul className="mt-3 flex-1 space-y-1 text-xs">
        {c.rules.map((r) => <li key={r.id} className={r.met ? "text-[#147c77]" : "text-[#627086]"} data-testid={`credential-rule-${c.credential.id}-${r.id}`}>{r.met ? "✓" : "○"} {r.label}</li>)}
      </ul>
      {award && award.status === "valid" ? (
        <div className="mt-4 space-y-2" data-testid={`credential-award-${c.credential.id}`}>
          <p className="font-mono text-xs">Code {award.code}</p>
          <div className="flex flex-wrap gap-3">
            <button type="button" className={BTN_PRIMARY} onClick={() => downloadFile(`/certificates/${award.code}/pdf`, `certificat-${award.code}.pdf`)} data-testid={`credential-download-${c.credential.id}`}>
              <Download size={14} aria-hidden="true" /> Télécharger le PDF
            </button>
            <button type="button" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#147c77] underline"
              onClick={() => { navigator.clipboard?.writeText(award.verification_url); setCopied(true); }} data-testid={`credential-share-${c.credential.id}`}>
              <Copy size={14} aria-hidden="true" /> {copied ? "Lien copié" : "Copier le lien de vérification"}
            </button>
          </div>
          <Link to={`/verifier/${award.code}`} className={LINK_ARROW} data-testid={`credential-verify-link-${c.credential.id}`}>Page de vérification</Link>
        </div>
      ) : (
        <div className="mt-4">
          {award?.status === "revoked" && <p className="mb-2 text-xs text-[#7E2828]" data-testid={`credential-revoked-${c.credential.id}`}>Certificat {award.code} révoqué : {award.revoke_reason}</p>}
          {c.reclaim?.blocked ? (
            <p className="text-sm font-semibold text-[#7E2828]" role="status" data-testid={`credential-reclaim-blocked-${c.credential.id}`}>Révoqué, nouvelle demande soumise à autorisation</p>
          ) : (
            <>
              {c.reclaim?.authorized && <p className="mb-2 text-xs text-[#147c77]" data-testid={`credential-reclaim-authorized-${c.credential.id}`}>Nouvelle demande autorisée par l'administrateur.</p>}
              <button type="button" className={BTN_PRIMARY} disabled={!c.eligible} onClick={claim} data-testid={`credential-claim-${c.credential.id}`}>
                {c.eligible ? "Obtenir le certificat" : "Conditions non remplies"}
              </button>
            </>
          )}
          {err && <p role="alert" className="mt-2 text-xs text-[#7E2828]">{err}</p>}
        </div>
      )}
    </li>
  );
};

export const CertificatesSection = () => {
  const [n, setN] = useState(0);
  const { data } = useApi("/learners/me/credentials", { n });
  return (
    <section aria-labelledby="my-certs-title" data-testid="espace-certificates">
      <SectionTitle id="my-certs-title" eyebrow="Certifications" title="Certificats" lead="Un certificat n'est délivré que si toutes ses preuves sont présentes et valides. Chacun porte un code vérifiable publiquement." />
      {data && <ul className="mt-6 grid gap-4 lg:grid-cols-3">{data.map((c) => <CredentialCard key={c.credential.id} c={c} onClaim={() => setN((x) => x + 1)} />)}</ul>}
    </section>
  );
};
