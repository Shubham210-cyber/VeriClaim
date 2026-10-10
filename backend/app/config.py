"""Central configuration, read from environment variables (never committed)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


class Settings:
    def __init__(self) -> None:
        self.database_url = _env("DATABASE_URL", f"sqlite:///{(ROOT / 'claimproof.db').as_posix()}")
        self.storage_dir = Path(_env("STORAGE_DIR", str(ROOT / "storage")))
        self.max_upload_bytes = int(_env("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
        self.confidence_threshold = float(_env("CONFIDENCE_THRESHOLD", "0.80"))
        self.ai_provider = _env("AI_PROVIDER", "mock").lower()  # mock | sonnet
        self.ai_enabled = _env("AI_ENABLED", "true").lower() == "true"
        self.ai_model = _env("AI_MODEL", "claude-sonnet-5-5")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.tesseract_cmd = _env("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        self.frontend_origin = _env("FRONTEND_ORIGIN", "http://localhost:5173")
        self.default_upload_hours = 72
        self.default_max_uploads = 5


settings = Settings()
