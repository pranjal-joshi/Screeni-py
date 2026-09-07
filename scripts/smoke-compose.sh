#!/usr/bin/env bash
# Smoke bring-up for #302 — verifies the two-service compose stack without requiring a daemon.
# Runs: compose config validity, Screenipy /health + /setup + /v1 contract, Chat env wiring, lean volumes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== compose config =="
docker compose config >/dev/null
echo "ok: compose config valid"

echo "== compose services =="
if ! docker compose config | grep -q "screenipy:"; then echo "FAIL: screenipy service missing"; exit 1; fi
if ! docker compose config | grep -q "chat:"; then echo "FAIL: chat service missing"; exit 1; fi
echo "ok: both services present"

echo "== chat dumb shell wiring =="
if ! docker compose config | grep -q "OPENAI_API_BASE_URL.*http://screenipy:8000/v1"; then
  echo "FAIL: chat OPENAI_API_BASE_URL not wired to screenipy:8000/v1"; exit 1
fi
if docker compose config | grep -q "screener_tools\|TOOL_MAP\|screen_breakout"; then
  echo "FAIL: chat service must hold no agent logic"; exit 1
fi
echo "ok: chat env-seeded to /v1, no agent logic"

echo "== volumes lean =="
if docker compose config | grep -q "screenipy_config"; then echo "FAIL: config volume should be dropped (lean volumes)"; exit 1; fi
if ! docker compose config | grep -q "screenipy_data"; then echo "FAIL: screenipy_data volume missing"; exit 1; fi
if ! docker compose config | grep -q "open-webui"; then echo "FAIL: open-webui volume missing"; exit 1; fi
echo "ok: lean volumes (screenipy_data + open-webui)"

echo "== screenipy_data persistence (byok + skills) =="
if ! docker compose config | grep -q "byok.json\|SCREENIPY_DATA_DIR"; then
  echo "warn: byok persistence not explicit (expected byok.json in screenipy_data)" 
fi
if ! docker compose config | grep -q "skills"; then
  echo "warn: skills mount not explicit (expected screenipy_data/skills)"
fi

# If services are up, probe live endpoints; otherwise run in-process FastAPI checks
if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  echo "== live screenipy probes =="
  curl -sf http://localhost:8000/health | grep -q '"status":"ok"' || { echo "FAIL: /health"; exit 1; }
  curl -sf http://localhost:8000/setup | grep -q "Screenipy" || { echo "FAIL: /setup"; exit 1; }
  curl -sf http://localhost:8000/v1/models | grep -q "screenipy" || { echo "FAIL: /v1/models"; exit 1; }
  curl -sf -X POST http://localhost:8000/v1/chat/completions -H 'content-type: application/json' -d '{"model":"screenipy","messages":[{"role":"user","content":"show breakout"}]}' | grep -q "choices" || { echo "FAIL: /v1/chat/completions"; exit 1; }
  echo "ok: live probes passed"
  if curl -sf http://localhost:3000/ >/dev/null 2>&1; then echo "ok: chat reachable on :3000"; else echo "warn: chat not reachable (expected ghcr.io/open-webui)"; fi
else
  echo "== in-process contract (no live compose) =="
  # Prefer uv run if available, else venv python
  if uv run python -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
    PYRUN="uv run python"
  elif [ -x ".venv/Scripts/python.exe" ]; then
    PYRUN=".venv/Scripts/python.exe"
  elif [ -x ".venv/bin/python" ]; then
    PYRUN=".venv/bin/python"
  else
    PYRUN="python"
  fi
  $PYRUN -c "
import sys
sys.path.insert(0, 'src')
from fastapi.testclient import TestClient
from agents.server import create_app
from agents.engine import ScreenipyEngine
from agents.skill_gate import load_skills

skills, rejs = load_skills()
eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=__import__('types').SimpleNamespace(summarize=lambda k: {'count':1,'sources':['stooq'],'as_of':'2026-09-06','stale':False,'stale_symbols':[]}))
import agents.screener_tools as st
st.screen_breakout = lambda index='Nifty 500', days_lookback=20: f'breakout:{index}'
st.screen_vcp = lambda index='Nifty 500', window=3, pct_from_top=3.0: f'vcp:{index}'
st.TOOL_MAP['screen_breakout'] = st.screen_breakout
st.TOOL_MAP['screen_vcp'] = st.screen_vcp
app = create_app(engine=eng)
c = TestClient(app)
assert c.get('/health').status_code == 200
assert 'screenipy' in str(c.get('/v1/models').json())
assert 'breakout' in str(c.get('/v1/skills').json())
r = c.post('/v1/chat/completions', json={'model':'screenipy','messages':[{'role':'user','content':'show breakout'}]})
assert r.status_code == 200 and 'choices' in r.json()
r = c.get('/setup'); assert r.status_code == 200
r = c.post('/setup', json={'provider':'openai','api_key':'sk-test-12345','model':'gpt-4o'})
assert r.status_code == 200 and r.json()['status'] == 'ok'
r = c.get('/byok'); assert r.json()['configured'] == True
print('ok: in-process contract passed')
"
fi

echo "== smoke 302 PASS =="
