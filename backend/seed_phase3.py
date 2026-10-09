from core import BaseDocument, SEED_DATE, db, insert_missing

RUBRIC = {
    "_id": "RUB-M16@1", "rubric_id": "RUB-M16", "version": 1, "status": "published", "module_id": "M16",
    "title": "Grille d'évaluation — Projet assistant des Journaux officiels", "pass_threshold": 0.6, "level": "L3",
    "competency_ids": ["comp-construire", "comp-evaluer", "comp-piloter"], "created_at": SEED_DATE,
    "levels": [{"score": 0, "label": "Insuffisant"}, {"score": 1, "label": "Partiel"}, {"score": 2, "label": "Satisfaisant"}, {"score": 3, "label": "Exemplaire"}],
    "criteria": [
        {"id": "cadrage", "label": "Cadrage du besoin et du périmètre", "weight": 1,
         "description": "Le besoin, les utilisateurs, le périmètre documentaire et les limites (absence de conseil juridique) sont explicites."},
        {"id": "corpus", "label": "Préparation et indexation du corpus", "weight": 2,
         "description": "Numérisation, contrôle qualité, découpage par article, métadonnées et double indexation sont décrits et justifiés."},
        {"id": "restitution", "label": "Consignes, contrôles et restitution", "weight": 2,
         "description": "Les consignes imposent le sourçage ; les contrôles de citation et le format de restitution (synthèse, preuves, limites) sont définis."},
        {"id": "evaluation", "label": "Évaluation et indicateurs", "weight": 2,
         "description": "Un jeu de test représentatif, des indicateurs (rappel, fidélité, refus justifiés) et des échecs analysés sont présentés."},
        {"id": "gouvernance", "label": "Gouvernance, risques et décision", "weight": 1,
         "description": "Droits d'accès, traçabilité, coûts et décisions proposées pour la suite sont argumentés."},
    ],
}

CREDENTIALS = [
    {"_id": "CERT-FOND", "code": "CERT-FOND", "version": 1, "status": "published", "title": "Certificat Fondamentaux de l'IA",
     "summary": "Atteste la compréhension des usages, des limites et du fonctionnement des systèmes d'IA générative, ainsi qu'un usage méthodique.",
     "rules": [
         {"id": "r1", "label": "Expliquer (L0) — évaluation notée M01", "competency_id": "comp-expliquer", "min_level": "L0", "module_id": "M01", "evidence_types": ["graded_attempt"], "min_score": 0.7},
         {"id": "r2", "label": "Utiliser (L1) — évaluation notée M02", "competency_id": "comp-utiliser", "min_level": "L1", "module_id": "M02", "evidence_types": ["graded_attempt"], "min_score": 0.7},
         {"id": "r3", "label": "Expliquer (L2) — évaluation notée M03", "competency_id": "comp-expliquer", "min_level": "L2", "module_id": "M03", "evidence_types": ["graded_attempt"], "min_score": 0.7}]},
    {"_id": "CERT-CONC", "code": "CERT-CONC", "version": 1, "status": "published", "title": "Certificat Concepteur d'assistant documentaire",
     "summary": "Atteste la capacité à concevoir, évaluer et présenter un assistant documentaire sourcé fondé sur le RAG.",
     "rules": [
         {"id": "r1", "label": "Construire (L3) — évaluation notée M09", "competency_id": "comp-construire", "min_level": "L3", "module_id": "M09", "evidence_types": ["graded_attempt"], "min_score": 0.7},
         {"id": "r2", "label": "Évaluer (L3) — évaluation notée M14", "competency_id": "comp-evaluer", "min_level": "L3", "module_id": "M14", "evidence_types": ["graded_attempt"], "min_score": 0.7},
         {"id": "r3", "label": "Construire (L3) — projet appliqué M16 validé", "competency_id": "comp-construire", "min_level": "L3", "module_id": "M16", "evidence_types": ["project"], "min_score": 0.6}]},
    {"_id": "CERT-PIL", "code": "CERT-PIL", "version": 1, "status": "published", "title": "Certificat Pilotage de projet IA",
     "summary": "Atteste la capacité à évaluer les coûts et les risques d'un projet IA et à en piloter la création de valeur.",
     "rules": [
         {"id": "r1", "label": "Piloter (L3) — évaluation notée M12", "competency_id": "comp-piloter", "min_level": "L3", "module_id": "M12", "evidence_types": ["graded_attempt"], "min_score": 0.7},
         {"id": "r2", "label": "Évaluer (L3) — évaluation notée M13", "competency_id": "comp-evaluer", "min_level": "L3", "module_id": "M13", "evidence_types": ["graded_attempt"], "min_score": 0.7},
         {"id": "r3", "label": "Piloter (L3) — évaluation notée M15", "competency_id": "comp-piloter", "min_level": "L3", "module_id": "M15", "evidence_types": ["graded_attempt"], "min_score": 0.7}]},
]


async def seed_phase3():
    await insert_missing("rubrics", BaseDocument(**RUBRIC))
    for c in CREDENTIALS:
        await insert_missing("credentials", BaseDocument(**c))
    await db.awards.create_index("code", unique=True)
    await db.enrollments.create_index([("user_id", 1), ("pathway_id", 1)], unique=True)
    await db.submissions.create_index([("user_id", 1), ("module_id", 1)])
