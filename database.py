"""
Database layer – SQLite with schema matching config.json.
All tables are auto-created on first import.
"""

import sqlite3
import os
from datetime import datetime

def _get_db_path():
    """Return a writable DB path – works on Streamlit Cloud (/tmp) and local dev."""
    local = os.path.join(os.path.dirname(__file__), "crm.db")
    if os.access(os.path.dirname(__file__) or ".", os.W_OK):
        return local
    return os.path.join("/tmp", "crm.db")

DB_PATH = _get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT    NOT NULL,
            last_name   TEXT    NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password_hash TEXT  NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'sales_rep',
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            industry    TEXT,
            website     TEXT,
            phone       TEXT,
            address     TEXT,
            city        TEXT,
            country     TEXT,
            created_by  INTEGER REFERENCES users(id),
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT    NOT NULL,
            last_name   TEXT    NOT NULL,
            email       TEXT,
            phone       TEXT,
            company_id  INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            status      TEXT    DEFAULT 'active',
            source      TEXT,
            owner_id    INTEGER REFERENCES users(id),
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            title               TEXT    NOT NULL,
            value               REAL    DEFAULT 0,
            stage               TEXT    NOT NULL DEFAULT 'lead',
            contact_id          INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            company_id          INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            owner_id            INTEGER REFERENCES users(id),
            expected_close_date TEXT,
            description         TEXT,
            created_at          TEXT    DEFAULT (datetime('now')),
            updated_at          TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            type         TEXT    NOT NULL,
            subject      TEXT    NOT NULL,
            description  TEXT,
            contact_id   INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            deal_id      INTEGER REFERENCES deals(id) ON DELETE SET NULL,
            owner_id     INTEGER REFERENCES users(id),
            due_date     TEXT,
            is_completed INTEGER DEFAULT 0,
            created_at   TEXT    DEFAULT (datetime('now')),
            updated_at   TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT    NOT NULL,
            entity_type TEXT    NOT NULL,
            entity_id   INTEGER NOT NULL,
            created_by  INTEGER REFERENCES users(id),
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


# ── seed a default admin if empty ─────────────────────────────────────
def seed_admin():
    import bcrypt
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    if row["cnt"] == 0:
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash, role) VALUES (?,?,?,?,?)",
            ("Admin", "User", "admin@crm.com", hashed, "admin"),
        )
        conn.commit()
    conn.close()


# Auto-init on import
init_db()
seed_admin()
