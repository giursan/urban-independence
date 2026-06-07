"""Environment-driven configuration (no secrets committed)."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # loads apps/api/.env when running locally


class Settings:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # Dev / test: auth is removed; all requests run as this fixed user.
    # Must match DEV_USER_ID in apps/web and the seeded profile in
    # supabase/migrations/0002_dev_disable_auth.sql.
    dev_user_id: str = os.getenv("DEV_USER_ID", "00000000-0000-0000-0000-000000000001")

    # CORS
    allowed_origins: list[str] = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    ]

    @property
    def model_str(self) -> str:
        return f"openai:{self.openai_model}"


settings = Settings()
