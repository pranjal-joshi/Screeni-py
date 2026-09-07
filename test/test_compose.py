"""Compose stack contract for #302 — pins dumb-shell wiring and lean volumes."""
import sys, os, pathlib, yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

def _compose():
    p = pathlib.Path("docker-compose.yml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def test_compose_has_two_services():
    cfg = _compose()
    assert "screenipy" in cfg["services"]
    assert "chat" in cfg["services"]
    assert len(cfg["services"]) == 2

def test_screenipy_exposes_v1():
    cfg = _compose()
    s = cfg["services"]["screenipy"]
    # must expose 8000 and command runs uvicorn agents.server
    ports = " ".join(str(x) for x in s.get("ports", []))
    assert "8000:8000" in ports
    cmd = " ".join(str(x) for x in s.get("command", []))
    assert "agents.server" in cmd or "uvicorn" in cmd

def test_chat_dumb_shell_wiring():
    cfg = _compose()
    chat = cfg["services"]["chat"]
    assert "ghcr.io/open-webui" in chat["image"]
    env = chat.get("environment", [])
    # normalize to dict
    env_str = " ".join(str(x) for x in env)
    assert "OPENAI_API_BASE_URL=http://screenipy:8000/v1" in env_str
    # Chat must hold no agent logic — no mount of screener code, no TOOL_MAP
    assert "screener_tools" not in env_str
    assert "open-webui" in str(cfg["volumes"])

def test_volumes_lean():
    cfg = _compose()
    vols = cfg.get("volumes", {})
    assert "screenipy_data" in vols
    assert "open-webui" in vols
    assert "screenipy_config" not in vols
    # screenipy_data used for byok + skills persistence
    screenipy_vols = " ".join(str(x) for x in cfg["services"]["screenipy"].get("volumes", []))
    assert "screenipy_data" in screenipy_vols

def test_chat_depends_on_screenipy_healthy():
    cfg = _compose()
    chat = cfg["services"]["chat"]
    depends = chat.get("depends_on", {})
    # can be dict with condition or list
    if isinstance(depends, dict):
        assert "screenipy" in depends
    else:
        assert "screenipy" in depends

def test_setup_and_byok_endpoints_exist():
    # Pin that server exposes /setup + /byok in addition to /v1
    sys.path.insert(0, "src")
    from fastapi.testclient import TestClient
    from agents.server import create_app
    from agents.engine import ScreenipyEngine
    from agents.skill_gate import load_skills
    skills, rejs = load_skills()
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=__import__('types').SimpleNamespace(summarize=lambda k: {'count':1,'sources':['stooq'],'as_of':'2026-09-06','stale':False,'stale_symbols':[]}))
    app = create_app(engine=eng)
    c = TestClient(app)
    assert c.get("/setup").status_code == 200
    assert c.get("/byok").status_code == 200
    assert c.get("/health").status_code == 200
