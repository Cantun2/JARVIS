# MANUAL_SETUP — checklist de branchement du réel

> Rien de ceci n'est requis pour `make demo` / `make check` (tout tourne en **mock**).
> Cette liste, c'est ce que **toi** feras à la main pour passer du mock au réel.
> Lance `make doctor` à tout moment pour voir ce qui est détecté sur la machine.

Machine cible détectée : Ubuntu 24.04, GNOME 46 **Wayland**, 3 écrans visés, **pas de GPU** (Intel iGPU).

## 0. Base de dev (déjà faisable maintenant)
- [x] `make install` — crée `.venv` et installe le projet + outils de dev.
- [x] `make check` — ruff + mypy strict + pytest (+ vitest si l'UI est installée).
- [x] `make demo` — joue la séquence de réveil en mock.
- [ ] UI : `cd ui && npm install` puis `make ui-dev` (navigateur) + `make serve` (API) dans deux terminaux.

## 1. Inférence
En mock, rien n'est nécessaire. Sur cette machine (CPU, pas de clé Anthropic) → **Ollama local**.

### a) Ollama local (recommandé — CPU, buildless) ✅
- [ ] Installer Ollama : `curl -fsSL https://ollama.com/install.sh | sh`.
- [ ] Tirer un petit modèle : `ollama pull qwen2.5:3b` (léger, adapté CPU).
- [ ] Dans `.env` : `JARVIS_MODE=real`, `JARVIS_OLLAMA_URL=http://localhost:11434`, `JARVIS_LOCAL_MODEL=qwen2.5:3b`.
- [ ] Vérifier : `make doctor` → `Backend inférence : ollama`. Note : le triage HERMES marche même si le
  modèle est lent (résumé best-effort avec repli). Baisse `limit` si besoin sur beaucoup de mails.

### b) OpenJarvis (serveur OpenAI-compatible) — optionnel
- [ ] Installer `uv` + Rust, lancer `jarvis serve`, puis `.env` : `JARVIS_MODE=real`,
  `JARVIS_INFERENCE_URL=http://localhost:8080/v1`.

### c) Cloud (Anthropic) — **différé** (pas de clé pour l'instant)
- [ ] Le jour venu : `pip install -e ".[cloud]"`, `ANTHROPIC_API_KEY=...` (backend cloud direct à ajouter).

## 2. Mails (HERMES) — OAuth Google
- [ ] `pip install -e ".[google]"` (google-api-python-client + auth).
- [ ] Créer un projet Google Cloud, activer l'API Gmail, créer des identifiants OAuth « Desktop »,
  télécharger le `credentials.json`.
- [ ] Générer un `token.json` autorisé (scope `gmail.readonly`) — via `jarvis connect gdrive` (OpenJarvis)
  ou un petit script `google-auth-oauthlib` (flow local une fois).
- [ ] Dans `.env` : `JARVIS_MODE=real`, `JARVIS_MAIL_BACKEND=gmail`,
  `GMAIL_CREDENTIALS_PATH=secrets/gmail_credentials.json`, `GMAIL_TOKEN_PATH=secrets/gmail_token.json`.
- [ ] `secrets/` est gitignoré. HERMES trie alors de vrais mails (lecture seule, jamais d'envoi).

## 3. Telegram (notifications / escalades)
- [ ] Créer un bot via @BotFather, récupérer le token.
- [ ] Dans `.env` : `TELEGRAM_BOT_TOKEN=...` et `TELEGRAM_CHAT_ID=...`.
- [ ] Sans token → `MockTelegram` (aucun envoi).

## 4. Desktop réel — placement multi-écran (GNOME/Wayland)
- [ ] Dans `.env` : `JARVIS_DESKTOP_BACKEND=gnome` (+ `JARVIS_MODE=real`).
- [ ] Installer l'extension de placement :
  ```bash
  cd extensions
  zip -r jarvis-desktop.zip jarvis-desktop@jarvis-suit.local
  gnome-extensions install --force jarvis-desktop.zip
  gnome-extensions enable jarvis-desktop@jarvis-suit.local
  ```
  Puis **se déconnecter/reconnecter** (le Shell ne recharge pas à chaud sous Wayland).
- [ ] Vérifier : `gdbus introspect --session --dest org.jarvis.DesktopExt --object-path /org/jarvis/DesktopExt`.
- [ ] Sans extension → lancement/URLs fonctionnent, placement pixel-précis dégradé (documenté).
- [ ] Adapter les profils navigateur dans `profiles/*.toml` (`chrome:profile=perso`) à tes vrais profils.

## 5. UI packagée (Tauri) — différé
- [ ] Installer : `sudo apt install libwebkit2gtk-4.1-dev build-essential curl libssl-dev` + Rust.
- [ ] `cd ui && npm run tauri build` (scaffold présent dans `ui/src-tauri/`).

## 6. VULCAN (Night Shift) — activation **manuelle** après branchement
- [ ] Installer la CLI Claude Code (`claude`) pour les sessions headless.
- [ ] N'activer qu'après revue : passer `Vulcan.contract.enabled=True` de façon contrôlée + config
  `night_shift.enabled=true`. **Aucune session nocturne réelle ne doit démarrer avant cette étape.**

## 7. Démarrage auto au login — différé
- [ ] systemd user unit lançant `jarvis-suit serve` (Phase 5 / polish).
