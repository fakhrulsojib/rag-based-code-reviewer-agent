"""Configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider Configuration
    llm_provider: Literal["gemini", "openai", "anthropic", "ollama"] = Field(
        default="ollama",
        description="LLM provider to use"
    )
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    openai_api_key: str = Field(default="", description="OpenAI API key (optional)")
    anthropic_api_key: Optional[str] = None
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "codemate-ai/mini-coder:latest"
    ollama_embedding_model: str = "nomic-embed-text"
    
    # Embedding Provider (separate from LLM provider)
    embedding_provider: Literal["gemini", "ollama"] = Field(
        default="ollama",
        description="Embedding provider to use (can be different from LLM provider)"
    )
    
    # Gemini Model Configuration
    gemini_model: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model to use"
    )
    gemini_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    gemini_max_tokens: int = Field(default=8192, ge=1)
    
    # Bitbucket Configuration
    bitbucket_workspace: str = Field(default="", description="Bitbucket workspace")
    bitbucket_repo_slug: str = Field(default="", description="Bitbucket repository slug")
    bitbucket_username: str = Field(default="", description="Bitbucket username")
    bitbucket_app_password: str = Field(default="", description="Bitbucket app password")
    bitbucket_webhook_secret: str = Field(default="", description="Webhook secret for validation")
    
    # Vector Store Configuration
    vector_store_type: Literal["chromadb", "faiss"] = Field(default="chromadb")
    chroma_persist_dir: str = Field(default="./vector_store")
    embedding_model: str = Field(
        default="models/embedding-001",
        description="Gemini embedding model"
    )
    
    # Application Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    rules_dir: str = Field(default="./rules")
    
    # Retrieval Configuration
    top_k_rules: int = Field(default=10, ge=1, description="Number of rules to retrieve")
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score"
    )
    chunk_size: int = Field(default=800, ge=100, description="Chunk size in tokens")
    chunk_overlap: int = Field(default=100, ge=0, description="Overlap between chunks")
    
    # Review Configuration
    max_retries: int = Field(default=3, ge=1, description="Max LLM API retries")
    retry_delay: int = Field(default=2, ge=1, description="Retry delay in seconds")
    review_timeout: int = Field(default=120, ge=10, description="Review timeout in seconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
