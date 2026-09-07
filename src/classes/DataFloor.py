"""
Keyless-first market-data floor (issue #299).

Sits behind the Fetcher seam and owns all network access for market data:

- Stooq (keyless) is primary for daily OHLCV.
- yfinance fills gaps plus intraday plus indices.
- Upstox v3 is a keyed-only fallback, attempted solely when
  UPSTOX_ACCESS_TOKEN is present.

Only raw market data is cached — never computed results. Every fetch
returns ``(dataframe, freshness)`` where freshness carries source, kind,
symbol, as-of, fetched-at and staleness for the downstream envelope layer.

Per-kind staleness contract:
- daily: fresh once fetched at/after the last NSE close (15:30 IST, weekdays)
- intraday: 15-minute TTL
- universe: 7-day TTL
"""
import csv
import gzip
import io
import json
import os
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

IST = timezone(timedelta(hours=5, minutes=30))
NSE_CLOSE = (15, 30)  # 15:30 IST

UPSTOX_TOKEN_ENV = 'UPSTOX_ACCESS_TOKEN'
UPSTOX_BASE = 'https://api.upstox.com/v3'
UPSTOX_MASTER_URL = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'

STOOQ_DAILY_URL = 'https://stooq.com/q/d/l/?s={symbol}{suffix}&i=d'

INTRADAY_TTL = timedelta(minutes=15)
UNIVERSE_TTL = timedelta(days=7)

OHLCV_COLUMNS = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']

#: Warmer order: flagship first, down to the tail.
WARM_UNIVERSE_ORDER = [1, 2, 3, 4, 5, 9, 10, 11, 6, 7, 8]


class DataUnavailable(Exception):
    """Raised when no source can serve a request and no stale cache exists."""
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def last_nse_close(now: datetime = None) -> datetime:
    """Most recent NSE 15:30 IST close at or before ``now``."""
    now = now or utcnow()
    ist = now.astimezone(IST)
    close = ist.replace(hour=NSE_CLOSE[0], minute=NSE_CLOSE[1], second=0, microsecond=0)
    if ist < close:
        close -= timedelta(days=1)
    while close.weekday() >= 5:  # Sat/Sun -> roll back to Friday
        close -= timedelta(days=1)
    return close


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def is_fresh(kind: str, fetched_at: datetime, now: datetime = None) -> bool:
    """Per-kind staleness check for a cache entry fetched at ``fetched_at``."""
    now = now or utcnow()
    fetched_at = _aware(fetched_at)
    if kind == 'daily':
        return fetched_at >= last_nse_close(now=now)
    if kind == 'intraday':
        return (now - fetched_at) <= INTRADAY_TTL
    if kind == 'universe':
        return (now - fetched_at) <= UNIVERSE_TTL
    raise ValueError(f"Unknown cache kind: {kind}")


def _freshness(source: str, kind: str, symbol: str, as_of: str,
               fetched_at: datetime, stale: bool = False) -> dict:
    return {
        'source': source,
        'kind': kind,
        'symbol': symbol,
        'as_of': as_of,
        'fetched_at': fetched_at.isoformat(),
        'stale': stale,
    }


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Map any source frame onto [Open, High, Low, Close, Adj Close, Volume]."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(level=1, axis=1)
    df = df.rename_axis(None, axis=1)
    if 'Adj Close' not in df.columns and 'Close' in df.columns:
        df = df.copy()
        df['Adj Close'] = df['Close']
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise DataUnavailable(f"OHLCV frame missing columns: {missing}")
    out = df[OHLCV_COLUMNS].copy()
    out.index = pd.to_datetime(out.index)
    return out


