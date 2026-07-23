use rusqlite::{params, Connection, Result as SqlResult};
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::Mutex;

use crate::crypto;

const DB_FILE: &str = "sshive.db";

/// Host entry matching the Python version's schema.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Host {
    pub id: Option<i64>,
    pub name: String,
    pub host: String,
    pub port: u16,
    pub username: String,
    #[serde(default)]
    pub password: String,
    #[serde(default = "default_auth_type")]
    pub auth_type: String,
    #[serde(default)]
    pub private_key_path: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub updated_at: String,
}

fn default_auth_type() -> String {
    "password".into()
}

pub struct Database {
    conn: Mutex<Connection>,
}

impl Database {
    /// Open or create the database at the given file path.
    /// Also runs migrations to ensure the schema is up to date.
    pub fn new(db_path: &Path) -> Result<Self, String> {
        let conn = Connection::open(db_path)
            .map_err(|e| format!("Failed to open database: {}", e))?;

        // Create tables if they don't exist
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS hosts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                host            TEXT NOT NULL,
                port            INTEGER DEFAULT 22,
                username        TEXT NOT NULL,
                password        TEXT DEFAULT '',
                auth_type       TEXT DEFAULT 'password',
                private_key_path TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                updated_at      TEXT DEFAULT (datetime('now','localtime'))
            );",
        )
        .map_err(|e| format!("Migration failed: {}", e))?;

        Ok(Database {
            conn: Mutex::new(conn),
        })
    }

    pub fn search_hosts(&self, keyword: &str, key: &[u8; 32]) -> Result<Vec<Host>, String> {
        let conn = self.conn.lock().map_err(|e| format!("Lock error: {}", e))?;
        let pattern = format!("%{}%", keyword);

        let mut stmt = conn
            .prepare(
                "SELECT id, name, host, port, username, password, auth_type,
                        private_key_path, description, created_at, updated_at
                 FROM hosts
                 WHERE name LIKE ?1 OR host LIKE ?1 OR username LIKE ?1 OR description LIKE ?1
                 ORDER BY name",
            )
            .map_err(|e| format!("Query error: {}", e))?;

        let hosts = stmt
            .query_map(params![pattern], |row| {
                let encrypted: String = row.get(5)?;
                let decrypted = crypto::decrypt_password(key, &encrypted).unwrap_or_default();
                Ok(Host {
                    id: Some(row.get(0)?),
                    name: row.get(1)?,
                    host: row.get(2)?,
                    port: row.get(3)?,
                    username: row.get(4)?,
                    password: decrypted,
                    auth_type: row.get(6)?,
                    private_key_path: row.get(7)?,
                    description: row.get(8)?,
                    created_at: row.get(9)?,
                    updated_at: row.get(10)?,
                })
            })
            .map_err(|e| format!("Query error: {}", e))?
            .collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("Query error: {}", e))?;

        Ok(hosts)
    }

    pub fn get_all_hosts(&self, key: &[u8; 32]) -> Result<Vec<Host>, String> {
        self.search_hosts("", key)
    }

    pub fn get_host(&self, id: i64, key: &[u8; 32]) -> Result<Host, String> {
        let conn = self.conn.lock().map_err(|e| format!("Lock error: {}", e))?;

        conn.query_row(
            "SELECT id, name, host, port, username, password, auth_type,
                    private_key_path, description, created_at, updated_at
             FROM hosts WHERE id = ?1",
            params![id],
            |row| {
                let encrypted: String = row.get(5)?;
                let decrypted = crypto::decrypt_password(key, &encrypted).unwrap_or_default();
                Ok(Host {
                    id: Some(row.get(0)?),
                    name: row.get(1)?,
                    host: row.get(2)?,
                    port: row.get(3)?,
                    username: row.get(4)?,
                    password: decrypted,
                    auth_type: row.get(6)?,
                    private_key_path: row.get(7)?,
                    description: row.get(8)?,
                    created_at: row.get(9)?,
                    updated_at: row.get(10)?,
                })
            },
        )
        .map_err(|e| format!("Host not found: {}", e))
    }

    pub fn add_host(&self, host: &Host, key: &[u8; 32]) -> Result<i64, String> {
        let conn = self.conn.lock().map_err(|e| format!("Lock error: {}", e))?;
        let encrypted = crypto::encrypt_password(key, &host.password)?;

        conn.execute(
            "INSERT INTO hosts (name, host, port, username, password, auth_type,
                                private_key_path, description)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                host.name,
                host.host,
                host.port,
                host.username,
                encrypted,
                host.auth_type,
                host.private_key_path,
                host.description,
            ],
        )
        .map_err(|e| format!("Insert error: {}", e))?;

        Ok(conn.last_insert_rowid())
    }

    pub fn update_host(&self, id: i64, host: &Host, key: &[u8; 32]) -> Result<(), String> {
        let conn = self.conn.lock().map_err(|e| format!("Lock error: {}", e))?;
        let encrypted = crypto::encrypt_password(key, &host.password)?;

        conn.execute(
            "UPDATE hosts
             SET name = ?1, host = ?2, port = ?3, username = ?4, password = ?5,
                 auth_type = ?6, private_key_path = ?7, description = ?8,
                 updated_at = datetime('now','localtime')
             WHERE id = ?9",
            params![
                host.name,
                host.host,
                host.port,
                host.username,
                encrypted,
                host.auth_type,
                host.private_key_path,
                host.description,
                id,
            ],
        )
        .map_err(|e| format!("Update error: {}", e))?;

        Ok(())
    }

    pub fn delete_host(&self, id: i64) -> Result<(), String> {
        let conn = self.conn.lock().map_err(|e| format!("Lock error: {}", e))?;

        conn.execute("DELETE FROM hosts WHERE id = ?1", params![id])
            .map_err(|e| format!("Delete error: {}", e))?;

        Ok(())
    }
}
