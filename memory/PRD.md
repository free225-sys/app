# CASA AI Academy — PRD

## Original problem statement (summary)
FARM web app, French UI. "CASA AI Academy" makes AI understandable to non-specialists. Phase 1 of 4: brand guidelines, Home, 7-step simulated interactive demo (Journal officiel de Côte d'Ivoire, 2 May 2002, café/cacao), Concepts, public Catalogue, Module pages, Parcours overview, Notre approche, "Se connecter" placeholder. The data model must be ready for later phases (accounts, quizzes, pathways, certificates, back-office with versioning). Required footer on every page: "by Relais IT (www.relaisit.com)". Consulting-firm style design: ivory, midnight blue, green and blue accents, Inter.

## Architecture
- Backend: FastAPI with /api prefix. /api/openapi.json and /api/docs are available. MongoDB is seeded idempotently at startup (upsert).
  - Collections: stages, phases, layers, competencies, levels, profiles, concepts, resources, modules + module_versions, courses + course_versions, pathways + pathway_versions, demo_scenarios.
  - Versioning: each entity has published_version and latest_version. Each version has status draft/review/published/retired. Everything is seeded as published v1.
  - Derived fields: a layer's modules are computed from the modules. A concept's levels and competencies come from its linked modules.
- Frontend: React and Tailwind. Pages: Home, Demo, Ressources, ConceptPage, ModulePage, Parcours, Approche, Connexion, NotFound.
  - Demo state (step, layer per step, technical detail, generation, quiz) is kept in the URL (?etape&couche&detail) and in sessionStorage.

## Implemented (2026-10-09)
- Full catalogue: 7 steps, 5 phases, 6 layers, 5 competencies, L0–L4, 4 profiles, 35 concepts, 16 modules (50 resources), 4 courses (M09 in C02 and C03), 2 pathways, demo scenario with 7 steps and a 3-question quiz.
- APIs: catalog/*, demo/scenarios, concepts (filters stage/layer/level/competency/q), modules (same filters), modules/{id}/versions, resources/{id}, courses, pathways.
- Interactive demo: specific visuals for each step, layer panel, technical detail toggle, progressive reveal (respects reduced motion), end-of-demo quiz, link to M01, account placeholder.
- Accessibility: skip link, visible focus, aria labels, mobile menu, works at 375px.
- Testing: iteration_1 found a crash when switching tabs in Ressources. It was fixed in useApi with a key-guarded state.

## Backlog
- P0 (Phase 3): pathway enrolment, certificates.
- P1 (Phase 4): DONE (see below).
- P2: email password reset, real video URLs, replace the logo with an image file, deduplicate diagnostic history, analytics.

## Phase 3 — Parcours, compétences et certificats (2026-10-09)
- Pathway enrolment, pinned to pathway_version, at /pathways/:id. Each pathway has mandatory and optional course groups and target competencies with required levels. Bridge rules are stored on pathway_courses.
- Automatic recognition of prior learning, captured when the learner enrols:
  - A module counts if it was completed in the same module version (module_completions.module_version).
  - A target competency counts if it was attained at the required level with an accepted evidence type.
  - The UI shows an "Acquis reconnu" badge with the source.
- M16 applied project: rubric RUB-M16 v1 (5 weighted criteria, levels 0–3, 60% to validate). Submissions accept a title, a description and an optional PDF/DOCX file of up to 10 MB, stored in Emergent Object Storage.
- Evaluator page /evaluation (evaluator@casa-academy.ci). Validating a project creates attainments with evidence_type "project".
- Attainments: unique on (user, competency, module, evidence_type), with a status of valid or invalidated.
- Credentials CERT-FOND, CERT-CONC (M09 graded + M14 graded + M16 project) and CERT-PIL.
  - Eligibility and claim are checked on the server. A certificate gets a code CASA-XXXX-XXXX.
  - The reportlab PDF includes the code, the verification URL (PUBLIC_APP_URL) and "by Relais IT".
  - Public verification at /verifier/:code.
- Temporary admin page /admin: revoke a certificate, or invalidate an evidence, which revokes the certificates that depend on it.
- /espace now has sections for pathways, projects and certificates.
- Tested in iteration_3: everything passes.
- JWT auth with bcrypt: register, login, logout, me, refresh. Forgot password shows a message only. Users have a roles field. Brute-force protection: 5 failures per email trigger a 15-minute lockout. Admin and learner accounts are seeded.
- Module reader /modules/:id/learn: resources in order with a sidebar and statuses. Progress comes from the "J'ai terminé cette ressource" button. M01-R4 is a video placeholder.
- Assessments: versioned question bank (questions, assessments, assessment_versions collections). Each of the 16 modules has 5 graded and 3 formative questions. Formative check is immediate. Graded quiz: 70% to pass, 3 attempts maximum, scored on the server, scores per competency, attainments with evidence.
- Diagnostic /diagnostic: 8 questions, works anonymously, saved when logged in.
- Course reader /courses/:id. Learner dashboard /espace. Anonymous demo progress and diagnostic answers are attached at signup or login.
- Tested in iteration_2: all flows pass. The lockout identifier was fixed after the test.

## Phase 4 — Back-office (2026-10-09)
- Attainments fix: the reported entries were not true duplicates. M16 projects give one attainment per rubric competency, and M09 graded quizzes give construire + utiliser. Unique index (user, competency, module, evidence_type) plus a dedupe cleanup at startup. /espace now groups evidence by competency.
- RBAC: multiple roles per user. A user has an active flag (deactivated → 403 at login, 401 with an existing token). Seeded accounts: author, reviewer, lead (see test_credentials.md).
- backend/admin.py: one versioning engine (TYPES) for concept, resource, module, question, assessment, course, pathway, credential.
  - Workflow: draft → review (approve or return with a comment) → published (pedagogical_lead or admin only) → retired.
  - Published and retired versions are immutable. Saving creates draft vN+1.
  - Courses pin module versions (module_pins, optional_module_ids). Pathways pin course versions (course_version). Course and pathway progress use these pins.
  - Publication checks: prerequisite cycles (concepts and modules), unpublished dependencies, unknown taxonomy → 422 with a clear message.
  - Version history with a field-level diff.
  - catalog_change_log (filterable), also for users, certificates and evidence.
  - Anonymous POST /api/events (demo_start, demo_complete, demo_layer_click). /api/admin/analytics returns real counts.
  - Resource file upload (object storage) and video_url.
  - Idempotent migration of the seeds. Seeds are now insert-only, so edits made in the back-office are kept.
- /admin UI with tabs: Tableau de bord, Contenus (8 editors), Relecture, Journal, Utilisateurs (admin), Certificats et preuves (admin).
- Tested in iteration_4: 38/38 Phase 4 tests and 34/34 regression tests pass. The frontend is verified. Test data was cleaned up.

## Next / backlog
- P1: real email password reset; markdown rendering for resources; reviewers cannot approve their own versions (four-eyes rule).
- P2: split admin.py into modules; analytics charts over time; CSV export of the change log.

## Phase 5 — Prototype UX alignment + JSON catalogue (2026-10-09)
- Footer and certificate PDF: "by Relais IT" with a link to https://www.relaisit.com. The URL no longer appears as visible text.
- Prototype charter applied globally:
  - styles/proto.css plus a palette remap of every page; Georgia headings, Arial body; Tailwind breakpoints md 721 / lg 1130.
  - Prototype sticky header; logo component (client PNG /logo-casa.png + "AI ACADEMY" pill, text fallback); favicon.
- Home and demo rewritten with the exact prototype texts.
  - Demo: 2 scenarios (Journal officiel, and the new "Comprendre une requête générale").
  - Layers marked "mobilisée" or "connexe", link to the filtered concepts, callout.
  - Rich visuals, persistence, quiz and tracking are kept.
- JSON catalogue (seed_catalog.py):
  - K-001..K-003, concept primary_stage + catalog_id, M-001..M-003, A-001..A-005.
  - Assessments: Q-001 practice, Q-002 project rubric, Q-003 graded 80 %.
  - CO-001/002, P-001/002, CERT-DOC-01 (new rule kind assessment_passed).
- Back-office Import / Export JSON (catalog_io.py, lead and admin):
  - export in the example format;
  - import shows a preview (create, update, unchanged, errors);
  - confirming creates drafts only; broken references or cycles are rejected; every import is logged.
- Never-published drafts can be deleted. Resources render markdown. M09 v2 draft and QA accounts removed.
- Tested in iteration_5: 17/17 Phase 5 tests and 72/72 regression tests pass. The frontend is verified at 1920 and 375 px.

## Backlog
- P1: reviewers cannot approve their own versions (four-eyes rule); real email password reset.
- P2: split admin.py and catalog_io.build_plan; analytics trends over time; CSV export of the change log.
