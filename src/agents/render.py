"""
Rendering polish for #303.

- Every pick links to TradingView.
- Screen answers are markdown tables with linked symbols.
"""
from typing import List, Dict, Any


def tradingview_url(symbol: str, exchange: str = "NSE") -> str:
    """
    TradingView deep-link for a symbol.

    NSE symbols (default): https://in.tradingview.com/chart?symbol=NSE%3A<SYMBOL>
    where <SYMBOL> is uppercased, trailing '.NS' and leading '^' stripped,
    and '&' replaced with '_' (matches ParallelProcessing urlStock logic).

    Non-NSE (e.g. NASDAQ/S&P): plain symbol without NSE prefix.
    """
    raw = symbol.strip().upper()
    # Strip common NSE suffixes
    if raw.endswith(".NS"):
        raw = raw[:-3]
    raw = raw.lstrip("^")
    # TradingView uses '_' for '&' in symbols like M&M
    raw = raw.replace("&", "_")
    # Also handle any remaining characters that TradingView dislikes: keep A-Z0-9_- only?
    # Preserve as-is for now; tests expect M_M.
    if exchange.upper() == "NSE":
        return f"https://in.tradingview.com/chart?symbol=NSE%3A{raw}"
    return f"https://in.tradingview.com/chart?symbol={raw}"


def _pick_keys(picks: List[Dict[str, Any]]) -> List[str]:
    if not picks:
        return []
    # Preserve Stock first, then others in insertion order
    all_keys = []
    seen = set()
    for p in picks:
        for k in p.keys():
            if k not in seen:
                seen.add(k)
                all_keys.append(k)
    # Move Stock to front
    if "Stock" in all_keys:
        all_keys.remove("Stock")
        all_keys = ["Stock"] + all_keys
    return all_keys


def render_picks(picks: List[Dict[str, Any]], skill: str = "", exchange: str = "NSE") -> str:
    """
    Render a list of stock picks as a markdown table with TradingView links.

    Every Stock cell is `[SYMBOL](tradingview_url)`.
    """
    if not picks:
        return f"No stocks matched the criteria for **{skill}**." if skill else "No stocks matched the criteria."

    keys = _pick_keys(picks)
    header = "| " + " | ".join(keys) + " |"
    sep = "| " + " | ".join("---" for _ in keys) + " |"
    rows = [header, sep]
    for p in picks:
        cells = []
        for k in keys:
            v = p.get(k, "")
            if k == "Stock":
                sym = str(v)
                url = tradingview_url(sym, exchange=exchange)
                cells.append(f"[{sym}]({url})")
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def render_screen_answer(skill: str, picks: List[Dict[str, Any]], index: str = "Nifty 500", exchange: str = "NSE", note: str = "") -> str:
    """
    Full chat answer for a screen: header + picks table + footer hint.
    """
    title = f"### {skill.title()} — {index}"
    body = render_picks(picks, skill=skill, exchange=exchange)
    parts = [title, body]
    if note:
        parts.append(note)
    # Follow-up hint for conversational flow
    if picks:
        parts.append("_Tip: Ask 'backtest {skill} on {index}' or 'details for SYMBOL' to continue._")
    return "\n\n".join(parts)


def render_backtest_answer(skill: str, picks: List[Dict[str, Any]], report: Dict[str, Any] | None = None, index: str = "Nifty 500", exchange: str = "NSE") -> str:
    """
    Backtest answer rendered conversationally.

    `report` may contain aggregated stats like {hit_rate, avg_return, n}.
    Picks may include per-stock backtest fields (e.g., '1Y Return').
    """
    header = f"### Backtest: {skill.title()} — {index}"
    # Summary line
    if report:
        n = report.get("n", len(picks))
        hit = report.get("hit_rate", report.get("hitRate", "—"))
        avg = report.get("avg_return", report.get("avgReturn", "—"))
        summary = f"Backtest on {n} picks: hit rate **{hit}**, avg return **{avg}**."
    else:
        summary = f"Backtest on {len(picks)} picks for **{skill}** ({index})."
    table = render_picks(picks, skill=skill, exchange=exchange)
    follow = "_Follow-up: say 'show breakout again' or 'details for SYMBOL' to continue._"
    return "\n\n".join([header, summary, table, follow])
