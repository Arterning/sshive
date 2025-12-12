import sqlite3
from pathlib import Path
from typing import List, Optional
from cryptography.fernet import Fernet


class DatabaseManager:
    def __init__(self, db_path: str = "sshive.db"):
        self.db_path = db_path
        self.conn = None
        self.cipher = None
        self._init_encryption()
        self._init_database()

    def _init_encryption(self):
        """初始化加密密钥"""
        key_file = Path("sshive.key")
        if key_file.exists():
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
        self.cipher = Fernet(key)

    def _init_database(self):
        """初始化数据库表"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER DEFAULT 22,
                username TEXT NOT NULL,
                password TEXT,
                auth_type TEXT DEFAULT 'password',
                private_key_path TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _encrypt_password(self, password: str) -> str:
        """加密密码"""
        if not password:
            return ""
        return self.cipher.encrypt(password.encode()).decode()

    def _decrypt_password(self, encrypted: str) -> str:
        """解密密码"""
        if not encrypted:
            return ""
        return self.cipher.decrypt(encrypted.encode()).decode()

    def add_host(self, name: str, host: str, port: int, username: str,
                 password: str = "", auth_type: str = "password",
                 private_key_path: str = "", description: str = "") -> int:
        """添加主机"""
        cursor = self.conn.cursor()
        encrypted_password = self._encrypt_password(password)
        cursor.execute("""
            INSERT INTO hosts (name, host, port, username, password, auth_type, private_key_path, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, host, port, username, encrypted_password, auth_type, private_key_path, description))
        self.conn.commit()
        return cursor.lastrowid

    def update_host(self, host_id: int, name: str, host: str, port: int,
                    username: str, password: str = "", auth_type: str = "password",
                    private_key_path: str = "", description: str = "") -> bool:
        """更新主机信息"""
        cursor = self.conn.cursor()
        encrypted_password = self._encrypt_password(password)
        cursor.execute("""
            UPDATE hosts
            SET name=?, host=?, port=?, username=?, password=?, auth_type=?,
                private_key_path=?, description=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (name, host, port, username, encrypted_password, auth_type,
              private_key_path, description, host_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_host(self, host_id: int) -> bool:
        """删除主机"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM hosts WHERE id=?", (host_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_host(self, host_id: int) -> Optional[dict]:
        """获取单个主机信息"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM hosts WHERE id=?", (host_id,))
        row = cursor.fetchone()
        if row:
            host_data = dict(row)
            host_data['password'] = self._decrypt_password(host_data['password'])
            return host_data
        return None

    def get_all_hosts(self) -> List[dict]:
        """获取所有主机"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM hosts ORDER BY name")
        rows = cursor.fetchall()
        hosts = []
        for row in rows:
            host_data = dict(row)
            host_data['password'] = self._decrypt_password(host_data['password'])
            hosts.append(host_data)
        return hosts

    def search_hosts(self, keyword: str) -> List[dict]:
        """搜索主机"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM hosts
            WHERE name LIKE ? OR host LIKE ? OR username LIKE ? OR description LIKE ?
            ORDER BY name
        """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
        rows = cursor.fetchall()
        hosts = []
        for row in rows:
            host_data = dict(row)
            host_data['password'] = self._decrypt_password(host_data['password'])
            hosts.append(host_data)
        return hosts

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
