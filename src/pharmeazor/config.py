"""Runtime configuration, read from the environment.

The API key never lives in the repository. Copy ``.env.example`` to ``.env``
(ignored by git) and fill it in there. Every member of the team uses their own
free key; multiplying accounts to dodge quotas is explicitly out of bounds.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader so the project runs without extra dependencies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    """All tunables in one place, so experiments stay reproducible."""

    # --- model (imposed by the module; same for every team) -----------------
    model_name: str = field(default_factory=lambda: os.getenv("PHARMEAZOR_MODEL", ""))
    api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))

    # --- paths --------------------------------------------------------------
    raw_dir: Path = DATA / "raw"
    interim_dir: Path = DATA / "interim"
    processed_dir: Path = DATA / "processed"
    reference_dir: Path = DATA / "reference"
    cache_dir: Path = ROOT / ".cache"

    # --- retrieval ----------------------------------------------------------
    retriever: str = field(default_factory=lambda: os.getenv("PHARMEAZOR_RETRIEVER", "bm25"))
    top_k: int = 8
    passage_chars: int = 900
    passage_overlap: int = 150

    # --- collection etiquette ----------------------------------------------
    request_delay_seconds: float = 2.0
    user_agent: str = "Pharmeazor/0.1 (projet universitaire, UC2 NTIC)"
    respect_robots_txt: bool = True

    def require_api_key(self) -> str:
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Copy .env.example to .env and add "
                "your own free key from Google AI Studio. Never commit it."
            )
        return self.api_key

    def ensure_dirs(self) -> None:
        for directory in (
            self.raw_dir, self.interim_dir, self.processed_dir,
            self.reference_dir, self.cache_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
