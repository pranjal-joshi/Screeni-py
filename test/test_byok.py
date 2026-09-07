"""BYOK persistence unit for #302."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest
from pathlib import Path
from agents.byok import save_byok, load_byok, is_configured, byok_path, redacted

def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    p = tmp_path / "byok.json"
    monkeypatch.setenv("SCREENIPY_BYOK_PATH", str(p))
    data = {"provider": "openai", "api_key": "sk-test-12345", "model": "gpt-4o", "base_url": "https://api.openai.com/v1"}
    save_byok(data)
    loaded = load_byok()
    assert loaded["provider"] == "openai"
    assert loaded["api_key"] == "sk-test-12345"
    assert loaded["model"] == "gpt-4o"
    assert loaded["base_url"] == "https://api.openai.com/v1"
    assert is_configured() is True
    assert redacted(loaded)["api_key"] != "sk-test-12345"
    assert "***" in redacted(loaded)["api_key"]
    # persists across reload
    assert load_byok(p) is not None

def test_save_rejects_empty_key(tmp_path, monkeypatch):
    p = tmp_path / "byok.json"
    monkeypatch.setenv("SCREENIPY_BYOK_PATH", str(p))
    with pytest.raises(ValueError, match="api_key"):
        save_byok({"provider": "openai", "api_key": "", "model": "gpt-4o"})

def test_save_rejects_bad_provider(tmp_path, monkeypatch):
    p = tmp_path / "byok.json"
    monkeypatch.setenv("SCREENIPY_BYOK_PATH", str(p))
    with pytest.raises(ValueError, match="provider"):
        save_byok({"provider": "bad", "api_key": "sk-123", "model": "gpt-4o"})

def test_save_sets_file_permissions(tmp_path, monkeypatch):
    p = tmp_path / "byok.json"
    monkeypatch.setenv("SCREENIPY_BYOK_PATH", str(p))
    save_byok({"provider": "openai-compatible", "api_key": "sk-abc", "base_url": "http://localhost:11434/v1", "model": "llama3"})
    assert p.exists()
    data = json.loads(p.read_text())
    assert data["provider"] == "openai-compatible"
    assert data["base_url"] == "http://localhost:11434/v1"

def test_default_path_uses_screenipy_data_when_no_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SCREENIPY_BYOK_PATH", raising=False)
    monkeypatch.delenv("SCREENIPY_DATA_DIR", raising=False)
    # byok_path should fall back to cwd/screenipy_data/byok.json or /opt/program/data/byok.json
    p = byok_path()
    assert p.name == "byok.json"

def test_redacted_never_leaks_full_key():
    assert redacted({"api_key": "sk-very-long-secret-key-123"})["api_key"].count("*") >= 3
    assert "sk-very-long" not in redacted({"api_key": "sk-very-long-secret-key-123"})["api_key"]
