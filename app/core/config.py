from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://centro:centro_pass@db:5432/centro_control"
    ADMIN_API_KEY: str = ""
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ENVIRONMENT: str = "development"
    PORT: int = 8000

    # Security settings
    # Comma-separated list of allowed origins for CORS
    # Example: "https://app.tudominio.com,https://admin.tudominio.com"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Campos excluidos de la auto-creación
    EXCLUDED_FIELDS: list[str] = ["IDLOTE", "USUARIO_PREASIGNADO"]

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def fix_postgres_url(self) -> "Settings":
        # Railway sometimes provides postgres:// instead of postgresql://
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgres://", "postgresql://", 1
            )
        return self


settings = Settings()
