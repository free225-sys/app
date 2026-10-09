from core import EntityVersion, SEED_DATE, VersionedEntity, db, insert_missing, BaseDocument

PASS_THRESHOLD = 0.7
MAX_ATTEMPTS = 3

# (énoncé, options, lettres correctes, explication, compétences "comp:poids+comp")
Q = {
    "M01": {
        "G": [
            ("Comment un assistant conversationnel produit-il sa réponse ?",
             ["Il recopie une réponse stockée dans une base de vérités", "Il calcule, token après token, la suite de texte la plus plausible", "Il interroge systématiquement internet"],
             "b", "Le modèle prédit séquentiellement les tokens les plus probables ; c'est ce qui explique sa fluidité et ses erreurs possibles.", "expliquer:2"),
            ("Qu'est-ce qu'une hallucination ?",
             ["Une réponse plausible mais non fondée ou fausse", "Un refus de répondre", "Une réponse trop longue"],
             "a", "Une hallucination est un contenu plausible sans fondement dans les sources, par exemple une référence inventée.", "expliquer"),
            ("Quels réflexes adopter avant d'utiliser une réponse dans un document professionnel ? (plusieurs réponses)",
             ["Vérifier que la source citée existe", "Vérifier la période et le pays concernés", "Diffuser tel quel si la réponse est bien rédigée", "Faire relire par une personne compétente"],
             "abd", "Source, périmètre et contrôle humain sont les trois réflexes de vérification ; la qualité rédactionnelle ne garantit pas l'exactitude.", "utiliser:2"),
            ("Vous devez analyser une note interne confidentielle. Que faites-vous ?",
             ["Je la colle dans n'importe quel outil gratuit", "J'utilise uniquement un outil validé par mon organisation pour ce type de données", "Je supprime les titres et je la colle dans l'outil"],
             "b", "Les données confidentielles ne doivent être traitées que dans un cadre validé ; retirer les titres ne suffit pas à protéger le contenu.", "utiliser"),
            ("Pourquoi un modèle peut-il ignorer un texte publié récemment ?",
             ["Parce que ses connaissances s'arrêtent à la date de son entraînement", "Parce qu'il refuse les textes juridiques", "Parce que les textes récents sont plus longs"],
             "a", "Sans documents fournis au moment de la question, le modèle ne connaît que ce qu'il a appris avant la fin de son entraînement.", "expliquer+utiliser"),
        ],
        "F": [
            ("Une réponse fluide et bien structurée est-elle forcément exacte ?", ["Oui", "Non"], "b", "La fluidité est une propriété du texte, pas une garantie de vérité.", "expliquer"),
            ("Quelle famille d'usages appelle le niveau de vérification le plus élevé ?", ["Un brouillon interne", "Un avis juridique transmis à un client", "Une reformulation d'e-mail"], "b", "Plus l'enjeu est élevé, plus la vérification doit être rigoureuse.", "utiliser"),
            ("Qui porte la responsabilité d'une réponse diffusée ?", ["L'outil d'IA", "La personne ou l'organisation qui la diffuse", "Le fournisseur du modèle"], "b", "L'outil assiste ; la responsabilité reste humaine.", "utiliser"),
        ],
    },
    "M02": {
        "G": [
            ("Quelles sont les composantes d'une demande efficace ? (plusieurs réponses)",
             ["La tâche", "Le contexte", "Les contraintes", "Le format attendu"], "abcd", "Tâche, contexte, contraintes et format : l'omission de l'un d'eux dégrade la réponse.", "utiliser:2"),
            ("À quoi sert un exemple de résultat attendu dans un prompt ?",
             ["À guider le modèle vers la forme souhaitée", "À augmenter la température", "À réduire la fenêtre de contexte à zéro"], "a", "Les exemples (« few-shot ») guident le modèle plus sûrement qu'une longue description.", "utiliser"),
            ("Que se passe-t-il quand une conversation devient très longue ?",
             ["Le modèle retient tout indéfiniment", "Les premières informations peuvent sortir de la fenêtre de contexte", "Le modèle devient plus précis"], "b", "La fenêtre de contexte est limitée : ce qui dépasse n'est plus pris en compte.", "utiliser"),
            ("Pour un nouveau sujet sans lien avec le précédent, il vaut mieux :",
             ["Continuer la même conversation", "Ouvrir une nouvelle conversation", "Répéter la question trois fois"], "b", "Repartir d'un contexte propre évite les interférences et économise la fenêtre.", "utiliser"),
            ("Quelle consigne favorise une réponse vérifiable ?",
             ["« Sois créatif »", "« Cite le texte et l'article pour chaque affirmation »", "« Réponds le plus vite possible »"], "b", "Exiger une citation par affirmation rend la réponse contrôlable.", "utiliser:2"),
        ],
        "F": [
            ("Joindre un document entier est-il toujours préférable à des extraits ciblés ?", ["Oui", "Non"], "b", "Des extraits pertinents économisent la fenêtre et améliorent la précision.", "utiliser"),
            ("Que précise la composante « format » d'une demande ?", ["Le public visé", "La forme du résultat : liste, tableau, note", "Les sources autorisées"], "b", "Le format décrit la forme attendue du résultat.", "utiliser"),
            ("Comment améliorer un gabarit de demande ?", ["Modifier une composante à la fois et comparer", "Tout réécrire à chaque essai", "Ne jamais le tester"], "a", "Ajuster une composante à la fois permet d'identifier ce qui fonctionne.", "utiliser"),
        ],
    },
    "M03": {
        "G": [
            ("Qu'est-ce qu'un token ?",
             ["Un fragment de texte associé à un identifiant numérique", "Un mot de passe", "Une phrase complète"], "a", "Le token est l'unité élémentaire manipulée par le modèle.", "expliquer:2"),
            ("Pourquoi les textes juridiques français consomment-ils souvent plus de tokens ?",
             ["Les mots techniques et rares sont découpés en plusieurs fragments", "Le français est interdit dans les modèles", "Les accents sont supprimés"], "a", "Les vocabulaires de tokens favorisent les séquences fréquentes ; les termes rares sont fragmentés.", "expliquer"),
            ("En quoi le nombre de tokens a-t-il un effet pratique ? (plusieurs réponses)",
             ["Il conditionne le coût", "Il conditionne ce qui tient dans la fenêtre de contexte", "Il détermine la couleur de l'interface"], "ab", "Facturation et limites de contexte s'expriment en tokens.", "construire+expliquer"),
            ("Dans un Transformer, la représentation d'un token :",
             ["Est fixe quel que soit le contexte", "Est transformée couche après couche selon le contexte", "Est choisie au hasard à chaque question"], "b", "Les vecteurs initiaux sont enrichis par le contexte à chaque couche.", "expliquer"),
            ("Vous estimez qu'un article fait 600 tokens. Combien d'articles entiers tiennent dans une fenêtre de 8 000 tokens si les consignes en occupent 800 ?",
             ["Environ 12", "Environ 20", "Environ 4"], "a", "(8 000 − 800) / 600 ≈ 12 articles, sans compter la réponse à produire.", "construire:2"),
        ],
        "F": [
            ("Un mot peut-il correspondre à plusieurs tokens ?", ["Oui", "Non"], "a", "Les mots rares ou longs sont découpés en sous-mots.", "expliquer"),
            ("Que reçoit réellement le modèle ?", ["Des lettres", "Des identifiants numériques de tokens", "Des images du texte"], "b", "Le texte est converti en suite d'identifiants.", "expliquer"),
            ("Les tokens proches par le sens ont des vecteurs :", ["Éloignés", "Voisins", "Identiques"], "b", "L'entraînement place les tokens de sens proche dans des régions voisines.", "expliquer"),
        ],
    },
    "M04": {
        "G": [
            ("Que vaut la similarité cosinus de deux vecteurs parfaitement alignés ?", ["0", "1", "−1"], "b", "Des vecteurs de même direction ont un cosinus de 1.", "expliquer:2"),
            ("La somme des probabilités attribuées à tous les tokens possibles vaut :", ["100", "1", "Elle varie"], "b", "Une distribution de probabilités somme à 1.", "expliquer"),
            ("À quoi sert la fonction softmax ?", ["À transformer des scores bruts en probabilités", "À supprimer des tokens", "À compresser le modèle"], "a", "Softmax normalise les scores en une distribution de probabilités.", "expliquer+construire"),
            ("Que mesure la fonction de perte pendant l'entraînement ?", ["La vitesse du GPU", "L'écart entre la prédiction et la réponse attendue", "Le nombre de paramètres"], "b", "La perte quantifie l'erreur de prédiction à réduire.", "construire"),
            ("Comment la descente de gradient ajuste-t-elle les paramètres ?", ["Au hasard", "Dans la direction qui réduit la perte", "En les remettant à zéro"], "b", "Chaque paramètre est modifié d'une petite quantité dans le sens qui diminue l'erreur.", "construire:2"),
        ],
        "F": [
            ("Un vecteur est :", ["Une liste ordonnée de nombres", "Un mot clé", "Un fichier"], "a", "On peut le voir comme une direction dans un espace.", "expliquer"),
            ("Deux vecteurs indépendants ont une similarité cosinus proche de :", ["1", "0", "10"], "b", "Un angle droit donne un cosinus nul.", "expliquer"),
            ("Une température plus élevée rend la distribution :", ["Plus étalée", "Plus concentrée", "Inchangée"], "a", "La température élevée donne plus de chances aux tokens moins probables.", "expliquer"),
        ],
    },
    "M05": {
        "G": [
            ("Quels éléments définissent le périmètre d'un corpus ? (plusieurs réponses)", ["Les sources", "La période", "Les règles d'accès", "La couleur du logo"], "abc", "Sources, période, langue et règles d'accès délimitent ce que le système peut savoir.", "construire:2"),
            ("Pourquoi conserver la date de publication de chaque document ?", ["Pour les citations et les contrôles de date", "Pour accélérer le GPU", "Ce n'est pas utile"], "a", "La provenance alimente les citations et la vérification du périmètre.", "construire"),
            ("Quel risque principal présente la numérisation de numéros anciens ?", ["Des erreurs de reconnaissance de caractères", "Une consommation électrique excessive", "Une perte de droits d'auteur"], "a", "L'OCR introduit des erreurs qui empêchent de retrouver le texte.", "evaluer"),
            ("Quelle dimension de qualité vérifie que le corpus est à jour ?", ["Complétude", "Fraîcheur", "Cohérence"], "b", "La fraîcheur mesure l'actualité du corpus.", "evaluer:2"),
            ("Quand fixer les seuils de qualité ?", ["Avant la mise en service", "Après les premières plaintes", "Jamais"], "a", "Des seuils définis à l'avance évitent de découvrir les défauts par les réponses erronées.", "evaluer"),
        ],
        "F": [
            ("Une réponse peut-elle être plus fiable que les données qui la fondent ?", ["Oui", "Non"], "b", "La qualité des données borne la fiabilité des réponses.", "evaluer"),
            ("Que faire d'une page de qualité insuffisante ?", ["L'ignorer silencieusement", "La signaler dans les métadonnées et la corriger si critique", "La dupliquer"], "b", "Signaler et corriger les pages critiques préserve la confiance.", "construire"),
            ("La cohérence des métadonnées signifie :", ["Des conventions identiques pour tous les documents", "Des documents tous de même longueur", "Un seul auteur"], "a", "Des conventions homogènes rendent les filtres fiables.", "evaluer"),
        ],
    },
    "M06": {
        "G": [
            ("Que calcule un neurone artificiel ?", ["Une somme pondérée suivie d'une fonction non linéaire", "Une recherche dans une base", "Un tri alphabétique"], "a", "C'est l'opération élémentaire des réseaux de neurones.", "expliquer:2"),
            ("Quel est le rôle du mécanisme d'attention ?", ["Pondérer l'importance de chaque token pour les autres", "Compresser le modèle", "Chiffrer les données"], "a", "L'attention relie les tokens entre eux selon leur pertinence mutuelle.", "expliquer"),
            ("Quelles sont les phases de construction d'un assistant ? (plusieurs réponses)", ["Pré-entraînement", "Ajustement par instructions", "Alignement", "Indexation lexicale"], "abc", "L'indexation relève de la recherche documentaire, pas de l'entraînement du modèle.", "expliquer+construire"),
            ("Pour un corpus juridique qui évolue chaque mois, on privilégie :", ["Le fine-tuning mensuel", "Le RAG", "Une température élevée"], "b", "Le RAG apporte des connaissances à jour et vérifiables.", "construire:2"),
            ("Les paramètres d'un modèle sont :", ["Les poids ajustés pendant l'entraînement", "Les questions des utilisateurs", "Les réglages de l'écran"], "a", "Ils déterminent le comportement appris du modèle.", "expliquer"),
        ],
        "F": [
            ("Plusieurs têtes d'attention servent à :", ["Capter des relations différentes", "Accélérer internet", "Stocker les documents"], "a", "Syntaxe, référence, thème : chaque tête peut se spécialiser.", "expliquer"),
            ("Le pré-entraînement apprend principalement à :", ["Prédire le token suivant", "Classer des images", "Répondre poliment"], "a", "C'est l'objectif de base des modèles de langage.", "expliquer"),
            ("Le fine-tuning modifie surtout :", ["Le style et le comportement", "Le contenu du Journal officiel", "Le matériel"], "a", "Il adapte le comportement, sans garantir des connaissances à jour.", "construire"),
        ],
    },
    "M07": {
        "G": [
            ("Quelle température convient à une réponse juridique sourcée ?", ["0,2", "1,5", "2,0"], "a", "Une température basse favorise la constance factuelle.", "construire:2"),
            ("En 16 bits, combien de mémoire occupe environ un modèle de 8 milliards de paramètres ?", ["2 Go", "16 Go", "160 Go"], "b", "Environ 2 Go par milliard de paramètres en 16 bits.", "evaluer"),
            ("Quel est l'effet de la quantification en 4 bits ?", ["Moins de mémoire, légère perte de qualité possible", "Plus de mémoire et plus de qualité", "Aucun effet"], "a", "On gagne en mémoire et vitesse au prix d'une dégradation à mesurer.", "evaluer:2"),
            ("Quels avantages offre un modèle local ? (plusieurs réponses)", ["Les données restent dans l'organisation", "Aucune exploitation à assurer", "Une maîtrise de l'hébergement"], "ac", "Le modèle local apporte la maîtrise des données, mais impose une exploitation.", "construire+evaluer"),
            ("La longueur maximale de réponse permet de :", ["Limiter coût et latence", "Augmenter la créativité", "Changer de modèle"], "a", "Moins de tokens générés, moins de coût et de temps.", "construire"),
        ],
        "F": [
            ("Pendant l'inférence, le modèle apprend-il ?", ["Oui", "Non"], "b", "Ses paramètres restent inchangés.", "construire"),
            ("Une séquence d'arrêt sert à :", ["Interrompre la génération à un repère défini", "Relancer l'entraînement", "Supprimer la mémoire"], "a", "Elle évite les réponses qui débordent.", "construire"),
            ("Qui doit mesurer la perte de qualité due à la quantification ?", ["L'équipe, sur ses propres cas", "Personne", "Le fournisseur uniquement"], "a", "L'effet dépend des tâches : il faut le mesurer sur ses cas.", "evaluer"),
        ],
    },
    "M08": {
        "G": [
            ("Un modèle d'embeddings transforme un texte en :", ["Un vecteur", "Une image", "Un résumé"], "a", "Le vecteur représente le sens du texte.", "expliquer:2"),
            ("Pour retrouver « décret n° 2002-xxx », quelle recherche est la plus fiable ?", ["Lexicale", "Sémantique seule", "Aucune"], "a", "L'index lexical excelle sur les numéros et termes exacts.", "construire"),
            ("Que combine la recherche hybride ?", ["Scores lexical et sémantique", "Texte et images", "Deux langues"], "a", "Elle tire parti des deux forces complémentaires.", "construire:2"),
            ("À quoi sert un modèle de reclassement ?", ["Réordonner les meilleurs résultats en lisant question et extrait ensemble", "Supprimer les doublons du corpus", "Traduire les extraits"], "a", "Le reclassement affine la sélection finale.", "construire"),
            ("Une question sur la « vente du cacao » retrouve un article sur sa « commercialisation ». C'est l'effet :", ["De la recherche sémantique", "De l'index lexical", "Du hasard"], "a", "La recherche sémantique retrouve les reformulations.", "expliquer"),
        ],
        "F": [
            ("Le modèle d'embeddings est-il le même que celui qui rédige ?", ["Oui", "Non"], "b", "C'est un modèle distinct, plus léger.", "expliquer"),
            ("Un seuil de similarité trop bas risque de :", ["Retenir des documents peu pertinents", "Ne rien retenir", "Accélérer le GPU"], "a", "Un seuil bas laisse passer du bruit.", "construire"),
            ("Les scores de la démonstration combinent :", ["Lexical et sémantique", "Prix et date", "Auteur et titre"], "a", "Score combiné = pondération des deux.", "expliquer"),
        ],
    },
    "M09": {
        "G": [
            ("Dans quel ordre se déroule une chaîne RAG au moment de la question ?", ["Génération puis recherche", "Analyse, recherche, sélection des extraits, génération", "Entraînement puis génération"], "b", "On cherche d'abord, puis on génère à partir des extraits.", "construire:2"),
            ("Comment découper un décret pour le rendre citable ?", ["Par article, en conservant titre, date et numéro", "Par blocs de 50 caractères", "Ne pas le découper"], "a", "Respecter la structure garde le contexte et la référence.", "construire"),
            ("Quelles causes relèvent d'un échec de recherche ? (plusieurs réponses)", ["OCR défaillant", "Filtre de date trop strict", "Mélange de deux textes par le modèle"], "ab", "Le mélange de textes est un échec de génération, pas de recherche.", "construire+utiliser"),
            ("Quelle consigne impose une réponse sourcée ?", ["« Réponds uniquement à partir des extraits et cite chaque source »", "« Réponds avec tes connaissances »", "« Sois bref »"], "a", "La consigne cadre le modèle sur les extraits fournis.", "utiliser:2"),
            ("Un texte a été abrogé depuis. Que doit permettre le corpus ?", ["Signaler la version en vigueur à une date donnée", "Supprimer toute trace du texte", "Rien de particulier"], "a", "Les liens entre textes et versions évitent des réponses obsolètes.", "construire"),
        ],
        "F": [
            ("Le RAG remplace-t-il la nécessité de contrôler les citations ?", ["Oui", "Non"], "b", "Des contrôles de fidélité restent nécessaires.", "utiliser"),
            ("Des extraits trop longs :", ["Diluent la pertinence et consomment la fenêtre", "Améliorent toujours la réponse", "Sont impossibles"], "a", "Il faut équilibrer contexte et précision.", "construire"),
            ("Qui valide les ajouts au corpus ?", ["Un responsable du corpus", "Le modèle", "Personne"], "a", "La gouvernance documentaire suppose un responsable identifié.", "construire"),
        ],
    },
    "M10": {
        "G": [
            ("Le modèle est-il le seul composant d'une application d'IA ?", ["Oui", "Non, il y a aussi interface, orchestrateur, recherche, contrôles, journalisation"], "b", "Le modèle n'est qu'un composant parmi d'autres.", "construire:2"),
            ("Que renvoie typiquement l'API d'un modèle ?", ["Le texte généré et le nombre de tokens consommés", "Les paramètres du modèle", "Le corpus entier"], "a", "Ces informations servent à l'affichage et au suivi des coûts.", "construire"),
            ("Où appliquer les droits d'accès dans un assistant documentaire ?", ["Dès la recherche", "Uniquement à l'affichage", "Nulle part"], "a", "Filtrer dès la recherche évite d'exposer un extrait non autorisé au modèle.", "construire:2"),
            ("Quelles mesures gèrent une indisponibilité de l'API ? (plusieurs réponses)", ["Délai d'attente", "Nouvelle tentative", "Message d'erreur explicite", "Augmenter la température"], "abc", "La température n'a aucun rapport avec la résilience.", "construire"),
            ("Le rôle de l'orchestrateur est :", ["D'enchaîner les étapes du traitement", "D'entraîner le modèle", "De numériser les documents"], "a", "Il coordonne analyse, recherche, appel, contrôles et restitution.", "construire"),
        ],
        "F": [
            ("La journalisation sert à :", ["Reconstituer le traitement d'une requête", "Décorer l'interface", "Réduire la latence"], "a", "Elle permet audit et amélioration.", "construire"),
            ("Les paramètres envoyés à l'API incluent :", ["Température et longueur maximale", "Le mot de passe de l'utilisateur", "Le corpus complet"], "a", "Ce sont les réglages d'inférence.", "construire"),
            ("Les instructions système sont rédigées par :", ["L'application", "L'utilisateur final", "Le fournisseur de GPU"], "a", "Elles cadrent le comportement attendu.", "construire"),
        ],
    },
    "M11": {
        "G": [
            ("Qu'est-ce qui distingue un agent d'un assistant ?", ["Il enchaîne des actions avec des outils pour atteindre un objectif", "Il écrit plus vite", "Il n'utilise pas de modèle"], "a", "Planifier, agir, observer, ajuster : c'est la boucle de l'agent.", "construire:2"),
            ("Qui exécute réellement l'appel d'outil ?", ["Le modèle", "L'application", "L'utilisateur"], "b", "Le modèle propose ; l'application exécute.", "construire"),
            ("Quelles actions exigent une validation humaine ? (plusieurs réponses)", ["Un envoi engageant", "Un paiement", "Une recherche dans l'index public"], "ab", "Les actions irréversibles ou engageantes doivent être validées.", "piloter:2"),
            ("Le principe du moindre privilège signifie :", ["Ne donner à l'agent que les outils et droits strictement nécessaires", "Donner tous les droits pour gagner du temps", "Ne jamais utiliser d'outil"], "a", "Cela limite l'impact d'une erreur ou d'un détournement.", "piloter"),
            ("Pour suivre les modifications d'un décret, l'agent doit d'abord :", ["Retrouver le texte initial et sa référence", "Rédiger la conclusion", "Augmenter la température"], "a", "La référence sert ensuite à rechercher les textes ultérieurs.", "construire"),
        ],
        "F": [
            ("Un agent doit-il avoir une limite d'étapes ?", ["Oui", "Non"], "a", "Une limite évite les boucles sans fin et maîtrise les coûts.", "piloter"),
            ("Chaque outil est décrit au modèle par :", ["Nom, fonction et paramètres", "Sa couleur", "Son prix"], "a", "Cette description permet au modèle de proposer un appel.", "construire"),
            ("Une approche agentique est-elle toujours préférable ?", ["Oui", "Non, seulement si le besoin exige plusieurs actions"], "b", "Elle ajoute complexité et risques ; elle doit être justifiée.", "piloter"),
        ],
    },
    "M12": {
        "G": [
            ("Pourquoi le GPU est-il adapté aux modèles d'IA ?", ["Il exécute massivement des opérations en parallèle", "Il stocke plus de documents", "Il remplace le réseau"], "a", "Les multiplications de matrices se parallélisent très bien.", "expliquer:2"),
            ("Quelle est souvent la contrainte principale pour choisir un GPU ?", ["Sa mémoire", "Sa couleur", "Son poids"], "a", "Le modèle et le contexte doivent tenir en mémoire.", "evaluer"),
            ("Avec un service externe facturé au token, le coût :", ["Croît avec le volume de questions et la taille des extraits", "Est fixe", "Est nul"], "a", "C'est un coût variable lié à l'usage.", "piloter"),
            ("Quels postes relèvent des coûts fixes d'un hébergement interne ? (plusieurs réponses)", ["Matériel", "Énergie", "Exploitation", "Tokens facturés par le fournisseur"], "abc", "Les tokens facturés relèvent d'un service externe.", "evaluer+piloter"),
            ("200 questions/jour × (3 000 + 400) tokens ≈ combien de tokens par mois (30 jours) ?", ["≈ 20 millions", "≈ 2 millions", "≈ 200 millions"], "a", "200 × 3 400 × 30 = 20,4 millions de tokens.", "evaluer:2"),
        ],
        "F": [
            ("Le CPU excelle dans :", ["Les tâches séquentielles variées", "Les calculs massivement parallèles", "Le stockage"], "a", "C'est le complément du GPU.", "expliquer"),
            ("Le point d'équilibre entre externe et interne dépend surtout :", ["Du volume d'usage", "De la langue", "Du logo"], "a", "Au-delà d'un volume, les coûts fixes deviennent compétitifs.", "piloter"),
            ("Réduire la taille des extraits transmis :", ["Diminue le coût par question", "Augmente le coût", "N'a aucun effet"], "a", "Moins de tokens en entrée, moins de coût.", "evaluer"),
        ],
    },
    "M13": {
        "G": [
            ("Qu'est-ce qu'une injection de consignes ?", ["Une instruction cachée dans un contenu qui détourne le modèle", "Une mise à jour du modèle", "Une erreur d'OCR"], "a", "Le modèle peut suivre une consigne présente dans un document s'il n'est pas protégé.", "evaluer:2"),
            ("Quelles parades limitent l'injection de consignes ? (plusieurs réponses)", ["Séparer instructions et contenus", "Filtrer les documents à l'intégration", "Limiter les capacités d'action", "Augmenter la fenêtre de contexte"], "abc", "La taille de la fenêtre ne protège pas contre l'injection.", "evaluer"),
            ("Une politique d'usage classe les données pour :", ["Associer à chaque classe les outils autorisés", "Les supprimer", "Les publier"], "a", "Chaque niveau de sensibilité correspond à des outils permis.", "piloter:2"),
            ("Exposer un document à un utilisateur non autorisé est un risque :", ["Sur les données", "Sur le comportement", "Sans importance"], "a", "C'est une fuite liée aux droits d'accès.", "evaluer"),
            ("Les usages doivent être :", ["Journalisés et revus périodiquement", "Anonymes et jamais revus", "Interdits"], "a", "Former et tracer font partie de la gouvernance.", "piloter"),
        ],
        "F": [
            ("Les échanges avec un fournisseur externe peuvent-ils être conservés ?", ["Oui, selon ses conditions", "Jamais"], "a", "D'où l'importance du cadre contractuel.", "evaluer"),
            ("Combien de classes de données propose la fiche synthèse ?", ["Deux", "Quatre", "Dix"], "b", "Publiques, internes, confidentielles, secrètes.", "piloter"),
            ("Une sortie inappropriée relève d'un risque :", ["Sur le comportement", "Sur le matériel"], "a", "Il se traite par des contrôles de sortie.", "evaluer"),
        ],
    },
    "M14": {
        "G": [
            ("Un jeu d'évaluation doit contenir :", ["Des questions réelles avec réponses et extraits attendus", "Uniquement des questions faciles", "Des questions inventées sans réponse"], "a", "Représentativité et référence permettent de mesurer.", "evaluer:2"),
            ("Quand rejouer le jeu d'évaluation ?", ["À chaque modification de corpus, prompt ou modèle", "Une fois par an", "Jamais"], "a", "Cela détecte les régressions.", "evaluer"),
            ("Le rappel de la recherche mesure :", ["La part des questions dont le bon extrait figure parmi les résultats", "La vitesse de réponse", "Le nombre d'utilisateurs"], "a", "C'est l'indicateur clé de la recherche.", "evaluer:2"),
            ("Quels indicateurs concernent la réponse ? (plusieurs réponses)", ["Fidélité aux sources", "Justesse des citations", "Temps de réponse", "Couleur du bouton"], "abc", "La couleur de l'interface n'est pas un indicateur de qualité.", "evaluer"),
            ("Une supervision efficace combine :", ["Tableau de bord et revue humaine d'un échantillon", "Uniquement des avis d'utilisateurs", "Aucune trace"], "a", "Mesures automatiques et regard humain sont complémentaires.", "evaluer"),
        ],
        "F": [
            ("Un refus justifié est-il un échec ?", ["Oui", "Non"], "b", "Refuser quand l'information manque est un comportement attendu.", "evaluer"),
            ("Une trace contient notamment :", ["Question, extraits, paramètres, contrôles", "Le mot de passe de l'utilisateur", "Rien"], "a", "Elle permet de reconstituer la réponse.", "evaluer"),
            ("L'évaluation humaine est-elle remplaçable entièrement par l'automatique ?", ["Oui", "Non"], "b", "Les deux sont complémentaires.", "evaluer"),
        ],
    },
    "M15": {
        "G": [
            ("Où se trouve le plus souvent la valeur d'un projet IA ?", ["Dans la transformation d'un processus", "Dans l'outil lui-même", "Dans le nombre de GPU"], "a", "La valeur vient du processus amélioré.", "piloter:2"),
            ("Pourquoi mesurer la situation initiale ?", ["Pour pouvoir démontrer un gain", "Pour retarder le projet", "Ce n'est pas utile"], "a", "Sans référence, aucun gain n'est démontrable.", "evaluer"),
            ("Quels critères servent à prioriser des cas d'usage ? (plusieurs réponses)", ["Valeur attendue", "Niveau de risque", "Disponibilité des données", "Popularité de l'outil"], "abc", "La popularité d'un outil n'est pas un critère de priorisation.", "piloter+evaluer"),
            ("Un bon cas pilote présente :", ["Une valeur démontrable et un risque maîtrisé", "Le risque le plus élevé possible", "Aucun utilisateur"], "a", "Il permet d'apprendre en sécurité.", "piloter"),
            ("Quel rôle arbitre les priorités et valide les mises en service ?", ["Un comité de gouvernance", "Le modèle", "Le fournisseur"], "a", "Les instances de gouvernance portent les décisions.", "piloter"),
        ],
        "F": [
            ("Un sponsor métier est-il nécessaire ?", ["Oui", "Non"], "a", "Il porte la valeur et l'adoption.", "piloter"),
            ("L'accompagnement du changement concerne :", ["Les utilisateurs et l'organisation", "Uniquement le matériel"], "a", "La transformation est d'abord humaine.", "piloter"),
            ("Un gain de temps de recherche est un indicateur :", ["De valeur", "De coût matériel"], "a", "C'est un bénéfice mesurable du processus.", "evaluer"),
        ],
    },
    "M16": {
        "G": [
            ("Quel est l'objectif de l'assistant des Journaux officiels ?", ["Retrouver les extraits pertinents et formuler une réponse sourcée", "Rédiger de nouveaux textes de loi", "Remplacer les juristes"], "a", "Il assiste la recherche, sans valeur de conseil juridique.", "piloter"),
            ("Quelle étape précède l'indexation ?", ["Le découpage par texte et par article", "La restitution", "L'évaluation"], "a", "On découpe et on décrit avant d'indexer.", "construire:2"),
            ("Quels contrôles imposer à la restitution ? (plusieurs réponses)", ["Chaque phrase factuelle rattachée à un extrait", "Toute référence citée existe dans le corpus", "Annoncer explicitement l'absence de résultat", "Masquer les limites"], "abc", "Les limites doivent être affichées, jamais masquées.", "construire+evaluer"),
            ("Un jeu de test doit inclure des questions sans réponse dans le corpus pour :", ["Vérifier que l'assistant sait le dire", "Allonger le test", "Tester le GPU"], "a", "Un bon assistant reconnaît l'absence d'information.", "evaluer:2"),
            ("La présentation finale du projet comprend :", ["Indicateurs, exemples d'échec analysés et décisions proposées", "Uniquement les réussites", "Le code source seul"], "a", "Une restitution honnête prépare la décision.", "piloter"),
        ],
        "F": [
            ("Le périmètre inclut-il une réponse ayant valeur de conseil juridique ?", ["Oui", "Non"], "b", "Les réponses sont informatives.", "piloter"),
            ("La double indexation désigne :", ["Lexicale et vectorielle", "Deux copies du corpus", "Deux langues"], "a", "Elle permet la recherche hybride.", "construire"),
            ("Le format de restitution recommandé comporte :", ["Synthèse, références avec extraits, limites", "Un seul paragraphe sans source"], "a", "Trois parties pour une réponse vérifiable.", "construire"),
        ],
    },
}

