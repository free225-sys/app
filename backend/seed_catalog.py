from core import BaseDocument, SEED_DATE, db, insert_missing

K_COMPETENCIES = [
    {"_id": "K-001", "order": 11, "kind": "referential", "category_id": "comp-expliquer", "levels": ["L0", "L1"],
     "name": "Expliquer les étapes d'un système d'IA documentaire", "description": "Expliquer les principales étapes d'un système d'IA documentaire"},
    {"_id": "K-002", "order": 12, "kind": "referential", "category_id": "comp-construire", "levels": ["L2", "L3"],
     "name": "Concevoir une chaîne de recherche augmentée", "description": "Concevoir une chaîne de recherche augmentée"},
    {"_id": "K-003", "order": 13, "kind": "referential", "category_id": "comp-evaluer", "levels": ["L1", "L2", "L3"],
     "name": "Évaluer les sources et citations générées", "description": "Évaluer les sources et citations générées"},
]

CONCEPT_MAP = {"concept-token": ("C-001", "stage-02"), "concept-embedding": ("C-002", "stage-03"), "concept-rag": ("C-003", "stage-03"),
               "concept-inference": ("C-004", "stage-04"), "concept-citation": ("C-005", "stage-06")}


def sec(*pairs):
    return [{"heading": h, "body": b} for h, b in pairs]


ASSETS = [
    ("A-001", "M-001", 1, "Exercice interactif", "Voir le chemin d'une requête", 10, sec(
        ("Suivre une question pas à pas", "Ouvrez la **démonstration interactive** et suivez la question « Quels textes régissent la commercialisation du café et du cacao ? » sur les sept étapes.\n\n- Notez à chaque étape les couches **mobilisées**.\n- Repérez l'étape où intervient la recherche documentaire.\n- Identifiez l'étape où le modèle produit le texte."),
        ("À retenir", "Une réponse d'assistant résulte d'une **chaîne de traitements** : interface, préparation, recherche éventuelle, inférence, génération, contrôles et restitution."))),
    ("A-002", "M-001", 2, "Texte", "Notions essentielles : tokens et inférence", 12, sec(
        ("Les tokens", "Le modèle ne lit pas des mots mais des **tokens**, c'est-à-dire des fragments de texte. « commercialisation » peut ainsi être découpé en plusieurs morceaux.\n\n- La longueur d'un texte se mesure en tokens.\n- Les coûts et la fenêtre de contexte s'expriment aussi en tokens."),
        ("L'inférence", "L'**inférence** est le calcul par lequel le modèle, à partir des tokens reçus, estime le token suivant le plus probable. Ce calcul mobilise les paramètres du modèle et des ressources matérielles (CPU ou GPU)."))),
    ("A-003", "M-002", 1, "Schéma commenté", "Index et recherche vectorielle", 15, sec(
        ("Deux index complémentaires", "Une chaîne RAG combine souvent :\n\n- un **index lexical**, précis sur les termes exacts et les dates ;\n- un **index vectoriel**, qui compare le sens grâce aux embeddings."),
        ("Du corpus aux extraits", "Les documents sont **découpés** en passages, encodés en vecteurs puis stockés. À la question, on calcule la similarité et on ne transmet au modèle que les **meilleurs extraits**."))),
    ("A-004", "M-002", 2, "Étude de cas", "Cas appliqué : Journal officiel ivoirien", 20, sec(
        ("Le contexte", "Les Journaux officiels de Côte d'Ivoire sont numérisés. L'objectif : répondre à des questions réglementaires en **citant l'article et le numéro** du Journal officiel."),
        ("Les choix de conception", "- Découpage par article avec métadonnées (date, numéro, ministère).\n- Recherche hybride avec seuil de pertinence.\n- Consigne imposant une réponse **sourcée**, ou un refus justifié."))),
    ("A-005", "M-003", 1, "Exercice interactif", "Contrôler les citations et les limites", 15, sec(
        ("Méthode de vérification", "Pour chaque affirmation de la réponse :\n\n1. Retrouvez l'**extrait cité**.\n2. Vérifiez que l'extrait dit bien ce qui est affirmé.\n3. Signalez toute affirmation **sans source**."),
        ("Limites à expliciter", "Une réponse responsable distingue les informations **directement sourcées**, les interprétations et les éléments non vérifiés."))),
]

