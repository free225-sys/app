import { Link } from "react-router-dom";
import { BTN_PRIMARY, Container, Eyebrow } from "@/components/common";

export default function NotFound() {
  return (
    <Container className="py-24 sm:py-32" data-testid="not-found-page">
      <Eyebrow>Erreur 404</Eyebrow>
      <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Cette page n'existe pas.</h1>
      <p className="mt-6 max-w-xl text-base text-[#505e75]">L'adresse demandée ne correspond à aucun contenu.</p>
      <Link to="/" className={`${BTN_PRIMARY} mt-10`} data-testid="not-found-home-link">Retour à l'accueil</Link>
    </Container>
  );
}
