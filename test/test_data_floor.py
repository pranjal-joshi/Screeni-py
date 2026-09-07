"""
Tests for the keyless-first data floor (DataFloor module, issue #299).

Seam: Fetcher/data. No network access — all sources are mocked.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

IST = timezone(timedelta(hours=5, minutes=30))

STOOQ_CSV = """Date,Open,High,Low,Close,Volume
2026-09-04,100.0,101.0,99.0,100.5,1000
2026-09-03,99.0,100.0,98.0,99.5,900
"""


class FakeResponse:
    def __init__(self, text='', json_data=None, status_code=200, content=None):
        self.text = text
        self._json = json_data
        self.status_code = status_code
        self.content = content if content is not None else text.encode('utf-8')

    def raise_for_status(self):
        if self.status_code >= 400:
            raise IOError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def _yf_frame(days: int = 2):
    import pandas as pd
    idx = pd.date_range(end='2026-09-04', periods=days, freq='B')
    n = len(idx)
    base = [100.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            'Open': base,
            'High': [b + 1.0 for b in base],
            'Low': [b - 1.0 for b in base],
            'Close': [b + 0.5 for b in base],
            'Adj Close': [b + 0.5 for b in base],
            'Volume': [1000 + i for i in range(n)],
        },
        index=idx,
    )


def _yfinance_stub():
    import types
    stub = types.ModuleType('yfinance')
    stub.download = lambda **kwargs: _yf_frame()
    return stub


class TestStooqPrimary:
    def test_stooq_success_returns_df_and_freshness(self, monkeypatch):
        """Stooq daily CSV maps to the OHLCV shape with stooq freshness."""
        import requests
        from classes import DataFloor
        monkeypatch.setattr(requests, 'get', lambda url, **kw: FakeResponse(text=STOOQ_CSV))
        df, fresh = DataFloor.fetch_daily('RELIANCE')
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        assert len(df) == 2
        assert fresh['source'] == 'stooq'
        assert fresh['kind'] == 'daily'
        assert fresh['symbol'] == 'RELIANCE'
        assert fresh['stale'] is False
        assert set(fresh) == {'source', 'kind', 'symbol', 'as_of', 'fetched_at', 'stale'}

    def test_stooq_failure_falls_back_to_yfinance(self, monkeypatch):
        """Stooq outage must fall back to yfinance with no user action."""
        import requests
        from classes import DataFloor

        def boom(url, **kw):
            raise IOError("stooq down")

        monkeypatch.setattr(requests, 'get', boom)
        monkeypatch.setitem(sys.modules, 'yfinance', _yfinance_stub())
        df, fresh = DataFloor.fetch_daily('RELIANCE')
        assert len(df) == 2
        assert fresh['source'] == 'yfinance'

    def test_all_sources_fail_raises_without_token(self, monkeypatch):
        """No sources and no Upstox key must raise, never silently empty."""
        import requests
        from classes import DataFloor
        monkeypatch.setattr(requests, 'get', lambda url, **kw: (_ for _ in ()).throw(IOError("down")))
        monkeypatch.delenv('UPSTOX_ACCESS_TOKEN', raising=False)
        try:
            DataFloor.fetch_daily('RELIANCE')
            raise AssertionError("should have raised")
        except DataFloor.DataUnavailable:
            pass


class TestRawCache:
    def test_cache_hit_serves_without_network(self, monkeypatch):
        """Fresh cache must short-circuit all network sources."""
        import requests
        from classes import DataFloor
        from datetime import timezone as _tz
        cache = DataFloor.RawCache()
        cache.set('daily', 'RELIANCE', (_yf_frame(), 'stooq'),
                  fetched_at=datetime.now(_tz.utc))
        calls = []
        monkeypatch.setattr(requests, 'get', lambda url, **kw: calls.append(url) or FakeResponse(text=STOOQ_CSV))
        df2, fresh2 = DataFloor.fetch_daily('RELIANCE', cache=cache)
        assert calls == []
        assert fresh2['source'] == 'stooq'
        assert len(df2) == 2

    def test_stale_daily_refetches(self, monkeypatch):
        """A daily entry from before the last close must refetch."""
        import requests
        from classes import DataFloor
        cache = DataFloor.RawCache()
        old = DataFloor.last_nse_close() - timedelta(days=2)
        cache.set('daily', 'RELIANCE', (_yf_frame(), 'stooq'), fetched_at=old)
        calls = []
        monkeypatch.setattr(requests, 'get', lambda url, **kw: calls.append(url) or FakeResponse(text=STOOQ_CSV))
        df, fresh = DataFloor.fetch_daily('RELIANCE', cache=cache)
        assert calls != []
        assert fresh['source'] == 'stooq'

    def test_intraday_ttl(self):
        """Intraday entries live 15 minutes."""
        from classes import DataFloor
        cache = DataFloor.RawCache()
        now = datetime.now(timezone.utc)
        assert DataFloor.is_fresh('intraday', now - timedelta(minutes=5), now=now) is True
        assert DataFloor.is_fresh('intraday', now - timedelta(minutes=30), now=now) is False

    def test_universe_ttl(self):
        """Universe lists live 7 days."""
        from classes import DataFloor
        now = datetime.now(timezone.utc)
        assert DataFloor.is_fresh('universe', now - timedelta(days=3), now=now) is True
        assert DataFloor.is_fresh('universe', now - timedelta(days=8), now=now) is False

    def test_daily_fresh_after_close(self):
        """A daily fetch after today's close is fresh until the next close."""
        from classes import DataFloor
        now = datetime.now(timezone.utc)
        close = DataFloor.last_nse_close(now=now)
        assert DataFloor.is_fresh('daily', close + timedelta(minutes=5), now=now) is True
        assert DataFloor.is_fresh('daily', close - timedelta(minutes=5), now=now) is False


