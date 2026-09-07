"""
BYOK persistence for #302.

First-run setup page writes {provider, api_key, base_url, model} to a JSON file
in the persisted screenipy_data volume. The engine hot-reloads it on next /health
or /setup and seeds Chat via OPENAI_API_BASE_URL env at first boot.

File location (first match):
  $SCREENIPY_BYOK_PATH
  /opt/program/data/byok.json  (compose screenipy_data volume)
  ./screenipy_data/byok.json    (local dev)
  ~/.screenipy/byok.json        (fallback)
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional

# Allow tests to override via env
ENV_PATH = "SCREENIPY_BYOK_PATH"
ENV_DATA_DIR = "SCREENIPY_DATA_DIR"

DEFAULT_REL = Path("screenipy_data") / "byok.json"

CANDIDATES = [
    Path("/opt/program/data/byok.json"),
    Path.cwd() / "screenipy_data" / "byok.json",
    Path.home() / ".screenipy" / "byok.json",
    Path.cwd() / "byok.json",
]

REQUIRED_KEYS = {"provider", "api_key"}

VALID_PROVIDERS = {"openai", "anthropic", "openai-compatible"}

def byok_path() -> Path:
    env = os.environ.get(ENV_PATH, "").strip()
    if env:
        return Path(env)
    data_dir = os.environ.get(ENV_DATA_DIR, "").strip()
    if data_dir:
        return Path(data_dir) / "byok.json"
    for p in CANDIDATES:
        # Use first existing parent or default location; prefer existing file if present
        if p.exists():
            return p
    # Default: screenipy_data volume if inside container else first candidate that is writable
    # Prefer /opt/program/data when that directory exists (compose mount)
    if Path("/opt/program/data").exists():
        return Path("/opt/program/data/byok.json")
    return CANDIDATES[1]  # cwd/screenipy_data/byok.json

def load_byok(path: Optional[Path] = None) -> Optional[Dict]:
    p = Path(path) if path is not None else byok_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    # Minimal validation: must have api_key
    if not data.get("api_key"):
        return None
    return data

def save_byok(data: Dict, path: Optional[Path] = None) -> Path:
    """Persist BYOK dict; validates and redacts on write? Returns path written."""
    if not isinstance(data, dict):
        raise ValueError("BYOK data must be a dict")
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        raise ValueError("api_key: required non-empty string")
    provider = (data.get("provider") or "openai").strip().lower()
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"provider: must be one of {sorted(VALID_PROVIDERS)} got {provider!r}")
    # Normalize
    norm = {
        "provider": provider,
        "api_key": api_key,
        "base_url": (data.get("base_url") or "").strip() or None,
        "model": (data.get("model") or "gpt-4o").strip(),
    }
    # Clean None base_url
    if not norm["base_url"]:
        norm["base_url"] = None

    p = Path(path) if path is not None else byok_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Write with restrictive permissions where possible (0o600)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(norm, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    tmp.replace(p)
    return p

def is_configured(path: Optional[Path] = None) -> bool:
    return load_byok(path) is not None

def redacted(data: Optional[Dict]) -> Optional[Dict]:
    if not data:
        return None
    out = dict(data)
    key = out.get("api_key", "")
    if key and len(key) > 8:
        out["api_key"] = key[:3] + "***" + key[-3:]
    elif key:
        out["api_key"] = "***"
    return out
