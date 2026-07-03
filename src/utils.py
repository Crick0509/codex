from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def ensure_directories() -> None:
    for relative in ("data", "reports", "logs"):
        (PROJECT_ROOT / relative).mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    ensure_directories()
    log_file = PROJECT_ROOT / "logs" / f"pubmed_brief_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("pubmed_cancer_brief")


def load_yaml(relative_path: str) -> dict[str, Any]:
    path = PROJECT_ROOT / relative_path
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ")
    return " ".join(text.split())