DIAGNOSTIC = [
    {"id": "D1", "prompt": "Quel est votre objectif principal ?", "kind": "profile", "weight": 2,
     "options": [("Comprendre ce qu'est l'IA, sans jargon", "profile-decouvrir"), ("Mieux utiliser les outils d'IA dans mon métier", "profile-utiliser"),
                 ("Concevoir une solution, par exemple un assistant documentaire", "profile-concevoir"), ("Décider et piloter un projet IA", "profile-piloter")]},
    {"id": "D2", "prompt": "Quelle description correspond le mieux à votre fonction ?", "kind": "profile", "weight": 1,
     "options": [("Curieux, étudiant ou en reconversion", "profile-decouvrir"), ("Professionnel métier (juridique, RH, finance, communication…)", "profile-utiliser"),
                 ("Consultant, analyste ou profil technique", "profile-concevoir"), ("Manager ou dirigeant", "profile-piloter")]},
    {"id": "D3", "prompt": "Un assistant d'IA produit sa réponse :", "kind": "knowledge",
     "options": [("En recopiant une réponse stockée", False), ("En prédisant la suite de texte la plus plausible", True), ("En interrogeant toujours internet", False)]},
    {"id": "D4", "prompt": "Un « token » est :", "kind": "knowledge",
     "options": [("Un fragment de texte manipulé par le modèle", True), ("Un jeton de paiement", False), ("Un mot de passe", False)]},
    {"id": "D5", "prompt": "Le RAG consiste à :", "kind": "knowledge",
     "options": [("Réentraîner le modèle chaque jour", False), ("Rechercher des documents puis générer une réponse fondée sur eux", True), ("Supprimer les hallucinations par magie", False)]},
    {"id": "D6", "prompt": "Pour une réponse factuelle et constante, on choisit une température :", "kind": "knowledge",
     "options": [("Basse", True), ("Élevée", False), ("Cela n'a aucun effet", False)]},
    {"id": "D7", "prompt": "Un embedding sert principalement à :", "kind": "knowledge",
     "options": [("Représenter le sens d'un texte sous forme de vecteur", True), ("Chiffrer un document", False), ("Afficher une image", False)]},
    {"id": "D8", "prompt": "Quel élément pèse le plus dans le coût d'exploitation d'un assistant externe ?", "kind": "knowledge",
     "options": [("Le volume de tokens traités", True), ("La couleur de l'interface", False), ("Le nombre de pages du site", False)]},
]


