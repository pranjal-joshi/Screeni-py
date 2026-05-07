"""
BrowserConfigStore — Browser-First Config Persistence via localStorage

Design pattern: Browser-First Config with Server Fallback
- Primary store: Browser localStorage (two JSON blobs)
    - screeni_config : screening params
    - screeni_llm    : LLM provider/model/base_url + optional api_key
- Fallback: screenipy.ini / screenipy.yaml on disk (still used by CLI)
- Load priority: localStorage → disk fallback → hardcoded defaults
- Save flow: localStorage first, then mirror to disk for CLI compatibility

Key constraint: streamlit-local-storage returns None on first render
(async hydration delay). Every read is guarded against None / empty.
"""

import os
import json
import configparser
import streamlit as st
from streamlit_local_storage import LocalStorage

# ── Constants ─────────────────────────────────────────────────────────────────
_KEY_CONFIG = "screeni_config"
_KEY_LLM = "screeni_llm"
_KEY_STORAGE = "_bcs_storage_init"

# ── Module-level LocalStorage singleton (NOT stored in st.session_state) ────
# We use an id()-based guard so exactly one instance is created per Python
# interpreter.  The LocalStorage component renders itself each script run
# (that's how Streamlit works) but we re-use the same Python object so that
# .storedItems stays accessible across reruns.
_storage: LocalStorage | None = None


def _get_storage() -> LocalStorage | None:
    """Return the per-process LocalStorage instance, or None on first render."""
    global _storage
    if _storage is None:
        _storage = LocalStorage(key=_KEY_STORAGE)
        # First render: component just mounted — browser hasn't synced yet.
        # storedItems will be empty; callers should fall back to defaults.
        return None
    return _storage


def _safe_json_load(raw) -> dict:
    """Parse a value from localStorage into a dict, returning {} on failure."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _find_screenipy_yaml() -> str:
    """Locate screenipy.yaml relative to this file or repo root."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'screenipy.yaml'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'screenipy.yaml'),
        'screenipy.yaml',
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.exists(p):
            return p
    return os.path.abspath(candidates[0])


# ── Public API ────────────────────────────────────────────────────────────────

def load_screening_config(fallback_cm) -> dict:
    """Load screening params from localStorage; fall back to ConfigManager.

    Args:
        fallback_cm: An initialised ConfigManager.tools() instance used as
                     fallback when localStorage returns nothing.

    Returns:
        dict with keys matching ConfigManager attribute names.
    """
    storage = _get_storage()
    if storage is None:
        # First render — browser component not yet hydrated.
        return _fallback_screening_config(fallback_cm)

    raw = storage.getItem(_KEY_CONFIG)
    data = _safe_json_load(raw)
    if data:
        return data

    # Fallback: read from ConfigManager instance
    return _fallback_screening_config(fallback_cm)


def _fallback_screening_config(fallback_cm) -> dict:
    return {
        "period": fallback_cm.period,
        "daysToLookback": fallback_cm.daysToLookback,
        "duration": fallback_cm.duration,
        "minLTP": fallback_cm.minLTP,
        "maxLTP": fallback_cm.maxLTP,
        "volumeRatio": fallback_cm.volumeRatio,
        "consolidationPercentage": fallback_cm.consolidationPercentage,
        "shuffleEnabled": fallback_cm.shuffleEnabled,
        "cacheEnabled": fallback_cm.cacheEnabled,
        "stageTwo": fallback_cm.stageTwo,
        "useEMA": fallback_cm.useEMA,
    }


def save_screening_config(data: dict, fallback_cm) -> None:
    """Persist screening params to localStorage and mirror to screenipy.ini.

    Args:
        data: dict with screening param values (keys match ConfigManager attrs).
        fallback_cm: ConfigManager.tools() instance used to write screenipy.ini.
    """
    storage = _get_storage()
    if storage is not None:
        storage.setItem(itemKey=_KEY_CONFIG, itemValue=data, key="save_screeni_config")

    # Mirror to disk for CLI compatibility
    fallback_cm.period = data.get("period", fallback_cm.period)
    fallback_cm.daysToLookback = data.get("daysToLookback", fallback_cm.daysToLookback)
    fallback_cm.duration = data.get("duration", fallback_cm.duration)
    fallback_cm.minLTP = data.get("minLTP", fallback_cm.minLTP)
    fallback_cm.maxLTP = data.get("maxLTP", fallback_cm.maxLTP)
    fallback_cm.volumeRatio = data.get("volumeRatio", fallback_cm.volumeRatio)
    fallback_cm.consolidationPercentage = data.get("consolidationPercentage",
                                                    fallback_cm.consolidationPercentage)
    fallback_cm.shuffleEnabled = data.get("shuffleEnabled", fallback_cm.shuffleEnabled)
    fallback_cm.cacheEnabled = data.get("cacheEnabled", fallback_cm.cacheEnabled)
    fallback_cm.stageTwo = data.get("stageTwo", fallback_cm.stageTwo)
    fallback_cm.useEMA = data.get("useEMA", fallback_cm.useEMA)
    fallback_cm.setConfig(
        configparser.ConfigParser(strict=False),
        default=True,
        showFileCreatedText=False,
    )


