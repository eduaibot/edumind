import hashlib
import hmac
import re
import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

HASHER = PasswordHasher()


@dataclass(frozen=True)
class User:
    id: str
    email: str | None


def normalize_email(value):
    email = value.strip().casefold()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Nhập địa chỉ email hợp lệ, ví dụ ban@example.com.")
    return email


class Auth:
    def __init__(self, store):
        self.store = store

    def register(self, email, password):
        email = normalize_email(email)
        if len(password) < 8:
            raise ValueError("Mật khẩu cần ít nhất 8 ký tự.")
        if len(password) > 1024:
            raise ValueError("Mật khẩu quá dài (tối đa 1024 ký tự).")
        user = User(str(uuid4()), email)
        password_hash = HASHER.hash(password)
        try:
            with self.store.connection() as conn:
                conn.execute("INSERT INTO users(username,password,email) VALUES(?,?,?)", (user.id, password_hash, email))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Email này đã được sử dụng. Hãy đăng nhập.") from exc
        return user

    def authenticate(self, identity, password, legacy=False):
        if len(password) > 1024:
            return None
        with self.store.connection() as conn:
            if legacy:
                row = conn.execute("SELECT * FROM users WHERE username=? AND email IS NULL", (identity.strip(),)).fetchone()
            else:
                row = conn.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (identity.strip(),)).fetchone()
            if not row:
                # Do equivalent expensive work for a missing account.
                HASHER.hash("invalid-account")
                return None
            stored = row["password"] or ""
            old_hash = bool(re.fullmatch(r"[a-fA-F0-9]{64}", stored))
            if old_hash:
                valid = hmac.compare_digest(stored.lower(), hashlib.sha256(password.encode()).hexdigest())
            else:
                try:
                    valid = HASHER.verify(stored, password)
                except (VerificationError, InvalidHashError):
                    valid = False
            if not valid:
                return None
            if old_hash or HASHER.check_needs_rehash(stored):
                conn.execute("UPDATE users SET password=? WHERE username=?", (HASHER.hash(password), row["username"]))
            return User(row["username"], row["email"])

    def link_legacy_email(self, identity, password, email):
        email = normalize_email(email)
        user = self.authenticate(identity, password, legacy=True)
        if not user:
            raise ValueError("Tên tài khoản hoặc mật khẩu cũ chưa đúng.")
        try:
            with self.store.connection() as conn:
                result = conn.execute("UPDATE users SET email=? WHERE username=? AND email IS NULL", (email, user.id))
                if result.rowcount != 1:
                    raise ValueError("Tài khoản đã chuyển đổi. Hãy đăng nhập bằng email.")
        except sqlite3.IntegrityError as exc:
            raise ValueError("Email này đã được sử dụng bởi tài khoản khác.") from exc
        return User(user.id, email)
