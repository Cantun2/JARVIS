# PROJET JARVIS — Spécification Master pour Claude Code

> **Objectif** : Construire un assistant personnel type JARVIS (Iron Man) qui se réveille avec moi,
> prépare mon environnement de travail (pages, écrans), triage mes mails, pilote mes projets en
> parallèle (y compris la nuit), le tout avec une interface ultra-moderne.
>
> **Philosophie** : Local-first (souveraineté, coût, latence), cloud quand nécessaire.
> On construit AU-DESSUS d'OpenJarvis (Stanford) — on ne réinvente pas la roue.

---

## 0. Décision d'architecture fondatrice

**Fondation : OpenJarvis** (`https://github.com/open-jarvis/OpenJarvis`)

Ce qu'il nous donne gratuitement :
- Abstraction `InferenceEngine` unifiée : Ollama / vLLM / llama.cpp en local, Anthropic / OpenAI / Google en cloud, interchangeables.
- Routing hybride local↔cloud par analyse de complexité de la requête (les requêtes simples restent locales et gratuites, les complexes montent vers Claude).
- 8 agents built-in sur 3 modes d'exécution : **on-demand**, **scheduled** (cron), **continuous** (moniteur 24/7 avec compression mémoire).
- Scheduler intégré (`jarvis scheduler`) pour les tâches nocturnes.
- Mémoire vectorielle locale (`jarvis memory index`) pour indexer documents et projets.
- Connecteur Google (`jarvis connect gdrive` : Gmail, Calendar, Tasks en un seul OAuth).
- Import des skills OpenClaw (~13 700 skills) et Hermes (~150) via le standard agentskills.io → **ma flotte d'agents existante se branche directement**.
- API serveur FastAPI + SSE compatible OpenAI (`jarvis serve`) → notre UI custom s'y connecte.
- Télémétrie énergie/coût/latence (utile pour optimiser ce qui tourne la nuit).

**Ce que NOUS construisons (le repo `jarvis-suit/`)** : la couche "Tony Stark" — orchestration
du quotidien, contrôle du poste de travail, gestion multi-projets, et l'interface.

---

## 1. Architecture globale

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS UI (Tauri + React)                 │
│   Dashboard HUD · Chat · Mission Control · Night Report      │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket / SSE
┌──────────────────────────▼──────────────────────────────────┐
│              JARVIS CORE (FastAPI, notre code)               │
│  ┌────────────┐ ┌────────────┐ ┌──────────────────────────┐ │
│  │ Event Bus  │ │ Orchestrator│ │ Policy & Permission Layer│ │
│  │ (Redis/    │ │ (routing des│ │ (qui a le droit de faire │ │
│  │  in-proc)  │ │  agents)    │ │  quoi, quand, budget)    │ │
│  └────────────┘ └────────────┘ └──────────────────────────┘ │
└───────┬──────────────┬───────────────────┬──────────────────┘
        │              │                   │
