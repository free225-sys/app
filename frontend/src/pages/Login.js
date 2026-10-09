import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { formatApiError, safeNext, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, LINK_ARROW } from "@/components/common";
import { AccountBenefits, AuthShell, Field, FormError } from "@/components/AuthForm";

export default function Login() {
  const { user, login } = useAuth();
  const [params] = useSearchParams();
  const next = safeNext(params.get("suite"));
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={next} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(form.email.trim(), form.password);
      navigate(next, { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell eyebrow="Espace apprenant" title="Se connecter" testId="login-page"
      lead={params.get("suite") ? "Connectez-vous pour continuer : vous serez ramené à la page demandée." : "Retrouvez vos modules, vos évaluations et vos compétences acquises."}
      aside={<AccountBenefits />}>
      <form onSubmit={submit} className="space-y-5" noValidate data-testid="login-form">
        <Field id="login-email" label="Adresse e-mail" type="email" autoComplete="email" required value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Field id="login-password" label="Mot de passe" type="password" autoComplete="current-password" required value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <FormError message={error} testId="login-error" />
        <button type="submit" className={`${BTN_PRIMARY} w-full`} disabled={busy} data-testid="login-submit-button">
          {busy ? "Connexion…" : "Se connecter"}
        </button>
      </form>
      <div className="mt-8 flex flex-col gap-3 text-sm">
        <Link to="/mot-de-passe-oublie" className={LINK_ARROW} data-testid="login-forgot-link">Mot de passe oublié ?</Link>
        <p className="text-[#505e75]">
          Pas encore de compte ?{" "}
          <Link to={`/inscription${params.get("suite") ? `?suite=${encodeURIComponent(next)}` : ""}`} className="font-semibold text-[#147c77] underline underline-offset-4" data-testid="login-register-link">
            Créer un compte
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
