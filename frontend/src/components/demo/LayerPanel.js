import { Link } from "react-router-dom";

export const LAYER_PROTO = {
  "layer-application": "La couche applicative organise l’interaction, choisit les outils et présente les résultats. Module proposé : concevoir une interface d’IA.",
  "layer-donnees": "Le système manipule des données de différentes natures : requête, contexte, corpus et résultats de recherche. Module : architecture des données.",
  "layer-mathematiques": "Les vecteurs, distances, distributions de probabilité et opérations matricielles interviennent à des niveaux distincts. Module : fondements mathématiques.",
  "layer-modeles": "Les algorithmes comprennent plusieurs familles : traitement du langage, recherche, classement et modèles de langage. Module : modèles et Transformers.",
  "layer-infrastructure": "Les ressources matérielles et logicielles assurent le calcul, l’accès aux données et le service des modèles. Module : déployer une IA locale.",
  "layer-securite": "Les contrôles d’accès, la protection des informations et l’évaluation de la qualité sont transversaux. Module : sécurité et gouvernance IA.",
};

export const LayerPanel = ({ layers, activeIds, selectedId, onSelect }) => {
  const selected = layers.find((l) => l.id === selectedId);
  return (
    <aside className="layerpanel" aria-labelledby="layers-title" data-testid="layer-panel">
      <div className="eyebrow">Architecture activée</div>
      <h2 id="layers-title">Explorer les couches</h2>
      <p>À chaque étape, plusieurs composantes interviennent. Sélectionnez-les pour comprendre leur fonction.</p>
      <ul className="layers">
        {layers.map((l) => {
          const on = activeIds.includes(l.id);
          return (
            <li key={l.id}>
              <button type="button" className={`layer ${l.id === selectedId ? "active" : ""}`} aria-pressed={l.id === selectedId} onClick={() => onSelect(l.id)} data-testid={`layer-button-${l.id}`}>
                <span className={`dot ${on ? "on" : ""}`} aria-hidden="true" />
                <span>
                  <strong data-testid={on ? `layer-active-${l.id}` : `layer-related-${l.id}`}>{l.name} {on ? "· mobilisée" : "· connexe"}</strong>
                  <small>{l.short}</small>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="layerdetail" aria-live="polite" data-testid="layer-detail">
        {selected && (
          <>
            <b>{selected.name}</b>
            <p data-testid="layer-detail-definition">{LAYER_PROTO[selected.id] || selected.definition}</p>
            {selected.modules?.length > 0 && (
              <p className="!mt-0" data-testid="layer-detail-modules">
                Modules : {selected.modules.slice(0, 4).map((m, i) => (
                  <span key={m.id}>{i > 0 && ", "}<Link to={`/modules/${m.id}`} className="!text-[11px] underline" data-testid={`layer-module-link-${m.id}`}>{m.code}</Link></span>
                ))}
              </p>
            )}
            <Link to={`/ressources?vue=notions&couche=${selected.id}`} data-testid="layer-concepts-link">Voir les notions associées ↗</Link>
          </>
        )}
      </div>
      <div className="note">Les mécanismes affichés constituent une simulation pédagogique. Les traitements réels dépendent de l'architecture et ne sont pas toujours séquentiels.</div>
    </aside>
  );
};
