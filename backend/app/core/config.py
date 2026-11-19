"""
Configuration centrale de MZ SITEHUB.
Toutes les valeurs sensibles viennent de l'environnement (.env) — jamais en dur.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Base de données ---
    database_url: str = "postgresql+asyncpg://mzsitehub:mzsitehub_dev_password@db:5432/mzsitehub"

    # --- Auth (JWT maison) ---
    jwt_secret: str = "change_moi_en_production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 480  # 8h — session de travail type

    # --- Stockage documents ---
    storage_driver: str = "local"  # "local" | "supabase"
    storage_local_path: str = "./storage"
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_bucket: str = "mz-sitehub-docs"

    # --- IA ---
    ai_provider: str = "ollama"  # "ollama" | "openai" | "anthropic"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    ai_api_key: str | None = None

    # --- Partage ---
    share_link_base_url: str = "http://localhost:5173/share"

    # --- CORS (section 82) ---
    # Origines autorisées, séparées par des virgules. En dev, seule l'URL du
    # frontend local. En production, remplacer par le(s) vrai(s) domaine(s)
    # déployé(s) — jamais "*" (audit Phase 21 : CORS était figé en dur dans
    # main.py, non configurable sans modifier le code).
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
