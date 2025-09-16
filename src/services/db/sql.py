"""
SQL execution and database operations.

This module provides functions for executing SQL queries safely
and retrieving database schema information.
"""

import json
from typing import List, Union, Optional, Dict, Any
from sqlalchemy import create_engine, text, Table, Column, String, DateTime, MetaData
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import config
from cache import cache_manager


class DatabaseService:
    """Service class for database operations."""
    
    def __init__(self):
        """Initialize the database service."""
        self.engine = create_engine(config.database.connection_string, future=True)
    
    def run_sql(self, sql: str) -> str:
        """
        Run read-only SQL and return a small text table.
        
        Args:
            sql: The SQL query to execute
            
        Returns:
            Formatted result as text table or error message
        """
        # Check for potentially unsafe SQL operations
        bad_operations = ("drop ", "alter ", "insert ", "update ", "delete ", "create ")
        if any(bad_op in sql.lower() for bad_op in bad_operations):
            return "(blocked potentially unsafe SQL)"
        
        # Try to get from cache first
        cached = cache_manager.get("sql", sql)
        if cached:
            return cached
        
        result_text = ""
        try:
            with self.engine.begin() as conn:
                res = conn.execute(text(sql))
                rows = res.fetchall()
                cols = res.keys()
            
            if not rows:
                result_text = "(no rows)"
            else:
                head = " | ".join(cols)
                lines = [head] + [" | ".join(str(x) for x in r) for r in rows[:200]]
                result_text = "\n".join(lines)
                
        except Exception as e:
            result_text = f"SQL execution error: {str(e)}"
        
        # Cache the result (even errors)
        try:
            cache_manager.set("sql", sql, result_text)
        except Exception:
            pass
        
        return result_text
    
    def get_schema_info(self, include_types: bool = False) -> Union[str, List[str]]:
        """
        Get schema information - columns only or with types.
        
        Args:
            include_types: Whether to include data types in the result
            
        Returns:
            Schema information as string (with types) or list of column names
        """
        key_input = f"schema:{include_types}"
        cached = cache_manager.get_json("schema", key_input)
        if cached:
            return cached
        
        if include_types:
            sql = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='properties'
            ORDER BY ordinal_position;
            """
            with self.engine.begin() as conn:
                rows = conn.execute(text(sql)).fetchall()
            result = "public.properties columns: " + ", ".join(f"{c} ({t})" for c, t in rows)
        else:
            sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='properties'
            ORDER BY ordinal_position;
            """
            with self.engine.begin() as conn:
                result = [r[0] for r in conn.execute(text(sql)).fetchall()]
        
        # Cache the result
        try:
            cache_manager.set_json("schema", key_input, result)
        except Exception:
            pass
        
        return result

    def create_properties_table_if_needed(self) -> bool:
        """Create the properties table and load data if it doesn't exist."""
        try:
            # Check if properties table exists by trying to query it
            test_result = self.run_sql("SELECT COUNT(*) FROM properties LIMIT 1")
            
            if "error" in test_result.lower() or "relation" in test_result.lower():
                print("📊 Properties table not found. Creating and loading data...")
                
                # Import data manager here to avoid circular imports
                from data import DataManager
                data_manager = DataManager()
                
                # Load the data
                success = data_manager.setup_properties_table()
                if success:
                    print("✅ Properties table created and data loaded successfully")
                    return True
                else:
                    print("❌ Failed to create properties table")
                    return False
            else:
                print("✅ Properties table already exists")
                return True
                
        except Exception as e:
            print(f"❌ Error checking/creating properties table: {e}")
            return False
    
    def create_properties_table(self, df, table_name: str = "properties") -> None:
        """
        Create the properties table from a DataFrame.
        
        Args:
            df: The DataFrame to load
            table_name: Name of the table to create
        """
        with self.engine.begin() as conn:
            # Drop existing table if it exists
            conn.exec_driver_sql(f'DROP TABLE IF EXISTS public."{table_name}" CASCADE;')
            
            # Create table from DataFrame
            df.to_sql(table_name, con=conn, schema="public", index=False)
            
            # Create helpful indexes automatically
            # 1) Categorical-ish text columns (low cardinality) -> B-tree
            for column in df.columns:
                col_name = df[column]
                if col_name.dtype == 'object':  # String columns
                    # low-ish cardinality relative to rows (tweak threshold as needed)
                    if (col_name.nunique(dropna=True) > 1 and 
                        col_name.nunique(dropna=True) / max(len(col_name), 1) <= 0.25):
                        conn.exec_driver_sql(
                            f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{column} '
                            f'ON public."{table_name}" ("{column}");'
                        )
            
            # 2) Numeric columns you'll likely filter/sort on -> B-tree
            for column in df.columns:
                if df[column].dtype in ['int64', 'float64']:  # Numeric columns
                    conn.exec_driver_sql(
                        f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{column} '
                        f'ON public."{table_name}" ("{column}");'
                    )
    
    def create_users_table(self) -> bool:
        """Create the users table if it doesn't exist."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        username VARCHAR(50) PRIMARY KEY,
                        password_hash VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        role VARCHAR(20) NOT NULL DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                return True
        except Exception as e:
            print(f"Error creating users table: {e}")
            return False
    
    def create_user(self, username: str, password_hash: str, email: str, role: str = "user") -> bool:
        """Create a new user in the database."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO users (username, password_hash, email, role, created_at, updated_at)
                    VALUES (:username, :password_hash, :email, :role, :created_at, :updated_at)
                """), {
                    "username": username,
                    "password_hash": password_hash,
                    "email": email,
                    "role": role,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
                return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information from the database."""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT username, password_hash, email, role, created_at, updated_at
                    FROM users WHERE username = :username
                """), {"username": username})
                
                row = result.fetchone()
                if row:
                    return {
                        "username": row[0],
                        "password_hash": row[1],
                        "email": row[2],
                        "role": row[3],
                        "created_at": row[4],
                        "updated_at": row[5]
                    }
        except Exception as e:
            print(f"Error getting user: {e}")
        return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from the database."""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT username, password_hash, email, role, created_at, updated_at
                    FROM users ORDER BY created_at DESC
                """))
                
                users = []
                for row in result:
                    users.append({
                        "username": row[0],
                        "password_hash": row[1],
                        "email": row[2],
                        "role": row[3],
                        "created_at": row[4],
                        "updated_at": row[5]
                    })
                return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    def update_user_password(self, username: str, new_password_hash: str) -> bool:
        """Update user password."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    UPDATE users 
                    SET password_hash = :password_hash, updated_at = :updated_at
                    WHERE username = :username
                """), {
                    "username": username,
                    "password_hash": new_password_hash,
                    "updated_at": datetime.now()
                })
                return True
        except Exception as e:
            print(f"Error updating user password: {e}")
            return False
    
    def update_user_email(self, username: str, new_email: str) -> bool:
        """Update user email."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    UPDATE users 
                    SET email = :email, updated_at = :updated_at
                    WHERE username = :username
                """), {
                    "username": username,
                    "email": new_email,
                    "updated_at": datetime.now()
                })
                return True
        except Exception as e:
            print(f"Error updating user email: {e}")
            return False
    
    def delete_user(self, username: str) -> bool:
        """Delete a user from the database."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    DELETE FROM users WHERE username = :username
                """), {"username": username})
                return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists in the database."""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM users WHERE username = :username
                """), {"username": username})
                
                count = result.fetchone()[0]
                return count > 0
        except Exception as e:
            print(f"Error checking if user exists: {e}")
            return False


# Global database service instance
db_service = DatabaseService()


# Convenience functions for backward compatibility
def run_sql(sql: str) -> str:
    """Run a SQL query and return formatted results."""
    return db_service.run_sql(sql)


def get_schema_info(include_types: bool = False) -> Union[str, List[str]]:
    """Get database schema information."""
    return db_service.get_schema_info(include_types)
