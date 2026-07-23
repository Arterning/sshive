use crate::db::Host;
use russh::client::{self, Handler};
use russh::{ChannelMsg, Disconnect};
use std::collections::HashMap;
use std::sync::Arc;
use tauri::{AppHandle, Emitter, Runtime};
use tokio::sync::{mpsc, Mutex};

/// Payload for the `ssh-data` event sent to the frontend.
#[derive(Clone, serde::Serialize)]
pub struct SshDataEvent {
    pub session_id: String,
    /// Base64-encoded data received from the SSH server.
    pub data: String,
}

/// Payload for the `ssh-closed` event.
#[derive(Clone, serde::Serialize)]
pub struct SshClosedEvent {
    pub session_id: String,
}

/// Payload for the `ssh-error` event.
#[derive(Clone, serde::Serialize)]
pub struct SshErrorEvent {
    pub session_id: String,
    pub error: String,
}

/// Handle to an active SSH session — used to send data and signal shutdown.
struct SessionHandle {
    sender: mpsc::Sender<Vec<u8>>,
    shutdown_tx: tokio::sync::oneshot::Sender<()>,
    _task: tokio::task::JoinHandle<()>,
}

/// Manages all active SSH sessions.
pub struct SshManager {
    sessions: Mutex<HashMap<String, SessionHandle>>,
}

impl SshManager {
    pub fn new() -> Self {
        SshManager {
            sessions: Mutex::new(HashMap::new()),
        }
    }

    pub async fn has_session(&self, host_id: i64) -> bool {
        let sessions = self.sessions.lock().await;
        sessions.contains_key(&host_id.to_string())
    }

    pub async fn connect<R: Runtime>(
        &self,
        host: Host,
        app_handle: AppHandle<R>,
    ) -> Result<(), String> {
        let session_id = host.id.unwrap_or(0).to_string();

        {
            let mut sessions = self.sessions.lock().await;
            if let Some(handle) = sessions.remove(&session_id) {
                let _ = handle.shutdown_tx.send(());
            }
        }

        let (send_tx, send_rx) = mpsc::channel::<Vec<u8>>(256);
        let (shutdown_tx, shutdown_rx) = tokio::sync::oneshot::channel::<()>();

        let host_clone = host.clone();
        let app_clone = app_handle.clone();
        let sid = session_id.clone();

        let task = tokio::spawn(async move {
            if let Err(e) =
                run_ssh_session(host_clone, send_rx, shutdown_rx, app_clone, &sid).await
            {
                let _ = app_handle.emit(
                    "ssh-error",
                    SshErrorEvent {
                        session_id: sid.clone(),
                        error: e,
                    },
                );
            }
        });

        let mut sessions = self.sessions.lock().await;
        sessions.insert(
            session_id,
            SessionHandle {
                sender: send_tx,
                shutdown_tx,
                _task: task,
            },
        );

        Ok(())
    }

    pub async fn send(&self, host_id: i64, data: Vec<u8>) -> Result<(), String> {
        let sessions = self.sessions.lock().await;
        let handle = sessions
            .get(&host_id.to_string())
            .ok_or_else(|| "Session not found".to_string())?;
        handle
            .sender
            .send(data)
            .await
            .map_err(|e| format!("Send error: {}", e))
    }

    pub async fn resize(
        &self,
        _host_id: i64,
        _cols: u32,
        _rows: u32,
    ) -> Result<(), String> {
        // TODO: implement PTY resize via a separate control channel
        Ok(())
    }

    pub async fn disconnect(&self, host_id: i64) -> Result<(), String> {
        let mut sessions = self.sessions.lock().await;
        if let Some(handle) = sessions.remove(&host_id.to_string()) {
            let _ = handle.shutdown_tx.send(());
        }
        Ok(())
    }

    pub async fn disconnect_all(&self) {
        let mut sessions = self.sessions.lock().await;
        for (_, handle) in sessions.drain() {
            let _ = handle.shutdown_tx.send(());
        }
    }
}

// ── RSSH Client Handler ──────────────────────────────────────────

struct ClientHandler;

