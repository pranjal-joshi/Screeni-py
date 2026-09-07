"""Presets + default strategy pack for #303 — selectable with no manual config."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from agents.presets import MODEL_PRESETS, DEFAULT_STRATEGY_PACK, list_model_ids

def test_model_presets_non_empty_selectable_without_byok():
    assert len(MODEL_PRESETS) >= 2
    ids = list_model_ids()
    assert "screenipy" in ids
    assert "gpt-4o" in ids
    # No BYOK file needed
    assert all("id" in m for m in MODEL_PRESETS)

def test_default_strategy_pack_breakout_vcp():
    assert "breakout" in DEFAULT_STRATEGY_PACK
    assert "vcp" in DEFAULT_STRATEGY_PACK

def test_presets_endpoint_requires_no_config():
    from fastapi.testclient import TestClient
    from agents.server import create_app
    from agents.engine import ScreenipyEngine
    from agents.skill_gate import load_skills
    # Empty custom dir, fresh cache, no BYOK file
    skills, rejs = load_skills()
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=__import__('types').SimpleNamespace(summarize=lambda k: {'count':1,'sources':['stooq'],'as_of':'2026-09-06','stale':False,'stale_symbols':[]}))
    app = create_app(engine=eng)
    c = TestClient(app)
    r = c.get("/v1/models")
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(m["id"] == "screenipy" for m in data)
    assert any(m["id"] == "gpt-4o" for m in data)
    r = c.get("/v1/skills")
    assert "breakout" in r.json()["skills"]
    assert "vcp" in r.json()["skills"]
    assert r.json()["default_strategy_pack"] == DEFAULT_STRATEGY_PACK
    r = c.get("/v1/presets")
    assert "models" in r.json()
    assert "default_strategy_pack" in r.json()
    # Chat completions selectable with preset model id without manual config
    r = c.post("/v1/chat/completions", json={"model": "gpt-4o", "messages": [{"role": "user", "content": "show breakout"}]})
    assert r.status_code == 200
    assert r.json()["model"] == "gpt-4o"
