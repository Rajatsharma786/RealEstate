"""
Authentication module for the Real Estate Agent application.

This module handles user authentication, JWT token management, and session handling.
"""

import jwt
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import hashlib
import secrets

from config import config
from src.services.db.sql import db_service


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthManager:
    """Manages user authentication and session handling."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        self.secret_key = config.auth.secret_key
        self.algorithm = config.auth.jwt_algorithm
        self.expiration_hours = config.auth.jwt_expiration_hours
        
        # Initialize database table
        print("🏗️ Initializing database tables...")
        db_service.create_users_table()
        db_service.create_properties_table_if_needed()
        
        # Create default admin user if it doesn't exist
        if not db_service.user_exists("admin"):
            db_service.create_user(
                username="admin",
                password_hash=self._hash_password("admin123"),
                email="admin@realestate.com",
                role="admin"
            )
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _create_token(self, username: str) -> str:
        """Create a JWT token for a user."""
        if not self.secret_key:
            raise ValueError("SECRET_KEY not configured")
        
        payload = {
            "username": username,
            "exp": datetime.utcnow() + timedelta(hours=self.expiration_hours),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        if not self.secret_key:
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user and return a JWT token if successful.
        
        Args:
            username: The username
            password: The password
            
        Returns:
            JWT token if authentication successful, None otherwise
        """
        user = db_service.get_user(username)
        if not user:
            return None
        
        if not self._verify_password(password, user["password_hash"]):
            return None
        
        return self._create_token(username)
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get current user information from token.
        
        Args:
            token: JWT token
            
        Returns:
            User information if token is valid, None otherwise
        """
        payload = self._verify_token(token)
        if not payload:
            return None
        
        username = payload.get("username")
        user = db_service.get_user(username)
        if not user:
            return None
        
        return {
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "created_at": user["created_at"]
        }
    
    def create_user(self, username: str, password: str, email: str, role: str = "user") -> bool:
        """
        Create a new user.
        
        Args:
            username: The username
            password: The password
            email: The email address
            role: The user role
            
        Returns:
            True if user created successfully, False otherwise
        """
        if db_service.user_exists(username):
            return False
        
        return db_service.create_user(
            username=username,
            password_hash=self._hash_password(password),
            email=email,
            role=role
        )
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change a user's password.
        
        Args:
            username: The username
            old_password: The current password
            new_password: The new password
            
        Returns:
            True if password changed successfully, False otherwise
        """
        user = db_service.get_user(username)
        if not user:
            return False
        
        if not self._verify_password(old_password, user["password_hash"]):
            return False
        
        return db_service.update_user_password(username, self._hash_password(new_password))
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user.
        
        Args:
            username: The username to delete
            
        Returns:
            True if user deleted successfully, False otherwise
        """
        if not db_service.user_exists(username):
            return False
        
        # Prevent deletion of admin user
        if username == "admin":
            return False
        
        return db_service.delete_user(username)
    
    def list_users(self) -> Dict[str, Dict[str, Any]]:
        """
        List all users.
        
        Returns:
            Dictionary of all users with their information
        """
        users = db_service.get_all_users()
        return {user["username"]: user for user in users}


# Global auth manager instance
auth_manager = AuthManager()


def get_user_id() -> str:
    """
    Get the current user ID from Streamlit session state.
    
    Returns:
        User ID string
    """
    if "user_id" not in st.session_state:
        # Generate a unique session ID for anonymous users
        st.session_state.user_id = f"anon_{secrets.token_hex(8)}"
    
    return st.session_state.user_id


def get_authenticated_user_id() -> Optional[str]:
    """
    Get the authenticated user ID from Streamlit session state.
    
    Returns:
        Authenticated user ID if logged in, None otherwise
    """
    if "authenticated_user" not in st.session_state:
        return None
    
    return st.session_state.authenticated_user.get("username")


def is_authenticated() -> bool:
    """
    Check if the current user is authenticated.
    
    Returns:
        True if user is authenticated, False otherwise
    """
    return "authenticated_user" in st.session_state and st.session_state.authenticated_user is not None


def login_user(username: str, password: str) -> bool:
    """
    Login a user and store authentication info in session state.
    
    Args:
        username: The username
        password: The password
        
    Returns:
        True if login successful, False otherwise
    """
    token = auth_manager.authenticate_user(username, password)
    if not token:
        return False
    
    user_info = auth_manager.get_current_user(token)
    if not user_info:
        return False
    
    st.session_state.authenticated_user = user_info
    st.session_state.auth_token = token
    return True


def logout_user():
    """Logout the current user and clear session state."""
    if "authenticated_user" in st.session_state:
        del st.session_state.authenticated_user
    if "auth_token" in st.session_state:
        del st.session_state.auth_token


def require_auth(func):
    """
    Decorator to require authentication for a function.
    
    Args:
        func: The function to protect
        
    Returns:
        Wrapped function that checks authentication
    """
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.error("Please log in to access this feature.")
            return None
        return func(*args, **kwargs)
    return wrapper
