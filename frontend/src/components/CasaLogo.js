import { useState } from "react";

const SOURCES = ["/logo-casa.png", "/logo.png", "/logo.svg"];

// Logo client : déposer /public/logo.png (fond transparent) ou /public/logo.svg ; sinon rendu texte du prototype.
export const CasaLogo = ({ inverted = false, className = "" }) => {
  const [idx, setIdx] = useState(0);
  const hasImage = idx < SOURCES.length;
  return (
    <span className={`brand inline-flex items-center ${inverted ? "inverted" : ""} ${className}`} data-testid="casa-logo">
      {hasImage ? (
        <img src={SOURCES[idx]} alt="CASA" className="mr-1 h-8 w-auto min-[721px]:h-11" onError={() => setIdx((i) => i + 1)} data-testid="casa-logo-image" />
      ) : "CASA"}
      <span>AI ACADEMY</span>
    </span>
  );
};
