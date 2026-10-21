"""Create CERT-DOC-01 option-B drafts via the admin API and submit them to review (no approval, no publication)."""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from creds import ADMIN  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=15).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
CL = "CERT-DOC-01 option B : quiz noté K-001 pour M-001 (brouillon, à valider par le client)"


def opts(*texts):
    return [{"id": "abcd"[i], "text": t} for i, t in enumerate(texts)]


QUESTIONS = [
    ("Q-M-001-G1", "single", 2, "Dans quel ordre s'enchaînent les traitements qui produisent une réponse d'assistant ?",
     opts("Interface, préparation, recherche éventuelle, inférence, génération, contrôles, restitution",
          "Recherche, interface, génération, inférence, préparation, restitution, contrôles",
          "Inférence, interface, préparation, contrôles, génération, recherche, restitution"), ["a"],
     "Une réponse résulte d'une chaîne de traitements. La recherche, quand elle existe, précède l'inférence ; les contrôles précèdent la restitution."),
    ("Q-M-001-G2", "single", 1, "Dans la démonstration (« Quels textes régissent la commercialisation du café et du cacao ? »), à quel moment intervient la recherche documentaire ?",
     opts("Avant la formulation de la demande", "Après la préparation de la demande et avant l'inférence du modèle",
          "Après la restitution, pour archiver la réponse"), ["b"],
     "Les extraits du Journal officiel sont retrouvés après la préparation de la demande, puis transmis au modèle avant qu'il ne calcule sa réponse."),
    ("Q-M-001-G3", "multiple", 2, "Une juriste colle l'intégralité d'un long recueil de textes dans l'assistant. Celui-ci indique qu'il ne peut pas tout traiter en une fois, et le coût d'utilisation augmente nettement. Quelles explications sont correctes ? (plusieurs réponses)",
     opts("La longueur du texte se mesure en tokens, et la fenêtre de contexte de l'assistant est limitée en tokens",
          "Le coût d'utilisation se calcule lui aussi en tokens",
          "Un mot long peut être découpé en plusieurs tokens, ce qui allonge la mesure du texte",
          "L'assistant compte les pages du document et refuse au-delà d'un nombre de pages"), ["a", "b", "c"],
     "Le modèle ne lit pas des pages ni des mots, mais des tokens : ils mesurent la longueur du texte, la capacité de la fenêtre de contexte et le coût."),
    ("Q-M-001-G4", "single", 2, "Dans le cas CASA, l'assistant cite un « décret de 2019 » qui n'existe pas dans la base documentaire. Aucun extrait correspondant n'est affiché, alors que les extraits retrouvés étaient bien pertinents. Quelle étape a produit ce passage erroné ?",
     opts("La recherche documentaire, qui aurait créé le décret",
          "L'inférence et la génération : le modèle a calculé un texte plausible à partir de ses paramètres, sans s'appuyer sur un extrait retrouvé",
          "La formulation de la demande par l'utilisateur", "La restitution, qui s'est contentée de mettre en forme la réponse"), ["b"],
     "La recherche retrouve des extraits existants ; elle ne rédige pas. Le texte est produit à l'inférence, quand le modèle estime token après token la suite la plus probable : un passage plausible mais absent des sources naît donc à cette étape."),
    ("Q-M-001-G5", "single", 1, "Un assistant RH répond aux salariés à partir du règlement intérieur de l'entreprise. Pour la question « Combien de jours de congé sont accordés pour un mariage ? », laquelle de ces opérations relève de la recherche documentaire, et non de la préparation ou de l'inférence ?",
     opts("Découper la question du salarié en tokens",
          "Retrouver dans le règlement intérieur l'article consacré aux congés pour événements familiaux",
          "Estimer, token après token, la suite de texte la plus probable",
          "Mobiliser les paramètres du modèle sur des processeurs CPU ou GPU"), ["b"],
     "Le découpage en tokens relève de la préparation ; l'estimation du token suivant et l'usage des paramètres sur CPU ou GPU relèvent de l'inférence. Seule la recherche documentaire va chercher le passage pertinent dans le règlement intérieur."),
]


def call(method, path, **kw):
    r = requests.request(method, f"{API}{path}", headers=H, timeout=30, **kw)
    assert r.status_code == 200, (path, r.status_code, r.text)
    return r.json()


def created(t, eid, content):
    call("POST", f"/admin/content/{t}", json={"id": eid, "content": content, "changelog": CL})
    call("POST", f"/admin/versions/{t}/{eid}/submit")
    print("draft+review", t, eid, "v1")


def new_version(t, eid, base, changes):
    content = {k: v for k, v in base.items() if k not in ("version", "status", "approved", "changelog", "created_at", "published_at", "reviews", "entity_id", "_id")}
    content.update(changes)
    d = call("PUT", f"/admin/content/{t}/{eid}", json={"content": content, "changelog": CL})
    call("POST", f"/admin/versions/{t}/{eid}/submit")
    print("draft+review", t, eid, f"v{d['latest']['version']}")


for qid, typ, w, prompt, options, correct, expl in QUESTIONS:
    created("question", qid, {"module_id": "M-001", "type": typ, "prompt": prompt, "options": options, "correct": correct,
                              "explanation": expl, "competencies": [{"competency_id": "K-001", "weight": w}]})
created("assessment", "A-M-001-G", {"code": "A-M-001-G", "kind": "graded", "title": "Évaluation notée — M-001", "module_id": "M-001",
                                    "pass_threshold": 0.8, "max_attempts": 3, "catalog_type": "graded_quiz",
                                    "questions": [{"question_id": q[0], "version": 1} for q in QUESTIONS]})
m1 = call("GET", "/admin/versions/module/M-001/1")
new_version("module", "M-001", m1.get("content", m1), {"levels": ["L0", "L1"], "assessment_ids": ["A-M-001-F", "A-M-001-G"], "completion_rule": "resources_and_graded"})
for co in ("CO-001", "CO-002"):
    c1 = call("GET", f"/admin/versions/course/{co}/1")
    c1 = c1.get("content", c1)
    new_version("course", co, c1, {"module_pins": {**c1["module_pins"], "M-001": 2}})