class TestWarmer:
    def test_warmer_biggest_first_order(self):
        """Warmer covers Nifty 50 before wider universes."""
        from classes import DataFloor
        seen = []
        loader = lambda opt: seen.append(('load', opt)) or [f"S{opt}"]
        fetcher = lambda sym: seen.append(('fetch', sym)) or (_yf_frame(), {'source': 'stooq'})
        cache = DataFloor.RawCache()
        warmer = DataFloor.Warmer(loader, fetcher, cache=cache, universe_order=[1, 5])
        stats = warmer.warm_now()
        assert seen.index(('load', 1)) < seen.index(('load', 5))
        assert stats['symbols'] == 2

    def test_warmer_skips_fresh(self):
        """Warmer must not refetch symbols already fresh in cache."""
        from classes import DataFloor
        cache = DataFloor.RawCache()
        now = datetime.now(timezone.utc)
        cache.set('daily', 'A', (_yf_frame(), 'stooq'), fetched_at=now)
        calls = []
        fetcher = lambda sym: calls.append(sym) or (_yf_frame(), {'source': 'stooq'})
        warmer = DataFloor.Warmer(lambda opt: ['A', 'B'], fetcher, cache=cache, universe_order=[1])
        warmer.warm_now()
        assert calls == ['B']


class TestUniverseCache:
    def test_universe_loader_called_once_within_ttl(self):
        """Universe lists serve from cache for 7 days."""
        from classes import DataFloor
        cache = DataFloor.RawCache()
        calls = []
        loader = lambda opt: calls.append(opt) or ['A', 'B']
        syms1, fresh1 = DataFloor.get_universe(1, loader=loader, cache=cache)
        syms2, fresh2 = DataFloor.get_universe(1, loader=loader, cache=cache)
        assert calls == [1]
        assert syms1 == syms2 == ['A', 'B']
        assert fresh1['kind'] == fresh2['kind'] == 'universe'
        assert fresh2['stale'] is False


class TestUpstoxFallback:
    def test_upstox_skipped_without_token(self, monkeypatch):
        """Without a token the keyed fallback must not be attempted."""
        import requests
        from classes import DataFloor
        monkeypatch.delenv('UPSTOX_ACCESS_TOKEN', raising=False)
        monkeypatch.setattr(requests, 'get', lambda url, **kw: (_ for _ in ()).throw(IOError("down")))
        try:
            DataFloor.fetch_daily('RELIANCE')
            raise AssertionError("should have raised")
        except DataFloor.DataUnavailable:
            pass

    def test_upstox_uses_bearer_header_with_token(self, monkeypatch):
        """With a token, Upstox is called with a Bearer header after keyless fails."""
        import gzip
        import json
        import requests
        from classes import DataFloor
        monkeypatch.setenv('UPSTOX_ACCESS_TOKEN', 'tok123')
        seen = {}

        master = [{'segment': 'NSE_EQ', 'trading_symbol': 'RELIANCE', 'instrument_key': 'NSE_EQ|INE002A01018'}]
        candles = {'status': 'success', 'data': {'candles': [
            ['2026-09-04T00:00:00+05:30', 100.0, 101.0, 99.0, 100.5, 1000, 0],
            ['2026-09-03T00:00:00+05:30', 99.0, 100.0, 98.0, 99.5, 900, 0],
        ]}}

        def fake_get(url, **kw):
            seen.setdefault('calls', []).append((url, kw.get('headers', {})))
            if 'assets.upstox.com' in url:
                return FakeResponse(content=gzip.compress(json.dumps(master).encode()))
            if 'api.upstox.com' in url:
                return FakeResponse(json_data=candles)
            raise IOError("keyless down")

        monkeypatch.setattr(requests, 'get', fake_get)
        df, fresh = DataFloor.fetch_daily('RELIANCE')
        assert fresh['source'] == 'upstox'
        assert len(df) == 2
        api_calls = [c for c in seen['calls'] if 'api.upstox.com' in c[0]]
        assert api_calls and api_calls[0][1].get('Authorization') == 'Bearer tok123'


