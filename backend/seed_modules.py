def r(rtype, title, minutes, sections):
    return {"type": rtype, "title": title, "duration_min": minutes,
            "sections": [{"heading": h, "body": b} for h, b in sections]}


def m(code, title, summary, objectives, prereq_text, prereq_modules, layers, stages, levels, comps, hours, resources):
    return {
        "_id": code, "code": code, "title": title, "summary": summary, "objectives": objectives,
        "prerequisites": prereq_text, "prerequisite_module_ids": prereq_modules,
        "layer_ids": [f"layer-{l}" for l in layers], "stage_ids": [f"stage-0{s}" for s in stages],
        "levels": levels, "competency_ids": [f"comp-{c}" for c in comps], "duration_hours": hours,
        "resources": resources,
    }


MODULES = [
    m("M01", "Comprendre les usages, capacités et limites",
      "Un module d'entrée, gratuit, pour situer ce que l'IA générative sait faire, ce qu'elle ne sait pas faire et les précautions à prendre avant tout usage professionnel.",
      ["Distinguer les grandes familles d'usages de l'IA en entreprise",
       "Identifier les capacités réelles d'un assistant conversationnel",
       "Reconnaître les principales limites : hallucinations, biais, données datées",
       "Adopter trois réflexes de vérification avant d'utiliser une réponse"],
      ["Aucun prérequis"], [], ["application", "securite"], [1, 7], ["L0"], ["expliquer", "utiliser"], 2,
      [r("Texte", "Ce que l'IA générative fait réellement", 12, [
          ("Un outil de production de texte probable", "Un assistant conversationnel ne consulte pas une base de vérités : il produit, token après token, la suite de texte la plus plausible au regard de sa question et de ce qu'il a appris. Cette mécanique explique à la fois sa fluidité et sa capacité à se tromper avec assurance."),
          ("Trois familles d'usages", "En contexte professionnel, on distingue la rédaction et la reformulation, la synthèse et l'analyse de documents, et l'assistance à la décision. Chaque famille appelle un niveau de vérification différent : faible pour un brouillon interne, élevé pour un avis juridique.")]),
       r("Fiche synthèse", "Les limites à connaître", 10, [
          ("Hallucinations et connaissances datées", "Le modèle peut inventer une référence ou ignorer un texte publié après son entraînement. Sans accès à des documents fournis au moment de la question, il ne peut pas garantir l'exactitude d'une information factuelle."),
          ("Confidentialité", "Toute information saisie dans un outil externe peut être conservée selon les conditions du fournisseur. Les données personnelles, stratégiques ou couvertes par le secret ne doivent être utilisées que dans un cadre validé par l'organisation.")]),
       r("Exercice guidé", "Trois réflexes de vérification", 15, [
          ("La source", "Demandez systématiquement d'où provient l'information et vérifiez que la source existe. Une réponse non sourcée est une hypothèse, pas un fait."),
          ("Le périmètre et la date", "Vérifiez que la réponse concerne bien le pays, la période et le domaine de votre question. Un texte ivoirien de 2002 ne se confond pas avec une règle actuelle."),
          ("Le contrôle humain", "Avant diffusion, une personne compétente relit et assume la réponse. L'outil assiste ; la responsabilité reste humaine.")]),
       {"type": "Vidéo", "title": "Trois minutes pour situer l'IA générative", "duration_min": 3, "video_url": None,
        "sections": [{"heading": "Transcription — de la question à la réponse", "body": "Lorsque vous posez une question à un assistant, il ne cherche pas une réponse toute faite : il calcule, mot après mot, la suite de texte la plus plausible. S'il dispose de documents fournis par l'application, il peut s'appuyer sur eux et les citer ; sinon, il s'appuie uniquement sur ce qu'il a appris."},
                     {"heading": "Transcription — ce qu'il faut retenir", "body": "Une réponse fluide n'est pas une réponse vérifiée. Demandez les sources, vérifiez le périmètre et la date, et gardez la décision finale entre des mains humaines."}]}]),

    m("M02", "Formuler des demandes et organiser le contexte",
      "Apprendre à structurer une demande — consigne, contexte, format, exemples — et à fournir à l'outil les bons éléments pour obtenir une réponse exploitable.",
      ["Structurer un prompt en consigne, contexte, contraintes et format",
       "Choisir les documents et informations à fournir au modèle",
       "Gérer la fenêtre de contexte sur une conversation longue",
       "Construire un gabarit de demande réutilisable pour son métier"],
      ["Avoir suivi M01 ou équivalent"], ["M01"], ["application", "modeles"], [1, 2], ["L0", "L1"], ["utiliser"], 3,
      [r("Texte", "Anatomie d'une bonne demande", 12, [
          ("Quatre composantes", "Une demande efficace précise la tâche (ce qu'il faut faire), le contexte (pour qui, dans quel cadre), les contraintes (sources autorisées, ton, longueur) et le format attendu (liste, tableau, note). L'omission de l'une d'elles est la première cause de réponse décevante."),
          ("Un exemple vaut mieux qu'une explication", "Montrer un exemple de résultat attendu guide le modèle plus sûrement qu'une longue description. On parle d'exemples « few-shot ».")]),
       r("Schéma commenté", "Ce qui occupe la fenêtre de contexte", 8, [
          ("Un budget partagé", "Instructions système, historique de conversation, documents ajoutés, question et réponse partagent la même fenêtre de tokens. Une conversation trop longue fait sortir les premières informations du champ du modèle."),
          ("Bonnes pratiques", "Repartir d'une conversation neuve pour un nouveau sujet, résumer les échanges utiles et ne joindre que les extraits pertinents plutôt que des documents entiers.")]),
       r("Exercice guidé", "Construire son gabarit de demande", 20, [
          ("Le cas", "Vous devez obtenir chaque semaine une synthèse des textes réglementaires publiés dans votre secteur. Rédigez un gabarit précisant la tâche, le public, les sources autorisées, la structure de la synthèse et l'obligation de citer chaque texte."),
          ("La critique", "Testez le gabarit sur deux semaines différentes et notez les écarts : informations manquantes, citations absentes, longueur excessive. Ajustez une composante à la fois.")])]),

    m("M03", "Langage, tokens et représentations",
      "Comprendre comment un texte devient une suite de nombres exploitable par un modèle : tokenisation, vocabulaire, représentations vectorielles et leurs conséquences pratiques.",
      ["Expliquer le principe de la tokenisation",
       "Estimer le nombre de tokens d'un texte et ses effets sur le coût",
       "Comprendre le passage du token à sa représentation vectorielle",
       "Identifier les spécificités du français et des textes juridiques"],
      ["M01 recommandé"], ["M01"], ["donnees", "modeles"], [2, 5], ["L1", "L2"], ["expliquer", "construire"], 4,
      [r("Texte", "Du texte aux tokens", 15, [
          ("Le découpage", "Un tokeniseur découpe le texte en fragments issus d'un vocabulaire fixe, souvent construit par fusion des séquences de caractères les plus fréquentes. Les mots courants forment un seul token ; les mots rares ou techniques sont découpés en plusieurs."),
          ("Conséquences pratiques", "Le français et les textes juridiques consomment généralement plus de tokens que l'anglais courant. Les limites de contexte et la facturation étant exprimées en tokens, cette différence a un effet direct sur le coût et la capacité.")]),
       r("Schéma commenté", "Du token au vecteur", 10, [
          ("Une table de correspondance", "Chaque identifiant de token est associé à un vecteur de plusieurs centaines ou milliers de nombres. Ces vecteurs, appris pendant l'entraînement, placent les tokens de sens proche dans des régions voisines de l'espace."),
          ("Le contexte modifie le sens", "Dans un Transformer, ces vecteurs initiaux sont ensuite transformés couche après couche selon le contexte : « avocat » ne sera pas représenté de la même façon dans un texte juridique et dans une recette.")]),
       r("Exercice guidé", "Compter et comparer", 15, [
          ("Mesure", "À l'aide d'un outil de comptage de tokens, comparez un article du Journal officiel et sa traduction anglaise. Relevez le nombre de tokens et les mots découpés en plusieurs fragments."),
          ("Interprétation", "Déduisez l'effet sur le nombre d'articles que l'on peut placer dans une fenêtre de 8 000 tokens et sur le coût d'une question.")])]),

    m("M04", "Probabilités, algèbre linéaire et optimisation",
      "Les fondements mathématiques indispensables, présentés à partir d'exemples concrets : vecteurs et similarité, distributions de probabilités, apprentissage par descente de gradient.",
      ["Manipuler vecteurs, produits scalaires et similarité cosinus",
       "Interpréter une distribution de probabilités sur des tokens",
       "Comprendre le principe de la fonction de perte",
       "Expliquer la descente de gradient sans formalisme excessif"],
      ["Mathématiques du niveau lycée"], [], ["mathematiques"], [3, 4, 5], ["L1", "L2", "L3"], ["expliquer", "construire"], 6,
      [r("Texte", "Vecteurs et similarité", 15, [
          ("Représenter par des nombres", "Un vecteur est une liste ordonnée de nombres que l'on peut voir comme une direction dans un espace. Deux textes représentés par des vecteurs peuvent être comparés par l'angle qui les sépare."),
          ("La similarité cosinus", "Le cosinus de cet angle vaut 1 pour des vecteurs alignés, 0 pour des vecteurs indépendants. C'est le score affiché à côté des documents candidats dans la démonstration.")]),
       r("Texte", "Probabilités et choix du token suivant", 12, [
          ("Une distribution sur tout le vocabulaire", "À chaque pas, le modèle attribue une probabilité à chacun des dizaines de milliers de tokens possibles. La somme vaut 1. La fonction softmax transforme les scores bruts en probabilités."),
          ("Choisir", "On peut retenir le token le plus probable ou tirer au sort selon la distribution, après l'avoir modifiée par la température.")]),
       r("Schéma commenté", "Apprendre en corrigeant ses erreurs", 15, [
          ("La fonction de perte", "Pendant l'entraînement, on mesure l'écart entre la prédiction du modèle et le token réellement attendu. Cet écart est la perte."),
          ("La descente de gradient", "On ajuste chaque paramètre d'une petite quantité dans la direction qui réduit la perte, puis on recommence sur des milliards d'exemples. C'est ainsi que les paramètres s'organisent.")])]),

    m("M05", "Données, collecte, qualité et préparation",
      "Comment constituer un corpus fiable : identification des sources, numérisation, contrôle qualité, métadonnées, découpage et documentation.",
      ["Délimiter et documenter le périmètre d'un corpus",
       "Évaluer la qualité d'un ensemble documentaire",
       "Définir les métadonnées utiles à la recherche",
       "Préparer et découper les documents pour l'indexation"],
      ["M01 recommandé"], ["M01"], ["donnees"], [3], ["L1", "L2", "L3"], ["construire", "evaluer"], 5,
      [r("Texte", "Constituer un corpus", 15, [
          ("Le périmètre", "Un corpus se définit par ses sources, sa période, sa langue et ses règles d'accès. Le documenter permet de savoir ce que le système peut et ne peut pas savoir."),
          ("La provenance", "Pour chaque document, on conserve l'origine, la date de publication, la date d'intégration et la version. Ces informations servent ensuite aux citations et aux contrôles.")]),
       r("Étude de cas", "Numériser le Journal officiel", 20, [
          ("Les difficultés", "Les numéros anciens sont souvent disponibles en image : la reconnaissance de caractères introduit des erreurs, les tableaux sont mal restitués et les colonnes peuvent se mélanger."),
          ("Les contrôles", "On mesure le taux d'erreur sur un échantillon, on corrige les pages critiques et on signale dans les métadonnées les documents de qualité insuffisante.")]),
       r("Fiche synthèse", "Indicateurs de qualité", 8, [
          ("Quatre dimensions", "Complétude (rien ne manque), exactitude (le texte est fidèle), fraîcheur (le corpus est à jour) et cohérence (les métadonnées suivent les mêmes conventions)."),
          ("Seuils", "Fixer des seuils d'acceptation avant mise en service évite de découvrir les défauts par les réponses erronées.")])]),

    m("M06", "Réseaux de neurones et Transformers",
      "Comprendre l'architecture des modèles de langage : neurones, couches, attention, entraînement et ajustement, avec des représentations visuelles plutôt que des équations.",
      ["Décrire le fonctionnement d'un réseau de neurones",
       "Expliquer le mécanisme d'attention",
       "Distinguer pré-entraînement, ajustement et alignement",
       "Situer le fine-tuning par rapport au RAG"],
      ["M03 et M04 recommandés"], ["M03", "M04"], ["modeles", "mathematiques"], [4, 5], ["L1", "L2", "L3"], ["expliquer", "construire"], 6,
      [r("Texte", "Du neurone au réseau profond", 15, [
          ("Le neurone artificiel", "Un neurone calcule une somme pondérée de ses entrées puis applique une fonction non linéaire. Empilés en couches, ces calculs simples permettent de représenter des relations complexes."),
          ("L'apprentissage", "Les poids de chaque connexion sont les paramètres du modèle. Ils sont ajustés lors de l'entraînement pour réduire l'erreur de prédiction.")]),
       r("Schéma commenté", "L'attention, cœur du Transformer", 15, [
          ("Relier les tokens entre eux", "Pour chaque token, l'attention calcule un poids pour tous les autres tokens du contexte. Le modèle peut ainsi relier « il » à « l'exportateur » mentionné trois lignes plus haut."),
          ("Plusieurs têtes, plusieurs couches", "Plusieurs têtes d'attention captent des relations différentes (syntaxe, référence, thème), et des dizaines de couches affinent progressivement la représentation.")]),
       r("Texte", "Pré-entraînement, ajustement, alignement", 12, [
          ("Trois phases", "Le pré-entraînement apprend à prédire le token suivant sur de vastes corpus. L'ajustement par instructions apprend à suivre des consignes. L'alignement oriente le comportement vers des réponses utiles et sûres."),
          ("Fine-tuning ou RAG ?", "Le fine-tuning modifie le comportement ou le style ; le RAG apporte des connaissances à jour et vérifiables. Pour un corpus juridique évolutif, le RAG est généralement prioritaire.")])]),

    m("M07", "Inférence, paramètres et modèles locaux",
      "Ce qui se passe lorsque le modèle s'exécute : réglages d'inférence, taille des modèles, quantification et exécution sur l'infrastructure de l'organisation.",
      ["Régler température et longueur de réponse selon la tâche",
       "Estimer la mémoire nécessaire à un modèle",
       "Comprendre l'intérêt et les limites de la quantification",
       "Évaluer l'opportunité d'un modèle local"],
      ["M03 recommandé"], ["M03"], ["modeles", "infrastructure"], [4, 5], ["L2", "L3"], ["construire", "evaluer"], 5,
      [r("Texte", "Les réglages d'inférence", 12, [
          ("Température et échantillonnage", "Une température basse (0 à 0,3) favorise la constance et convient aux réponses factuelles ; une température plus élevée favorise la diversité, utile en rédaction créative."),
          ("Longueur et arrêt", "La longueur maximale de réponse limite le coût et la latence. Des séquences d'arrêt et un format imposé évitent les réponses qui débordent.")]),
       r("Fiche synthèse", "Taille, mémoire et quantification", 10, [
          ("Ordre de grandeur", "En précision 16 bits, chaque milliard de paramètres occupe environ 2 Go de mémoire. Un modèle de 8 milliards de paramètres nécessite donc environ 16 Go, hors mémoire de contexte."),
          ("Quantifier", "En 4 bits, la même empreinte tombe à environ 5 Go, ce qui rend l'exécution possible sur un GPU courant, avec une perte de qualité à mesurer sur ses propres cas.")]),
       r("Étude de cas", "Héberger l'assistant CASA en interne", 18, [
          ("Le besoin", "L'organisation souhaite que les documents et les questions ne quittent pas son infrastructure."),
          ("Les arbitrages", "Un modèle local de taille moyenne, quantifié, couplé à un RAG de qualité, offre des réponses sourcées satisfaisantes. En contrepartie, l'équipe doit assurer l'exploitation, les mises à jour et la supervision.")])]),

    m("M08", "Embeddings et recherche sémantique",
      "Retrouver l'information par le sens : modèles d'embeddings, similarité, bases vectorielles et recherche hybride combinant mots-clés et sens.",
      ["Expliquer le principe des embeddings",
       "Calculer et interpréter un score de similarité",
       "Comparer recherche lexicale et recherche sémantique",
       "Paramétrer une recherche hybride"],
      ["M03 et M04 recommandés"], ["M03", "M04"], ["mathematiques", "donnees"], [3], ["L1", "L2", "L3"], ["expliquer", "construire"], 5,
      [r("Texte", "Représenter le sens", 12, [
          ("Le modèle d'embeddings", "Un modèle d'embeddings transforme un texte entier — une phrase, un article — en un vecteur unique. Il est distinct du modèle qui rédige les réponses et beaucoup plus léger."),
          ("Proximité de sens", "Des textes qui traitent du même sujet obtiennent des vecteurs proches, même s'ils n'utilisent pas les mêmes mots.")]),
       r("Schéma commenté", "Lexical, sémantique, hybride", 12, [
          ("Deux forces complémentaires", "L'index lexical est imbattable sur les numéros de décret, les dates et les noms propres. La recherche sémantique retrouve les reformulations. La recherche hybride combine les deux scores."),
          ("Le reclassement", "Un modèle de reclassement peut ensuite réordonner les vingt premiers résultats en lisant question et extrait ensemble, pour ne garder que les plus pertinents.")]),
       r("Exercice guidé", "Lire des scores de pertinence", 15, [
          ("Le jeu de données", "Cinq documents candidats sont présentés avec leur score lexical et leur score sémantique pour la question CASA."),
          ("La décision", "Choisissez un seuil et une pondération, puis justifiez quels documents vous retenez. Comparez avec la sélection de la démonstration.")])]),

    m("M09", "RAG et gestion documentaire",
      "Concevoir une chaîne de génération augmentée par la recherche : découpage, indexation, sélection des extraits, consignes de citation et contrôles de fidélité.",
      ["Décrire les étapes d'une chaîne RAG",
       "Choisir une stratégie de découpage adaptée au corpus",
       "Rédiger des consignes imposant une réponse sourcée",
       "Identifier les causes d'échec d'un RAG et y remédier"],
      ["M02 et M08 recommandés"], ["M02", "M08"], ["donnees", "application"], [3, 4, 6], ["L2", "L3"], ["construire", "utiliser"], 6,
      [r("Texte", "La chaîne RAG de bout en bout", 15, [
          ("Avant la question", "Les documents sont découpés en extraits, enrichis de métadonnées (date, type, référence), encodés en vecteurs et indexés."),
          ("Au moment de la question", "La question est analysée, la recherche hybride renvoie des candidats, les meilleurs extraits sont sélectionnés et insérés dans le prompt avec la consigne de ne répondre qu'à partir d'eux et de citer chaque source.")]),
       r("Schéma commenté", "Découper un texte réglementaire", 12, [
          ("Respecter la structure", "Un décret se découpe naturellement par article. Chaque extrait conserve le titre du texte, sa date et le numéro d'article afin d'être citable."),
          ("Éviter deux écueils", "Des extraits trop courts perdent leur contexte ; trop longs, ils diluent la pertinence et consomment la fenêtre de contexte.")]),
       r("Étude de cas", "Pourquoi un RAG échoue", 15, [
          ("Échecs de recherche", "Le bon extrait n'est pas retrouvé : vocabulaire différent, OCR défaillant, filtre de date trop strict. Le modèle répond alors sans fondement ou déclare ne pas savoir."),
          ("Échecs de génération", "Le bon extrait est fourni mais mal exploité : citation erronée, mélange de deux textes, extrapolation. Des contrôles de fidélité après génération permettent de les détecter.")]),
       r("Fiche synthèse", "Gouvernance documentaire", 8, [
          ("Versions et abrogations", "Un texte peut être modifié ou abrogé. Le corpus doit relier les textes entre eux et signaler la version en vigueur à une date donnée."),
          ("Responsabilités", "Un responsable du corpus valide les ajouts, les corrections et les retraits ; chaque modification est tracée.")])]),

    m("M10", "Architecture applicative, API et outils",
      "Comment une application orchestre modèle, données et contrôles : composants, appels d'API, gestion des droits, journalisation et intégration au système d'information.",
      ["Décrire les composants d'une application d'IA",
       "Comprendre l'appel d'un modèle par API",
       "Placer les contrôles de droits et les garde-fous",
       "Concevoir la journalisation d'une chaîne IA"],
      ["M02 et M09 recommandés"], ["M02", "M09"], ["application", "modeles"], [1, 4, 6], ["L2", "L3"], ["construire"], 5,
      [r("Schéma commenté", "Les composants d'une application d'IA", 15, [
          ("Au-delà du modèle", "Une application comprend une interface, un orchestrateur, un service de recherche, un ou plusieurs modèles, des contrôles, une journalisation et une gestion des droits. Le modèle n'est qu'un composant parmi d'autres."),
          ("L'orchestrateur", "Il enchaîne les étapes : analyse de la demande, recherche, assemblage du prompt, appel du modèle, contrôles, restitution.")]),
       r("Texte", "Appeler un modèle par API", 12, [
          ("La requête", "L'application envoie à l'API les messages (instructions système, contexte, question) et les paramètres (température, longueur maximale). Elle reçoit le texte généré et le nombre de tokens consommés."),
          ("Les contraintes", "Authentification, quotas, latence et indisponibilités doivent être gérés : délais d'attente, nouvelles tentatives, message d'erreur explicite.")]),
       r("Exercice guidé", "Placer les contrôles", 15, [
          ("Le schéma", "Sur le schéma de l'assistant CASA, positionnez le contrôle des droits, le filtrage des entrées, la vérification des citations et la journalisation."),
          ("La justification", "Expliquez pourquoi les droits doivent s'appliquer dès la recherche et non au seul affichage.")])]),

    m("M11", "Agents, orchestration et actions",
      "Passer de l'assistant qui répond à l'agent qui agit : outils, planification, boucles d'exécution et encadrement des actions.",
      ["Définir un agent et le distinguer d'un assistant",
       "Décrire l'usage d'outils par un modèle",
       "Encadrer les actions par des autorisations et validations",
       "Évaluer la pertinence d'une approche agentique"],
      ["M10 recommandé"], ["M10"], ["application", "modeles"], [4, 6], ["L2", "L3", "L4"], ["construire", "piloter"], 5,
      [r("Texte", "Qu'est-ce qu'un agent ?", 12, [
          ("Une boucle", "Un agent reçoit un objectif, choisit une action (rechercher, calculer, appeler un service), observe le résultat et décide de l'étape suivante, jusqu'à atteindre l'objectif ou une limite fixée."),
          ("Les outils", "Chaque outil est décrit au modèle par son nom, sa fonction et ses paramètres. Le modèle propose un appel ; l'application l'exécute.")]),
       r("Étude de cas", "Suivre l'évolution d'un texte", 15, [
          ("L'objectif", "Retrouver un décret de 2002, puis identifier les textes ultérieurs qui l'ont modifié ou abrogé."),
          ("Le déroulé", "L'agent recherche le texte initial, extrait sa référence, interroge l'index sur les mentions ultérieures de cette référence et produit une chronologie sourcée.")]),
       r("Fiche synthèse", "Encadrer les actions", 8, [
          ("Le principe du moindre privilège", "Un agent ne dispose que des outils strictement nécessaires, avec des droits limités."),
          ("La validation humaine", "Toute action irréversible ou engageante — envoi, paiement, modification de données — requiert une validation explicite.")])]),

    m("M12", "Infrastructure IA, GPU et coûts",
      "Comprendre le socle matériel et économique : processeurs, GPU, hébergement, consommation et modèle de coût d'un service d'IA.",
      ["Distinguer CPU et GPU et leur rôle",
       "Estimer les ressources nécessaires à un cas d'usage",
       "Comparer service externe et hébergement interne",
       "Construire un modèle de coût simple"],
      ["M01 recommandé"], ["M01"], ["infrastructure"], [4], ["L1", "L2", "L3"], ["expliquer", "evaluer", "piloter"], 4,
      [r("Texte", "CPU, GPU et calcul parallèle", 12, [
          ("Deux logiques", "Le CPU excelle dans les tâches séquentielles variées ; le GPU exécute des milliers d'opérations identiques en parallèle, ce que demandent les multiplications de matrices des modèles."),
          ("La mémoire, contrainte principale", "La taille du modèle et du contexte doit tenir dans la mémoire du GPU. C'est souvent elle, plus que la vitesse, qui détermine le matériel nécessaire.")]),
       r("Fiche synthèse", "Les composantes du coût", 10, [
          ("Coûts variables", "Avec un service externe, on paie au token : le coût croît avec le nombre de questions et la longueur des extraits transmis."),
          ("Coûts fixes", "En interne, on paie le matériel, l'énergie, l'hébergement et l'exploitation, quel que soit l'usage. Le point d'équilibre dépend du volume.")]),
       r("Exercice guidé", "Estimer le coût de l'assistant CASA", 15, [
          ("Les hypothèses", "200 questions par jour, 3 000 tokens en entrée et 400 en sortie par question."),
          ("Le calcul", "Calculez le volume mensuel de tokens, appliquez un tarif de référence et comparez au coût mensuel d'un serveur GPU. Identifiez le volume à partir duquel l'hébergement interne devient compétitif.")])]),

    m("M13", "Cybersécurité, confidentialité et risques",
      "Les risques propres aux systèmes d'IA — fuite de données, injection de consignes, contournement des droits — et les mesures pour les maîtriser.",
      ["Identifier les risques spécifiques aux systèmes d'IA",
       "Classer les données selon leur sensibilité",
       "Comprendre l'injection de consignes et ses parades",
       "Définir une politique d'usage responsable"],
      ["M01 recommandé"], ["M01"], ["securite"], [1, 3, 6], ["L1", "L2", "L3"], ["evaluer", "piloter"], 4,
      [r("Texte", "Cartographie des risques", 12, [
          ("Risques sur les données", "Fuite d'informations confidentielles vers un fournisseur, exposition de documents à des utilisateurs non autorisés, conservation non maîtrisée des échanges."),
          ("Risques sur le comportement", "Injection de consignes cachées dans un document, contournement des règles, production de contenus erronés ou inappropriés.")]),
       r("Étude de cas", "L'injection de consignes", 15, [
          ("Le mécanisme", "Un document intégré au corpus contient une phrase du type « ignore les instructions précédentes ». Si l'application la transmet au modèle sans précaution, celui-ci peut la suivre."),
          ("Les parades", "Séparer clairement instructions et contenus, filtrer les documents à l'intégration, limiter les capacités d'action et contrôler les sorties.")]),
       r("Fiche synthèse", "Politique d'usage", 8, [
          ("Classer", "Données publiques, internes, confidentielles, secrètes : à chaque classe correspondent des outils autorisés."),
          ("Former et tracer", "Les utilisateurs connaissent les règles ; les usages sont journalisés et revus périodiquement.")])]),

    m("M14", "Évaluation, fiabilité et observabilité",
      "Mesurer la qualité d'un système d'IA avant et après sa mise en service : jeux de tests, indicateurs, évaluation humaine et automatique, supervision continue.",
      ["Construire un jeu d'évaluation représentatif",
       "Choisir des indicateurs de qualité adaptés",
       "Combiner évaluation humaine et automatique",
       "Mettre en place une supervision en production"],
      ["M09 recommandé"], ["M09"], ["securite", "modeles"], [6, 7], ["L1", "L2", "L3", "L4"], ["evaluer"], 5,
      [r("Texte", "Construire un jeu d'évaluation", 15, [
          ("Représentativité", "Le jeu réunit des questions réelles, fréquentes et difficiles, avec pour chacune la réponse attendue et les extraits qui la justifient."),
          ("Stabilité", "Le même jeu est rejoué à chaque modification — corpus, prompt, modèle — pour détecter toute régression.")]),
       r("Fiche synthèse", "Indicateurs clés", 10, [
          ("Pour la recherche", "Taux de questions pour lesquelles le bon extrait figure parmi les résultats retenus (rappel)."),
          ("Pour la réponse", "Exactitude, fidélité aux sources, présence et justesse des citations, taux de refus justifiés, temps de réponse.")]),
       r("Étude de cas", "Superviser l'assistant CASA", 15, [
          ("Les traces", "Chaque réponse est associée à une trace : question, extraits, paramètres, contrôles, avis de l'utilisateur."),
          ("Le tableau de bord", "Suivi hebdomadaire des citations rejetées, des questions sans résultat et des retours négatifs, avec revue humaine d'un échantillon.")])]),

    m("M15", "Transformation des processus et création de valeur",
      "Identifier, prioriser et conduire les cas d'usage de l'IA : analyse des processus, mesure de la valeur, organisation, accompagnement du changement.",
      ["Repérer les processus où l'IA crée de la valeur",
       "Prioriser des cas d'usage selon valeur, risque et faisabilité",
       "Définir les indicateurs de valeur d'un projet",
       "Organiser la gouvernance et l'accompagnement"],
      ["M01 recommandé"], ["M01"], ["application", "securite"], [1, 7], ["L1", "L2", "L3"], ["piloter", "evaluer"], 4,
      [r("Texte", "Où l'IA crée-t-elle de la valeur ?", 12, [
          ("Analyser le processus", "La valeur se trouve rarement dans l'outil lui-même mais dans la transformation d'un processus : réduction du temps de recherche, homogénéité des analyses, accès élargi à l'expertise."),
          ("Mesurer avant", "Sans mesure de la situation initiale — temps passé, erreurs, délais — il est impossible de démontrer un gain.")]),
       r("Exercice guidé", "Prioriser ses cas d'usage", 15, [
          ("La matrice", "Évaluez cinq cas d'usage selon la valeur attendue, le niveau de risque, la disponibilité des données et la complexité technique."),
          ("La décision", "Retenez un cas pilote à valeur démontrable et à risque maîtrisé, comme l'assistant de recherche dans les Journaux officiels.")]),
       r("Fiche synthèse", "Gouvernance d'un programme IA", 8, [
          ("Les rôles", "Un sponsor métier, un responsable produit, un référent données, un référent sécurité et des utilisateurs pilotes."),
          ("Les instances", "Un comité qui arbitre les priorités, valide les mises en service et examine les incidents.")])]),

    m("M16", "Projet appliqué : assistant des Journaux officiels",
      "Projet de synthèse : concevoir de bout en bout un assistant qui répond, avec citations, aux questions portant sur les Journaux officiels de Côte d'Ivoire.",
      ["Cadrer le besoin et le périmètre documentaire",
       "Concevoir la chaîne de préparation et d'indexation du corpus",
       "Définir les consignes, contrôles et format de restitution",
       "Évaluer l'assistant et présenter ses limites"],
      ["M05, M09 et M14 recommandés"], ["M05", "M09", "M14"], ["donnees", "application", "securite"], [1, 2, 3, 4, 5, 6, 7], ["L2", "L3"], ["construire", "evaluer", "piloter"], 10,
      [r("Étude de cas", "Cadrage du projet", 20, [
          ("Le besoin", "Juristes, analystes et chercheurs passent un temps important à retrouver dans les Journaux officiels les textes applicables à une question. L'objectif est un assistant qui retrouve les extraits pertinents et formule une réponse sourcée."),
          ("Le périmètre", "Numéros du Journal officiel sur une période définie, en français, accès en lecture pour des profils identifiés, réponses informatives sans valeur de conseil juridique.")]),
       r("Texte", "Préparation du corpus", 20, [
          ("De l'image au texte structuré", "Numérisation, reconnaissance de caractères, correction des pages critiques, puis découpage par texte et par article avec date, type de texte et numéro."),
          ("Indexation", "Double indexation lexicale et vectorielle ; filtres par date et par type de texte ; liens entre textes modificatifs et textes modifiés.")]),
       r("Exercice guidé", "Concevoir la restitution", 20, [
          ("Le format", "Réponse en trois parties : synthèse, références citées avec extraits, limites et textes à vérifier."),
          ("Les contrôles", "Chaque phrase factuelle doit être rattachée à un extrait ; toute référence citée doit exister dans le corpus ; l'absence de résultat est annoncée explicitement.")]),
       r("Exercice guidé", "Évaluer et présenter", 25, [
          ("Le jeu de test", "Trente questions couvrant recherches simples, recherches par date et questions sans réponse dans le corpus."),
          ("La restitution", "Présentez les indicateurs obtenus, trois exemples d'échec analysés et les décisions proposées pour la suite.")])]),
]
