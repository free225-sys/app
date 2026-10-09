import { useState } from "react";
import { Link } from "react-router-dom";
import { http } from "@/lib/api";
import { BTN_PRIMARY, LINK_ARROW } from "@/components/common";
import { AuthShell } from "@/components/AuthForm";

export default function ForgotPassword() {
  const [message, setMessage] = useState("");
  const ask = async () => {
    const { data } = await http.post("/auth/forgot-password");
    setMessage(data.message);
  };
  return (
    <AuthShell eyebrow="Espace apprenant" title="Mot de passe oublié" testId="forgot-page"
      lead="La réinitialisation par e-mail n'est pas encore disponible dans cette version de la plateforme.">
      {message ? (
        <p role="status" className="border-l-2 border-[#365ac8] bg-white px-4 py-3 text-sm leading-relaxed" data-testid="forgot-message">{message}</p>
      ) : (
        <button type="button" onClick={ask} className={BTN_PRIMARY} data-testid="forgot-submit-button">Que dois-je faire ?</button>
      )}
      <Link to="/connexion" className={`${LINK_ARROW} mt-8`} data-testid="forgot-login-link">Retour à la connexion</Link>
    </AuthShell>
  );
}
