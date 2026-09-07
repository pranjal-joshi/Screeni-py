"""HTTP contract tests for /v1 (issue #301) + engine freshness/gate integration."""
import sys, os, textwrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest

from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from agents.server import create_app
from agents.engine import ScreenipyEngine
from agents.skill_gate import load_skills

VALID_CUSTOM = textwrap.dedent("""
---
name: custom_momo
when_to_use: User wants momentum or custom chain for testing the loader.
tools:
  - tool: screen_momentum
    params:
      index: Nifty 500
---
# Custom Momo
## Entry
Momentum entry.
## Exit
Stop below 10 DMA.
## Rendering
Momentum table.
""").strip()

def _mock_screener(monkeypatch):
    """Patch screener tools to avoid real network/screener."""
    import agents.screener_tools as st
    monkeypatch.setattr(st, "screen_breakout", lambda index="Nifty 500", days_lookback=20: f"breakout:{index}:{days_lookback}")
    monkeypatch.setattr(st, "screen_volume_breakout", lambda index="Nifty 500", volume_ratio=1.5: f"vol:{index}:{volume_ratio}")
    monkeypatch.setattr(st, "screen_vcp", lambda index="Nifty 500", window=3, pct_from_top=3.0: f"vcp:{index}:{window}:{pct_from_top}")
    monkeypatch.setattr(st, "screen_momentum", lambda index="Nifty 500": f"momentum:{index}")
    monkeypatch.setattr(st, "screen_rsi", lambda index="Nifty 500", min_rsi=40, max_rsi=60: f"rsi:{index}:{min_rsi}-{max_rsi}")
    # also patch TOOL_MAP entries to point at same patches
    for k in list(st.TOOL_MAP.keys()):
        if hasattr(st, k):
            st.TOOL_MAP[k] = getattr(st, k)

class _FreshCache:
    def summarize(self, kind):
        return {"count": 1, "sources": ["stooq"], "as_of": "2026-09-06", "stale": False, "stale_symbols": []}

class _StaleCache:
    def summarize(self, kind):
        return {"count": 1, "sources": ["stooq"], "as_of": "2026-09-01", "stale": True, "stale_symbols": ["RELIANCE"]}

@pytest.fixture
def fresh_client(monkeypatch):
    _mock_screener(monkeypatch)
    skills, rejs = load_skills()
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=_FreshCache())
    app = create_app(engine=eng)
    return TestClient(app)

@pytest.fixture
def stale_client(monkeypatch):
    _mock_screener(monkeypatch)
    skills, rejs = load_skills()
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=_StaleCache())
    app = create_app(engine=eng)
    return TestClient(app)

def test_health_and_models(fresh_client):
    r = fresh_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "breakout" in r.json()["skills"]
    r = fresh_client.get("/v1/models")
    assert r.status_code == 200
    assert r.json()["object"] == "list"
    assert any(d["id"] == "screenipy" for d in r.json()["data"])

def test_skills_endpoint_lists_curated(fresh_client):
    r = fresh_client.get("/v1/skills")
    assert r.status_code == 200
    assert "breakout" in r.json()["skills"]
    assert "vcp" in r.json()["skills"]

def test_plain_language_returns_chat_complete(fresh_client):
    r = fresh_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [{"role": "user", "content": "show me breakout stocks on Nifty 50"}]
    })
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert "choices" in body and len(body["choices"]) == 1
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["finish_reason"] == "stop"
    content = body["choices"][0]["message"]["content"]
    assert isinstance(content, str) and len(content) > 0
    # chat-complete answer must contain tool output / skill header
    assert "breakout" in content.lower()

def test_auto_routes_vcp(fresh_client):
    r = fresh_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [{"role": "user", "content": "find VCP setups for me"}]
    })
    assert r.status_code == 200
    assert "vcp" in r.json()["choices"][0]["message"]["content"].lower()

