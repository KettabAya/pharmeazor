from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = PROCESSED_DIR / "cache.json"
COUNTER_FILE = PROCESSED_DIR / "call_counter.json"
MODEL_NAME = "openai/gpt-oss-20b"
BASE_URL = "https://api.groq.com/openai/v1"


def _load_api_key() -> str:
    try:
        from google.colab import userdata

        key = userdata.get("GROQ_API_KEY")
        if key:
            print(f"[llm_client] key loaded (ends ...{key[-4:]})")
            return key
    except ImportError:
        pass

    try:
        from kaggle_secrets import UserSecretsClient

        key = UserSecretsClient().get_secret("GROQ_API_KEY")
        if key:
            print(f"[llm_client] key loaded from Kaggle (ends ...{key[-4:]})")
            return key
    except (ImportError, Exception):
        pass

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not found.")
    print(f"[llm_client] key loaded from env (ends ...{key[-4:]})")
    return key


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open() as f:
        return json.load(f)


def _save_json(path: Path, data) -> None:
    with path.open("w") as f:
        json.dump(data, f, indent=2)


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=_load_api_key(), base_url=BASE_URL)
    return _client


def ask_llm(prompt: str, use_cache: bool = True, temperature: float = 0.0) -> str:
    key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    cache = _load_json(CACHE_FILE, {})
    if use_cache and key in cache:
        print("[llm_client] CACHE HIT")
        return cache[key]

    print("[llm_client] API CALL")
    try:
        response = _get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        answer = response.choices[0].message.content or ""

        cache[key] = answer
        _save_json(CACHE_FILE, cache)

        counter = _load_json(COUNTER_FILE, {"count": 0})
        counter["count"] += 1
        _save_json(COUNTER_FILE, counter)

        return answer

    except Exception as exc:
        return f"ERROR: {exc}"


def get_call_count() -> int:
    return _load_json(COUNTER_FILE, {"count": 0})["count"]


if __name__ == "__main__":
    print(ask_llm("What is the capital of Algeria?"))
    print(ask_llm("What is the capital of Algeria?"))
    print(f"Total API calls: {get_call_count()}")
