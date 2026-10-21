import { Link } from "react-router-dom";
import { LINK_ARROW } from "@/components/common";
import { AuthShell } from "@/components/AuthForm";

export default function ForgotPassword() {
  return (
    <AuthShell eyebrow="Espace apprenant" title="Mot de passe oublié" testId="forgot-page"
      lead="La réinitialisation par e-mail n'est pas disponible : l'administrateur vous attribue un mot de passe provisoire.">
      <p role="status" className="border-l-2 border-[#365ac8] bg-white px-4 py-3 text-sm leading-relaxed" data-testid="forgot-message">
        Contactez l'administrateur de la plateforme : <a href="mailto:contact@relaisit.com" className="font-semibold text-[#147c77] underline" data-testid="forgot-contact-link">contact@relaisit.com</a>
      </p>
      <Link to="/connexion" className={`${LINK_ARROW} mt-8`} data-testid="forgot-login-link">Retour à la connexion</Link>
    </AuthShell>
  );
}
