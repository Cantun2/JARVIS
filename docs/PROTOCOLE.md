# PROTOCOLE — exploitation & branchement de JARVIS (jarvis-suit)

Runbook ordonné, avec un **point de contrôle vérifiable** (« ✅ tu dois voir… ») à chaque étape.
Tout fonctionne en **mock** sans rien brancher ; le réel s'ajoute étape par étape, chacune isolée et
réversible (repasser à `JARVIS_MODE=mock` suffit à revenir en arrière).

> Règles d'or (non négociables) :
> 1. `make check` **vert** avant chaque commit.
> 2. **VULCAN reste désarmé** tant que la §6 n'est pas faite consciemment.
> 3. Rien n'est mergé sur `main`/`master` sans ta validation. Les secrets vont dans `.env` (jamais commité).

---

## 0. TL;DR — le chemin le plus court (mock, aucun credential)
```bash
make install          # venv + dépendances
make doctor           # état de la machine
make demo             # séquence de réveil en mock
# HUD live (2 terminaux) :
cd ui && npm install && cd ..
make serve            # terminal 1 : API + WebSocket
make ui-dev           # terminal 2 : http://localhost:5173
```
✅ `make demo` finit par « ✓ Séquence de réveil cohérente. Démo OK. »

---

## 1. Prérequis machine
- Python ≥ 3.11 (3.12 présent), Node ≥ 20 (v22 présent), `git`.
- Rien d'autre n'est requis pour le mock. Le reste (Rust, Ollama, webkit2gtk…) n'est demandé qu'au
  branchement du réel — voir `docs/MANUAL_SETUP.md`.

## 2. Bootstrap
```bash
make install                  # crée .venv, installe le projet + outils de dev
cp .env.example .env          # facultatif ; en mock, les valeurs par défaut suffisent
```
✅ `.venv/` existe ; `make doctor` s'exécute sans erreur.

## 3. Vérification en mock (3 portes de qualité)
```bash
make doctor    # outils présents/absents + mode effectif (doit afficher: Mode=mock, inférence=mock)
make check     # ruff + mypy strict + pytest + vitest
make demo      # joue le réveil ATLAS→HERMES→ORACLE et vérifie la séquence
```
✅ `make check` : « All checks passed » + 91 pytest + 26 vitest verts.
✅ `make demo` : flux d'événements coloré, 3 écrans placés, briefing ORACLE poussé sur (Mock)Telegram.

## 4. Lancer le HUD en local
Terminal 1 :
```bash
make serve                    # API sur http://127.0.0.1:8000  (port occupé ? voir §8)
```
Terminal 2 :
```bash
make ui-dev                   # HUD sur http://localhost:5173
```
Sanity check API (terminal 3) :
```bash
curl -s http://127.0.0.1:8000/api/health
curl -s -X POST http://127.0.0.1:8000/api/agents/ATLAS/run \
     -H 'Content-Type: application/json' -d '{"profile":"deep-work"}'
```
✅ Le HUD montre le badge « connecté », l'arc de statut des agents, et le flux d'événements en direct
quand tu déclenches ATLAS.

---

## 5. Passer au RÉEL — étape par étape (chacune indépendante et testable)

Édite `.env`, mets `JARVIS_MODE=real`, puis n'active qu'**un** bloc à la fois et re-teste avant le suivant.
Rollback à tout moment : `JARVIS_MODE=mock`.

### 5.1 Inférence — choisis A (cloud, simple) ou B (local, gratuit mais lent ici)

**A) Cloud Anthropic (recommandé pour démarrer — raisonnement/rédaction)**
```bash
.venv/bin/pip install -e ".[cloud]"
```
`.env` :
```
JARVIS_MODE=real
ANTHROPIC_API_KEY=sk-ant-...
JARVIS_CLOUD_MODEL=claude-sonnet-4-6
```

**B) Local via OpenJarvis + Ollama (pas de GPU ici ⇒ lent, petit modèle)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                       # uv
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh        # Rust (build natif OpenJarvis)
curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen3:4b # modèle CPU
jarvis serve                                                          # serveur OpenAI-compatible
```
`.env` : `JARVIS_MODE=real` et `JARVIS_INFERENCE_URL=http://localhost:8080/v1`

Test (commun A/B) :
```bash
make serve
curl -s http://127.0.0.1:8000/api/health     # inference_backend doit passer à "openjarvis"
```
✅ `inference_backend` ≠ `mock`. HERMES résumera via le vrai modèle.

### 5.2 Mails réels (HERMES) — OAuth Google
```bash
jarvis connect gdrive        # un seul OAuth : Gmail + Calendar + Tasks
```
Puis brancher le fetch réel à la place des fixtures `src/jarvis/agents/mocks/mail_fixtures.py`
(remplacer la source dans `Hermes.run`). Personnalise tes règles VIP/urgence (`VIP_SENDERS`).
✅ HERMES classe tes vrais mails ; toujours **aucun envoi** (permission `MAIL_SEND` refusée par design).

