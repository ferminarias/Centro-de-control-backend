from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://centro:centro_pass@db:5432/centro_control"
    ADMIN_API_KEY: str = ""
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ENVIRONMENT: str = "development"
    AUTH_ENABLED: bool = False
    PORT: int = 8000

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
