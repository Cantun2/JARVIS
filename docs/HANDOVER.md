# HANDOVER — état de jarvis-suit (fin de session 1)

## En une phrase
Les **fondations** (Phase 1) et la **séquence de réveil** (ATLAS → HERMES → ORACLE) tournent
**entièrement en mock**, sans credential ni GPU, testées de bout en bout. VULCAN est livré **désarmé**.

## Comment vérifier tout de suite
```bash
make install     # venv + deps (si pas déjà fait)
make doctor      # ce que la machine offre (mock vs réel)
make demo        # séquence de réveil complète, en mock, avec assertions
make check       # ruff + mypy strict + pytest + vitest
# UI live :
cd ui && npm install
make serve       # terminal 1 : API + WebSocket (:8000)
make ui-dev      # terminal 2 : HUD dans le navigateur (:5173)
```

## Ce qui MARCHE (en mock, vérifié)
- **Core event-driven** : bus + journal SQLite rejouable ; `AgentRunner` applique permissions + budget +
  émet le cycle de vie. `MAIL_SEND` jamais accordée ; VULCAN refusé car désarmé.
- **Réveil ATLAS** (profil `deep-work`) : `wake_up` → layout desktop (kill discord/steam ; lance
  spotify/vscode/terminal/obsidian ; ouvre calendar/gmail/github ; place sur 3 écrans) → HERMES → ORACLE.
- **HERMES** : classe 9 mails factices (urgent/action/info/newsletter/spam), résume via le gateway,
  trie par priorité. N'envoie rien.
- **ORACLE** : compose le briefing (mails urgents, agenda, Night Report factice, météo), l'émet et le
  pousse sur `MockTelegram`.
- **API** : REST + WebSocket (snapshot + flux live). Testé via uvicorn réel.
- **UI** : HUD sombre, flux d'événements live, arc de statut des agents, badge de connexion (26 tests).
- **Desktop réel** : backend GNOME/Wayland + extension `org.jarvis.DesktopExt` (31 tests headless) —
  code présent et typé, à activer (cf. ci-dessous).

## Ce qui ATTEND la checklist manuelle (`docs/MANUAL_SETUP.md`)
- Inférence réelle (OpenJarvis local **ou** Anthropic cloud) — mock par défaut.
- OAuth Google pour HERMES (remplacer les fixtures par un vrai fetch Gmail).
- Token Telegram (sinon MockTelegram).
- Extension GNOME à installer + `JARVIS_DESKTOP_BACKEND=gnome` pour le placement pixel-précis réel.
- Packaging Tauri (webkit2gtk + Rust).
- Activation **manuelle** de VULCAN après revue.

## Limites connues / dettes
- **Pas de GPU** sur la machine : l'inférence locale (Qwen) sera lente (CPU). Recommandation : mock →
  cloud pour le lourd → local léger optionnel.
- **Wayland** : sans l'extension GNOME, le placement pixel-précis est dégradé (lancement/URLs OK).
- **Tauri non packagé** ici (webkit2gtk absent) — l'UI tourne en navigateur.
- `OpenJarvisBackend.stream` est non incrémental (une réponse) — SSE token-par-token à brancher.
- HERMES v1 ne rédige pas de brouillons (v2) ; règles de classification à personnaliser.
- Recharts installé mais gauges CPU/GPU/RAM pas encore câblées (le flux `system.health` arrive déjà).

## Hors périmètre de cette session (roadmap)
DAEDALUS (décomposition d'objectifs), VULCAN opérationnel (worktrees + Claude Code headless + garde-fous
SENTINEL), ECHO (whisper.cpp + Piper), HERMES v2, QUARTERMASTER, SCRIBE, animations/thèmes/packaging (Phase 5).

## Carte du code (où regarder)
- Cœur : `src/jarvis/core/` (`orchestrator.py`, `bus.py`, `journal.py`, `contracts.py`, `context.py`).
- Inférence : `src/jarvis/inference/` (`gateway.py`, `mock_backend.py`, `openjarvis_backend.py`).
- Desktop : `src/jarvis/desktop/` (`controller.py`, `mock_desktop.py`, `gnome_wayland.py`) + `extensions/`.
- Agents : `src/jarvis/agents/` (`atlas.py`, `hermes.py`, `oracle.py`, `vulcan.py`, `mocks/`).
- API : `src/jarvis/api/` ; composition : `src/jarvis/assembly.py`.
- UI : `ui/src/` ; démo/doctor : `src/jarvis/demo.py`, `src/jarvis/doctor.py`.
- Décisions : `docs/DECISIONS.md`. Étapes manuelles : `docs/MANUAL_SETUP.md`.

## Chiffres
117 tests verts (91 pytest + 26 vitest), mypy strict sur 53 fichiers, ruff clean. `make demo` et
`make serve` fonctionnels en mock.
