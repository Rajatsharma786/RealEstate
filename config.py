"""
Configuration management for the Real Estate Agent application.

This module handles environment variables, database connections, and application settings.
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 6024
    database: str = "langchain"
    username: str = "langchain"
    password: str = ""
    
    @property
    def connection_string(self) -> str:
        """Get the PostgreSQL connection string."""
        return f"postgresql+psycopg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    model_name: str = "gpt-4o"
    temperature: float = 0.0
    streaming: bool = True
    api_key: Optional[str] = None


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    ttl: int = 60 * 60  # 1 hour default
    namespace: str = "real_estate"


@dataclass
class RedisConfig:
    """Redis configuration settings."""
    url: str = "redis://localhost:6379"
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


@dataclass
class EmailConfig:
    """Email configuration settings."""
    sender_email: str = ""
    sender_password: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587


@dataclass
class AuthConfig:
    """Authentication configuration settings."""
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24


@dataclass
class AppConfig:
    """Main application configuration."""
    database: DatabaseConfig
    llm: LLMConfig
    embedding: EmbeddingConfig
    cache: CacheConfig
    redis: RedisConfig
    email: EmailConfig
    auth: AuthConfig
    
    # Data file paths
    data_dictionary_csv: str
    properties_csv: str
    
    # Vector store settings
    collection_name: str = "real_estate_dict"
    use_jsonb: bool = True


def load_config() -> AppConfig:
    """
    Load configuration from environment variables and defaults.
    
    Returns:
        AppConfig: Complete application configuration
    """
    # Database configuration
    database = DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "6024")),
        database=os.getenv("DB_NAME", "langchain"),
        username=os.getenv("DB_USER", "langchain"),
        password=os.getenv("DB_PASSWORD", "")
    )
    
    # LLM configuration
    llm = LLMConfig(
        model_name=os.getenv("LLM_MODEL", "gpt-4o"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        streaming=os.getenv("LLM_STREAMING", "true").lower() == "true",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Embedding configuration
    embedding = EmbeddingConfig(
        model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    
    # Cache configuration
    cache = CacheConfig(
        ttl=int(os.getenv("CACHE_TTL", "3600")),
        namespace=os.getenv("CACHE_NAMESPACE", "real_estate")
    )
    
    # Redis configuration
    redis = RedisConfig(
        url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD")
    )
    
    # Email configuration
    email = EmailConfig(
        sender_email=os.getenv("EMAIL_SENDER", ""),
        sender_password=os.getenv("EMAIL_PASSWORD", ""),
        smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587"))
    )
    
    # Authentication configuration
    auth = AuthConfig(
        secret_key=os.getenv("SECRET_KEY", ""),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    )
    
    # Data file paths
    data_dictionary_csv = os.getenv(
        "DATA_DICTIONARY_CSV", 
        "data/data_dictionary.csv"
    )
    properties_csv = os.getenv(
        "PROPERTIES_CSV", 
        "data/properties_augmented_vic.csv"
    )
    
    return AppConfig(
        database=database,
        llm=llm,
        embedding=embedding,
        cache=cache,
        redis=redis,
        email=email,
        auth=auth,
        data_dictionary_csv=data_dictionary_csv,
        properties_csv=properties_csv
    )


# Global configuration instance
config = load_config()
