"""
HTTP contract tests for the read-only MCP tool surface (issue #300).

Seam: MCP HTTP. Tool fns are stubbed — no screening, no network —
except the transport roundtrip, which runs a real Streamable HTTP
server + client against stub tools.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

EXPECTED_ROSTER = [
    'screen_breakout',
    'screen_volume_breakout',
    'screen_consolidation',
    'screen_rsi',
    'screen_reversal',
    'screen_chart_patterns',
    'screen_vcp',
    'screen_momentum',
    'screen_narrow_range',
    'screen_ipo_base',
    'screen_confluence',
    'screen_ma_reversal',
    'screen_rsi_ma_cross',
    'screen_lorentzian',
]


def _stub_tools():
    import inspect
    from agents.screener_tools import TOOL_MAP
    out = {}
    for name, real_fn in TOOL_MAP.items():
        sig = inspect.signature(real_fn)

        def _mk(text, _sig=sig):
            def _stub(*args, **kwargs):
                """Stub screen."""
                return text
            # Mirror the real tool's signature so FastMCP exposes 1:1 inputSchema
            _stub.__signature__ = _sig
            _stub.__annotations__ = getattr(real_fn, '__annotations__', {})
            return _stub

        out[name] = _mk(f"{name} ok")
    return out


def _frame():
    import pandas as pd
    return pd.DataFrame(
        {'Open': [100.0], 'High': [101.0], 'Low': [99.0],
         'Close': [100.5], 'Adj Close': [100.5], 'Volume': [1000]},
        index=pd.to_datetime(['2026-09-04']),
    )


class TestRoster:
    def test_tool_map_has_agreed_roster(self):
        """TOOL_MAP must expose exactly the 14 agreed screen tools."""
        from agents.screener_tools import TOOL_MAP
        assert sorted(TOOL_MAP) == sorted(EXPECTED_ROSTER)

    def test_wrappers_cover_roster_1_to_1(self):
        """One wrapper per tool, no more, no less."""
        from agents.mcp_server import build_wrappers
        wrappers = build_wrappers(_stub_tools())
        assert sorted(wrappers) == sorted(EXPECTED_ROSTER)


class TestEnvelope:
    def test_ok_envelope_validates(self):
        """A successful call returns a valid ok envelope."""
        from agents.mcp_server import build_wrappers, validate_envelope
        wrappers = build_wrappers(_stub_tools())
        payload = json.loads(wrappers['screen_breakout'](index='Nifty 50'))
        assert validate_envelope(payload) is True
        assert payload['status'] == 'ok'
        assert payload['tool'] == 'screen_breakout'
        assert payload['data'] == 'screen_breakout ok'
        assert payload['error'] is None
        assert payload['read_only'] is True

    def test_error_envelope_validates(self):
        """A failing tool returns a valid error envelope, never raises."""
        from agents.mcp_server import build_wrappers, validate_envelope

        def boom(index: str = "Nifty 500") -> str:
            """Boom."""
            raise RuntimeError("kaput")

        wrappers = build_wrappers({'screen_breakout': boom})
        payload = json.loads(wrappers['screen_breakout']())
        assert validate_envelope(payload) is True
        assert payload['status'] == 'error'
        assert 'kaput' in payload['error']
        assert 'RuntimeError' in payload['error']

    def test_wrapper_preserves_input_schema(self):
        """Wrapper must expose the original tool's input schema 1:1."""
        import inspect
        from agents.screener_tools import TOOL_MAP
        from agents.mcp_server import build_wrappers
        wrappers = build_wrappers()
        for name, fn in TOOL_MAP.items():
            assert inspect.signature(wrappers[name]) == inspect.signature(fn), name

    def test_freshness_fields_present(self):
        """Every envelope carries data-as-of and staleness markers."""
        from agents.mcp_server import build_wrappers
        wrappers = build_wrappers(_stub_tools())
        payload = json.loads(wrappers['screen_rsi'](index='Nifty 50'))
        fresh = payload['freshness']
        assert set(fresh) == {'universe', 'daily', 'intraday'}
        assert {'as_of', 'stale'} <= set(fresh['universe'])
        assert {'as_of', 'stale', 'sources'} <= set(fresh['daily'])

    def test_freshness_reflects_cache(self):
        """Envelope staleness must track the data-floor cache state."""
        from classes.DataFloor import RawCache
        from agents import mcp_server
        from datetime import datetime, timezone, timedelta
        cache = RawCache()
        now = datetime.now(timezone.utc)
        cache.set('universe', '1', (['A'], 'nse'), fetched_at=now)
        cache.set('daily', 'A', (_frame(), 'stooq'), fetched_at=now)
        fresh = mcp_server.envelope_freshness(1, cache=cache)
        assert fresh['universe']['stale'] is False
        assert fresh['daily']['sources'] == ['stooq']
        assert fresh['daily']['stale'] is False
        old = mcp_server.envelope_freshness(1, cache=RawCache())
        assert old['universe']['stale'] is True