┌───────▼──────┐ ┌─────▼────────┐ ┌────────▼─────────────┐
│  OpenJarvis  │ │ Desktop      │ │  Night Shift Manager │
│  (inférence, │ │ Controller   │ │  (projets parallèles,│
│  scheduler,  │ │ (fenêtres,   │ │  sessions Claude Code│
│  mémoire,    │ │  écrans,     │ │  headless, rapports) │
│  skills)     │ │  apps, audio)│ │                      │
└──────────────┘ └──────────────┘ └──────────────────────┘
```

**Principes non négociables :**
1. **Event-driven** : tout est événement (`wake_up`, `mail.received`, `project.task_done`, `night.report_ready`). Les agents s'abonnent au bus. Pas de spaghetti d'appels directs.
2. **Chaque agent = un contrat** : entrée typée (Pydantic), sortie typée, budget (tokens/temps/€), permissions déclarées. Un agent sans contrat ne tourne pas.
3. **Local par défaut** : triage de mails, résumés, classification → modèle local (Qwen 3.x via Ollama). Raisonnement complexe, code, planification → Claude via API.
4. **Tout est loggé et rejouable** : chaque action d'agent écrit dans un journal SQLite (qui, quoi, pourquoi, coût). C'est la base du Night Report et du debug.

---

## 2. Stack technique

| Couche | Choix | Pourquoi |
|---|---|---|
| Fondation agents | OpenJarvis (Python 3.11+, uv) | Voir §0 |
| Core / API | FastAPI + Pydantic v2 | Cohérent avec OpenJarvis, typage fort |
| Event bus | Redis Streams (ou bus in-process au début) | Simple, persistant, rejouable |
| Base de données | SQLite (WAL) → Postgres si besoin | Zéro ops au départ |
| Inférence locale | Ollama (Qwen 3.x 4–8B selon GPU) | Auto-détecté par `jarvis init` |
| Inférence cloud | Anthropic API (claude-sonnet-4-6 par défaut) | Meilleur rapport qualité/prix pour l'orchestration |
| UI | Tauri 2 + React + TypeScript + Tailwind | Natif, léger, cohérent avec le desktop app OpenJarvis |
| Data viz UI | Recharts + framer-motion | HUD animé |
| Voix (STT) | whisper.cpp local (faster-whisper) | Local-first |
| Voix (TTS) | Piper (local) ; option Cartesia/ElevenLabs (cloud) pour la voix "JARVIS" | Le digest OpenJarvis supporte déjà Cartesia |
| Contrôle desktop | Voir §4 (dépend de l'OS) | |
| Mails | Gmail API via connecteur OpenJarvis + IMAP fallback | |
| Nuit / projets | Claude Code en mode headless (`claude -p`) + git worktrees | Voir §5 |

**Question à trancher au setup (Claude Code doit demander) : OS cible ?**
- **Windows 11** : contrôle fenêtres via PowerShell + pywin32/pygetwindow, multi-écrans via `screeninfo`, startup via Task Scheduler.
- **Linux (X11/Wayland)** : `wmctrl`/`xdotool` (X11) ou `swaymsg`/portails (Wayland), startup via systemd user units.
- **macOS** : AppleScript/JXA + `yabai` optionnel, startup via launchd.
Le Desktop Controller doit être une interface abstraite avec un backend par OS (on n'implémente que celui de la machine cible en Phase 1).

---

## 3. La flotte d'agents

### 3.1 Agents existants (à importer via skills OpenClaw / à adapter)
- Mes agents OpenClaw actuels (automatisations perso/pro, canal Telegram) → importés via `jarvis skill sync` puis wrappés dans le contrat d'agent JARVIS.
- Le canal **Telegram reste une interface d'entrée/sortie** : JARVIS doit pouvoir me notifier et recevoir des ordres via Telegram quand je ne suis pas au PC.

### 3.2 Nouveaux agents (à construire)

| Agent | Mode | Rôle | Modèle |
|---|---|---|---|
| **ATLAS** — Wake-Up Orchestrator | scheduled + déclenchable | Séquence de réveil complète (§4) : détecte le login/l'heure, lance le profil de journée | local |
| **HERMES** — Mail Triage | scheduled (toutes les 15 min) + on-demand | Scanne les mails, classe (urgent / action / info / spam), résume, propose des brouillons de réponse. NE JAMAIS envoyer sans validation | local pour classer, cloud pour rédiger |
| **VULCAN** — Night Shift Manager | continuous (fenêtre 23h–7h) | Fait avancer les projets pendant le sommeil (§5) | cloud (Claude Code headless) |
| **ORACLE** — Daily Briefing | scheduled (au wake-up) | Briefing parlé + visuel : mails critiques, calendrier, météo, état des projets, ce que VULCAN a fait cette nuit | local + TTS |
| **SENTINEL** — System & Security Monitor | continuous | Surveille CPU/GPU/RAM/disque/température, processus anormaux, échecs des autres agents ; coupe VULCAN si la machine surchauffe | local |
| **SCRIBE** — Memory Keeper | scheduled (nuit) | Indexe les nouveaux documents/notes/code dans la mémoire vectorielle, compresse les vieux souvenirs, maintient un "état du monde" | local |
| **DAEDALUS** — Project Planner | on-demand | Prend un objectif flou → le décompose en backlog de tâches exécutables par VULCAN, avec critères d'acceptation | cloud |
| **ECHO** — Voice Interface | continuous (hotword) | Wake-word "Jarvis", STT → orchestrateur → TTS | local |
| **QUARTERMASTER** — Budget & Telemetry | scheduled (quotidien) | Agrège la télémétrie OpenJarvis : coût API, watts, latences ; alerte si dérive | local |

### 3.3 Contrat d'agent (à implémenter en Phase 1, tout le reste en dépend)

```python
class AgentContract(BaseModel):
    name: str
    mode: Literal["on_demand", "scheduled", "continuous"]
    permissions: list[Permission]      # ex: MAIL_READ, MAIL_DRAFT, SHELL_SANDBOXED, FS_PROJECT_DIRS
    budget: Budget                     # max_tokens_day, max_usd_day, max_runtime_min
    escalation: EscalationPolicy      # quand demander confirmation humaine (Telegram/UI)
    inputs: type[BaseModel]
    outputs: type[BaseModel]
