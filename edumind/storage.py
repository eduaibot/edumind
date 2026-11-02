"""Versioned SQLite storage. Every conversation operation is owner-scoped."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import Conversation, Feature, now_iso

SCHEMA_VERSION = 2


class OwnershipError(PermissionError):
    pass


class ImageQuotaExceeded(ValueError):
    def __init__(self, daily_limit):
        self.daily_limit = daily_limit
        super().__init__(
            f"Bạn đã dùng hết {daily_limit} lượt giải bài bằng ảnh hôm nay. "
            "Hạn mức sẽ được làm mới vào ngày mai."
        )


class Store:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def migrate(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup_path = self.path.with_name(f"{self.path.stem}.incompatible-v{version}-{stamp}.db")
                with sqlite3.connect(backup_path) as backup:
                    conn.backup(backup)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                return
            if version == SCHEMA_VERSION:
                return
            has_tables = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone()
            if has_tables:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup_path = self.path.with_name(f"{self.path.stem}.backup-{stamp}.db")
                with sqlite3.connect(backup_path) as backup:
                    conn.backup(backup)
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, email TEXT)")
            user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
            if "email" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users(email COLLATE NOCASE) WHERE email IS NOT NULL")
            conn.execute("""CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY, username TEXT, title TEXT, messages TEXT,
                feature TEXT NOT NULL DEFAULT 'study', created_at TEXT, updated_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}')""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(chats)")}
            additions = {
                "username": "TEXT", "feature": "TEXT NOT NULL DEFAULT 'study'",
                "created_at": "TEXT", "updated_at": "TEXT", "metadata": "TEXT NOT NULL DEFAULT '{}'",
            }
            for name, declaration in additions.items():
                if name not in columns:
                    conn.execute(f"ALTER TABLE chats ADD COLUMN {name} {declaration}")
            conn.execute("CREATE INDEX IF NOT EXISTS chats_owner_updated ON chats(username, updated_at DESC)")
            conn.execute("""CREATE TABLE IF NOT EXISTS image_usage (
                username TEXT NOT NULL, usage_date TEXT NOT NULL, requests INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (username, usage_date))""")
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def require_owner(owner):
        if not owner or not owner.strip():
            raise OwnershipError("Cần đăng nhập để truy cập lịch sử đã lưu.")

    @staticmethod
    def decode(row):
        messages = json.loads(row["messages"] or "[]")
        metadata = json.loads(row["metadata"] or "{}")
        if not isinstance(messages, list) or not isinstance(metadata, dict):
            raise ValueError("Invalid conversation data")
        messages = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
        return Conversation(
            id=row["id"], owner=row["username"], title=row["title"] or "Cuộc trò chuyện",
            feature=Feature(row["feature"]), messages=messages, metadata=metadata,
            created_at=row["created_at"], updated_at=row["updated_at"], persisted=True,
            save_enabled=row["feature"] != Feature.WELLBEING.value,
        )

    def list_chats(self, owner, search=""):
        self.require_owner(owner)
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM chats WHERE username=? ORDER BY updated_at DESC, rowid DESC", (owner,)).fetchall()
        chats = []
        for row in rows:
            try:
                chat = self.decode(row)
            except (ValueError, TypeError):
                continue
            if not search or search.casefold() in (chat.title + " " + " ".join(m["content"] for m in chat.messages)).casefold():
                chats.append(chat)
        return chats

    def get_chat(self, owner, chat_id):
        self.require_owner(owner)
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM chats WHERE id=? AND username=?", (chat_id, owner)).fetchone()
        return self.decode(row) if row else None

    def save_chat(self, owner, chat):
        self.require_owner(owner)
        if chat.owner not in (None, owner):
            raise OwnershipError("Bạn không có quyền sửa cuộc trò chuyện này.")
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT username FROM chats WHERE id=?", (chat.id,)).fetchone()
            if existing and existing["username"] != owner:
                raise OwnershipError("Bạn không có quyền sửa cuộc trò chuyện này.")
            conn.execute("""INSERT INTO chats (id,username,title,messages,feature,created_at,updated_at,metadata)
                VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,messages=excluded.messages,feature=excluded.feature,
                updated_at=excluded.updated_at,metadata=excluded.metadata WHERE chats.username=excluded.username""",
                (chat.id, owner, chat.title, json.dumps(chat.messages, ensure_ascii=False), chat.feature.value,
                 chat.created_at, chat.updated_at, json.dumps(chat.metadata, ensure_ascii=False)))
        chat.owner, chat.persisted = owner, True

    def rename_chat(self, owner, chat_id, title):
        self.require_owner(owner)
        title = title.strip()
        if not title or len(title) > 120:
            raise ValueError("Tên cuộc trò chuyện cần từ 1 đến 120 ký tự.")
        with self.connection() as conn:
            result = conn.execute("UPDATE chats SET title=?, updated_at=? WHERE id=? AND username=?", (title, now_iso(), chat_id, owner))
            if result.rowcount != 1:
                raise OwnershipError("Không tìm thấy cuộc trò chuyện của bạn.")

    def delete_chat(self, owner, chat_id):
        self.require_owner(owner)
        with self.connection() as conn:
            result = conn.execute("DELETE FROM chats WHERE id=? AND username=?", (chat_id, owner))
            if result.rowcount != 1:
                raise OwnershipError("Không tìm thấy cuộc trò chuyện của bạn.")

    def image_quota_status(self, owner, usage_date, daily_limit):
        self.require_owner(owner)
        if daily_limit < 1:
            raise ValueError("Hạn mức ảnh phải là số nguyên dương.")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT requests FROM image_usage WHERE username=? AND usage_date=?",
                (owner, usage_date),
            ).fetchone()
        used = row["requests"] if row else 0
        return used, max(0, daily_limit - used)

    def reserve_image_quota(self, owner, usage_date, daily_limit):
        self.require_owner(owner)
        if daily_limit < 1:
            raise ValueError("Hạn mức ảnh phải là số nguyên dương.")
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT requests FROM image_usage WHERE username=? AND usage_date=?",
                (owner, usage_date),
            ).fetchone()
            used = row["requests"] if row else 0
            if used >= daily_limit:
                raise ImageQuotaExceeded(daily_limit)
            if row:
                conn.execute(
                    "UPDATE image_usage SET requests=requests+1 WHERE username=? AND usage_date=?",
                    (owner, usage_date),
                )
            else:
                conn.execute(
                    "INSERT INTO image_usage (username, usage_date, requests) VALUES (?, ?, 1)",
                    (owner, usage_date),
                )
        return daily_limit - used - 1
