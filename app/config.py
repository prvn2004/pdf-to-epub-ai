import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    BASE_DIR: Path = BASE_DIR
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    CROPS_DIR: Path = BASE_DIR / "crops"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    STATIC_DIR: Path = BASE_DIR / "static"

    OPENCODE_API_KEY: str = os.getenv("OPENCODE_API_KEY", "")
    OPENCODE_URL: str = os.getenv(
        "OPENCODE_URL", "https://opencode.ai/zen/go/v1/chat/completions"
    )
    OPENCODE_MODEL: str = os.getenv("OPENCODE_MODEL", "qwen3.7-plus")

    MAX_IMAGE_SIDE: int = 1568
    MAX_CROP_SIDE: int = 1200

    def init_directories(self):
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        self.CROPS_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.init_directories()
