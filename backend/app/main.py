from dataclasses import dataclass
import os


@dataclass
class Settings:
    workspace_root: str = os.getenv("WORKSPACE_ROOT", "/workspace")
    app_port: int = int(os.getenv("APP_PORT", "8000"))


settings = Settings()