def parse_comps(spec: str):
    out = []
    for part in spec.split("+"):
        name, _, weight = part.partition(":")
        out.append({"competency_id": f"comp-{name}", "weight": int(weight or 1)})
    return out


def build_question(qid: str, module_id: str, item) -> dict:
    prompt, options, correct, explanation, comps = item
    letters = "abcdefgh"
    return {"_id": f"{qid}@1", "question_id": qid, "version": 1, "status": "published", "module_id": module_id,
            "type": "multiple" if len(correct) > 1 else "single", "prompt": prompt,
            "options": [{"id": letters[i], "text": t} for i, t in enumerate(options)],
            "correct": list(correct), "explanation": explanation, "competencies": parse_comps(comps)}


async def seed_assessment(aid: str, module_id, kind: str, title: str, questions: list, extra: dict):
    for q in questions:
        await insert_missing("questions", BaseDocument(**q))
    await insert_missing("assessments", VersionedEntity(_id=aid, code=aid, kind=kind, module_id=module_id, title=title,
                                                published_version=1, latest_version=1, created_at=SEED_DATE,
                                                updated_at=SEED_DATE, **extra))
    await insert_missing("assessment_versions", EntityVersion(_id=f"{aid}@1", entity_id=aid, version=1, status="published",
                                                      changelog="Version initiale", created_at=SEED_DATE, published_at=SEED_DATE,
                                                      questions=[{"question_id": q["question_id"], "version": 1} for q in questions]))


