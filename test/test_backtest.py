"""Backtest conversational rendering for #303."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from agents.render import render_backtest_answer

def test_render_backtest_contains_tradingview_and_followup():
    picks = [{"Stock": "RELIANCE", "LTP": "2450", "1Y Return": "12.3%"},
             {"Stock": "TCS", "LTP": "3200", "1Y Return": "8.1%"}]
    report = {"n": 2, "hit_rate": "60%", "avg_return": "10.2%"}
    md = render_backtest_answer(skill="breakout", picks=picks, report=report, index="Nifty 500")
    assert "Backtest:" in md
    assert "RELIANCE" in md and "TCS" in md
    assert md.count("tradingview.com") == 2
    assert "Follow-up" in md
    assert "hit rate" in md.lower()

def test_backtest_engine_conversational_via_v1(monkeypatch):
    # Pin that /v1 chat with backtest intent renders conversationally and supports follow-up
    from fastapi.testclient import TestClient
    from agents.server import create_app
    from agents.engine import ScreenipyEngine
    from agents.skill_gate import load_skills
    import agents.screener_tools as st

    # Mock screener to return deterministic picks
    st.screen_breakout = lambda index="Nifty 500", days_lookback=20: "Breakout stocks in Nifty 500:\n{'Stock': 'RELIANCE', 'LTP': '2450'}\n{'Stock': 'TCS', 'LTP': '3200'}"
    st.screen_vcp = lambda index="Nifty 500", window=3, pct_from_top=3.0: "VCP stocks in Nifty 500:\n{'Stock': 'INFY', 'LTP': '1500'}"
    st.TOOL_MAP["screen_breakout"] = st.screen_breakout
    st.TOOL_MAP["screen_vcp"] = st.screen_vcp

    skills, rejs = load_skills()
    eng = ScreenipyEngine(skills=skills, rejections=rejs, cache=__import__('types').SimpleNamespace(summarize=lambda k: {'count':1,'sources':['stooq'],'as_of':'2026-09-06','stale':False,'stale_symbols':[]}))
    app = create_app(engine=eng)
    c = TestClient(app)

    r = c.post("/v1/chat/completions", json={"model": "screenipy", "messages": [{"role": "user", "content": "backtest breakout on Nifty 500"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "Backtest:" in content
    assert "tradingview.com" in content
    assert "RELIANCE" in content
    assert "Follow-up" in content

    # Follow-up: details for a symbol
    r2 = c.post("/v1/chat/completions", json={"model": "screenipy", "messages": [
        {"role": "user", "content": "backtest breakout on Nifty 500"},
        {"role": "assistant", "content": content},
        {"role": "user", "content": "details for RELIANCE"}
    ]})
    assert r2.status_code == 200
    content2 = r2.json()["choices"][0]["message"]["content"]
    assert "RELIANCE" in content2
    assert "tradingview.com" in content2
