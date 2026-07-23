mod crypto;
mod db;
mod ssh;

use db::{Database, Host};
use ssh::SshManager;
use std::path::PathBuf;
use std::sync::Arc;
use tauri::Manager;

/// Application state — holds the database and encryption key.
/// Database has its own internal mutex, so this struct is thread-safe as-is.
pub struct AppState {
    pub db: Database,
    pub crypto_key: [u8; 32],
    pub app_dir: PathBuf,
}

// ── Host CRUD Commands ────────────────────────────────────────────

#[tauri::command]
fn get_all_hosts(state: tauri::State<'_, AppState>) -> Result<Vec<Host>, String> {
    state.db.get_all_hosts(&state.crypto_key)
}

#[tauri::command]
fn search_hosts(
    state: tauri::State<'_, AppState>,
    keyword: String,
) -> Result<Vec<Host>, String> {
    state.db.search_hosts(&keyword, &state.crypto_key)
}

#[tauri::command]
fn add_host(state: tauri::State<'_, AppState>, host: Host) -> Result<Host, String> {
    let id = state.db.add_host(&host, &state.crypto_key)?;
    state.db.get_host(id, &state.crypto_key)
}

#[tauri::command]
fn update_host(state: tauri::State<'_, AppState>, id: i64, host: Host) -> Result<(), String> {
    state.db.update_host(id, &host, &state.crypto_key)
}

#[tauri::command]
fn delete_host(state: tauri::State<'_, AppState>, id: i64) -> Result<(), String> {
    state.db.delete_host(id)
}

// ── SSH Commands ──────────────────────────────────────────────────

#[tauri::command]
async fn ssh_connect(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    ssh_manager: tauri::State<'_, Arc<SshManager>>,
    host_id: i64,
) -> Result<(), String> {
    let host = state.db.get_host(host_id, &state.crypto_key)?;
    ssh_manager.connect(host, app_handle).await
}

#[tauri::command]
async fn ssh_send(
    ssh_manager: tauri::State<'_, Arc<SshManager>>,
    host_id: i64,
    data: Vec<u8>,
) -> Result<(), String> {
    ssh_manager.send(host_id, data).await
}

#[tauri::command]
async fn ssh_disconnect(
    ssh_manager: tauri::State<'_, Arc<SshManager>>,
    host_id: i64,
) -> Result<(), String> {
    ssh_manager.disconnect(host_id).await
}

// ── App Entry Point ───────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let app_dir = app
                .path()
                .app_data_dir()
                .expect("Failed to get app data directory");

            std::fs::create_dir_all(&app_dir).expect("Failed to create app data dir");

            let crypto_key =
                crypto::get_or_create_key(&app_dir).expect("Failed to initialize encryption key");

            let db_path = app_dir.join("sshive.db");
            let db = Database::new(&db_path).expect("Failed to initialize database");

            let ssh_manager = Arc::new(SshManager::new());

            app.manage(AppState {
                db,
                crypto_key,
                app_dir,
            });
            app.manage(ssh_manager);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_all_hosts,
            search_hosts,
            add_host,
            update_host,
            delete_host,
            ssh_connect,
            ssh_send,
            ssh_disconnect,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