### 5.3 Telegram (notifications + escalades)
1. @BotFather → créer un bot → token. 2. Récupérer ton `chat_id`.
`.env` :
```
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
```
Test : lance ORACLE, tu dois recevoir le briefing sur Telegram.
✅ Sans token → `MockTelegram` (aucun envoi). Avec token → message réel reçu.

### 5.4 Desktop réel + placement multi-écran (GNOME/Wayland)
```bash
cd extensions
zip -r jarvis-desktop.zip jarvis-desktop@jarvis-suit.local
gnome-extensions install --force jarvis-desktop.zip
gnome-extensions enable jarvis-desktop@jarvis-suit.local
# puis SE DÉCONNECTER / RECONNECTER (le Shell ne recharge pas à chaud sous Wayland)
gdbus introspect --session --dest org.jarvis.DesktopExt --object-path /org/jarvis/DesktopExt
```
`.env` : `JARVIS_DESKTOP_BACKEND=gnome` (+ `JARVIS_MODE=real`).
Adapte les profils navigateur dans `profiles/*.toml` (`chrome:profile=perso`) à tes vrais profils.
✅ `make doctor` montre l'extension détectée ; ATLAS place réellement les fenêtres sur tes 3 écrans.
   Sans extension : lancement/URLs OK, placement pixel-précis dégradé (pas d'erreur).

---

## 6. Activer VULCAN (Night Shift) — protocole de sécurité, **plus tard**
VULCAN est livré **désarmé** (`enabled=False` dans `src/jarvis/agents/vulcan.py`). Ne l'active qu'après :
1. avoir installé la CLI `claude` (sessions headless) ;
2. avoir vérifié la sandbox (dossiers projets déclarés, budget nuit, garde-fous SENTINEL) ;
3. avoir relu le module en connaissance de cause.
Alors seulement : passer `enabled=True` de façon contrôlée + config `night_shift.enabled=true`.
> Tant que ce n'est pas fait, l'orchestrateur **refuse** VULCAN (`AgentDisarmed`) et aucune session
> nocturne réelle ne peut démarrer. C'est voulu.

---

## 7. Boucle de développement (pour continuer le build)
```bash
git checkout -b phase-2-...        # jamais bosser directement sur master
# ... code ...
make fmt                            # ruff format + autofix
make check                          # DOIT être vert avant de committer
git commit ...                      # message clair ; VULCAN reste désarmé
```
- Mets à jour `docs/JOURNAL.md` en fin de session (état, décisions, questions ouvertes).
- Toute décision d'archi → une entrée dans `docs/DECISIONS.md`.
- Rien mergé sur `master` sans validation humaine.

## 8. Dépannage
- **Port 8000 déjà pris** : `JARVIS_PORT=8137 make serve`, ou trouver le coupable
  `ss -ltnp | grep :8000` puis `kill <pid>`.
- **`tauri dev` échoue** : normal (webkit2gtk absent). Utilise `make ui-dev` (navigateur) ; packaging en §MANUAL_SETUP.
- **Placement fenêtres sans effet** : extension GNOME non installée/activée, ou pas de relog Wayland (§5.4).
- **Inférence lente** : pas de GPU → préfère le cloud (§5.1 A) pour le lourd, garde le local pour le léger.
- **Reset état local** : `make clean` (supprime caches + `var/*.db`).

## 9. Roadmap (prochaines phases, dans l'ordre suggéré)
- **Phase 2 (réel)** : §5.1 + §5.2 branchés, ORACLE enrichi, corrections de classification apprises.
- **Phase 3 (nuit)** : DAEDALUS (objectif→backlog), puis VULCAN opérationnel (worktrees + Claude Code
  headless + garde-fous SENTINEL), écran Mission Control (review de diffs).
- **Phase 4 (sens)** : ECHO (whisper.cpp + Piper) → ORACLE parlé ; HERMES v2 (brouillons) ; QUARTERMASTER.
- **Phase 5 (polish)** : animations HUD, mode invité, raccourcis globaux, packaging Tauri + démarrage auto.

## 10. Aide-mémoire commandes
| Commande | Effet |
|---|---|
| `make install` | venv + dépendances |
| `make doctor` | diagnostic environnement (mock vs réel) |
| `make check` | ruff + mypy strict + pytest + vitest |
| `make demo` | séquence de réveil en mock (auto-vérifiée) |
| `make serve` | API + WebSocket (`:8000`) |
| `make ui-dev` | HUD navigateur (`:5173`) |
| `make fmt` | formate + autofix |
| `make clean` | purge caches + base locale |

Endpoints : `GET /api/health` · `GET /api/agents` · `POST /api/agents/{name}/run` · `GET /api/events?since=` · `WS /ws`.