def _stub_heavy(monkeypatch):
    """Stub third-party modules missing from this env (prod has them all)."""
    import types
    from unittest.mock import MagicMock
    for mod in ('yfinance', 'nsetools', 'pytz', 'joblib', 'alive_progress'):
        if mod not in sys.modules:
            stub = types.ModuleType(mod)
            stub.__version__ = '0.0.0'
            monkeypatch.setitem(sys.modules, mod, stub)
    sys.modules['alive_progress'].alive_bar = MagicMock()
    sys.modules['nsetools'].Nse = MagicMock()
    return sys.modules['yfinance']


def _multi_frame():
    """yfinance-style frame with MultiIndex columns."""
    import pandas as pd
    cols = pd.MultiIndex.from_product(
        [['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'], ['RELIANCE.NS']])
    return pd.DataFrame(
        [[100.0, 101.0, 99.0, 100.5, 100.5, 1000],
         [101.0, 102.0, 100.0, 101.5, 101.5, 1100]],
        index=pd.to_datetime(['2026-09-03', '2026-09-04']),
        columns=cols,
    )


def _fetcher():
    from types import SimpleNamespace
    from classes.Fetcher import tools as FetcherTools
    fetcher = FetcherTools.__new__(FetcherTools)
    fetcher.configManager = SimpleNamespace(cacheEnabled=True, shuffleEnabled=False, stageTwo=False)
    return fetcher


