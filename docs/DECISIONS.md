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

## ADR-7 — VULCAN livré désarmé
**Contexte.** Le Night Shift est le module le plus puissant et le plus dangereux.
**Décision.** VULCAN est livré `enabled=False`. L'`AgentRunner` refuse tout agent désarmé (`AgentDisarmed`) ;
`Vulcan.run` lève aussi par défense en profondeur. Aucune session nocturne réelle ne peut démarrer en
Phase 1.
**Conséquences.** Activation manuelle, explicite, après branchement (cf. MANUAL_SETUP / HANDOVER).
