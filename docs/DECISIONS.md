# Décisions d'architecture (ADR condensés)

Journal des choix structurants. Chaque décision : contexte → décision → conséquences.

## ADR-1 — Bâtir au-dessus d'OpenJarvis, mais jamais en dépendance dure
**Contexte.** OpenJarvis (Stanford, Apache-2.0) fournit inférence, mémoire, scheduler, connecteurs.
Mais son installation impose un build natif Rust (maturin), absent de la machine cible.
**Décision.** Le Core ne dépend d'aucun symbole `openjarvis` au chargement. Toute l'inférence passe
par une abstraction maison `InferenceGateway` avec des backends interchangeables `{Mock, OpenJarvis}`.
`openjarvis` est un extra optionnel (`[openjarvis]`).
**Conséquences.** Le repo tourne 100 % en mock sans Rust/modèle/credential. Brancher OpenJarvis =
changer une config, pas le code.

## ADR-2 — OpenJarvis via HTTP OpenAI-compatible, pas via import Python
**Contexte.** OpenJarvis expose à la fois un SDK Python (build natif) et un serveur `jarvis serve`
compatible OpenAI.
**Décision.** `OpenJarvisBackend` parle par défaut au serveur HTTP (`/v1/chat/completions`) via `httpx`.
Aucun build Rust côté jarvis-suit. L'import du SDK reste possible mais réservé à l'extra `[openjarvis]`.
**Conséquences.** Découplage process ; on peut lancer OpenJarvis en conteneur (Docker présent) et s'y
connecter par URL (`JARVIS_INFERENCE_URL`).

## ADR-3 — Un seul point d'exécution : `AgentRunner`
**Contexte.** « Chaque agent = un contrat » (permissions, budget). Il faut que ce soit appliqué par le
Core, pas par la bonne volonté des agents.
**Décision.** `core/orchestrator.py::AgentRunner` est le seul chemin d'exécution. Il vérifie
permissions → budget → construit un `AgentContext` ne contenant QUE les capacités accordées → exécute
avec timeout → émet les événements de cycle de vie. Un agent sans `DESKTOP_WINDOW` n'a physiquement pas
l'objet desktop.
**Conséquences.** Sécurité par construction. `MAIL_SEND` n'est jamais accordée par défaut
(`PermissionEnforcer.DEFAULT_DENIED`).

## ADR-4 — Journal-first : SQLite (WAL) source de vérité, rejouable
**Contexte.** « Tout est loggé et rejouable » (base du Night Report et du debug).
**Décision.** `EventBus.publish` écrit d'abord dans le journal puis diffuse sans bloquer. Le journal
(`seq` = ordre total) est la vérité ; le bus n'est qu'un transport. Les tests assertent des **séquences
d'événements** relues du journal, pas des retours de fonction.
**Conséquences.** Déterminisme des tests malgré l'asynchronisme ; l'UI peut bootstrapper via
`GET /api/events` puis suivre le live via WebSocket.

## ADR-5 — Desktop Wayland : lecture native + extension GNOME pour le placement
**Contexte.** GNOME 46 / Wayland : la topologie des écrans est lisible via `org.gnome.Mutter.DisplayConfig`,
mais **déplacer** une fenêtre est impossible sans extension.
**Décision.** `DesktopController` abstrait ; backend `GnomeWaylandDesktop` (lancement via gio/gtk-launch,
URLs via xdg-open/profils, topologie via Mutter D-Bus) + extension GNOME `org.jarvis.DesktopExt` pour le
placement pixel-précis. **Dégradation propre** si l'extension est absente (`move_window` renvoie
`placed=False` sans lever). `MockDesktop` (3 écrans factices) par défaut.
**Conséquences.** Le réveil fonctionne partout ; le placement précis multi-moniteur nécessite d'installer
l'extension (cf. MANUAL_SETUP).

## ADR-6 — UI en Vite/navigateur d'abord, packaging Tauri différé
**Contexte.** Tauri 2 est la cible, mais `webkit2gtk-4.1` est absent → `tauri dev/build` impossible ici.
**Décision.** UI développée et testée en navigateur (Vite) ; `ui/src-tauri/` scaffoldé mais packaging
différé.
**Conséquences.** `make ui-dev` + `make serve` donnent le HUD live immédiatement, sans dépendance système.

## ADR-8 — Source de mails abstraite (MailSource), Gmail derrière config
**Contexte.** HERMES doit trier de vrais mails (Gmail) sans casser le mode mock ni imposer l'OAuth.
**Décision.** `io/mail.py` : Protocol `MailSource` + `MockMailSource` (défaut) + `GmailMailSource` (réel,
`google-api-python-client`, import paresseux, extra `[google]`, service injectable pour les tests).
Injecté dans `AgentContext.mail`, **gaté par `Permission.MAIL_READ`**, consommé via `ctx.require_mail()`.
Même moule que Telegram.
**Conséquences.** `make check`/`make demo` restent verts sans credential ; brancher Gmail = config + OAuth
(cf. MANUAL_SETUP), zéro changement de code agent.

## ADR-9 — Inférence réelle = Ollama local (CPU), pas de cloud pour l'instant
**Contexte.** Machine actuelle et suivante **sans GPU** ; **pas de clé Anthropic**. L'inférence locale doit
tourner sur CPU, sans build.
**Décision.** `OllamaBackend` (httpx sur l'API OpenAI-compatible d'Ollama `:11434/v1`, buildless) branché
dans `build_backend` en priorité si `JARVIS_OLLAMA_URL` est défini ; sinon serveur OpenAI-compatible
générique ; sinon Mock (défaut). Le cloud (Anthropic) est **différé**. Côté HERMES, le résumé via modèle est
**best-effort** (timeout + repli déterministe) : le triage (règles) ne dépend jamais du modèle → robuste sur
CPU lent.
**Conséquences.** Chemin réel simple et local : `ollama pull <modèle>` + une variable d'env. Pas de Rust, pas
de cloud, pas de coût.

