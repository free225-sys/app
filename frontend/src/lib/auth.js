import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { http } from "./api";
import { Loading } from "@/components/common";

const TOKEN_KEY = "casa-token";
export const DEMO_STORE_KEY = "casa-demo-state";
export const DIAG_STORE_KEY = "casa-diagnostic-answers";

http.interceptors.request.use((cfg) => {
  const t = localStorage.getItem(TOKEN_KEY);
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export function formatApiError(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return "Une erreur est survenue. Veuillez réessayer.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => {
      const field = d?.loc?.[d.loc.length - 1];
      if (field === "email") return "Adresse e-mail invalide.";
      if (field === "password") return "Le mot de passe doit contenir au moins 8 caractères.";
      return "Veuillez vérifier les champs du formulaire.";
    }).filter((v, i, a) => a.indexOf(v) === i).join(" ");
  }
  return String(detail);
}

export const safeNext = (next) => (next && next.startsWith("/") && !next.startsWith("//") ? next : "/espace");
export const isAdmin = (u) => !!u && u.role === "admin";
export const homeFor = (u, next) => (isAdmin(u) ? (next && next.startsWith("/admin") ? next : "/admin") : safeNext(next));

const readJson = (key) => {
  try {
    return JSON.parse(sessionStorage.getItem(key) || "null");
  } catch {
    return null;
  }
};

async function attachAnonymousProgress() {
  const demo = readJson(DEMO_STORE_KEY);
  if (demo?.maxStep) await http.post("/learners/me/demo-progress", { max_step: demo.maxStep, quiz_answers: demo.quiz || {} }).catch(() => {});
  const diag = readJson(DIAG_STORE_KEY);
  if (diag) {
    await http.post("/diagnostic/submit", { answers: diag }).catch(() => {});
    sessionStorage.removeItem(DIAG_STORE_KEY);
  }
}

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (localStorage.getItem(TOKEN_KEY) ? null : false));

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return;
    http.get("/auth/me").then((r) => setUser(r.data)).catch(() => {
      localStorage.removeItem(TOKEN_KEY);
      setUser(false);
    });
  }, []);

  const start = async (path, body) => {
    const { data } = await http.post(path, body);
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (!isAdmin(data.user)) await attachAnonymousProgress();
    setUser(data.user);
    return data.user;
  };

  const value = {
    user,
    login: (email, password) => start("/auth/login", { email, password }),
    register: (body) => start("/auth/register", body),
    logout: async () => {
      await http.post("/auth/logout").catch(() => {});
      localStorage.removeItem(TOKEN_KEY);
      setUser(false);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const RequireAuth = ({ children, learner = false }) => {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === null) return <Loading />;
  if (!user) return <Navigate to={`/connexion?suite=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  if (learner && isAdmin(user)) return <Navigate to="/admin" replace />;
  return children;
};

export const STATUS_LABEL = { not_started: "Non commencé", in_progress: "En cours", completed: "Terminé" };
export const statusLabel = (s) => STATUS_LABEL[s] || (s ? "Statut indisponible" : "—");
