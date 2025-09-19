#!/usr/bin/env python3
"""
Real Estate Agent - Main Application

This is the main Streamlit web application for the Real Estate Agent system.
It provides a web interface for interacting with the real estate analysis system,
including authentication, conversation streaming, and user session management.
"""

import streamlit as st
import time
import json
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
try:
    from data import data_manager
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback: import the class directly
    from data import DataManager
    data_manager = DataManager()
from src.services.db.sql import db_service

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from auth import (
    auth_manager, 
    login_user, 
    logout_user, 
    is_authenticated, 
    get_user_id,
    get_authenticated_user_id,
    require_auth
)
from src.services.agent import call_agent, get_agent_response
from config import config
from cache import cache_manager


def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "OPENAI_API_KEY",
        "DB_PASSWORD",
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        st.error("❌ Missing required environment variables:")
        for var in missing_vars:
            st.error(f"   - {var}")
        st.error("Please set these variables in your environment or .env file.")
        st.error("See env.example for reference.")
        return False
    
    return True


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = get_user_id()
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    
    if "show_admin" not in st.session_state:
        st.session_state.show_admin = False


def get_conversation_id() -> str:
    """Get or create a conversation ID for the current user."""
    user_id = get_authenticated_user_id() or get_user_id()
    
    if st.session_state.current_conversation_id:
        return st.session_state.current_conversation_id
    
    # Create new conversation ID
    conversation_id = f"{user_id}_{int(time.time())}"
    st.session_state.current_conversation_id = conversation_id
    
    # Initialize conversation in Redis
    conversation_data = {
        "id": conversation_id,
        "user_id": user_id,
        "title": "New Conversation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": []
    }
    cache_manager.save_conversation(user_id, conversation_id, conversation_data)
    
    return conversation_id


def save_message(role: str, content: str, metadata: Optional[Dict] = None):
    """Save a message to the current conversation."""
    conversation_id = get_conversation_id()
    user_id = get_authenticated_user_id() or get_user_id()
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    
    # Save message to Redis
    cache_manager.add_message_to_conversation(user_id, conversation_id, message)


