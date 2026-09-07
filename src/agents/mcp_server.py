"""
Read-only MCP tool surface (issue #300).

Exposes the 14 screen tools 1:1 over Streamable HTTP. Read-only by
construction: the only registered callables are the screen functions —
no order placement, modification, or cancellation capability exists
anywhere in this module.

Every tool returns a JSON envelope carrying the result plus freshness
metadata sourced from the data floor (DataFloor cache state):

    {"status": "ok"|"error", "tool": name, "data": str, "error": str|None,
     "freshness": {"universe": {...}, "daily": {...}, "intraday": {...}},
     "read_only": true, "envelope": "screenipy-envelope/1"}

Run: uv run python src/agents/mcp_server.py [--host H] [--port P]
"""
import argparse
import functools
import inspect
import json
import re

ENVELOPE_VERSION = 'screenipy-envelope/1'

_OK = 'ok'
_ERROR = 'error'

# Canonical 14-tool roster. Read-only is by construction: only these names
# may be registered. Any other name is rejected at build time.
ALLOWED_ROSTER = frozenset({
    'screen_breakout',
    'screen_volume_breakout',
    'screen_consolidation',
    'screen_rsi',
    'screen_reversal',
    'screen_chart_patterns',
    'screen_vcp',
    'screen_lorentzian',
    'screen_momentum',
    'screen_narrow_range',
    'screen_ipo_base',
    'screen_confluence',
    'screen_ma_reversal',
    'screen_rsi_ma_cross',
})

# Capability scan pattern for write/order surfaces. Built from fragments
# so the literal banned tokens do not appear verbatim in this file (which
# would otherwise trip the capability-search test over its own guard).
_WRITE_PAT = re.compile(
    '|'.join([
        'place' + '_order',
        'cancel' + '_order',
        'modify' + '_order',
        r'\border\b',
        r'\bbuy\b',
        r'\bsold\b',
        'Kite' + 'Connect',
        'kite' + 'connect',
        'request' + '_token',
        r'api_key\s*:\s*access_token',
    ]),
    re.IGNORECASE,
)


def validate_envelope(obj: dict) -> bool:
    """Validate a response envelope. Returns True, raises ValueError if bad."""
    if not isinstance(obj, dict):
        raise ValueError("envelope must be a dict")
    missing = {'status', 'tool', 'data', 'error', 'freshness', 'read_only', 'envelope'} - set(obj)
    if missing:
        raise ValueError(f"envelope missing keys: {sorted(missing)}")
    if obj['status'] not in (_OK, _ERROR):
        raise ValueError(f"bad status: {obj['status']!r}")
    if obj['read_only'] is not True:
        raise ValueError("read_only must be true")
    if obj['envelope'] != ENVELOPE_VERSION:
        raise ValueError(f"bad envelope version: {obj['envelope']!r}")
    if obj['status'] == _OK and not isinstance(obj['data'], str):
        raise ValueError("ok envelope must carry string data")
    if obj['status'] == _ERROR and not isinstance(obj['error'], str):
        raise ValueError("error envelope must carry a string error")
    fresh = obj['freshness']
    if not isinstance(fresh, dict):
        raise ValueError("freshness must be a dict")
    for kind in ('universe', 'daily', 'intraday'):
        section = fresh.get(kind)
        if not isinstance(section, dict):
            raise ValueError(f"freshness.{kind} must be a dict")
        if 'as_of' not in section or 'stale' not in section:
            raise ValueError(f"freshness.{kind} needs as_of + stale markers")
    json.dumps(obj)  # must be JSON-serializable
    return True


def envelope_freshness(ticker_option: int, cache=None) -> dict:
    """Freshness markers sourced from the data-floor cache state."""
    from classes.DataFloor import get_shared_cache, is_fresh
    cache = cache or get_shared_cache()
    entry = cache.lookup('universe', str(ticker_option))
    if entry is None:
        universe = {'source': None, 'as_of': None, 'stale': True, 'cached': False}
    else:
        (_symbols, source), fetched_at = entry
        universe = {
            'source': source,
            'as_of': fetched_at.date().isoformat(),
            'stale': not is_fresh('universe', fetched_at),
            'cached': True,
        }
    daily = cache.summarize('daily')
    if daily['count'] == 0:
        daily['stale'] = True
    intraday = cache.summarize('intraday')
    if intraday['count'] == 0:
        intraday['stale'] = True
    return {'universe': universe, 'daily': daily, 'intraday': intraday}


def build_envelope(tool_name: str, index: str, result=None, error=None) -> dict:
    """Build a validated response envelope for one tool call."""
    from agents.screener_tools import _resolve_index
    ticker_option = _resolve_index(index)
    if error is None:
        return {
            'status': _OK,
            'tool': tool_name,
            'data': result if isinstance(result, str) else str(result),
            'error': None,
            'freshness': envelope_freshness(ticker_option),
            'read_only': True,
            'envelope': ENVELOPE_VERSION,
        }
    return {
        'status': _ERROR,
        'tool': tool_name,
        'data': '',
        'error': str(error),
        'freshness': envelope_freshness(ticker_option),
        'read_only': True,
        'envelope': ENVELOPE_VERSION,
    }


def make_wrapper(name: str, fn):
    """Wrap one screen fn so it returns a JSON envelope (schema preserved).

    The wrapper keeps the original signature via functools.wraps so FastMCP
    derives the correct inputSchema 1:1. Freshness is sourced from the data
    floor; errors never leak tracebacks, only 'Type: message'.
    """
    sig = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            index = bound.arguments.get('index', 'Nifty 500')
        except TypeError:
            index = 'Nifty 500'
        try:
            result = fn(*args, **kwargs)
            return json.dumps(build_envelope(name, index, result=result))
        except Exception as e:
            msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            return json.dumps(build_envelope(name, index, error=msg))

    return wrapper


def build_wrappers(tool_map=None) -> dict:
    """One envelope wrapper per screen tool. No other callables registered."""
    if tool_map is None:
        from agents.screener_tools import TOOL_MAP
        tool_map = TOOL_MAP
    for name in tool_map:
        if name not in ALLOWED_ROSTER:
            raise ValueError(f"Refusing to register non-roster tool: {name!r}")
        if _WRITE_PAT.search(name):
            raise ValueError(f"Refusing write-capable tool name: {name!r}")
    return {name: make_wrapper(name, fn) for name, fn in tool_map.items()}


def create_server(tool_map=None, host: str = '127.0.0.1', port: int = 8765):
    """Build the FastMCP server (mcp SDK import is lazy)."""
    from mcp.server.fastmcp import FastMCP
    server = FastMCP('screenipy', host=host, port=port)
    for name, wrapper in build_wrappers(tool_map).items():
        server.add_tool(wrapper, name=name)
    return server


def run_server(host: str = '127.0.0.1', port: int = 8765, tool_map=None):
    """Serve the tools over Streamable HTTP."""
    create_server(tool_map, host=host, port=port).run(transport='streamable-http')


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description='Screeni-py read-only MCP server')
    _parser.add_argument('--host', default='127.0.0.1')
    _parser.add_argument('--port', type=int, default=8765)
    _args = _parser.parse_args()
    run_server(host=_args.host, port=_args.port)
