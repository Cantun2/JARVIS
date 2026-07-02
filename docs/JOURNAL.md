# JOURNAL de bord

## Session 2 — 2026-07-02 — Phase 2 : le réveil branché au réel

**Objectif.** Rendre HERMES/ORACLE réels tout en gardant le mock par défaut (spec §Phase 2, items 8-9).
Contrainte : CPU-only (machine actuelle et suivante), pas de clé Anthropic → **inférence locale Ollama**.

**Fait.**
- **MailSource** (`io/mail.py`) : `Mail`, Protocol `MailSource`, `MockMailSource` (défaut), `GmailMailSource`
  (réel, extra `[google]`, service injectable) + `build_mail`. Injecté dans `AgentContext.mail`
  (`require_mail()`), gaté par `MAIL_READ`. HERMES lit désormais `ctx.require_mail().fetch(...)`.
- **OllamaBackend** (`inference/ollama_backend.py`) : API OpenAI-compatible d'Ollama, buildless, transport
  injectable ; branché en priorité dans `build_backend` (`JARVIS_OLLAMA_URL`). Résumé HERMES **best-effort**
  (timeout + repli déterministe) → robuste sur CPU.
- **Événements** : `mail.triaged` enrichi (`subject`+`sender`). **API** : `GET /api/inbox`, `GET /api/briefing`
  (dérivés du journal, sans état neuf).
- **UI** : navigation par **onglets** (Dashboard/Inbox/Briefing), panneaux **Inbox** (lecture seule) et
  **Briefing** (texte + sections + Night Report), boutons de déclenchement (ATLAS/HERMES/ORACLE).
- **Config** : `mail_backend`, `gmail_*`, `ollama_url`, `local_model` + `.env.example`. **doctor** enrichi.
  Extra `[google]` dans `pyproject`.

**Validation.** `make check` vert : ruff clean, mypy strict (55 fichiers), pytest (backend) + vitest (44
tests UI). Mock reste le défaut (aucun test ne touche le réseau ; Gmail/Ollama testés avec faux client/transport).

**Décisions.** ADR-8 (MailSource) et ADR-9 (Ollama local, cloud différé) — cf. `DECISIONS.md`.

**Questions ouvertes.** Génération du `token.json` Gmail (script OAuth one-shot vs `jarvis connect gdrive`) ;
modèle Ollama à retenir sur la future machine ; seuils de `limit`/timeout HERMES selon la vitesse CPU réelle.

**Prochaine étape.** Brancher réellement (Ollama + OAuth Gmail) et vérifier bout-en-bout ; puis Phase 3
(DAEDALUS → VULCAN) ou Phase 4 (ECHO voix, HERMES v2 corrections).

## Session 1 — 2026-07-01 — Fondations + réveil (mock)

**Objectif.** Fondations solides d'abord (choix utilisateur) : Phase 1 complète et testée + la
séquence de réveil (ATLAS/HERMES/ORACLE) en mock. VULCAN désarmé, voix reportée.

**Fait.**
- Vérifié qu'OpenJarvis (Stanford, Apache-2.0) est réel et cadré l'intégration (cf. `DECISIONS.md`).
- Core event-driven : `events`, `journal` (SQLite WAL, rejouable), `bus` (journal-first),
  `contracts` (permissions/budget/escalade), `permissions` (enforcement unique), `registry`,
  `orchestrator` (`AgentRunner`).
- Inférence : `InferenceGateway` + `MockBackend` (déterministe) + `OpenJarvisBackend` (HTTP OpenAI-compat) +
  `ComplexityRouter` (stub local↔cloud).
- Desktop : `DesktopController` abstrait + `MockDesktop` (3 écrans) + **backend GNOME/Wayland réel**
  (`mutter_display`, `gnome_wayland`, `gnome_extension`) + **extension GNOME Shell** `org.jarvis.DesktopExt`.
- Profiles : modèles + parsing DSL + loader TOML + `ProfileExecutor` ; profils `deep-work` et `default`.
- Agents : ATLAS (réveil), HERMES (triage par règles + résumé gateway), ORACLE (briefing + Telegram),
  VULCAN (désarmé). Fixtures mock (mails, night report).
- I/O : `TelegramNotifier` (Mock + Stub réel opt-in).
- API : FastAPI (`/api/health`, `/api/agents`, `POST /api/agents/{name}/run`, `/api/events`) + WebSocket `/ws`.
- UI : HUD Vite+React+TS+Tailwind (Dashboard, EventFeed, AgentStatusArc, ConnectionBadge) + `useEventStream`.
- Outillage : `Makefile` (`check/demo/doctor/serve/ui-dev`), `demo.py`, `doctor.py`, `assembly.py`.

**Validation.** `make check` vert : ruff clean, **mypy strict 53 fichiers**, **91 tests pytest**,
**26 tests vitest** (117 au total). `make demo` : séquence de réveil cohérente. Serveur uvicorn testé
en live (health, run ATLAS → 6 fenêtres placées, 42 événements).

**Décisions notables.** Voir `DECISIONS.md` (ADR 1-7). En résumé : OpenJarvis jamais en dépendance dure,
enforcement unique, journal-first, extension GNOME pour Wayland, Tauri différé, VULCAN désarmé.

**Questions ouvertes / à trancher avec l'humain.**
- Vrais profils navigateur (noms des profils Chrome/Firefox) à mettre dans `profiles/*.toml`.
- Modèle local à retenir vu l'absence de GPU (Qwen 4B CPU ? ou tout cloud au départ ?).
- Règles VIP/urgence de HERMES à personnaliser (`agents/mocks/mail_fixtures.py::VIP_SENDERS` → règles réelles).

**Prochaine session (suggestion).** Phase 2 réelle : OAuth Google + fetch Gmail (remplacer fixtures),
brancher un backend d'inférence, ORACLE parlé (Phase 4 ECHO), puis préparer DAEDALUS/VULCAN (Phase 3).
