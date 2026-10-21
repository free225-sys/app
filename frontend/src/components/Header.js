import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { isAdmin, useAuth } from "@/lib/auth";
import { CasaLogo } from "./CasaLogo";

export const NAV_LINKS = [
  { label: "Accueil", to: "/", testId: "nav-link-accueil", end: true },
  { label: "Explorer l'IA", to: "/demo", testId: "nav-link-decouvrir" },
  { label: "Parcours", to: "/parcours", testId: "nav-link-parcours" },
  { label: "Notre approche", to: "/approche", testId: "nav-link-approche" },
  { label: "Ressources", to: "/ressources", testId: "nav-link-ressources" },
];

const AccountLinks = ({ mobile = false }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const p = mobile ? "mobile-" : "";
  const cls = mobile ? "border-b border-[#e5e9ef] py-3.5 text-left text-base" : "button minimal";
  if (user === null) return null;
  if (!user) return <NavLink to="/connexion" className={cls} data-testid={`${p}nav-link-connexion`}>Se connecter</NavLink>;
  return (
    <>
      {isAdmin(user)
        ? <NavLink to="/admin" className={cls} data-testid={`${p}nav-link-admin`}>Administration</NavLink>
        : <NavLink to="/espace" className={cls} data-testid={`${p}nav-link-espace`}>Mon espace</NavLink>}
      <button type="button" className={cls} onClick={async () => { await logout(); navigate("/"); }} data-testid={`${p}logout-button`}>Se déconnecter</button>
    </>
  );
};

export const Header = () => {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  return (
    <header className="top" data-testid="site-header">
      <div className="shell nav">
        <Link to="/" aria-label="CASA AI Academy — accueil" data-testid="header-logo-link"><CasaLogo /></Link>
        <nav className="navlinks" aria-label="Navigation principale">
          {NAV_LINKS.map((l) => <NavLink key={l.to} to={l.to} end={l.end} data-testid={l.testId}>{l.label}</NavLink>)}
        </nav>
        <div className="rightnav">
          <span className="hidden items-center gap-1 min-[721px]:flex"><AccountLinks /></span>
          <Link to="/demo" className="button secondary nav-btn" data-testid="header-demo-cta">Essayer la démo ↗</Link>
          <button type="button" className="inline-flex h-10 w-10 items-center justify-center rounded-[10px] border border-[#e5e9ef] lg:hidden" aria-expanded={open} aria-controls="menu-mobile"
            aria-label={open ? "Fermer le menu" : "Ouvrir le menu"} onClick={() => setOpen((o) => !o)} data-testid="mobile-menu-toggle">
            {open ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
          </button>
        </div>
      </div>
      {open && (
        <nav id="menu-mobile" aria-label="Navigation mobile" className="casa-fade border-t border-[#e5e9ef] bg-white lg:hidden" data-testid="mobile-menu">
          <div className="shell flex flex-col py-4">
            {NAV_LINKS.map((l) => <NavLink key={l.to} to={l.to} end={l.end} className="border-b border-[#e5e9ef] py-3.5 text-base" data-testid={`mobile-${l.testId}`}>{l.label}</NavLink>)}
            <AccountLinks mobile />
            <Link to="/demo" className="button secondary mt-4" data-testid="mobile-demo-cta">Essayer la démo ↗</Link>
          </div>
        </nav>
      )}
    </header>
  );
};