MODULES = [
    {"_id": "M-001", "code": "M-001", "title": "De la requête au modèle", "level": "L0", "concepts": ["concept-token", "concept-inference"], "comps": ["K-001", "comp-expliquer"],
     "summary": "Comprendre le chemin d'une requête, de la question saisie à l'inférence du modèle.", "prereq": [], "layers": ["layer-application", "layer-donnees", "layer-modeles"],
     "stages": ["stage-01", "stage-02", "stage-04"], "assets": ["A-001", "A-002"], "assessments": ["A-M-001-F"], "rule": "resources"},
    {"_id": "M-002", "code": "M-002", "title": "Rechercher dans une base documentaire", "level": "L2", "concepts": ["concept-embedding", "concept-rag"], "comps": ["K-002", "comp-construire"],
     "summary": "Concevoir la partie recherche d'une chaîne RAG : découpage, index et sélection des extraits.", "prereq": ["M-001"], "layers": ["layer-donnees", "layer-mathematiques", "layer-modeles"],
     "stages": ["stage-03"], "assets": ["A-003", "A-004"], "assessments": ["RUB-M-002"], "rule": "resources"},
    {"_id": "M-003", "code": "M-003", "title": "Fiabiliser une réponse documentaire", "level": "L1", "concepts": ["concept-citation"], "comps": ["K-003", "comp-evaluer"],
     "summary": "Vérifier les citations, expliciter les limites et décider si une réponse peut être utilisée.", "prereq": [], "layers": ["layer-application", "layer-securite"],
     "stages": ["stage-06", "stage-07"], "assets": ["A-005"], "assessments": ["A-M-003-G"], "rule": None},
]

Q = lambda qid, mid, prompt, opts, correct, expl, comps: {  # noqa: E731
    "_id": f"{qid}@1", "question_id": qid, "entity_id": qid, "version": 1, "status": "published", "module_id": mid,
    "type": "multiple" if len(correct) > 1 else "single", "prompt": prompt, "options": [{"id": "abcd"[i], "text": t} for i, t in enumerate(opts)],
    "correct": correct, "explanation": expl, "competencies": comps}
K1, K3 = {"competency_id": "K-001", "weight": 1}, {"competency_id": "K-003", "weight": 2}
QUESTIONS = {
    "A-M-001-F": [
        Q("Q-M-001-F1", "M-001", "Qu'est-ce qu'un token ?", ["Un fragment de texte traité par le modèle", "Un mot de passe", "Un document source"], ["a"], "Le modèle découpe le texte en tokens avant de le traiter.", [K1]),
        Q("Q-M-001-F2", "M-001", "À quelle étape le modèle calcule-t-il la suite la plus probable ?", ["Restitution", "Inférence", "Demande"], ["b"], "L'inférence mobilise les paramètres du modèle pour estimer le token suivant.", [K1]),
        Q("Q-M-001-F3", "M-001", "La recherche documentaire (RAG) est-elle présente dans tous les assistants ?", ["Oui, toujours", "Non, elle est ajoutée quand une source doit être exploitée"], ["b"], "Le RAG est une brique applicative ajoutée selon le cas d'usage.", [K1]),
    ],
    "A-M-003-G": [
        Q("Q-M-003-G1", "M-003", "Une réponse fluide et assurée est-elle une preuve d'exactitude ?", ["Oui", "Non"], ["b"], "La fluidité ne garantit pas la vérité : il faut relier les affirmations aux sources.", [K3, K1]),
        Q("Q-M-003-G2", "M-003", "Que faire d'une affirmation sans extrait cité ?", ["La présenter comme certaine", "La signaler comme non vérifiée", "La supprimer de la source"], ["b"], "Une réponse responsable distingue ce qui est sourcé de ce qui ne l'est pas.", [K3]),
        Q("Q-M-003-G3", "M-003", "Quels éléments vérifier pour une citation du Journal officiel ? (plusieurs réponses)", ["Le numéro et la date du Journal", "L'article cité", "La couleur de l'interface", "La concordance entre l'extrait et l'affirmation"], ["a", "b", "d"], "La référence complète et la concordance du contenu sont nécessaires.", [K3, K1]),
        Q("Q-M-003-G4", "M-003", "Les contrôles applicatifs garantissent-ils automatiquement la vérité ?", ["Oui", "Non, ils réduisent les risques sans les supprimer"], ["b"], "Les contrôles sont conçus dans l'application et ont des limites.", [K3]),
        Q("Q-M-003-G5", "M-003", "À quelle étape les citations sont-elles vérifiées dans le scénario CASA ?", ["Contrôles", "Demande", "Tokenisation"], ["a"], "L'étape 6 (Contrôles) vérifie citations, droits et règles.", [K3, K1]),
    ],
}