def load_llm_config(fallback_yaml_path: str = None) -> dict:
    """Load LLM config from localStorage; fall back to screenipy.yaml.

    Args:
        fallback_yaml_path: Optional explicit path to screenipy.yaml.

    Returns:
        dict with keys: provider, model, base_url, api_key, remember_api_key.
    """
    storage = _get_storage()
    if storage is not None:
        raw = storage.getItem(_KEY_LLM)
        data = _safe_json_load(raw)
        if data:
            return data

    # Fallback: read from YAML
    yaml_path = fallback_yaml_path or _find_screenipy_yaml()
    defaults = {
        "provider": "openai",
        "model": "gpt-4o",
        "base_url": "http://localhost:11434/v1",
        "api_key": os.environ.get("SCREENIPY_API_KEY", ""),
        "remember_api_key": False,
    }
    if not os.path.exists(yaml_path):
        return defaults
    try:
        import yaml
        with open(yaml_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        llm = cfg.get("llm", {})
        defaults["provider"] = llm.get("provider", defaults["provider"])
        defaults["model"] = llm.get("model", defaults["model"])
        defaults["base_url"] = llm.get("base_url") or defaults["base_url"]
    except Exception:
        pass
    return defaults


def save_llm_config(data: dict, remember_api_key: bool, fallback_yaml_path: str = None) -> None:
    """Persist LLM config to localStorage and mirror safe fields to screenipy.yaml.

    Args:
        data: dict with LLM config values (provider, model, base_url, api_key).
        remember_api_key: If True, include api_key in the localStorage blob.
        fallback_yaml_path: Optional explicit path to screenipy.yaml.
    """
    blob = {
        "provider": data.get("provider", "openai"),
        "model": data.get("model", "gpt-4o"),
        "base_url": data.get("base_url", ""),
        "remember_api_key": remember_api_key,
    }
    if remember_api_key:
        blob["api_key"] = data.get("api_key", "")

    storage = _get_storage()
    if storage is not None:
        storage.setItem(itemKey=_KEY_LLM, itemValue=blob, key="save_screeni_llm")

    # Mirror provider/model/base_url to YAML — never persist api_key to disk
    yaml_path = fallback_yaml_path or _find_screenipy_yaml()
    try:
        import yaml
        if os.path.exists(yaml_path):
            with open(yaml_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
        else:
            cfg = {}
        llm = cfg.setdefault("llm", {})
        llm["provider"] = blob["provider"]
        llm["model"] = blob["model"]
        if blob["provider"] == "openai-compatible" and blob.get("base_url"):
            llm["base_url"] = blob["base_url"]
        else:
            llm["base_url"] = None
        with open(yaml_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        st.toast(f"Could not mirror LLM config to YAML: {e}", icon="⚠️")


def clear_all() -> None:
    """Clear all browser-stored config blobs and relevant session_state keys."""
    storage = _get_storage()
    if storage is not None:
        storage.eraseItem(itemKey=_KEY_CONFIG, key="clear_screeni_config")
        storage.eraseItem(itemKey=_KEY_LLM, key="clear_screeni_llm")

    # Clear related session_state keys so defaults reload on next render
    for key in (
        "ai_provider", "ai_model", "ai_base_url", "ai_api_key",
        "_llm_defaults_loaded", "_bcs_llm_loaded",
        "cfg_period", "cfg_lookback", "cfg_duration",
        "cfg_minprice", "cfg_maxprice", "cfg_volratio",
        "cfg_consolpct", "cfg_shuffle", "cfg_cache",
        "cfg_stagetwo", "cfg_useema",
    ):
        st.session_state.pop(key, None)
