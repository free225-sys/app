import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, HelpCircle, XCircle } from "lucide-react";
import { useApi } from "@/lib/api";
import { BTN_PRIMARY, Container, Loading, PageHeader } from "@/components/common";

const date = (iso) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });

const Result = ({ code }) => {
  const { data, loading } = useApi(`/verify/${encodeURIComponent(code)}`);
  if (loading) return <Loading />;
  const s = data.status;
  const style = s === "valid" ? "border-[#147c77] bg-[#eef5f3]" : s === "revoked" ? "border-[#A04444] bg-[#FBECEC]" : "border-[#e5e9ef] bg-white";
  const Icon = s === "valid" ? CheckCircle2 : s === "revoked" ? XCircle : HelpCircle;
  return (
    <section className={`casa-fade mt-10 max-w-3xl border-l-2 px-6 py-6 ${style}`} role="status" data-testid="verify-result">
      <p className="flex items-center gap-2 text-xl font-semibold" data-testid="verify-status">
        <Icon size={22} aria-hidden="true" />
        {s === "valid" ? "Certificat valide" : s === "revoked" ? "Certificat révoqué" : "Aucun certificat ne correspond à ce code"}
      </p>
      {s !== "not_found" && (
        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-[#627086]">Titulaire</dt><dd className="font-semibold" data-testid="verify-holder">{data.holder_name}</dd></div>
          <div><dt className="text-xs text-[#627086]">Certification</dt><dd className="font-semibold">{data.credential_title}</dd></div>
          <div><dt className="text-xs text-[#627086]">Délivré le</dt><dd>{date(data.issued_at)}</dd></div>
          <div><dt className="text-xs text-[#627086]">Code</dt><dd className="font-mono">{data.code}</dd></div>
          {s === "revoked" && <div className="sm:col-span-2"><dt className="text-xs text-[#627086]">Révoqué le</dt><dd data-testid="verify-revoked-info">{date(data.revoked_at)} — {data.revoke_reason}</dd></div>}
          <div className="sm:col-span-2"><dt className="text-xs text-[#627086]">Preuves</dt><dd><ul className="mt-1 space-y-1">{data.evidence.map((e) => <li key={e.label}>— {e.label}</li>)}</ul></dd></div>
        </dl>
      )}
    </section>
  );
};

export default function Verify() {
  const { code } = useParams();
  const navigate = useNavigate();
  const [value, setValue] = useState(code || "");
  return (
    <div data-testid="verify-page">
      <PageHeader eyebrow="Vérification" title="Vérifier un certificat" lead="Saisissez le code figurant sur le certificat (format CASA-XXXX-XXXX) pour en confirmer l'authenticité." />
      <Container className="pt-10">
        <form className="flex max-w-xl flex-col gap-3 sm:flex-row" onSubmit={(e) => { e.preventDefault(); if (value.trim()) navigate(`/verifier/${value.trim().toUpperCase()}`); }} data-testid="verify-form">
          <label htmlFor="verify-code" className="sr-only">Code du certificat</label>
          <input id="verify-code" value={value} onChange={(e) => setValue(e.target.value)} placeholder="CASA-XXXX-XXXX" className="flex-1 border border-[#e5e9ef] bg-white px-3 py-3 font-mono text-sm uppercase" data-testid="verify-code-input" />
          <button type="submit" className={BTN_PRIMARY} data-testid="verify-submit-button">Vérifier</button>
        </form>
        {code && <Result key={code} code={code} />}
      </Container>
    </div>
  );
}
