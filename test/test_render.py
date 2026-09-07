"""TradingView rendering seam for #303 — every pick links out."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from agents.render import tradingview_url, render_picks, render_screen_answer

def test_tradingview_url_nse():
    assert tradingview_url("RELIANCE") == "https://in.tradingview.com/chart?symbol=NSE%3ARELIANCE"
    assert "NSE%3A" in tradingview_url("TCS")

def test_tradingview_url_handles_ns_suffix_and_ampersand():
    assert tradingview_url("M&M.NS") == "https://in.tradingview.com/chart?symbol=NSE%3AM_M"
    assert tradingview_url("M&M") == "https://in.tradingview.com/chart?symbol=NSE%3AM_M"

def test_tradingview_url_non_nse():
    # S&P 500 symbols use plain chart url without NSE prefix
    assert tradingview_url("AAPL", exchange="NASDAQ") == "https://in.tradingview.com/chart?symbol=AAPL"

def test_render_picks_contains_link_per_stock():
    picks = [{"Stock": "RELIANCE", "LTP": "2450"}, {"Stock": "TCS", "LTP": "3200"}]
    md = render_picks(picks, skill="breakout")
    assert md.count("tradingview.com") == 2
    assert "[RELIANCE]" in md
    assert "[TCS]" in md
    assert "NSE%3ARELIANCE" in md

def test_render_picks_handles_empty():
    assert "No stocks" in render_picks([], skill="breakout")

def test_render_screen_answer_wraps_picks_with_tradingview():
    picks = [{"Stock": "INFY", "LTP": "1500", "Pattern": "Inside Bar"}]
    answer = render_screen_answer(skill="breakout", picks=picks, index="Nifty 50")
    assert "INFY" in answer
    assert "tradingview.com" in answer
    assert "Nifty 50" in answer

def test_render_screen_answer_no_picks_still_has_context():
    answer = render_screen_answer(skill="vcp", picks=[], index="Nifty 500")
    assert "vcp" in answer.lower()
    assert "No stocks" in answer