class TestReadOnly:
    def test_no_write_capability_in_roster(self):
        """Roster must contain no order/write capability by name."""
        import re
        from agents.mcp_server import build_wrappers
        banned = re.compile(r'place_order|cancel_order|\bbuy\b|\bsell\b|KiteConnect|kiteconnect|request_token')
        for name in build_wrappers(_stub_tools()):
            assert not banned.search(name), name

    def test_no_write_symbols_in_server_source(self):
        """Capability search over the server module, not just convention."""
        import re
        path = os.path.join(os.path.dirname(__file__), '..', 'src', 'agents', 'mcp_server.py')
        with open(os.path.abspath(path)) as f:
            src = f.read()
        banned = re.compile(r'place_order|cancel_order|KiteConnect|kiteconnect|request_token')
        assert not banned.search(src)

    def test_allowlist_rejects_unknown_tool(self):
        """Non-roster tools are rejected by construction."""
        import pytest as _pytest
        from agents.mcp_server import build_wrappers

        def evil(index: str = "Nifty 500") -> str:
            """Evil."""
            return "evil"

        with _pytest.raises(ValueError, match="non-roster"):
            build_wrappers({'place_order': evil})
        with _pytest.raises(ValueError, match="non-roster"):
            build_wrappers({'screen_breakout': evil, 'extra_tool': evil})

    def test_allowlist_rejects_write_names(self):
        """Write-like names are rejected even if allowlisted."""
        from agents.mcp_server import ALLOWED_ROSTER, _WRITE_PAT
        assert 'screen_breakout' in ALLOWED_ROSTER
        for bad in ('place_order', 'cancel_order', 'modify_order', 'order', 'KiteConnect', 'kiteconnect', 'request_token'):
            assert _WRITE_PAT.search(bad), bad
        assert not _WRITE_PAT.search('screen_breakout')
        assert not _WRITE_PAT.search('screen_rsi')


class TestTransport:
    def test_streamable_http_roundtrip(self):
        """Real server + client over Streamable HTTP: roster + envelope."""
        pytest.importorskip('mcp.server.fastmcp', reason='mcp SDK required')
        import socket
        import threading
        import time
        import inspect
        from agents.mcp_server import create_server, validate_envelope
        from agents.screener_tools import TOOL_MAP

        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        server = create_server(_stub_tools(), host='127.0.0.1', port=port)
        thread = threading.Thread(
            target=server.run,
            kwargs={'transport': 'streamable-http'},
            daemon=True,
        )
        thread.start()

        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.session import ClientSession
        import asyncio

        async def _go():
            async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp") as (rs, ws, _):
                async with ClientSession(rs, ws) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = sorted(t.name for t in tools.tools)
                    by_name = {t.name: t for t in tools.tools}
                    # Verify per-tool input schemas preserved 1:1 over the wire (all 14)
                    for tool_name, real_fn in TOOL_MAP.items():
                        schema_props = set(by_name[tool_name].inputSchema.get('properties', {}))
                        expected = set(inspect.signature(real_fn).parameters)
                        assert expected <= schema_props, f"{tool_name}: missing {expected - schema_props}"
                    # Call every tool once; each must return a valid envelope
                    texts = {}
                    for tool_name in EXPECTED_ROSTER:
                        sig = inspect.signature(TOOL_MAP[tool_name])
                        kwargs = {}
                        if 'index' in sig.parameters:
                            kwargs['index'] = 'Nifty 50'
                        # supply one required-ish kwarg per tool to exercise per-tool params
                        if 'days_lookback' in sig.parameters:
                            kwargs['days_lookback'] = 20
                        if 'volume_ratio' in sig.parameters:
                            kwargs['volume_ratio'] = 1.5
                        if 'min_rsi' in sig.parameters:
                            kwargs['min_rsi'] = 30
                        if 'max_rsi' in sig.parameters:
                            kwargs['max_rsi'] = 70
                        res = await session.call_tool(tool_name, kwargs)
                        texts[tool_name] = res.content[0].text
                    # Read-only posture over HTTP: no write-named tool leaked
                    assert not any('place_order' in n or 'KiteConnect' in n for n in names)
                    return names, texts

        deadline = time.time() + 30
        while True:
            try:
                names, texts = asyncio.run(_go())
                break
            except Exception:
                if time.time() > deadline:
                    raise
                time.sleep(0.5)

        assert names == sorted(EXPECTED_ROSTER)
        for tool_name, text in texts.items():
            assert validate_envelope(json.loads(text)) is True, tool_name
