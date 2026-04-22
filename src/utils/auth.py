import bcrypt
import streamlit as st
from src.database.db import get_user_by_username, create_user

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def login(username, password):
    """
    Attempts to log in the user.
    Returns True and sets session state if successful, False otherwise.
    """
    user = get_user_by_username(username)
    if user and verify_password(password, user['password_hash']):
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user['id']
        st.session_state['username'] = user['username']
        st.session_state['is_system_admin'] = bool(user['is_system_admin'])
        st.session_state['group_id'] = user['group_id']
        return True
    return False

def signup(username, email, password, group_id):
    """
    Registers a new user.
    Users created via signup are standard users by default.
    """
    hashed_pw = hash_password(password)
    return create_user(username, email, hashed_pw, is_system_admin=False, group_id=group_id)

def logout():
    """Clears the session state to log out."""
    for key in ['logged_in', 'user_id', 'username', 'is_system_admin', 'group_id', 'current_project']:
        if key in st.session_state:
            del st.session_state[key]