class RawCache:
    """In-process raw-market-data cache. Thread-safe. No computed results."""
    def __init__(self):
        self._lock = threading.Lock()
        self._entries = {}  # (kind, key) -> (payload, fetched_at)

    def set(self, kind: str, key: str, payload, fetched_at: datetime = None):
        with self._lock:
            self._entries[(kind, key)] = (payload, fetched_at or utcnow())

    def lookup(self, kind: str, key: str):
        """Return (payload, fetched_at) or None."""
        with self._lock:
            return self._entries.get((kind, key))

    def fresh(self, kind: str, key: str, now: datetime = None):
        """Return payload if the entry is fresh, else None."""
        entry = self.lookup(kind, key)
        if entry is None:
            return None
        payload, fetched_at = entry
        if is_fresh(kind, fetched_at, now=now):
            return payload
        return None


_shared_cache = None
_shared_lock = threading.Lock()


def get_shared_cache() -> RawCache:
    """Process-wide cache shared by the Warmer and every Fetcher.

    The Warmer pre-fills it on app open; screening reads from it.
    """
    global _shared_cache
    with _shared_lock:
        if _shared_cache is None:
            _shared_cache = RawCache()
        return _shared_cache


def _fetch_stooq_daily(symbol: str, suffix: str = '.ns') -> pd.DataFrame:
    url = STOOQ_DAILY_URL.format(symbol=symbol.lower(), suffix=suffix.lower())
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(resp.text.strip())))
    rows = [r for r in rows if r.get('Close') not in (None, '', 'N/D')]
    if not rows:
        raise DataUnavailable(f"Stooq returned no daily rows for {symbol}")
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date').sort_index()
    for col in ('Open', 'High', 'Low', 'Close', 'Volume'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return _normalize_ohlcv(df)


def _fetch_yfinance_daily(symbol: str, suffix: str = '.NS') -> pd.DataFrame:
    import yfinance as yf  # lazy: keeps this module importable without yfinance
    df = yf.download(
        tickers=symbol.upper() + suffix.upper(),
        period='300d',
        interval='1d',
        progress=False,
        timeout=10,
        auto_adjust=False,
    )
    if df is None or len(df) == 0:
        raise DataUnavailable(f"yfinance returned no daily rows for {symbol}")
    return _normalize_ohlcv(df)


def _upstox_token() -> str:
    token = os.environ.get(UPSTOX_TOKEN_ENV, '')
    if not token:
        raise DataUnavailable("Upstox fallback skipped: no access token configured")
    return token


def _upstox_instrument_key(symbol: str, token: str) -> str:
    """Resolve an NSE equity symbol via the cached instrument master file."""
    resp = requests.get(UPSTOX_MASTER_URL, timeout=30)
    resp.raise_for_status()
    master = json.loads(gzip.decompress(resp.content).decode('utf-8'))
    want = symbol.upper()
    for entry in master:
        if entry.get('segment') == 'NSE_EQ' and (entry.get('trading_symbol') or '').upper() == want:
            return entry['instrument_key']
    raise DataUnavailable(f"Upstox instrument key not found for {symbol}")


def _upstox_candles(instrument_key: str, unit: str, interval: str,
                    to_date: str, from_date: str = None, intraday: bool = False) -> pd.DataFrame:
    token = _upstox_token()
    path = f"{UPSTOX_BASE}/historical-candle/intraday/{instrument_key}/{unit}/{interval}" if intraday else \
        f"{UPSTOX_BASE}/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
    resp = requests.get(
        path,
        headers={'Accept': 'application/json', 'Authorization': f'Bearer {token}'},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    candles = (body.get('data') or {}).get('candles') or []
    if body.get('status') != 'success' or not candles:
        raise DataUnavailable(f"Upstox returned no candles for {instrument_key}")
    df = pd.DataFrame(candles, columns=['ts', 'Open', 'High', 'Low', 'Close', 'Volume', 'OI'])
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.set_index('ts').sort_index()
    return _normalize_ohlcv(df[['Open', 'High', 'Low', 'Close', 'Volume']])


def _fetch_upstox_daily(symbol: str) -> pd.DataFrame:
    token = _upstox_token()
    key = _upstox_instrument_key(symbol, token)
    today = datetime.now(IST).date()
    frm = today - timedelta(days=370)
    return _upstox_candles(key, 'days', '1', today.isoformat(), frm.isoformat())


def fetch_daily(symbol: str, cache: RawCache = None, suffix: str = '.ns'):
    """Daily OHLCV for ``symbol``: Stooq -> yfinance -> Upstox (keyed).

    ``suffix`` is the Stooq market suffix ('.ns' for NSE, '' for US/indices).
    Returns (dataframe, freshness). Falls back to stale cache before raising.
    """
    symbol = symbol.upper()
    suffix = (suffix or '').lower()
    key = symbol if suffix == '.ns' else f"{symbol}|{suffix}"
    now = utcnow()
    # Cache payload shape is (dataframe, source); fetched_at rides alongside.
    cached = cache.lookup('daily', key) if cache is not None else None
    if cached is not None:
        (df, source), fetched_at = cached
        as_of = df.index[-1].date().isoformat()
        if is_fresh('daily', fetched_at, now=now):
            return df, _freshness(source, 'daily', symbol, as_of, now)
    last_error = None
    for source, fn in (('stooq', lambda s: _fetch_stooq_daily(s, suffix)),
                       ('yfinance', lambda s: _fetch_yfinance_daily(s, suffix.upper())),
                       ('upstox', _fetch_upstox_daily)):
        try:
            df = fn(symbol)
            break
        except DataUnavailable as e:
            last_error = e
            continue
        except Exception as e:  # network shape errors degrade to next source
            last_error = e
            continue
    else:
        if cached is not None:
            (df, source), _fetched = cached
            as_of = df.index[-1].date().isoformat()
            return df, _freshness(source, 'daily', symbol, as_of, now, stale=True)
        raise DataUnavailable(f"No source could serve daily {symbol}: {last_error}")
    as_of = df.index[-1].date().isoformat()
    fresh = _freshness(source, 'daily', symbol, as_of, now)
    if cache is not None:
        cache.set('daily', key, (df, source), fetched_at=now)
    return df, fresh


def fetch_intraday(symbol: str, interval: str = '15m', cache: RawCache = None,
                   suffix: str = '.NS'):
    """Intraday candles: yfinance -> Upstox intraday (keyed)."""
    symbol = symbol.upper()
    suffix = (suffix or '').upper()
    key = f"{symbol}@{interval}" if suffix == '.NS' else f"{symbol}@{interval}|{suffix}"
    now = utcnow()
    cached = cache.lookup('intraday', key) if cache is not None else None
    if cached is not None:
        (df, source), fetched_at = cached
        if is_fresh('intraday', fetched_at, now=now):
            return df, _freshness(source, 'intraday', symbol,
                                  df.index[-1].isoformat(), now)
    last_error = None
    df, source = None, None
    try:
        import yfinance as yf  # lazy: keeps this module importable without yfinance
        raw = yf.download(
            tickers=symbol + suffix.upper(),
            period='5d',
            interval=interval,
            progress=False,
            timeout=10,
            auto_adjust=False,
        )
        if raw is None or len(raw) == 0:
            raise DataUnavailable(f"yfinance returned no intraday rows for {symbol}")
        df, source = _normalize_ohlcv(raw), 'yfinance'
    except DataUnavailable as e:
        last_error = e
    except Exception as e:
        last_error = e
    if df is None:
        try:
            token = _upstox_token()
            ukey = _upstox_instrument_key(symbol, token)
            unit, step = ('minutes', interval.rstrip('m')) if interval.endswith('m') else ('hours', '1')
            df = _upstox_candles(ukey, unit, step, '', intraday=True)
            source = 'upstox'
        except (DataUnavailable, Exception) as e:
            last_error = last_error or e
        if df is None:
            if cached is not None:
                (sdf, ssource), _fetched = cached
                return sdf, _freshness(ssource, 'intraday', symbol,
                                       sdf.index[-1].isoformat(), now, stale=True)
            raise DataUnavailable(f"No source could serve intraday {symbol}: {last_error}")
    fresh = _freshness(source, 'intraday', symbol, df.index[-1].isoformat(), now)
    if cache is not None:
        cache.set('intraday', key, (df, source), fetched_at=now)
    return df, fresh


def _default_universe_loader(option: int):
    """Universe lists via the existing Fetcher seam (NSE CSVs, keyless).

    Import direction is one-way: Fetcher imports DataFloor at module top;
    DataFloor imports Fetcher only here, lazily. Keep it that way.
    """
    from classes.Fetcher import tools as FetcherTools
    fetcher = FetcherTools.__new__(FetcherTools)
    return list(FetcherTools.fetchCodes(fetcher, option))


def get_universe(option: int, loader=None, cache: RawCache = None):
    """Symbol universe for a ticker option, cached 7 days. Returns (list, freshness)."""
    key = str(option)
    now = utcnow()
    if cache is not None:
        hit = cache.fresh('universe', key, now=now)
        if hit is not None:
            symbols, _source = hit
            return symbols, _freshness('nse', 'universe', key, now.date().isoformat(), now)
    loader = loader or _default_universe_loader
    symbols = list(loader(option))
    if cache is not None:
        cache.set('universe', key, (symbols, 'nse'), fetched_at=now)
    return symbols, _freshness('nse', 'universe', key, now.date().isoformat(), now)


class Warmer:
    """Background-capable cache warmer: flagship universes first, down to the tail."""

    def __init__(self, universe_loader, daily_fetch, cache: RawCache = None,
                 universe_order=None, max_per_universe: int = None):
        self.universe_loader = universe_loader
        self.daily_fetch = daily_fetch
        self.cache = cache or RawCache()
        self.universe_order = universe_order or list(WARM_UNIVERSE_ORDER)
        self.max_per_universe = max_per_universe
        self._thread = None

    def warm_now(self) -> dict:
        stats = {'symbols': 0, 'refreshed': 0, 'skipped': 0, 'failed': 0}
        for option in self.universe_order:
            try:
                symbols = list(self.universe_loader(option))
            except Exception:
                stats['failed'] += 1
                continue
            if self.max_per_universe is not None:
                symbols = symbols[:self.max_per_universe]
            for symbol in symbols:
                stats['symbols'] += 1
                hit = self.cache.fresh('daily', symbol.upper())
                if hit is not None:
                    stats['skipped'] += 1
                    continue
                try:
                    self.daily_fetch(symbol)
                    stats['refreshed'] += 1
                except Exception:
                    stats['failed'] += 1
        return stats

    def start_background(self) -> threading.Thread:
        """Warm in a daemon thread; returns the handle for join()."""
        self._thread = threading.Thread(target=self.warm_now, daemon=True, name='datafloor-warmer')
        self._thread.start()
        return self._thread

    def join(self, timeout: float = None):
        if self._thread is not None:
            self._thread.join(timeout=timeout)


def warm_on_startup(universe_loader=None, daily_fetch=None, cache: RawCache = None) -> Warmer:
    """App-open hook: warm core universes in the background. Returns the Warmer."""
    cache = cache or get_shared_cache()
    raw_loader = universe_loader or _default_universe_loader

    def _load(option: int):
        # Route through the universe cache so entries are pre-filled, not
        # just the daily frames the Warmer fetches per symbol.
        symbols, _fresh = get_universe(option, loader=raw_loader, cache=cache)
        return symbols

    loader = _load if universe_loader is None else universe_loader

    def _fetch(symbol: str):
        return fetch_daily(symbol, cache=cache)

    warmer = Warmer(loader, daily_fetch or _fetch, cache=cache)
    warmer.start_background()
    return warmer
