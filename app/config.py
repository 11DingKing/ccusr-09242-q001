from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'invest_ledger.db'}"
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "水果深加工招商台账后端服务"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