RUBRIC = {"_id": "RUB-M-002@1", "rubric_id": "RUB-M-002", "catalog_id": "Q-002", "version": 1, "status": "published", "module_id": "M-002",
          "title": "Grille — Projet chaîne de recherche augmentée", "pass_threshold": 0.6, "level": "L2", "competency_ids": ["K-002"], "created_at": SEED_DATE,
          "levels": [{"score": 0, "label": "Insuffisant"}, {"score": 1, "label": "Partiel"}, {"score": 2, "label": "Satisfaisant"}, {"score": 3, "label": "Exemplaire"}],
          "criteria": [{"id": "corpus", "label": "Préparation du corpus", "weight": 1, "description": "Découpage, métadonnées et qualité des documents sont décrits."},
                       {"id": "index", "label": "Choix des index", "weight": 2, "description": "Index lexical et vectoriel justifiés, seuil de pertinence défini."},
                       {"id": "evaluation", "label": "Évaluation de la recherche", "weight": 1, "description": "Jeu de questions test et indicateurs de rappel présentés."}]}

BRIDGE = {"module_recognition": "same_module_version", "accepted_evidence_types": ["graded_attempt", "project"]}
COURSES = [
    {"_id": "CO-001", "title": "Comprendre une IA documentaire", "modules": ["M-001", "M-003"], "levels": ["L0", "L1"], "profile_id": "profile-decouvrir",
     "summary": "Comprendre le chemin d'une requête documentaire et apprendre à fiabiliser la réponse obtenue."},
    {"_id": "CO-002", "title": "Construire et évaluer un RAG", "modules": ["M-001", "M-002", "M-003"], "levels": ["L0", "L1", "L2"], "profile_id": "profile-concevoir",
     "summary": "De la requête au modèle, concevoir la recherche documentaire puis évaluer les citations produites."},
]
PATHWAYS = [
    {"_id": "P-001", "title": "Découverte / utilisateur", "courses": ["CO-001"], "profiles": ["profile-decouvrir", "profile-utiliser"], "levels": ["L0", "L1"],
     "summary": "Un parcours court pour comprendre une IA documentaire et vérifier ses réponses.", "targets": [("K-001", "L1"), ("K-003", "L1")]},
    {"_id": "P-002", "title": "Consultant / concepteur", "courses": ["CO-001", "CO-002"], "profiles": ["profile-concevoir"], "levels": ["L0", "L1", "L2"],
     "summary": "Comprendre, concevoir puis évaluer une chaîne de recherche augmentée.", "targets": [("K-001", "L1"), ("K-002", "L2"), ("K-003", "L1")]},
]
CREDENTIAL = {"_id": "CERT-DOC-01", "code": "CERT-DOC-01", "title": "Fondamentaux de l'IA documentaire",
              "summary": "Atteste la capacité à expliquer les étapes d'un système d'IA documentaire et à évaluer les sources et citations générées.",
              "rules": [{"id": "r1", "label": "K-001 Expliquer les étapes d'un système d'IA documentaire (L1)", "competency_id": "K-001", "min_level": "L1", "module_id": None,
                         "evidence_types": ["graded_attempt", "project"], "min_score": 0},
                        {"id": "r2", "label": "K-003 Évaluer les sources et citations générées (L1)", "competency_id": "K-003", "min_level": "L1", "module_id": None,
                         "evidence_types": ["graded_attempt", "project"], "min_score": 0},
                        {"id": "r3", "kind": "assessment_passed", "label": "Évaluation notée Q-003 réussie (80 %)", "assessment_id": "A-M-003-G", "competency_id": None, "module_id": "M-003"}]}


async def versioned(entity: str, versions: str, eid: str, content: dict, entity_extra: dict = None, projection=False):
    vdoc = BaseDocument(_id=f"{eid}@1", entity_id=eid, version=1, status="published", approved=True, changelog="Import du catalogue exemple",
                        created_at=SEED_DATE, published_at=SEED_DATE, reviews=[], **content)
    await insert_missing(versions, vdoc)
    base = {**content, "version": 1, "status": "published"} if projection else {"code": eid, "created_at": SEED_DATE, "updated_at": SEED_DATE, **(entity_extra or {})}
    await insert_missing(entity, BaseDocument(_id=eid, published_version=1, latest_version=1, **base))