def test_explicit_override(fresh_client):
    r = fresh_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [{"role": "user", "content": "show breakout stocks but use vcp"}]
    })
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    # explicit use vcp wins even though query says breakout
    assert "vcp" in content.lower()

def test_fresh_data_silent(fresh_client):
    r = fresh_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [{"role": "user", "content": "show breakout"}]
    })
    content = r.json()["choices"][0]["message"]["content"]
    assert "stale" not in content.lower()
    assert "outdated" not in content.lower()

def test_stale_blocks_on_choice(stale_client):
    r = stale_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [{"role": "user", "content": "show breakout"}]
    })
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "stale" in content.lower()
    assert "reply with 'fresh'" in content.lower()
    assert "'stale'" in content.lower()

def test_stale_choice_stale_returns_note_plus_result(stale_client):
    # multi-turn: user intent, assistant stale block, then user says 'stale'
    r = stale_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [
            {"role": "user", "content": "show breakout"},
            {"role": "assistant", "content": "Data is stale (as of 2026-09-01). Reply with 'fresh' or 'stale' to proceed."},
            {"role": "user", "content": "stale"},
        ]
    })
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "outdated" in content.lower()
    assert "as of 2026-09-01" in content

def test_stale_choice_fresh_proceeds_without_note(stale_client):
    r = stale_client.post("/v1/chat/completions", json={
        "model": "screenipy",
        "messages": [
            {"role": "user", "content": "show breakout"},
            {"role": "assistant", "content": "Data is stale. Reply with 'fresh' or 'stale'."},
            {"role": "user", "content": "fresh"},
        ]
    })
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    # fresh choice proceeds to tool output, no outdated prefix
    assert "outdated" not in content.lower()

def test_custom_skill_valid_loaded(tmp_path, monkeypatch):
    _mock_screener(monkeypatch)
    good = tmp_path / "custom_momo.md"
    good.write_text(VALID_CUSTOM, encoding="utf-8")
    skills, rejs = load_skills(user_dir=str(tmp_path))
    assert "custom_momo" in skills
    assert str(good) not in rejs
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=_FreshCache())
    # explicit use custom_momo
    r = eng.answer("use custom_momo please")
    assert "momentum" in r.lower()

def test_custom_skill_invalid_rejected_chat_visible(tmp_path, monkeypatch):
    _mock_screener(monkeypatch)
    bad = tmp_path / "bad.md"
    bad.write_text(textwrap.dedent("""
    ---
    name: bad
    when_to_use: short
    tools:
      - tool: screen_breakout
    ---
    ## Entry
    x
    ## Exit
    y
    ## Rendering
    z
    """), encoding="utf-8")
    skills, rejs = load_skills(user_dir=str(tmp_path))
    assert str(bad) in rejs
    msg = rejs[str(bad)]
    assert "when_to_use" in msg
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=_FreshCache())
    app = create_app(engine=eng)
    client = TestClient(app)
    r = client.get("/v1/skills")
    # rejection is chat-visible via /v1/skills
    assert any("when_to_use" in v for v in r.json()["rejections"])

def test_http_contract_requires_messages(fresh_client):
    r = fresh_client.post("/v1/chat/completions", json={"model": "screenipy", "messages": []})
    assert r.status_code == 400
    r = fresh_client.post("/v1/chat/completions", json={"model": "screenipy", "messages": [{"role": "user", "content": ""}]})
    assert r.status_code == 400
    r = fresh_client.post("/v1/chat/completions", json={"model": "screenipy", "messages": [{"role": "user", "content": "hi"}], "stream": True})
    assert r.status_code == 400

def test_breakout_and_vcp_work_without_custom_files(monkeypatch):
    _mock_screener(monkeypatch)
    # load with empty custom dir
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        skills, rejs = load_skills(user_dir=td)
        assert "breakout" in skills
        assert "vcp" in skills
        assert rejs == {}
        eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=_FreshCache())
        assert "breakout" in eng.answer("show breakout").lower()
        assert "vcp" in eng.answer("show vcp").lower()