```

---

## 4. Séquence de réveil (ATLAS) — le moment "Good morning, sir"

**Déclencheurs** : login de session, heure programmée, commande vocale, bouton UI, ou message Telegram "jarvis debout".

**Concept clé : les Day Profiles** (fichiers TOML dans `profiles/`) :

```toml
# profiles/deep-work.toml
[layout]
screen_1 = ["vscode:~/projets/projet-actif", "terminal"]
screen_2 = ["chrome:profile=perso:tabs=[calendar,gmail]", "obsidian"]

[apps]
launch = ["spotify:playlist=focus"]
kill = ["discord", "steam"]

[briefing]
voice = true
include = ["mails_urgents", "calendrier", "night_report", "meteo"]

[focus]
do_not_disturb = true
```

**Séquence exécutée :**
1. SENTINEL check santé machine (disque, updates en attente, batterie).
2. Chargement du Day Profile (choisi selon le calendrier du jour, ou demandé vocalement).
3. Desktop Controller : lance les apps, ouvre les URLs dans les bons profils navigateur, **positionne chaque fenêtre sur le bon écran** (API par OS, cf. §2).
4. HERMES : scan mail flash → top 5 urgents.
5. ORACLE : briefing parlé (TTS) + panneau briefing dans l'UI : "Bonjour. 3 mails demandent une action. VULCAN a terminé 4 tâches cette nuit, 1 est bloquée et attend ta décision. Premier rendez-vous à 10h."
6. Ouverture du **Mission Control** (UI) avec le Night Report en premier plan.

---

## 5. Night Shift (VULCAN) — les projets qui avancent pendant le sommeil

C'est le module le plus puissant et le plus dangereux. Architecture stricte :

### 5.1 Modèle d'exécution
- Chaque projet vit dans son repo git. VULCAN travaille **uniquement dans des git worktrees dédiés** (`.jarvis/worktrees/<tache>`), jamais sur `main`.
- Pour chaque tâche du backlog (produit par DAEDALUS ou par moi), VULCAN lance une session **Claude Code headless** : `claude -p "<tâche>" --output-format stream-json` dans le worktree, avec permissions limitées au dossier.
- Chaque tâche produit obligatoirement : une branche + un commit + un **rapport de tâche** (ce qui a été fait, tests passés, doutes, questions).
- **Rien n'est mergé automatiquement.** Le matin, je review les PR/branches depuis Mission Control (diff visuel + rapport). Merge = un clic, mais un clic HUMAIN.

### 5.2 Garde-fous (non négociables)
- Sandbox : exécution dans un conteneur/dossier jail limité aux répertoires projets déclarés. Aucun accès à `~/.ssh`, aux tokens, aux dossiers persos.
- Budget dur par nuit : `max_usd_night` (ex. 5 €) et `max_tasks_night` (ex. 6). QUARTERMASTER coupe au-delà.
- SENTINEL tue VULCAN si : température GPU > seuil, RAM > 90 %, ou heure > heure de réveil - 30 min.
- File de blocages : si une tâche exige une décision (choix d'archi, credentials, ambiguïté), VULCAN la met en `BLOCKED` avec une question précise → apparaît dans le briefing du matin. Il ne devine jamais sur les sujets critiques.
- Journal complet de chaque commande shell exécutée.

### 5.3 Night Report
Généré à la fin de la fenêtre nocturne : tâches faites/bloquées/échouées, diffs, coût total, temps par tâche, suggestions pour la nuit suivante. Affiché par ORACLE au réveil + envoyé sur Telegram.

---

## 6. HERMES — Triage mail

- Connexion via le connecteur Google d'OpenJarvis (`jarvis connect gdrive`).
- Pipeline : fetch → dédup → classification locale (urgent / action requise / info / newsletter / spam) → résumé 1 ligne → score de priorité.
- Pour les mails "action requise" : génération d'un **brouillon** de réponse (cloud), stocké en draft Gmail, jamais envoyé seul.
- Règles apprises : je peux corriger une classification dans l'UI → la correction alimente un petit dataset local (l'optimisation de skills d'OpenJarvis via traces sert exactement à ça).
- Alerte immédiate (Telegram + toast UI) uniquement pour la catégorie urgent, définie par des règles que je contrôle (expéditeurs VIP, mots-clés, deadlines).

---

## 7. Interface — "Mission Control"

**Stack** : Tauri 2 + React + TypeScript + Tailwind + framer-motion + Recharts. Connexion au Core via WebSocket.

**Direction artistique** : HUD sombre type Stark Industries — fond quasi noir, accents cyan/ambre, glassmorphism léger, micro-animations, typographie mono pour les données. Mais lisible avant d'être joli : c'est un outil quotidien.

**Écrans :**
1. **Dashboard (HUD)** : horloge/météo, arc de statut des agents (vert/ambre/rouge), flux d'événements en temps réel, gauges CPU/GPU/RAM/température, coût API du jour, prochain événement calendrier.
2. **Mission Control (projets)** : un kanban par projet (Backlog → In Progress → Review → Done), les tâches VULCAN avec leur diff et rapport, boutons Approve/Reject/Retry, file des blocages.
3. **Inbox triage** : les mails classés, résumés, brouillons proposés, correction de classification en un clic.
4. **Chat JARVIS** : conversation avec l'orchestrateur (texte + voix), avec affichage des actions qu'il entreprend en direct (tool calls visibles).
5. **Night Report** : le rapport du matin, visuel, avec timeline de la nuit.
6. **Settings** : Day Profiles, budgets, permissions par agent, planning du scheduler.

---

## 8. Sécurité & vie privée (couche transverse)

- Secrets dans un vault local (fichier chiffré age/sops ou keyring OS), jamais en clair dans les configs, jamais accessibles aux agents sandboxés.
- Matrice de permissions par agent (§3.3) appliquée par le Core, pas par bonne volonté des agents.
- Tout contenu mail traité localement par défaut ; seuls des extraits explicitement nécessaires montent au cloud (et c'est loggé).
- Mode "invité" : un raccourci qui fige JARVIS (pas de TTS, pas de notifications, écran neutre) quand quelqu'un d'autre utilise le PC.
- Kill switch physique : hotkey globale qui stoppe tous les agents continus.

---

## 9. Roadmap d'implémentation (ordre pour Claude Code)

> **MODE D'EXÉCUTION : BUILD COMPLET AUTONOME.**
> Pas de pression de délai, la qualité prime sur la vitesse. Claude Code construit les
> **5 phases en entier**, dans l'ordre, sans attendre de validation humaine entre les phases.
> Règles de ce mode :
> - Tout ce qui exige une intervention humaine (OAuth Google, clés API, token Telegram,
>   calibration des écrans, credentials quelconques) n'est **PAS bloquant** : implémenter le
>   module complet, le brancher derrière une config manquante, et l'inscrire dans
>   `docs/MANUAL_SETUP.md` — la checklist exhaustive de ce que je ferai à la main à la fin.
> - Chaque module doit avoir un **mode mock/demo** (données factices) pour être testable
>   sans credentials : l'Inbox avec de faux mails, VULCAN en dry-run sur un repo d'exemple,
>   ORACLE avec un briefing fictif. `make demo` lance l'ensemble en mode mock.
> - Tests automatisés obligatoires à chaque module (pytest + vitest) ; la CI locale
>   (`make check`) doit passer avant chaque commit. C'est le filet de sécurité qui remplace
>   ma review continue.
> - **Signal de fin** : quand les 5 phases sont terminées, générer `docs/HANDOVER.md`
>   (état complet, ce qui marche en mock, ce qui attend la checklist manuelle, limites connues,
>   suggestions) et me notifier clairement. Ensuite seulement, on branche le réel ensemble.
> - VULCAN inclus dans le build, mais livré **désarmé** : dry-run par défaut
>   (`night_shift.enabled = false` dans la config), activation manuelle après la phase de
>   branchement. Aucune session nocturne réelle ne doit pouvoir démarrer avant ça.

### Phase 1 — Squelette (fondations)
1. `git init jarvis-suit`, structure monorepo : `core/`, `agents/`, `desktop/`, `ui/`, `profiles/`, `docs/`.
2. Installer OpenJarvis comme dépendance, `jarvis init` (auto-détection hardware), vérifier `jarvis doctor`.
3. Core FastAPI : event bus in-process, journal SQLite, AgentContract + Permission layer, endpoint WebSocket.
4. Desktop Controller : interface abstraite + backend de l'OS cible (lancer app, ouvrir URL, déplacer/redimensionner fenêtre sur un écran donné, kill app). Tests manuels sur 2 écrans.
5. UI minimale : Dashboard avec flux d'événements live + statut agents.

### Phase 2 — Le réveil
6. Day Profiles (parser TOML + validation).
7. ATLAS : séquence complète (§4) sans la voix.
8. HERMES v1 : OAuth Google, fetch, classification locale, résumés, panneau Inbox dans l'UI.
9. ORACLE v1 : briefing textuel dans l'UI + notification Telegram.

### Phase 3 — La nuit
10. DAEDALUS : décomposition objectif → backlog (format tâche exécutable).
11. VULCAN : worktrees, sessions Claude Code headless, rapports de tâche, garde-fous budget/température (avec SENTINEL v1).
12. Night Report + écran Mission Control complet (review de diffs, approve/reject).

### Phase 4 — Les sens
13. ECHO : wake-word + whisper.cpp + TTS Piper ; ORACLE devient parlé.
14. HERMES v2 : brouillons de réponse + apprentissage des corrections.
15. QUARTERMASTER + dashboard télémétrie (données OpenJarvis).

### Phase 5 — Polish & folies
16. Animations HUD, thèmes, raccourcis globaux, mode invité, packaging (installeur + démarrage auto au boot).

**Definition of Done par phase** : tests (pytest + vitest), doc dans `docs/`, démo scriptée (`make demo-phaseN`).

---

## 10. Idées folles (backlog long terme)

- **JARVIS proactif contextuel** : il voit (avec permission) la fenêtre active et propose : "Tu débogues ce module depuis 40 min, veux-tu que je lance une analyse en parallèle ?"
- **Jumeau vocal streaming** : conversation continue mains libres pendant que tu codes, JARVIS prend des notes et crée les tâches à la volée.
- **Mur d'écran ambiant** : quand tu quittes le PC, les écrans passent en mode "salle de contrôle" (globes, flux, métriques) — inutile et magnifique.
- **Agent négociateur d'agenda** : il propose des créneaux et rédige les mails de replanification tout seul (validation humaine).
- **Mode "Protocole Maison"** : intégration Home Assistant — lumières qui suivent le Day Profile, "Jarvis, protocole cinéma".
- **Digest géo-temporel** : le matin d'un départ (train/avion détecté dans les mails), briefing spécial trajet + check-in + météo destination.
- **Simulation "What-if"** : "Jarvis, si je consacre 3 nuits à ce projet, où en serai-je vendredi ?" → DAEDALUS simule le backlog.
- **Auto-amélioration supervisée** : une nuit par semaine, VULCAN travaille sur... le code de JARVIS lui-même (branche `self-improve/`, review humaine obligatoire, évidemment).
- **Multi-machine** : JARVIS orchestre PC fixe + laptop + un petit serveur, et route les jobs vers la machine la plus adaptée (la télémétrie énergie d'OpenJarvis rend ça naturel).
- **Interface AR/gestuelle** : contrôle du HUD par gestes via webcam (MediaPipe) — le vrai délire Tony Stark.

---

## 11. Brief de démarrage pour Claude Code (à coller tel quel)

> Tu es l'ingénieur principal du projet **jarvis-suit** décrit dans `JARVIS_MASTER_SPEC.md`.
> Mode : **build complet autonome** (voir l'encadré en tête de la section 9). Pas de pression
> de délai : construis les 5 phases en entier, dans l'ordre, proprement.
> Seule question à me poser AVANT de commencer : l'OS cible et la configuration d'écrans
> (nombre + résolutions). Ensuite, avance sans attendre ma validation entre les phases.
> Tout ce qui nécessite mes credentials ou une action manuelle : implémente le module,
> mets-le derrière un mode mock/demo fonctionnel, et consigne l'étape dans
> `docs/MANUAL_SETUP.md`. Ne me sollicite en cours de route que si un choix d'architecture
> majeur est réellement bloquant — sinon, décide, documente la décision dans
> `docs/DECISIONS.md`, et continue.
> Contraintes dures : typage strict (mypy/Pydantic), tests pour chaque module,
> `make check` vert avant chaque commit, aucune permission implicite pour les agents,
> aucun secret en clair, VULCAN livré désarmé (dry-run par défaut, `night_shift.enabled = false`),
> et rien de mergé sur main sans mon accord. À chaque fin de session, mets à jour
> `docs/JOURNAL.md` (état, décisions, questions ouvertes).
> Quand tout est terminé : génère `docs/HANDOVER.md`, lance `make demo` pour vérifier
> l'ensemble en mode mock, et préviens-moi — on branchera le réel ensemble à partir
> de la checklist `MANUAL_SETUP.md`.
