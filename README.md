# jarvis-suit

Un assistant personnel type **JARVIS** (Iron Man) : réveil orchestré, triage mail, HUD moderne —
la couche « Tony Stark » construite **au-dessus d'[OpenJarvis](https://github.com/open-jarvis/OpenJarvis)**
(Stanford, Apache-2.0).

> **État** : Fondations (Phase 1) + réveil (ATLAS/HERMES/ORACLE) en **mode mock**.
> Tout tourne **sans credential ni GPU**. VULCAN (nuit) est livré **désarmé**. Voir `docs/HANDOVER.md`.

## Philosophie

- **Local-first** : classification/triage en local (quand un modèle est branché), raisonnement lourd → cloud.
- **Event-driven** : tout est un événement, écrit dans un journal SQLite rejouable.
- **Contrat par agent** : permissions + budget déclarés, appliqués par le Core (un seul point d'enforcement).
- **Mock-first** : chaque module a un mode démo à données factices.

## Démarrage rapide (mode mock, aucun credential)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # ou : pip install -r requirements-dev.txt
make doctor                  # que détecte-t-on sur cette machine ?
make demo                    # joue la séquence de réveil ATLAS en mock
make check                   # ruff + mypy strict + pytest (+ vitest si l'UI est installée)
```

UI (dans le navigateur, via Vite — Tauri packagé plus tard, cf. `docs/MANUAL_SETUP.md`) :

```bash
cd ui && npm install && npm run dev
# puis, dans un autre terminal : make serve  (API + WebSocket sur :8000)
```

## Architecture

```
UI (React/Vite, HUD)  ──WS/REST──►  Core FastAPI
                                     ├─ EventBus (in-proc) ──► Journal SQLite (WAL, rejouable)
                                     ├─ AgentRunner (permissions + budget + events)
                                     ├─ InferenceGateway {Mock | OpenJarvis}
                                     ├─ DesktopController {Mock | GNOME/Wayland (+ extension)}
                                     └─ Agents : ATLAS · HERMES · ORACLE · VULCAN(désarmé)
```

Voir `docs/DECISIONS.md` pour les choix d'architecture, `JARVIS_MASTER_SPEC.md` pour la vision complète.

## Licence

Apache-2.0 (cohérent avec OpenJarvis).
