import { AppWindow, BadgeCheck, Blocks, Compass, Cpu, Database, Hammer, Lightbulb, Lock, MessageSquare, Network, PenLine, ScanText, Scale, Search, Send, Server, ShieldCheck, Sigma, Sprout, Briefcase, Wrench } from "lucide-react";

const STAGES = { "stage-01": MessageSquare, "stage-02": ScanText, "stage-03": Search, "stage-04": Cpu, "stage-05": PenLine, "stage-06": ShieldCheck, "stage-07": Send };
const LAYERS = { "layer-application": AppWindow, "layer-donnees": Database, "layer-mathematiques": Sigma, "layer-modeles": Network, "layer-infrastructure": Server, "layer-securite": Lock };
const COMPETENCIES = { "K-001": Lightbulb, "K-002": Hammer, "K-003": Scale, "comp-expliquer": Lightbulb, "comp-utiliser": Wrench, "comp-construire": Hammer, "comp-evaluer": Scale, "comp-piloter": Compass };
const PROFILES = { "profile-decouvrir": Sprout, decouvrir: Sprout, "profile-utiliser": Briefcase, utiliser: Briefcase, "profile-concevoir": Blocks, concevoir: Blocks, "profile-piloter": Compass, piloter: Compass };
const ALL = { ...STAGES, ...LAYERS, ...COMPETENCIES, ...PROFILES };

// Pictogramme trait sobre (couleur ink/blue) pour étapes, couches, compétences et profils.
export const Picto = ({ id, size = 16, className = "", category }) => {
  const Icon = ALL[id] || (category ? ALL[category] : null) || BadgeCheck;
  return <Icon size={size} strokeWidth={1.6} className={`shrink-0 text-[#365ac8] ${className}`} aria-hidden="true" data-testid={`picto-${id}`} />;
};
