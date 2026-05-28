from pydantic import model_validator
from pydantic_settings import BaseSettings

_WEAK_SECRET_KEY = "change-me-to-a-random-secret-key"
_MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://centro:centro_pass@db:5432/centro_control"
    ADMIN_API_KEY: str = ""
    FOOTBALL_DATA_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_ALLOWED_DOMAIN: str = ""  # e.g. "gruponods.com" — vacío = cualquier dominio
    SECRET_KEY: str = _WEAK_SECRET_KEY
    ENVIRONMENT: str = "development"
    PORT: int = 8000

    # CORS: comma-separated list of allowed origins
    # Example: "https://app.tudominio.com,https://admin.tudominio.com"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Campos excluidos de la auto-creación de campos dinámicos
    EXCLUDED_FIELDS: list[str] = ["IDLOTE", "USUARIO_PREASIGNADO"]

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        # Normalize Railway postgres:// URL
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

        # In production: enforce secure SECRET_KEY and ADMIN_API_KEY
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == _WEAK_SECRET_KEY or len(self.SECRET_KEY) < _MIN_SECRET_KEY_LENGTH:
                raise ValueError(
                    f"SECRET_KEY must be a secure random string of at least "
                    f"{_MIN_SECRET_KEY_LENGTH} characters in production. "
                    f"Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if not self.ADMIN_API_KEY:
                raise ValueError(
                    "ADMIN_API_KEY must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )

        return self


settings = Settings()
