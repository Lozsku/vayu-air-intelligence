"""Central configuration, loaded from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "vayu.db"
SEED_PATH = DATA_DIR / "seed_stations.json"

# AI backend (provider-agnostic).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Live data.
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "").strip()

HOST = os.getenv("VAYU_HOST", "0.0.0.0")
PORT = int(os.getenv("VAYU_PORT", "8095"))


def ai_backend() -> str:
    """Which AI backend is active — used by the UI to show provenance honestly."""
    if GEMINI_API_KEY:
        return "gemini"
    if OPENAI_API_KEY:
        return "openai"
    return "local"
