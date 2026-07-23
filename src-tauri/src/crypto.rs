use aes_gcm::aead::{Aead, OsRng};
use aes_gcm::{Aes256Gcm, Key, KeyInit, Nonce};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use rand::RngCore;
use std::fs;
use std::path::Path;

const KEY_FILE: &str = "sshive.key";

/// Get or create the encryption key stored in the app data directory.
/// On first run, generates a random 256-bit key and persists it to `sshive.key`.
pub fn get_or_create_key(app_dir: &Path) -> Result<[u8; 32], String> {
    let key_path = app_dir.join(KEY_FILE);

    if key_path.exists() {
        let b64 = fs::read_to_string(&key_path)
            .map_err(|e| format!("Failed to read key file: {}", e))?;
        let key_bytes = BASE64
            .decode(b64.trim())
            .map_err(|e| format!("Failed to decode key: {}", e))?;
        if key_bytes.len() != 32 {
            return Err("Key file corrupted: wrong length".into());
        }
        let mut key = [0u8; 32];
        key.copy_from_slice(&key_bytes);
        Ok(key)
    } else {
        let mut key = [0u8; 32];
        OsRng.fill_bytes(&mut key);
        let b64 = BASE64.encode(key);
        fs::create_dir_all(app_dir).map_err(|e| format!("Failed to create app dir: {}", e))?;
        fs::write(&key_path, &b64).map_err(|e| format!("Failed to write key file: {}", e))?;
        Ok(key)
    }
}

/// Encrypt a password string with AES-256-GCM.
/// Returns a base64 string: nonce (12 bytes) || ciphertext.
pub fn encrypt_password(key: &[u8; 32], password: &str) -> Result<String, String> {
    let cipher =
        Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));
    let mut nonce_bytes = [0u8; 12];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ciphertext = cipher
        .encrypt(nonce, password.as_bytes())
        .map_err(|e| format!("Encryption failed: {}", e))?;

    // Prepend nonce to ciphertext for storage
    let mut combined = nonce_bytes.to_vec();
    combined.extend_from_slice(&ciphertext);
    Ok(BASE64.encode(&combined))
}

/// Decrypt a password string with AES-256-GCM.
/// The input is a base64 string: nonce (12 bytes) || ciphertext.
pub fn decrypt_password(key: &[u8; 32], encrypted: &str) -> Result<String, String> {
    if encrypted.is_empty() {
        return Ok(String::new());
    }

    let cipher =
        Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));

    let combined = BASE64
        .decode(encrypted)
        .map_err(|e| format!("Failed to decode encrypted data: {}", e))?;

    if combined.len() < 12 {
        return Err("Encrypted data too short".into());
    }

    let (nonce_bytes, ciphertext) = combined.split_at(12);
    let nonce = Nonce::from_slice(nonce_bytes);

    let plaintext = cipher
        .decrypt(nonce, ciphertext)
        .map_err(|e| format!("Decryption failed: {}", e))?;

    String::from_utf8(plaintext).map_err(|e| format!("Invalid UTF-8: {}", e))
}
