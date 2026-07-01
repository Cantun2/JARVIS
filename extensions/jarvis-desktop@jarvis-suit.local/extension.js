// JARVIS Desktop — extension GNOME Shell 46 (GJS, ESM).
//
// Sous Wayland, un client externe ne peut ni énumérer ni déplacer des fenêtres : seul le
// compositeur (GNOME Shell) en a le droit. Cette extension exporte l'interface D-Bus
// `org.jarvis.DesktopExt` sur `/org/jarvis/DesktopExt`, appelée par le backend Python
// (`src/jarvis/desktop/gnome_extension.py`). C'est le SEUL moyen fiable de placement
// pixel-précis multi-moniteur sous Wayland.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const IFACE = `
<node>
  <interface name="org.jarvis.DesktopExt">
    <method name="ListWindows">
      <arg type="a(sssiiiii)" direction="out" name="windows"/>
    </method>
    <method name="ListMonitors">
      <arg type="a(iiiii)" direction="out" name="monitors"/>
    </method>
    <method name="MoveWindow">
      <arg type="s" direction="in" name="id"/>
      <arg type="i" direction="in" name="monitor"/>
      <arg type="i" direction="in" name="x"/>
      <arg type="i" direction="in" name="y"/>
      <arg type="i" direction="in" name="w"/>
      <arg type="i" direction="in" name="h"/>
      <arg type="b" direction="out" name="ok"/>
    </method>
    <method name="FocusWindow">
      <arg type="s" direction="in" name="id"/>
      <arg type="b" direction="out" name="ok"/>
    </method>
    <method name="CloseWindow">
      <arg type="s" direction="in" name="id"/>
      <arg type="b" direction="out" name="ok"/>
    </method>
    <method name="GetWindowByPid">
      <arg type="i" direction="in" name="pid"/>
      <arg type="s" direction="out" name="id"/>
    </method>
    <signal name="WindowOpened">
      <arg type="s" name="id"/>
      <arg type="s" name="wm_class"/>
      <arg type="i" name="pid"/>
    </signal>
  </interface>
</node>`;

class DesktopService {
    constructor() {
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
    }

    export() {
        this._dbus.export(Gio.DBus.session, '/org/jarvis/DesktopExt');
    }

    unexport() {
        this._dbus.unexport();
    }

    emitWindowOpened(id, wmClass, pid) {
        this._dbus.emit_signal(
            'WindowOpened',
            new GLib.Variant('(ssi)', [String(id), String(wmClass), pid | 0])
        );
    }

    _windows() {
        // Fenêtres normales uniquement (on ignore docks, menus, etc.).
        return global.get_window_actors()
            .map(actor => actor.meta_window)
            .filter(win => win && win.get_window_type() === Meta.WindowType.NORMAL);
    }

    _findById(id) {
        for (const win of this._windows()) {
            if (String(win.get_id()) === String(id))
                return win;
        }
        return null;
    }

    // ------------------------------------------------------------- méthodes D-Bus
    ListWindows() {
        const out = [];
        for (const win of this._windows()) {
            const r = win.get_frame_rect();
            out.push([
                String(win.get_id()),
                win.get_wm_class() || '',
                win.get_title() || '',
                win.get_monitor(),
                r.x, r.y, r.width, r.height,
            ]);
        }
        return out;
    }

    ListMonitors() {
        const out = [];
        const n = global.display.get_n_monitors();
        for (let i = 0; i < n; i++) {
            const g = global.display.get_monitor_geometry(i);
            out.push([i, g.x, g.y, g.width, g.height]);
        }
        return out;
    }

    MoveWindow(id, monitor, x, y, w, h) {
        const win = this._findById(id);
        if (!win)
            return false;
        try {
            if (win.get_maximized())
                win.unmaximize(Meta.MaximizeFlags.BOTH);
            const n = global.display.get_n_monitors();
            if (monitor >= 0 && monitor < n && win.get_monitor() !== monitor)
                win.move_to_monitor(monitor);
            win.move_resize_frame(true, x, y, w, h);
            return true;
        } catch (_e) {
            return false;
        }
    }

    FocusWindow(id) {
        const win = this._findById(id);
        if (!win)
            return false;
        win.activate(global.get_current_time());
        return true;
    }

    CloseWindow(id) {
        const win = this._findById(id);
        if (!win)
            return false;
        win.delete(global.get_current_time());
        return true;
    }

    GetWindowByPid(pid) {
        for (const win of this._windows()) {
            if (win.get_pid() === pid)
                return String(win.get_id());
        }
        return '';
    }
}

export default class JarvisDesktopExtension extends Extension {
    enable() {
        this._service = new DesktopService();
        this._service.export();

        // Émet WindowOpened à chaque nouvelle fenêtre (défensif).
        this._createdId = global.display.connect('window-created', (_disp, win) => {
            try {
                this._service.emitWindowOpened(
                    String(win.get_id()),
                    win.get_wm_class() || '',
                    win.get_pid() || 0
                );
            } catch (_e) {
                // On ne casse jamais le Shell sur une fenêtre exotique.
            }
        });
    }

    disable() {
        if (this._createdId) {
            global.display.disconnect(this._createdId);
            this._createdId = null;
        }
        if (this._service) {
            this._service.unexport();
            this._service = null;
        }
    }
}
