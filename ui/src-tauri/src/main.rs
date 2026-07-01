// Packaging différé, cf docs/MANUAL_SETUP.md.
// webkit2gtk absent sur la machine de dev : ce binaire n'est PAS compilé ici.
// Fenêtre par défaut (déclarée dans tauri.conf.json), aucun handler custom.

// Empêche l'ouverture d'une console Windows en release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("erreur au lancement de l'application JARVIS");
}
