import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { CatalogContext, useApi } from "@/lib/api";
import Home from "@/pages/Home";
import Demo from "@/pages/Demo";
import Ressources from "@/pages/Ressources";
import ConceptPage from "@/pages/ConceptPage";
import ModulePage from "@/pages/ModulePage";
import Parcours from "@/pages/Parcours";
import Approche from "@/pages/Approche";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import Diagnostic from "@/pages/Diagnostic";
import ModuleLearn from "@/pages/ModuleLearn";
import CourseReader from "@/pages/CourseReader";
import Espace from "@/pages/Espace";
import PathwayPage from "@/pages/PathwayPage";
import Evaluation from "@/pages/Evaluation";
import Admin from "@/pages/Admin";
import Verify from "@/pages/Verify";
import { AuthProvider } from "@/lib/auth";
import NotFound from "@/pages/NotFound";

const ScrollManager = () => {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) return el.scrollIntoView();
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
};

function App() {
  const { data: catalog } = useApi("/catalog/overview");
  return (
    <div className="App flex min-h-screen flex-col">
      <CatalogContext.Provider value={catalog}>
        <AuthProvider>
        <BrowserRouter>
          <a href="#contenu" className="skip-link" data-testid="skip-link">
            Aller au contenu
          </a>
          <ScrollManager />
          <Header />
          <main id="contenu" tabIndex={-1} className="flex-1 outline-none">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/demo" element={<Demo />} />
              <Route path="/ressources" element={<Ressources />} />
              <Route path="/concepts/:id" element={<ConceptPage />} />
              <Route path="/modules/:id" element={<ModulePage />} />
              <Route path="/modules/:id/learn" element={<ModuleLearn />} />
              <Route path="/courses/:id" element={<CourseReader />} />
              <Route path="/parcours" element={<Parcours />} />
              <Route path="/approche" element={<Approche />} />
              <Route path="/connexion" element={<Login />} />
              <Route path="/inscription" element={<Register />} />
              <Route path="/mot-de-passe-oublie" element={<ForgotPassword />} />
              <Route path="/diagnostic" element={<Diagnostic />} />
              <Route path="/espace" element={<Espace />} />
              <Route path="/pathways/:id" element={<PathwayPage />} />
              <Route path="/evaluation" element={<Evaluation />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/verifier" element={<Verify />} />
              <Route path="/verifier/:code" element={<Verify />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
          <Footer />
        </BrowserRouter>
        </AuthProvider>
      </CatalogContext.Provider>
    </div>
  );
}

export default App;
