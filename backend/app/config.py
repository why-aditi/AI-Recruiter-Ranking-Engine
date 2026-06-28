from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://recruiter:recruiter@localhost:5432/recruiter_ranking"
    database_url_sync: str = "postgresql://recruiter:recruiter@localhost:5432/recruiter_ranking"
    redis_url: str = "redis://localhost:6379/0"

    groq_api_key: str = ""
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fast: str = "llama-3.1-8b-instant"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    mlflow_tracking_uri: str = "http://localhost:5000"
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"
    cors_origins: str = "http://localhost:3000"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    retrieval_top_k: int = 200
    rerank_top_k: int = 20
    final_top_k: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
