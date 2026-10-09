BRIDGE = {"module_recognition": "same_module_version", "accepted_evidence_types": ["graded_attempt", "project"]}

COURSES = [
    {"_id": "C01", "code": "C01", "title": "Découvrir l'IA", "profile_id": "profile-decouvrir", "levels": ["L0", "L1"],
     "summary": "Un premier cours pour comprendre, sans jargon, ce qu'est l'IA générative, comment l'interroger et comment le texte devient calcul.",
     "module_ids": ["M01", "M02", "M03"], "duration_hours": 9},
    {"_id": "C02", "code": "C02", "title": "Utiliser l'IA au quotidien", "profile_id": "profile-utiliser", "levels": ["L1", "L2"],
     "summary": "Exploiter les outils d'IA dans son métier avec méthode : formuler, préparer ses documents, s'appuyer sur des sources et protéger ses données.",
     "module_ids": ["M02", "M05", "M09", "M13"], "duration_hours": 18},
    {"_id": "C03", "code": "C03", "title": "Concevoir un assistant documentaire", "profile_id": "profile-concevoir", "levels": ["L2", "L3"],
     "summary": "Concevoir de bout en bout un assistant documentaire sourcé, du corpus à l'évaluation, appliqué aux Journaux officiels ivoiriens.",
     "module_ids": ["M03", "M04", "M06", "M07", "M08", "M09", "M10", "M11", "M14", "M16"], "duration_hours": 57},
    {"_id": "C04", "code": "C04", "title": "Piloter un projet IA", "profile_id": "profile-piloter", "levels": ["L1", "L3"],
     "summary": "Décider et gouverner : usages et limites, coûts, risques, évaluation et transformation des processus.",
     "module_ids": ["M01", "M12", "M13", "M14", "M15"], "duration_hours": 19},
]

PATHWAYS = [
    {"_id": "P01", "code": "P01", "title": "Comprendre et utiliser l'IA",
     "summary": "Pour les curieux et les utilisateurs métier : de la compréhension des mécanismes à un usage quotidien rigoureux.",
     "profile_ids": ["profile-decouvrir", "profile-utiliser"], "course_ids": ["C01", "C02", "C04"], "levels": ["L0", "L1", "L2"],
     "pathway_courses": [
         {"course_id": "C01", "group": "mandatory", "bridge": BRIDGE},
         {"course_id": "C02", "group": "mandatory", "bridge": BRIDGE},
         {"course_id": "C04", "group": "optional", "bridge": BRIDGE}],
     "target_competencies": [{"competency_id": "comp-expliquer", "level": "L1"}, {"competency_id": "comp-utiliser", "level": "L2"}]},
    {"_id": "P02", "code": "P02", "title": "Concevoir et piloter une solution IA",
     "summary": "Pour les consultants, analystes et dirigeants : concevoir un assistant documentaire et en gouverner le déploiement.",
     "profile_ids": ["profile-concevoir", "profile-piloter"], "course_ids": ["C03", "C04", "C02"], "levels": ["L1", "L2", "L3"],
     "pathway_courses": [
         {"course_id": "C03", "group": "mandatory", "bridge": BRIDGE},
         {"course_id": "C04", "group": "mandatory", "bridge": BRIDGE},
         {"course_id": "C02", "group": "optional", "bridge": BRIDGE}],
     "target_competencies": [{"competency_id": "comp-construire", "level": "L3"}, {"competency_id": "comp-evaluer", "level": "L3"},
                             {"competency_id": "comp-piloter", "level": "L3"}]},
]
