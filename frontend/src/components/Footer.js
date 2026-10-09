import { Link } from "react-router-dom";
import { CasaLogo } from "./CasaLogo";
import { NAV_LINKS } from "./Header";

export const Footer = () => (
  <footer className="mt-24 border-t border-[#e5e9ef] bg-white" data-testid="site-footer">
    <div className="shell grid gap-10 py-14 md:grid-cols-12">
      <div className="md:col-span-6">
        <CasaLogo />
        <p className="mt-5 max-w-md text-sm leading-relaxed text-[#627086]">
          Une expérience de formation qui rend visible le fonctionnement de l'intelligence artificielle, de la question à la réponse.
        </p>
      </div>
      <nav aria-label="Pied de page" className="md:col-span-3">
        <p className="eyebrow">Plateforme</p>
        <ul className="mt-4 space-y-2.5 text-sm">
          {NAV_LINKS.map((l) => (
            <li key={l.to}><Link to={l.to} className="text-[#505e75] hover:text-[#365ac8]" data-testid={`footer-${l.testId}`}>{l.label}</Link></li>
          ))}
        </ul>
      </nav>
      <div className="md:col-span-3">
        <p className="eyebrow">Apprendre</p>
        <p className="mt-4 text-sm leading-relaxed text-[#627086]">Démonstration et catalogue en accès libre. Modules, évaluations et suivi des compétences avec un compte apprenant.</p>
        <Link to="/diagnostic" className="mt-3 block text-sm font-semibold text-[#365ac8] hover:underline" data-testid="footer-diagnostic-link">Test de positionnement</Link>
        <Link to="/verifier" className="mt-2 block text-sm font-semibold text-[#365ac8] hover:underline" data-testid="footer-verify-link">Vérifier un certificat</Link>
      </div>
    </div>
    <div className="shell flex flex-col gap-2 border-t border-[#e5e9ef] py-6 text-[11px] text-[#68778b] sm:flex-row sm:justify-between">
      <span>© {new Date().getFullYear()} CASA AI Academy</span>
      <span data-testid="footer-relais-it">
        by <a href="https://www.relaisit.com" target="_blank" rel="noopener" className="font-semibold text-[#14243c] hover:text-[#365ac8] hover:underline" data-testid="footer-relais-it-link">Relais IT</a>
      </span>
    </div>
  </footer>
);