async def seed_catalog():
    for k in K_COMPETENCIES:
        await insert_missing("competencies", BaseDocument(**k))
    async for c in db.concepts.find({"primary_stage": {"$exists": False}}):
        await db.concepts.update_one({"_id": c["_id"]}, {"$set": {"primary_stage": (c.get("stage_ids") or [None])[0]}})
    async for c in db.concept_versions.find({"primary_stage": {"$exists": False}}):
        await db.concept_versions.update_one({"_id": c["_id"]}, {"$set": {"primary_stage": (c.get("stage_ids") or [None])[0]}})
    for cid, (cat, stage) in CONCEPT_MAP.items():
        await db.concepts.update_one({"_id": cid}, {"$set": {"catalog_id": cat, "primary_stage": stage}})
        await db.concept_versions.update_many({"entity_id": cid}, {"$set": {"catalog_id": cat, "primary_stage": stage}})
    for aid, mid, order, typ, title, minutes, sections in ASSETS:
        await versioned("resources", "resource_versions", aid, {"module_id": mid, "order": order, "type": typ, "title": title, "duration_min": minutes, "sections": sections}, projection=True)
    for m in MODULES:
        content = {"code": m["code"], "title": m["title"], "summary": m["summary"], "objectives": [], "prerequisites": ["M-001 recommandé"] if m["prereq"] else ["Aucun prérequis"],
                   "prerequisite_module_ids": m["prereq"], "layer_ids": m["layers"], "stage_ids": m["stages"], "levels": [m["level"]], "competency_ids": m["comps"],
                   "duration_hours": 2, "resource_ids": m["assets"], "assessment_ids": m["assessments"], "completion_rule": m["rule"]}
        await versioned("modules", "module_versions", m["_id"], content)
        for cid in m["concepts"]:
            await db.concepts.update_one({"_id": cid}, {"$addToSet": {"module_ids": m["_id"]}})
            await db.concept_versions.update_many({"entity_id": cid, "status": "published"}, {"$addToSet": {"module_ids": m["_id"]}})
    for aid, qs in QUESTIONS.items():
        for q in qs:
            await insert_missing("questions", BaseDocument(**q))
            await insert_missing("question_bank", BaseDocument(_id=q["question_id"], code=q["question_id"], module_id=q["module_id"], published_version=1, latest_version=1, created_at=SEED_DATE))
        graded = aid.endswith("-G")
        meta = {"code": aid, "kind": "graded" if graded else "formative", "module_id": qs[0]["module_id"], "title": f"{'Évaluation notée' if graded else 'Quiz formatif'} — {qs[0]['module_id']}",
                "pass_threshold": 0.8 if graded else None, "max_attempts": 3 if graded else None, "catalog_id": "Q-003" if graded else "Q-001",
                "catalog_type": "graded_quiz" if graded else "practice_quiz"}
        await versioned("assessments", "assessment_versions", aid, {**meta, "questions": [{"question_id": q["question_id"], "version": 1} for q in qs]}, meta)
    await insert_missing("rubrics", BaseDocument(**RUBRIC))
    for c in COURSES:
        await versioned("courses", "course_versions", c["_id"], {"code": c["_id"], "title": c["title"], "summary": c["summary"], "profile_id": c["profile_id"], "levels": c["levels"],
                                                                 "module_ids": c["modules"], "module_pins": {m: 1 for m in c["modules"]}, "optional_module_ids": [], "duration_hours": 2 * len(c["modules"])})
    for p in PATHWAYS:
        await versioned("pathways", "pathway_versions", p["_id"], {
            "code": p["_id"], "title": p["title"], "summary": p["summary"], "profile_ids": p["profiles"], "levels": p["levels"], "course_ids": p["courses"],
            "pathway_courses": [{"course_id": c, "course_version": 1, "group": "mandatory", "bridge": BRIDGE} for c in p["courses"]],
            "target_competencies": [{"competency_id": k, "level": lv} for k, lv in p["targets"]]})
    await versioned("credentials", "credential_versions", CREDENTIAL["_id"], {k: v for k, v in CREDENTIAL.items() if k != "_id"}, projection=True)