async def seed_assessments():
    for mid, sets in Q.items():
        graded = [build_question(f"Q-{mid}-G{i}", mid, it) for i, it in enumerate(sets["G"], 1)]
        formative = [build_question(f"Q-{mid}-F{i}", mid, it) for i, it in enumerate(sets["F"], 1)]
        await seed_assessment(f"A-{mid}-G", mid, "graded", f"Évaluation notée — {mid}", graded,
                              {"pass_threshold": PASS_THRESHOLD, "max_attempts": MAX_ATTEMPTS})
        await seed_assessment(f"A-{mid}-F", mid, "formative", f"Quiz formatif — {mid}", formative,
                              {"pass_threshold": None, "max_attempts": None})
    diag = []
    for d in DIAGNOSTIC:
        letters = "abcd"
        diag.append({"_id": f"Q-DIAG-{d['id']}@1", "question_id": f"Q-DIAG-{d['id']}", "version": 1, "status": "published",
                     "module_id": None, "type": "single", "prompt": d["prompt"], "diagnostic_kind": d["kind"],
                     "weight": d.get("weight", 1),
                     "options": [{"id": letters[i], "text": t} for i, (t, _) in enumerate(d["options"])],
                     "option_values": {letters[i]: v for i, (_, v) in enumerate(d["options"])},
                     "correct": [letters[i] for i, (_, v) in enumerate(d["options"]) if v is True],
                     "explanation": "", "competencies": []})
    await seed_assessment("A-DIAG", None, "diagnostic", "Test de positionnement", diag, {"pass_threshold": None, "max_attempts": None})
    await db.assessment_versions.create_index([("entity_id", 1), ("version", 1)], unique=True)