impl Handler for ClientHandler {
    type Error = russh::Error;

    async fn check_server_key(
        &mut self,
        _server_public_key: &russh::keys::PublicKey,
    ) -> Result<bool, Self::Error> {
        // Auto-accept (same as Python's AutoAddPolicy)
        Ok(true)
    }
}

// ── SSH Session Loop ─────────────────────────────────────────────

async fn run_ssh_session<R: Runtime>(
    host: Host,
    mut send_rx: mpsc::Receiver<Vec<u8>>,
    mut shutdown_rx: tokio::sync::oneshot::Receiver<()>,
    app_handle: AppHandle<R>,
    session_id: &str,
) -> Result<(), String> {
    let sid = session_id.to_string();

    let config = Arc::new(client::Config::default());

    let addr = format!("{}:{}", host.host, host.port);

    // Connect
    let mut session = client::connect(config, addr.as_str(), ClientHandler)
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    // Authenticate
    let auth_success = if host.auth_type == "key" && !host.private_key_path.is_empty() {
        let key_data = tokio::fs::read_to_string(&host.private_key_path)
            .await
            .map_err(|e| format!("Cannot read key file: {}", e))?;

        let key = russh::keys::decode_secret_key(&key_data, None)
            .map_err(|e| format!("Failed to parse private key: {}", e))?;

        let key_with_hash = russh::keys::PrivateKeyWithHashAlg::new(Arc::new(key), None);

        session
            .authenticate_publickey(&host.username, key_with_hash)
            .await
            .map_err(|e| format!("Key authentication failed: {}", e))?
            .success()
    } else {
        session
            .authenticate_password(&host.username, &host.password)
            .await
            .map_err(|e| format!("Password authentication failed: {}", e))?
            .success()
    };

    if !auth_success {
        return Err("Authentication rejected".into());
    }

    // Open a shell channel
    let mut channel = session
        .channel_open_session()
        .await
        .map_err(|e| format!("Channel open failed: {}", e))?;

    // Request PTY — disable remote echo since xterm.js handles local display
    channel
        .request_pty(false, "xterm-256color", 80, 24, 0, 0, &[
            (russh::Pty::ECHO, 0),
            (russh::Pty::ICRNL, 1),
            (russh::Pty::ONLCR, 1),
        ])
        .await
        .map_err(|e| format!("PTY request failed: {}", e))?;

    // Start shell
    channel
        .request_shell(true)
        .await
        .map_err(|e| format!("Shell request failed: {}", e))?;

    // Drain bash's initial output (may contain duplicate prompt with ECHO=0),
    // trigger a clean prompt via empty command
    tokio::time::sleep(std::time::Duration::from_millis(300)).await;
    // Discard any initial data
    while let Ok(Some(_)) =
        tokio::time::timeout(std::time::Duration::from_millis(100), channel.wait()).await
    {}
    // Send empty command to get a clean prompt
    let _ = channel.data(b"\n").await;

    // Main event loop
    loop {
        tokio::select! {
            msg = channel.wait() => {
                match msg {
                    Some(ChannelMsg::Data { ref data }) => {
                        use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
                        let b64 = BASE64.encode(data);
                        let _ = app_handle.emit("ssh-data", SshDataEvent {
                            session_id: sid.clone(),
                            data: b64,
                        });
                    }
                    Some(ChannelMsg::Eof) | None => {
                        let _ = app_handle.emit("ssh-closed", SshClosedEvent {
                            session_id: sid.clone(),
                        });
                        break;
                    }
                    _ => {}
                }
            }

            data = send_rx.recv() => {
                match data {
                    Some(bytes) => {
                        if let Err(e) = channel.data(&bytes[..]).await {
                            let _ = app_handle.emit("ssh-error", SshErrorEvent {
                                session_id: sid.clone(),
                                error: format!("Send error: {}", e),
                            });
                            break;
                        }
                    }
                    None => break,
                }
            }

            _ = &mut shutdown_rx => {
                break;
            }
        }
    }

    let _ = channel.eof().await;
    let _ = session.disconnect(Disconnect::ByApplication, "", "en").await;

    Ok(())
}