class TestFetcherWiring:
    """The screening path must go through the floor, not raw yfinance."""

    def test_daily_routes_through_floor(self, monkeypatch):
        """Live daily screening uses the floor and skips yfinance."""
        import datetime as _dt
        yf = _stub_heavy(monkeypatch)
        import classes.Fetcher as FetcherMod
        from classes import DataFloor
        yf_calls = []
        monkeypatch.setattr(FetcherMod.yf, 'download',
                            lambda **kw: yf_calls.append(kw) or _multi_frame(),
                            raising=False)
        floor_calls = []
        monkeypatch.setattr(
            FetcherMod, 'floor_daily',
            lambda sym, **kw: floor_calls.append((sym, kw)) or (_yf_frame(days=300), {'source': 'stooq'}))
        fetcher = _fetcher()
        data, date_dict = fetcher.fetchStockData(
            'RELIANCE', '300d', '1d', None, None, None, 1, backtestDate=_dt.date.today())
        assert floor_calls and floor_calls[0][0] == 'RELIANCE'
        assert yf_calls == []
        assert len(data) == len(_yf_frame(days=300))
        assert date_dict is None
        assert data.attrs['freshness']['source'] == 'stooq'

    def test_floor_failure_falls_back_to_legacy(self, monkeypatch):
        """Floor outage must degrade to the legacy yfinance path."""
        import datetime as _dt
        yf = _stub_heavy(monkeypatch)
        import classes.Fetcher as FetcherMod
        from classes import DataFloor
        yf_calls = []
        monkeypatch.setattr(FetcherMod.yf, 'download',
                            lambda **kw: yf_calls.append(kw) or _multi_frame(),
                            raising=False)
        monkeypatch.setattr(
            FetcherMod, 'floor_daily',
            lambda sym, **kw: (_ for _ in ()).throw(DataFloor.DataUnavailable("down")))
        fetcher = _fetcher()
        data, _ = fetcher.fetchStockData(
            'RELIANCE', '300d', '1d', None, None, None, 1, backtestDate=_dt.date.today())
        assert yf_calls != []
        assert list(data.columns) == ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']

    def test_backtest_window_bypasses_floor(self, monkeypatch):
        """Backtest windows keep the legacy path (custom ranges, no cache)."""
        import datetime as _dt
        yf = _stub_heavy(monkeypatch)
        import classes.Fetcher as FetcherMod
        monkeypatch.setattr(FetcherMod.yf, 'download', lambda **kw: _multi_frame(),
                            raising=False)
        floor_calls = []
        monkeypatch.setattr(
            FetcherMod, 'floor_daily',
            lambda sym, **kw: floor_calls.append(sym) or (_yf_frame(days=300), {'source': 'stooq'}))
        fetcher = _fetcher()
        fetcher.fetchStockData(
            'RELIANCE', '300d', '1d', None, None, None, 1,
            backtestDate=_dt.date.today() - _dt.timedelta(days=30))
        assert floor_calls == []

    def test_codes_serve_from_universe_cache(self, monkeypatch):
        """fetchStockCodes resolves through the cached universe layer."""
        _stub_heavy(monkeypatch)
        import classes.Fetcher as FetcherMod
        calls = []
        monkeypatch.setattr(
            FetcherMod, 'get_universe',
            lambda opt, **kw: calls.append(opt) or ([f"S{i}" for i in range(11)], {'source': 'nse'}))
        fetcher = _fetcher()
        codes = fetcher.fetchStockCodes(1)
        assert calls == [1]
        assert len(codes) == 11

    def test_shared_cache_singleton(self):
        """Warmer and Fetchers share one process-wide cache."""
        from classes import DataFloor
        assert DataFloor.get_shared_cache() is DataFloor.get_shared_cache()

    def test_long_period_keeps_legacy(self, monkeypatch):
        """A period beyond floor coverage must keep the legacy path."""
        import datetime as _dt
        yf = _stub_heavy(monkeypatch)
        import classes.Fetcher as FetcherMod
        yf_calls = []
        monkeypatch.setattr(FetcherMod.yf, 'download',
                            lambda **kw: yf_calls.append(kw) or _multi_frame(),
                            raising=False)
        floor_calls = []
        monkeypatch.setattr(
            FetcherMod, 'floor_daily',
            lambda sym, **kw: floor_calls.append(sym) or (_yf_frame(days=300), {'source': 'stooq'}))
        fetcher = _fetcher()
        fetcher.fetchStockData(
            'RELIANCE', '5y', '1d', None, None, None, 1, backtestDate=_dt.date.today())
        assert floor_calls != []
        assert yf_calls != []

    def test_compat_guard_passes_flat_frames(self, monkeypatch):
        """makeDataBackwardCompatible must not crash on floor (flat) frames."""
        _stub_heavy(monkeypatch)
        from classes.Fetcher import tools as FetcherTools
        fetcher = FetcherTools.__new__(FetcherTools)
        flat = _yf_frame()
        out = fetcher.makeDataBackwardCompatible(flat)
        assert list(out.columns) == ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']

    def test_intraday_stale_fallback(self, monkeypatch):
        """Intraday outage with a stale cache serves stale, never raises."""
        import requests
        from classes import DataFloor
        from datetime import timezone as _tz
        cache = DataFloor.RawCache()
        old = datetime.now(_tz.utc) - timedelta(minutes=60)
        cache.set('intraday', 'RELIANCE@15m', (_yf_frame(), 'yfinance'), fetched_at=old)
        monkeypatch.setattr(requests, 'get', lambda url, **kw: (_ for _ in ()).throw(IOError("down")))
        monkeypatch.delenv('UPSTOX_ACCESS_TOKEN', raising=False)
        df, fresh = DataFloor.fetch_intraday('RELIANCE', '15m', cache=cache)
        assert fresh['stale'] is True
        assert len(df) == 2

    def test_startup_prefills_universe_cache(self, monkeypatch):
        """warm_on_startup fills universe entries as well as daily frames."""
        from classes import DataFloor
        cache = DataFloor.RawCache()
        monkeypatch.setattr(DataFloor, 'WARM_UNIVERSE_ORDER', [1])
        monkeypatch.setattr(DataFloor, '_default_universe_loader', lambda opt: ['A'])
        warmer = DataFloor.warm_on_startup(
            daily_fetch=lambda s: (_yf_frame(), {}), cache=cache)
        warmer.join(timeout=10)
        assert cache.fresh('universe', '1') is not None
