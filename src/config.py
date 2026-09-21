import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    BASE_DIR / ".env"
)


# ============================================================
# OLLAMA
# ============================================================

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:8b",
)


# ============================================================
# PATHS
# ============================================================

DATABASE_PATH = (
    BASE_DIR
    / "data"
    / "sponsorship_agent.db"
)

COMPANIES_PATH = (
    BASE_DIR
    / "companies.yaml"
)

EVENTS_PATH = (
    BASE_DIR
    / "events.yaml"
)

PROMPTS_DIR = (
    BASE_DIR
    / "src"
    / "prompts"
)


# ============================================================
# SPONSORSHIP THRESHOLDS
# ============================================================

SPONSORSHIP_THRESHOLD = int(
    os.getenv(
        "SPONSORSHIP_THRESHOLD",
        "75",
    )
)

CONFIDENCE_THRESHOLD = float(
    os.getenv(
        "CONFIDENCE_THRESHOLD",
        "0.70",
    )
)


# ============================================================
# BUSINESS SIGNAL THRESHOLDS
# ============================================================

SIGNAL_RELEVANCE_THRESHOLD = int(
    os.getenv(
        "SIGNAL_RELEVANCE_THRESHOLD",
        "60",
    )
)

SIGNAL_CONFIDENCE_THRESHOLD = float(
    os.getenv(
        "SIGNAL_CONFIDENCE_THRESHOLD",
        "0.60",
    )
)


# ============================================================
# DUPLICATION THRESHOLDS
# ============================================================

SEMANTIC_DUPLICATE_THRESHOLD = float(
    os.getenv(
        "SEMANTIC_DUPLICATE_THRESHOLD",
        "0.88",
    )
)

EVENT_DUPLICATE_THRESHOLD = float(
    os.getenv(
        "EVENT_DUPLICATE_THRESHOLD",
        "0.84",
    )
)