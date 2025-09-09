"""
Caching functionality for the Real Estate Agent application.

This module provides a Redis-based caching system for storing and retrieving
cached results to improve performance and reduce API calls.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
import redis

from config import config


class CacheManager:
    """Manages caching operations using Redis as the cache store."""
    
    def __init__(self):
        """Initialize the cache manager with Redis connection."""
        self.url = config.redis.url
        self.ttl = config.cache.ttl
        self._connection = None
    
    def _get_connection(self):
        """Get Redis connection with connection pooling."""
        if self._connection is None:
            try:
                self._connection = redis.from_url(
                    self.url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self._connection.ping()
            except Exception as e:
                print(f"Redis connection error: {e}")
                return None
        return self._connection
    
    def _cache_key(self, namespace: str, value: str) -> str:
        """Generate cache key."""
        h = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"cache:{namespace}:{h}"
    
    def get(self, namespace: str, value: str) -> Optional[str]:
        """Get cached value."""
        r = self._get_connection()
        if not r:
            return None
        
        try:
            key = self._cache_key(namespace, value)
            return r.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, namespace: str, value: str, data: str, ttl: Optional[int] = None) -> None:
        """Set cached value."""
        r = self._get_connection()
        if not r:
            return
        
        try:
            key = self._cache_key(namespace, value)
            ttl = ttl or self.ttl
            r.setex(key, ttl, data)
        except Exception as e:
            print(f"Redis set error: {e}")
    
    def delete(self, namespace: str, value: str) -> None:
        """Delete cached value."""
        r = self._get_connection()
        if not r:
            return
        
        try:
            key = self._cache_key(namespace, value)
            r.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")
    
    def get_json(self, namespace: str, value: str) -> Optional[dict]:
        """Get cached JSON value."""
        cached = self.get(namespace, value)
        if cached:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    def set_json(self, namespace: str, value: str, data: dict, ttl: Optional[int] = None) -> None:
        """Set cached JSON value."""
        json_data = json.dumps(data)
        self.set(namespace, value, json_data, ttl)
    
    def clear_namespace(self, namespace: str) -> None:
        """Clear all keys in a namespace."""
        r = self._get_connection()
        if not r:
            return
        try:
            pattern = f"cache:{namespace}:*"
            keys = r.keys(pattern)
            if keys:
                r.delete(*keys)
        except Exception as e:
            print(f"Redis clear namespace error: {e}")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        r = self._get_connection()
        if not r:
            return {}
        
        try:
            info = r.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            print(f"Redis stats error: {e}")
            return {}
    
    # Conversation-specific methods
    def _conversation_key(self, user_id: str, conversation_id: str) -> str:
        """Generate conversation cache key."""
        return f"conversation:{user_id}:{conversation_id}"
    
    def _user_conversations_key(self, user_id: str) -> str:
        """Generate user conversations list key."""
        return f"user_conversations:{user_id}"
    
    def save_conversation(self, user_id: str, conversation_id: str, conversation_data: dict, ttl: Optional[int] = None) -> None:
        """Save a conversation to Redis."""
        r = self._get_connection()
        if not r:
            return
        
        try:
            # Save the conversation
            conv_key = self._conversation_key(user_id, conversation_id)
            conv_data = json.dumps(conversation_data)
            ttl = ttl or (10 * 60)  # Default 7 days for conversations
            r.setex(conv_key, ttl, conv_data)
            
            # Add to user's conversation list
            user_conv_key = self._user_conversations_key(user_id)
            r.sadd(user_conv_key, conversation_id)
            r.expire(user_conv_key, ttl)
            
        except Exception as e:
            print(f"Redis save conversation error: {e}")
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[dict]:
        """Get a conversation from Redis."""
        r = self._get_connection()
        if not r:
            return None
        
        try:
            conv_key = self._conversation_key(user_id, conversation_id)
            conv_data = r.get(conv_key)
            if conv_data:
                return json.loads(conv_data)
        except Exception as e:
            print(f"Redis get conversation error: {e}")
        return None
    
    def get_user_conversations(self, user_id: str) -> list:
        """Get all conversation IDs for a user."""
        r = self._get_connection()
        if not r:
            return []
        
        try:
            user_conv_key = self._user_conversations_key(user_id)
            conversation_ids = r.smembers(user_conv_key)
            
            # Get conversation details and sort by creation time
            conversations = []
            for conv_id in conversation_ids:
                conv_data = self.get_conversation(user_id, conv_id)
                if conv_data:
                    conversations.append(conv_data)
            
            # Sort by creation time (newest first)
            conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return conversations
            
        except Exception as e:
            print(f"Redis get user conversations error: {e}")
            return []
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete a conversation from Redis."""
        r = self._get_connection()
        if not r:
            return False
        
        try:
            # Remove from user's conversation list
            user_conv_key = self._user_conversations_key(user_id)
            r.srem(user_conv_key, conversation_id)
            
            # Delete the conversation
            conv_key = self._conversation_key(user_id, conversation_id)
            r.delete(conv_key)
            
            return True
        except Exception as e:
            print(f"Redis delete conversation error: {e}")
            return False
    
    def add_message_to_conversation(self, user_id: str, conversation_id: str, message: dict) -> None:
        """Add a message to an existing conversation."""
        conversation = self.get_conversation(user_id, conversation_id)
        if conversation:
            if "messages" not in conversation:
                conversation["messages"] = []
            conversation["messages"].append(message)
            conversation["updated_at"] = datetime.now().isoformat()
            self.save_conversation(user_id, conversation_id, conversation)


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions for backward compatibility
def cache_get(namespace: str, value: str) -> Optional[str]:
    """Get a cached value."""
    return cache_manager.get(namespace, value)


def cache_set(namespace: str, value: str, data: str, ttl: int = None) -> None:
    """Set a cached value."""
    cache_manager.set(namespace, value, data, ttl)


def cache_delete(namespace: str, value: str) -> None:
    """Delete a cached value."""
    cache_manager.delete(namespace, value)
