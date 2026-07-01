# JARVIS Desktop — extension GNOME Shell

Extension GNOME Shell 46 qui expose une interface D-Bus (`org.jarvis.DesktopExt`)
permettant au backend `jarvis-suit` de **lister, déplacer, focaliser et fermer des
fenêtres** de façon **pixel-précise et multi-moniteur**.

## Pourquoi une extension ?

Sous **Wayland**, pour des raisons de sécurité, un client externe **ne peut pas**
déplacer/redimensionner les fenêtres des autres applications ni connaître leur position :
seul le compositeur (GNOME Shell) en a le droit. Les vieux outils X11 (`wmctrl`, `xdotool`)
ne fonctionnent donc pas de façon fiable.

Cette extension, exécutée **dans** le Shell, est le **seul moyen fiable de placement
pixel-précis multi-moniteur sous Wayland**. Le backend Python la pilote via `gdbus`.

## Interface D-Bus

- Bus name : `org.jarvis.DesktopExt`
- Objet : `/org/jarvis/DesktopExt`
- Méthodes :
  - `ListWindows() -> a(sssiiiii)` : `(id, wm_class, title, monitor, x, y, w, h)`
  - `ListMonitors() -> a(iiiii)` : `(index, x, y, w, h)`
  - `MoveWindow(s id, i monitor, i x, i y, i w, i h) -> b`
  - `FocusWindow(s id) -> b`
  - `CloseWindow(s id) -> b`
  - `GetWindowByPid(i pid) -> s` (id de fenêtre, `""` si introuvable)
- Signal : `WindowOpened(s id, s wm_class, i pid)`

L'`id` de fenêtre est `String(win.get_id())`, stable pour la durée de vie de la fenêtre.

## Installation

### Option A — depuis un zip (recommandé)

```bash
cd extensions
zip -r jarvis-desktop.zip jarvis-desktop@jarvis-suit.local
gnome-extensions install --force jarvis-desktop.zip
```

### Option B — copie manuelle

```bash
mkdir -p ~/.local/share/gnome-shell/extensions
cp -r extensions/jarvis-desktop@jarvis-suit.local \
      ~/.local/share/gnome-shell/extensions/
```

### Activation

```bash
gnome-extensions enable jarvis-desktop@jarvis-suit.local
```

Puis **fermez la session et reconnectez-vous** (relog) sous Wayland : GNOME Shell ne peut
pas être rechargé à chaud en session Wayland. (En session X11 uniquement, `Alt+F2` puis `r`
suffit — mais la cible du projet est Wayland.)

## Vérification

```bash
# L'interface doit répondre :
gdbus introspect --session --dest org.jarvis.DesktopExt \
  --object-path /org/jarvis/DesktopExt

# Lister les moniteurs vus par le Shell :
gdbus call --session --dest org.jarvis.DesktopExt \
  --object-path /org/jarvis/DesktopExt \
  --method org.jarvis.DesktopExt.ListMonitors

# Lister les fenêtres :
gdbus call --session --dest org.jarvis.DesktopExt \
  --object-path /org/jarvis/DesktopExt \
  --method org.jarvis.DesktopExt.ListWindows
```

Si `available()` du client Python renvoie `False`, c'est que l'extension n'est pas
activée ou que la session n'a pas été relancée : le backend dégrade alors proprement
(`move_window` renvoie `WindowPlacementResult(placed=False, reason="extension_unavailable")`).

## Journalisation / dépannage

```bash
# Logs du Shell (utile en cas d'erreur d'export D-Bus) :
journalctl --user -f -o cat /usr/bin/gnome-shell

# État de l'extension :
gnome-extensions info jarvis-desktop@jarvis-suit.local
```
