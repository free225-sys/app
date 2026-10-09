import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { BarChart3, ClipboardCheck, FileClock, FileJson, Layers, ShieldCheck, Users as UsersIcon } from "lucide-react";
import { http } from "@/lib/api";
import { RequireAuth, formatApiError, useAuth } from "@/lib/auth";
import { Container, ErrorState, Loading, PageHeader } from "@/components/common";
import { ContentSection } from "@/components/admin/ContentSection";
import { Dashboard } from "@/components/admin/Dashboard";
import { Users } from "@/components/admin/Users";
import { Certificates, ChangeLog, ReviewQueue } from "@/components/admin/Panels";
import { ImportExport } from "@/components/admin/ImportExport";
import { OptionsContext, PUBLISHERS, ROLE_LABEL, STAFF, hasRole } from "@/components/admin/shared";

const TABS = [
  { id: "tableau-de-bord", label: "Tableau de bord", icon: BarChart3 },
  { id: "contenus", label: "Contenus", icon: Layers },
  { id: "relecture", label: "Relecture", icon: ClipboardCheck },
  { id: "journal", label: "Journal", icon: FileClock },
  { id: "import-export", label: "Import / Export JSON", icon: FileJson, publisher: true },
  { id: "utilisateurs", label: "Utilisateurs", icon: UsersIcon, admin: true },
  { id: "certificats", label: "Certificats et preuves", icon: ShieldCheck, admin: true },
];

function BackOffice() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [types, setTypes] = useState(null);
  const [options, setOptions] = useState(null);
  const [error, setError] = useState(null);
  const isAdmin = user.roles.includes("admin");
  const tabs = TABS.filter((t) => (!t.admin || isAdmin) && (!t.publisher || hasRole(user, PUBLISHERS)));
  const tab = tabs.find((t) => t.id === params.get("onglet"))?.id || "tableau-de-bord";
  const reloadOptions = useCallback(() => http.get("/admin/options").then((r) => setOptions(r.data)).catch(() => {}), []);
  useEffect(() => {
    http.get("/admin/content-types").then((r) => setTypes(r.data)).catch(setError);
    reloadOptions();
  }, [reloadOptions]);
  const forbidden = ["utilisateurs", "certificats"].includes(params.get("onglet")) && !isAdmin;

  if (error) return <ErrorState message={formatApiError(error)} />;
  if (!types) return <Loading />;
  return (
    <OptionsContext.Provider value={options}>
      <div data-testid="backoffice-page">
        <PageHeader eyebrow="Back-office" title="Pilotage du catalogue" lead="Rédiger, relire, publier et suivre les contenus pédagogiques — chaque version publiée reste immuable et traçable.">
          <p className="mt-6 text-sm text-[#505e75]" data-testid="backoffice-roles">Connecté en tant que {user.first_name} {user.last_name} · {user.roles.map((r) => ROLE_LABEL[r]).join(", ")}</p>
        </PageHeader>
        <Container className="grid gap-10 py-12 lg:grid-cols-[220px_1fr]">
          <nav aria-label="Sections du back-office" className="lg:sticky lg:top-24 lg:self-start">
            <ul className="flex gap-2 overflow-x-auto lg:flex-col lg:gap-1">
              {tabs.map((t) => (
                <li key={t.id}>
                  <button type="button" onClick={() => setParams({ onglet: t.id })} aria-current={tab === t.id ? "page" : undefined}
                    className={`flex w-full items-center gap-2 whitespace-nowrap rounded-[10px] px-3 py-2 text-left text-sm font-medium transition-colors duration-150 ${tab === t.id ? "bg-[#14243c] text-white" : "text-[#14243c] hover:bg-white"}`}
                    data-testid={`admin-tab-${t.id}`}>
                    <t.icon size={15} aria-hidden="true" />{t.label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          <div className="min-w-0">
            {forbidden ? <p role="alert" className="border-l-2 border-[#A04444] bg-white px-4 py-3 text-sm" data-testid="admin-forbidden">Section réservée aux administrateurs.</p>
              : tab === "tableau-de-bord" ? <Dashboard />
              : tab === "contenus" ? <ContentSection types={types} type={params.get("type") || "concept"} id={params.get("id")} setParams={setParams} reloadOptions={reloadOptions} />
              : tab === "relecture" ? <ReviewQueue open={(type, id) => setParams({ onglet: "contenus", type, id })} />
              : tab === "journal" ? <ChangeLog types={types} />
              : tab === "import-export" ? <ImportExport />
              : tab === "utilisateurs" ? <Users />
              : <Certificates />}
          </div>
        </Container>
      </div>
    </OptionsContext.Provider>
  );
}

function Gate() {
  const { user } = useAuth();
  if (!hasRole(user, STAFF)) return <ErrorState message="Le back-office est réservé aux équipes pédagogiques et aux administrateurs." />;
  return <BackOffice />;
}

export default function Admin() {
  return <RequireAuth><Gate /></RequireAuth>;
}