def display_conversation_history():
    """Display the conversation history in the sidebar."""
    st.sidebar.markdown("### 💬 Conversations")
    
    user_id = get_authenticated_user_id() or get_user_id()
    user_conversations = cache_manager.get_user_conversations(user_id)
    
    for conv in user_conversations:
        is_active = conv["id"] == st.session_state.current_conversation_id
        css_class = "conversation-item active" if is_active else "conversation-item"
        
        with st.sidebar.container():
            st.markdown(f'<div class="{css_class}" onclick="selectConversation(\'{conv["id"]}\')">', 
                       unsafe_allow_html=True)
            st.write(f"**{conv['title']}**")
            created_at = datetime.fromisoformat(conv['created_at'])
            st.write(f"📅 {created_at.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"💬 {len(conv.get('messages', []))} messages")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # New conversation button
    if st.sidebar.button("➕ New Conversation", use_container_width=True):
        st.session_state.current_conversation_id = None
        st.rerun()


def display_messages():
    """Display the current conversation messages."""
    conversation_id = get_conversation_id()
    user_id = get_authenticated_user_id() or get_user_id()
    conversation = cache_manager.get_conversation(user_id, conversation_id)
    messages = conversation.get("messages", []) if conversation else []
    
    # Display messages
    for message in messages:
        role = message["role"]
        content = message["content"]
        timestamp = datetime.fromisoformat(message["timestamp"])
        
        if role == "user":
            with st.chat_message("user"):
                st.write(content)
                st.caption(f"🕒 {timestamp.strftime('%H:%M:%S')}")
        else:
            with st.chat_message("assistant"):
                st.write(content)
                st.caption(f"🕒 {timestamp.strftime('%H:%M:%S')}")
                
                # Display metadata if available
                metadata = message.get("metadata", {})
                if metadata:
                    with st.expander("📊 Details"):
                        if "sql_query" in metadata:
                            st.code(metadata["sql_query"], language="sql")
                        if "sql_result" in metadata:
                            st.json(metadata["sql_result"])
                        if "context_used" in metadata:
                            st.write("**Context Used:**")
                            st.write(metadata["context_used"])


def stream_agent_response(prompt: str) -> str:
    """Stream the agent response and display it in real-time."""
    user_id = get_authenticated_user_id() or get_user_id()
    print(f"DEBUG: App user_id: {user_id}")
    conversation_id = get_conversation_id()
    print(f"DEBUG: App conversation_id: {conversation_id}")
    
    # Create a placeholder for the streaming response
    response_placeholder = st.empty()
    full_response = ""
    
    try:
        # Initialize state for streaming
        user_id = st.session_state.authenticated_user.get("username", "") if st.session_state.authenticated_user else get_user_id()
        print(f"DEBUG: App final user_id: {user_id}")
        
        initial_state = {
            "question": prompt,
            "context": [],
            "needs_sql": False,
            "sql_result": "",
            "llm_sql": "",
            "messages": [{"role": "user", "content": prompt}],
            "report": "",
            "needs_email": False,
            "email_state": None,
            "user_id": user_id
        }
        
        print(f"DEBUG: App initial_state user_id: {initial_state['user_id']}")
        
        # Stream the response
        from src.graph.workflow import app
        events = app.stream(
            initial_state,
            {"configurable": {"thread_id": conversation_id}, "recursion_limit": 150},
            stream_mode="values"
        )
        
        print(f"DEBUG: App starting workflow with prompt: {prompt}")
        
        for i, event in enumerate(events):
            print(f"DEBUG: App Event {i+1}: {list(event.keys())}")
            
            if "needs_email" in event:
                print(f"DEBUG: App Event {i+1} needs_email: {event['needs_email']}")
            
            if "email_state" in event and event["email_state"]:
                print(f"DEBUG: App Event {i+1} email_state: {event['email_state']}")
            
            if "report" in event and event["report"]:
                # Update the response in real-time
                full_response = event["report"]
                print(f"DEBUG: App Event {i+1} report length: {len(full_response)}")
                
                # Check if this is an email request
                if event.get("needs_email", False):
                    print(f"DEBUG: App Event {i+1} - EMAIL REQUEST DETECTED")
                    print(f"DEBUG: App Event {i+1} - email_state: {event.get('email_state', 'None')}")
                    
                    # For email requests, show a confirmation message instead of the full report
                    email_confirmation = f"📧 **Email Report Generated!**\n\nYour report has been generated and sent to your email address. The report includes comprehensive analysis of your query: *{prompt}*\n\n✅ **Email Status**: Report sent successfully\n📊 **Report Length**: {len(full_response)} characters\n\n*You can continue chatting below for more queries.*"
                    response_placeholder.markdown(email_confirmation)
                else:
                    # For regular reports, show the full content
                    response_placeholder.markdown(full_response)
                time.sleep(0.1)  # Small delay for better UX
        
        print(f"DEBUG: App workflow completed")
        
        # Save the final response
        metadata = {}
        if "llm_sql" in event:
            metadata["sql_query"] = event["llm_sql"]
        if "sql_result" in event:
            metadata["sql_result"] = event["sql_result"]
        if "context" in event:
            metadata["context_used"] = event["context"]
        
        save_message("assistant", full_response, metadata)
        
        return full_response
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        response_placeholder.error(error_msg)
        save_message("assistant", error_msg, {"error": str(e)})
        return error_msg


def login_page():
    """Display the login page."""
    st.markdown('<div class="main-header">🏠 Real Estate Agent</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("Login", use_container_width=True)
            
            if submit_button:
                if login_user(username, password):
                    st.success("Login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        st.markdown("---")
        st.markdown("### 📝 Sign Up")
        
        with st.form("signup_form"):
            new_username = st.text_input("New Username", placeholder="Choose a username", key="signup_username")
            new_email = st.text_input("Email", placeholder="Enter your email", key="signup_email")
            new_password = st.text_input("New Password", type="password", placeholder="Choose a password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="signup_confirm")
            signup_button = st.form_submit_button("Sign Up", use_container_width=True)
            
            if signup_button:
                if not new_username or not new_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    if auth_manager.create_user(new_username, new_password, new_email, "user"):
                        st.success("Account created successfully! You can now login.")
                    else:
                        st.error("Username already exists or failed to create account")
        


def admin_panel():
    """Display the admin panel for user management."""
    st.markdown('<div class="main-header">👑 Admin Panel</div>', unsafe_allow_html=True)
    
    # Back to main app button
    if st.button("← Back to Main App", use_container_width=True):
        st.session_state.show_admin = False
        st.rerun()
    
    st.markdown("---")
    
    # Admin panel tabs
    tab1, tab2, tab3 = st.tabs(["👥 Users", "🔐 Change Password", "🧪 Test Login"])
    
    with tab1:
        st.markdown("### 👥 All Users")
        
        users = auth_manager.list_users()
        if not users:
            st.info("No users found")
        else:
            for username, user_info in users.items():
                with st.expander(f"👤 {username}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Email:** {user_info['email']}")
                        st.write(f"**Role:** {user_info['role']}")
                    with col2:
                        created_at = user_info['created_at']
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at)
                        st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        if st.button(f"🗑️ Delete {username}", key=f"delete_{username}"):
                            if auth_manager.delete_user(username):
                                st.success(f"User {username} deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Cannot delete this user (admin user or user not found)")
    
    with tab2:
        st.markdown("### 🔐 Change User Password")
        
        with st.form("change_password_form"):
            users = auth_manager.list_users()
            change_username = st.selectbox("Select User", list(users.keys()))
            old_password = st.text_input("Current Password", type="password", placeholder="Enter current password")
            new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password")
            change_button = st.form_submit_button("Change Password", use_container_width=True)
            
            if change_button:
                if not old_password or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    if auth_manager.change_password(change_username, old_password, new_password):
                        st.success(f"Password changed successfully for {change_username}!")
                    else:
                        st.error("Failed to change password. Check current password.")
    
    with tab3:
        st.markdown("### 🧪 Test User Login")
        
        with st.form("test_login_form"):
            users = auth_manager.list_users()
            test_username = st.selectbox("Select User to Test", list(users.keys()))
            test_password = st.text_input("Password", type="password", placeholder="Enter password")
            test_button = st.form_submit_button("Test Login", use_container_width=True)
            
            if test_button:
                if not test_password:
                    st.error("Please enter a password")
                else:
                    token = auth_manager.authenticate_user(test_username, test_password)
                    if token:
                        user_info = auth_manager.get_current_user(token)
                        st.success("✅ Login successful!")
                        st.write(f"**Username:** {user_info['username']}")
                        st.write(f"**Email:** {user_info['email']}")
                        st.write(f"**Role:** {user_info['role']}")
                    else:
                        st.error("❌ Login failed - invalid credentials")


def main_app():
    """Display the main application interface."""
    # Check if admin panel should be shown
    if st.session_state.get("show_admin", False):
        admin_panel()
        return
    
    st.markdown('<div class="main-header">🏠 Real Estate Agent</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 👤 User Info")
        user_info = st.session_state.authenticated_user
        st.write(f"**Username:** {user_info['username']}")
        
        # Display role with appropriate icon
        role = user_info['role']
        if role == 'admin':
            st.write(f"**Role:** 👑 {role.upper()}")
        else:
            st.write(f"**Role:** 👤 {role.upper()}")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
        
        st.markdown("---")
        
        # Display conversation history
        display_conversation_history()
        
        st.markdown("---")
        
        # Configuration info
        st.markdown("### ⚙️ Configuration")
        st.write(f"**Model:** {config.llm.model_name}")
        st.write(f"**Cache TTL:** {config.cache.ttl}s")
        st.write(f"**User ID:** {get_authenticated_user_id()}")
        
        # Admin panel access
        if user_info['role'] == 'admin':
            st.markdown("---")
            st.markdown("### 👑 Admin Panel")
            if st.button("🔧 User Management", use_container_width=True):
                st.session_state.show_admin = True
                st.rerun()
    
    # Main chat interface
    st.markdown("### 💬 Chat with Real Estate Agent")
    
    # Display conversation history
    display_messages()
    
    # Chat input
    if prompt := st.chat_input("Ask me about real estate properties, market analysis, or any property-related questions..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.write(prompt)
        
        # Stream agent response
        with st.chat_message("assistant"):
            response = stream_agent_response(prompt)
    
    # Quick action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏠 Property Search", use_container_width=True):
            sample_query = "Show me properties in Melbourne with 3+ bedrooms under $800,000"
            st.session_state.sample_query = sample_query
            st.rerun()
    
    with col2:
        if st.button("📊 Market Analysis", use_container_width=True):
            sample_query = "What's the average price per square foot in different suburbs?"
            st.session_state.sample_query = sample_query
            st.rerun()
    
    with col3:
        if st.button("💰 Price Trends", use_container_width=True):
            sample_query = "Show me price trends for properties built in the last 5 years"
            st.session_state.sample_query = sample_query
            st.rerun()
    
    with col4:
        if st.button("📧 Email Report", use_container_width=True):
            sample_query = "Generate a report and email it to me"
            st.session_state.sample_query = sample_query
            st.rerun()
    
    # Handle sample query
    if "sample_query" in st.session_state:
        sample_query = st.session_state.sample_query
        del st.session_state.sample_query
        
        # Display user message
        with st.chat_message("user"):
            st.write(sample_query)
        
        # Stream agent response
        with st.chat_message("assistant"):
            response = stream_agent_response(sample_query)


def main():
    """Main application entry point."""
    # Check environment variables
    if not check_environment():
        st.stop()
    
    try:
        # Check if properties table exists
        schema = db_service.get_schema_info(include_types=True)
        if "properties" not in schema:
            st.info("🔄 Setting up database... This may take a moment.")
            data_manager.load_all_data()
            st.success("✅ Database initialized successfully!")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Database initialization failed: {e}")
        st.stop()
    
    # Page configuration
    st.set_page_config(
        page_title="Real Estate Agent",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #1f77b4;
        }
        .user-message {
            background-color: #f0f2f6;
            border-left-color: #1f77b4;
        }
        .assistant-message {
            background-color: #e8f4fd;
            border-left-color: #28a745;
        }
        .error-message {
            background-color: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }
        .success-message {
            background-color: #d4edda;
            border-left-color: #28a745;
            color: #155724;
        }
        .sidebar-section {
            margin-bottom: 2rem;
        }
        .conversation-item {
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 0.25rem;
            background-color: #f8f9fa;
            cursor: pointer;
        }
        .conversation-item:hover {
            background-color: #e9ecef;
        }
         .conversation-item.active {
             background-color: #1f77b4;
             color: white;
         }
         .admin-panel {
             background-color: #f8f9fa;
             padding: 1rem;
             border-radius: 0.5rem;
             border-left: 4px solid #dc3545;
         }
         .user-card {
             background-color: #ffffff;
             padding: 1rem;
             border-radius: 0.5rem;
             border: 1px solid #dee2e6;
             margin-bottom: 1rem;
         }
    </style>
    """, unsafe_allow_html=True)
    
    initialize_session_state()
    
    # Check if user is authenticated
    if not is_authenticated():
        login_page()
    else:
        main_app()


if __name__ == "__main__":
    main()
