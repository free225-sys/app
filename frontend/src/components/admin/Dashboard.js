import { Fragment } from "react";
import { useApi } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { Loading } from "@/components/common";
import { Notice, ROLE_LABEL, pct } from "./shared";

const Stat = ({ label, value, sub, testId }) => (
  <div className="border border-[#e5e9ef] bg-white p-5" data-testid={testId}>
    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#627086]">{label}</p>
    <p className="mt-3 font-mono text-3xl font-semibold text-[#14243c]" data-testid={`${testId}-value`}>{value}</p>
    {sub && <p className="mt-1 text-xs text-[#627086]">{sub}</p>}
  </div>
);

export const Dashboard = () => {
  const { data, error } = useApi("/admin/analytics");
  if (error) return <Notice kind="error">{formatApiError(error)}</Notice>;
  if (!data) return <Loading />;
  const { demo, learning, users, credentials, projects, content } = data;
  const maxLayer = Math.max(1, ...demo.by_layer.map((l) => l.count));
  return (
    <section aria-labelledby="dash-title" data-testid="admin-dashboard">
      <h2 id="dash-title" className="text-2xl font-semibold tracking-tight">Tableau de bord</h2>
      <p className="mt-2 text-sm text-[#627086]">Chiffres réels issus de la plateforme. Une valeur nulle signifie qu'aucun événement n'a encore été enregistré.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Démos démarrées" value={demo.starts} testId="stat-demo-starts" />
        <Stat label="Démos terminées (7 étapes)" value={demo.completions} sub={`Taux de complétion : ${pct(demo.completion_rate)}`} testId="stat-demo-completions" />
        <Stat label="Clics sur les couches" value={demo.layer_clicks} testId="stat-demo-layer-clicks" />
        <Stat label="Apprenants ayant commencé M01" value={learning.m01_starters} testId="stat-m01-starters" />
        <Stat label="Réussite aux quiz notés" value={pct(learning.success_rate)} sub={`${learning.graded_passed} réussites / ${learning.graded_attempts} tentatives`} testId="stat-quiz-success" />
        <Stat label="Inscriptions" value={users.total} sub={`${users.registrations_30d} sur les 30 derniers jours`} testId="stat-registrations" />
        <Stat label="Certificats délivrés" value={credentials.issued} sub={`${credentials.valid} valides`} testId="stat-certificates-issued" />
        <Stat label="Certificats révoqués" value={credentials.revoked} testId="stat-certificates-revoked" />
      </div>
      <div className="mt-10 grid gap-8 lg:grid-cols-2">
        <div className="border border-[#e5e9ef] bg-white p-5" data-testid="dash-layers">
          <h3 className="text-sm font-semibold">Couches consultées dans la démonstration</h3>
          {demo.by_layer.length === 0 ? <p className="mt-3 text-sm text-[#627086]">Aucun clic enregistré.</p> : (
            <ul className="mt-4 space-y-2">
              {demo.by_layer.map((l) => (
                <li key={l.layer_id} className="text-sm" data-testid={`dash-layer-${l.layer_id}`}>
                  <div className="flex justify-between"><span>{l.name}</span><span className="font-mono">{l.count}</span></div>
                  <div className="mt-1 h-1.5 bg-[#edf1f5]"><div className="h-full bg-[#365ac8]" style={{ width: `${(l.count / maxLayer) * 100}%` }} /></div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="border border-[#e5e9ef] bg-white p-5" data-testid="dash-activity">
          <h3 className="text-sm font-semibold">Activité pédagogique</h3>
          <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
            <dt>Modules terminés</dt><dd className="text-right font-mono">{learning.module_completions}</dd>
            <dt>Inscriptions à un parcours</dt><dd className="text-right font-mono">{learning.enrollments}</dd>
            <dt>Projets en attente</dt><dd className="text-right font-mono">{projects.submitted}</dd>
            <dt>Projets validés / refusés</dt><dd className="text-right font-mono">{projects.validated} / {projects.rejected}</dd>
            {Object.entries(users.by_role).map(([r, n]) => (<Fragment key={r}><dt>Comptes {ROLE_LABEL[r] || r}</dt><dd className="text-right font-mono">{n}</dd></Fragment>))}
          </dl>
        </div>
      </div>
      <div className="mt-10 overflow-x-auto border border-[#e5e9ef] bg-white" data-testid="dash-content">
        <table className="w-full min-w-[520px] text-left text-sm">
          <caption className="px-4 pt-4 text-left text-sm font-semibold">Versions de contenus par statut</caption>
          <thead className="text-xs text-[#627086]"><tr>{["Type", "Brouillons", "En relecture", "Publiées", "Retirées"].map((h) => <th key={h} scope="col" className="px-4 py-2 font-semibold">{h}</th>)}</tr></thead>
          <tbody className="divide-y divide-[#e5e9ef]">
            {Object.entries(content).map(([t, c]) => (
              <tr key={t}><td className="px-4 py-2">{c.label}</td><td className="px-4 py-2 font-mono">{c.draft}</td><td className="px-4 py-2 font-mono">{c.review}</td><td className="px-4 py-2 font-mono">{c.published}</td><td className="px-4 py-2 font-mono">{c.retired}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