## ADR-10 — État des tâches dans un store dédié (projection), journal = trace
**Contexte.** Le Night Shift a besoin d'un **état mutable** (backlog → in_progress → review → done /
blocked / failed), incompatible avec le journal append-only.
**Décision.** Nouveau `night/store.py::TaskStore` (SQLite, tables `projects`/`tasks`/`night_reports`), sur
le moule de `SQLiteJournal`. C'est la **projection** de l'état courant ; chaque transition émet aussi un
événement (`task.transitioned`, `backlog.ready`, `night.report_ready`) sur le bus → le journal reste la
trace rejouable (ADR-4). Le store est injecté via `AgentContext.tasks` (service **non gaté** par permission,
comme `emit`/`trigger`).
**Conséquences.** UI Mission Control alimentée par le store (état) + le flux d'événements (live).

## ADR-11 — Night Shift en simulation dry-run ; VULCAN jamais armé
**Contexte.** Phase 3 « La nuit » sans exécuter de code (VULCAN déprioritisé et dangereux).
**Décision.** `night/manager.py::NightShiftManager` est un **service dry-run** (pas un agent, sans
`SHELL_SANDBOXED`/`FS_PROJECT_DIRS`) : il fait progresser les tâches avec rapports/diffs **factices**
(`dry_run=True`), respecte `max_usd_night`/`max_tasks_night`, et n'invoque **aucun** process (test garde-fou
qui monkeypatche `subprocess`/`os.system`/`create_subprocess_exec`). DAEDALUS (planner) n'a que
`NET_CLOUD_INFERENCE`. VULCAN reste `enabled=False`.
**Conséquences.** Toute la structure (backlog, cycle de vie, Night Report, Mission Control) est prête ;
VULCAN réel (worktrees + `claude -p`) la pilotera plus tard, après armement manuel explicite.

## ADR-12 — Voix (ECHO) locale, mock-first, gatée par une permission dédiée
**Contexte.** Phase 4 « Les sens » : JARVIS doit entendre (STT) et parler (TTS), sur une machine CPU sans
GPU ni micro garanti, sans clé cloud.
**Décision.** `io/voice.py` sur le moule de `io/mail.py` : Protocols `SpeechToText`/`TextToSpeech` +
`VoiceIO` (wake-word « jarvis »). Backends **Mock** par défaut (déterministes, hors-ligne, aucun son) ;
adaptateurs **réels** `WhisperSTT` (faster-whisper) / `PiperTTS` (piper) en **imports paresseux, moteur
injectable**, construits seulement en `mode=real` + `JARVIS_VOICE_BACKEND=real`. La voix est **locale
uniquement** (aucun audio au cloud) et gatée par une nouvelle `Permission.VOICE_IO` (comme
`NOTIFY_TELEGRAM`) : injectée dans `AgentContext.voice` seulement si accordée. ECHO (`agents/echo.py`,
`mode=continuous`) détecte le wake-word, route l'intention (déterministe : nuit→store, mails→HERMES,
briefing→ORACLE ; free-form→gateway best-effort) via `ctx.trigger`, puis parle. ORACLE gagne `VOICE_IO` et
prononce le briefing (best-effort).
**Conséquences.** Tout testable en mock (STT/TTS injectés) ; le réel se branche via `MANUAL_SETUP` sans
toucher le Core. ECHO n'a aucune I/O dangereuse propre — il ne fait que déclencher d'autres agents.

## ADR-13 — HERMES v2 : brouillons jamais envoyés + apprentissage local par overrides
**Contexte.** Rendre HERMES utile (rédaction) et personnalisable (corriger un classement), sans jamais
envoyer de mail.
**Décision.** Nouveau store `mail/store.py::MailMemory` (SQLite, tables `drafts`/`overrides`), injecté comme
service d'état **non gaté** `AgentContext.mail_memory` (comme `tasks`). (1) **Brouillons** : pour les mails
`action`/`urgent`, et **seulement** si `MAIL_DRAFT` est accordée, HERMES rédige un brouillon (gateway
best-effort, repli gabarit déterministe), le persiste et émet `mail.drafted`. `MAIL_SEND` reste dans
`DEFAULT_DENIED` : **aucun canal d'envoi n'existe**. (2) **Apprentissage** : `classify(mail, overrides)`
consulte d'abord les règles apprises (expéditeur → catégorie) ; l'UI corrige via
`POST /api/inbox/{id}/reclassify` → `set_override` + `mail.reclassified`. Le prochain tri applique la règle.
**Conséquences.** L'utilisateur contrôle la classification (dataset local) ; les brouillons sont relisibles
dans l'UI (dépli) mais jamais expédiés. Garde-fou vérifié par test (`MAIL_SEND` absente du contrat).

## ADR-7 — VULCAN livré désarmé
**Contexte.** Le Night Shift est le module le plus puissant et le plus dangereux.
**Décision.** VULCAN est livré `enabled=False`. L'`AgentRunner` refuse tout agent désarmé (`AgentDisarmed`) ;
`Vulcan.run` lève aussi par défense en profondeur. Aucune session nocturne réelle ne peut démarrer en
Phase 1.
**Conséquences.** Activation manuelle, explicite, après branchement (cf. MANUAL_SETUP / HANDOVER).
