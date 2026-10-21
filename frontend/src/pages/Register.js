import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { formatApiError, homeFor, safeNext, useAuth } from "@/lib/auth";
import { BTN_PRIMARY } from "@/components/common";
import { AccountBenefits, AuthShell, Field, FormError } from "@/components/AuthForm";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Register() {
  const { user, register } = useAuth();
  const [params] = useSearchParams();
  const next = safeNext(params.get("suite"));
  const navigate = useNavigate();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homeFor(user, params.get("suite"))} replace />;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.first_name.trim() || !form.last_name.trim()) return setError("Le prénom et le nom sont obligatoires.");
    if (!EMAIL_RE.test(form.email.trim())) return setError("Adresse e-mail invalide.");
    if (form.password.length < 8) return setError("Le mot de passe doit contenir au moins 8 caractères.");
    setBusy(true);
    setError("");
    try {
      const u = await register({ ...form, email: form.email.trim() });
      navigate(homeFor(u, params.get("suite")), { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell eyebrow="Espace apprenant" title="Créer un compte" testId="register-page"
      lead="Votre progression dans la démonstration et votre test de positionnement de cette session seront rattachés à votre compte."
      aside={<AccountBenefits />}>
      <form onSubmit={submit} className="space-y-5" noValidate data-testid="register-form">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field id="register-first-name" label="Prénom" autoComplete="given-name" required value={form.first_name} onChange={set("first_name")} />
          <Field id="register-last-name" label="Nom" autoComplete="family-name" required value={form.last_name} onChange={set("last_name")} />
        </div>
        <Field id="register-email" label="Adresse e-mail" type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        <Field id="register-password" label="Mot de passe" type="password" autoComplete="new-password" required minLength={8}
          hint="8 caractères minimum." value={form.password} onChange={set("password")} />
        <FormError message={error} testId="register-error" />
        <button type="submit" className={`${BTN_PRIMARY} w-full`} disabled={busy} data-testid="register-submit-button">
          {busy ? "Création du compte…" : "Créer mon compte"}
        </button>
      </form>
      <p className="mt-8 text-sm text-[#505e75]">
        Déjà inscrit ?{" "}
        <Link to={`/connexion${params.get("suite") ? `?suite=${encodeURIComponent(next)}` : ""}`} className="font-semibold text-[#147c77] underline underline-offset-4" data-testid="register-login-link">
          Se connecter
        </Link>
      </p>
    </AuthShell>
  );
}
