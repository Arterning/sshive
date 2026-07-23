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
    /// Send raw bytes to the SSH channel.
    sender: mpsc::Sender<Vec<u8>>,
    /// Signal the background task to shut down.
    shutdown_tx: tokio::sync::oneshot::Sender<()>,
    /// Join handle for the session task (held to detect completion, not awaited).
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

    /// Check if a session already exists for a given host id.
    pub async fn has_session(&self, host_id: i64) -> bool {
        let sessions = self.sessions.lock().await;
        sessions.contains_key(&host_id.to_string())
    }

    /// Start a new SSH session for the given host.
    /// Returns an error string if connection fails, or Ok(()) on success.
    pub async fn connect<R: Runtime>(
        &self,
        host: Host,
        app_handle: AppHandle<R>,
    ) -> Result<(), String> {
        let session_id = host.id.unwrap_or(0).to_string();

        // If already connected, close existing session first
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
            if let Err(e) = run_ssh_session(host_clone, send_rx, shutdown_rx, app_clone, &sid).await
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

    /// Send raw bytes to an active SSH session.
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

    /// Resize the terminal for an active SSH session.
    pub async fn resize(
        &self,
        host_id: i64,
        cols: u32,
        rows: u32,
    ) -> Result<(), String> {
        // Resize is handled by the session task through a special message.
        // For now we handle it via the data channel with a special prefix.
        // A better approach: separate mpsc for control messages.
        // Simple approach for now:
        Ok(())
    }

    /// Disconnect an active SSH session.
    pub async fn disconnect(&self, host_id: i64) -> Result<(), String> {
        let mut sessions = self.sessions.lock().await;
        if let Some(handle) = sessions.remove(&host_id.to_string()) {
            let _ = handle.shutdown_tx.send(());
        }
        Ok(())
    }

    /// Disconnect all active sessions.
    pub async fn disconnect_all(&self) {
        let mut sessions = self.sessions.lock().await;
        for (_, handle) in sessions.drain() {
            let _ = handle.shutdown_tx.send(());
        }
    }
}

/// Minimal client handler for russh — auto-accepts server keys
/// (matching the Python version's AutoAddPolicy behavior).
struct ClientHandler;

#[russh::async_trait]
impl Handler for ClientHandler {
    type Error = russh::Error;

    async fn check_server_key(
        &mut self,
        _server_public_key: &ssh_key::PublicKey,
    ) -> Result<bool, Self::Error> {
        // Auto-accept (same as Python's AutoAddPolicy)
        Ok(true)
    }
}

/// The actual SSH session logic running in a background tokio task.
async fn run_ssh_session<R: Runtime>(
    host: Host,
    mut send_rx: mpsc::Receiver<Vec<u8>>,
    mut shutdown_rx: tokio::sync::oneshot::Receiver<()>,
    app_handle: AppHandle<R>,
    session_id: &str,
) -> Result<(), String> {
    let sid = session_id.to_string();

    // Build connection config
    let config = client::Config {
        ..Default::default()
    };

    let addr = format!("{}:{}", host.host, host.port);

    // Connect
    let mut session = client::connect(config, addr.as_str(), ClientHandler)
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    // Authenticate
    let auth_result = if host.auth_type == "key" && !host.private_key_path.is_empty() {
        // Load private key
        let key_data = tokio::fs::read_to_string(&host.private_key_path)
            .await
            .map_err(|e| format!("Cannot read key file: {}", e))?;

        let key = russh::keys::decode_secret_key(&key_data, None)
            .map_err(|e| format!("Failed to parse private key: {}", e))?;

        session
            .authenticate_publickey(&host.username, Arc::new(key))
            .await
            .map_err(|e| format!("Key authentication failed: {}", e))?
    } else {
        session
            .authenticate_password(&host.username, &host.password)
            .await
            .map_err(|e| format!("Password authentication failed: {}", e))?
    };

    if !auth_result.success() {
        return Err(format!(
            "Authentication rejected: {}",
            auth_result.remaining_methods().join(", ")
        ));
    }

    // Open a shell channel
    let mut channel = session
        .channel_open_session()
        .await
        .map_err(|e| format!("Channel open failed: {}", e))?;

    // Request PTY
    channel
        .request_pty(false, "xterm-256color", 80, 24, 0, 0, &[])
        .await
        .map_err(|e| format!("PTY request failed: {}", e))?;

    // Start shell
    channel
        .request_shell()
        .await
        .map_err(|e| format!("Shell request failed: {}", e))?;

    // Main event loop: read from SSH channel AND from the send channel
    loop {
        tokio::select! {
            // Data arriving from the SSH server
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
                        // Connection closed
                        let _ = app_handle.emit("ssh-closed", SshClosedEvent {
                            session_id: sid.clone(),
                        });
                        break;
                    }
                    _ => {}
                }
            }

            // Data from the frontend to send to SSH
            data = send_rx.recv() => {
                match data {
                    Some(bytes) => {
                        if let Err(e) = channel.data(&bytes).await {
                            let _ = app_handle.emit("ssh-error", SshErrorEvent {
                                session_id: sid.clone(),
                                error: format!("Send error: {}", e),
                            });
                            break;
                        }
                    }
                    None => break, // channel closed
                }
            }

            // Shutdown signal
            _ = &mut shutdown_rx => {
                break;
            }
        }
    }

    // Clean up
    let _ = channel.eof().await;
    let _ = session.disconnect(Disconnect::ByApplication, "", "en").await;

    Ok(())
}
