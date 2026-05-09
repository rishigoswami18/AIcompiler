"""
Authentication helpers – bcrypt hashing + session management via st.session_state.
"""

import bcrypt
import streamlit as st
from database import get_connection


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def authenticate(email: str, password: str):
    """Return user dict or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,)).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def register_user(first_name, last_name, email, password, role="sales_rep"):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash, role) VALUES (?,?,?,?,?)",
            (first_name, last_name, email, hash_password(password), role),
        )
        conn.commit()
        return True, "Account created successfully!"
    except Exception as e:
        if "UNIQUE" in str(e):
            return False, "Email already exists."
        return False, str(e)
    finally:
        conn.close()


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def current_user():
    return st.session_state.get("user")


def logout():
    st.session_state.pop("user", None)
