import os
import sys
from types import SimpleNamespace

import pandas as pd


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from classes.Fetcher import tools as Fetcher
from classes.ParallelProcessing import StockConsumer


def _prices(value):
    index = pd.date_range('2025-01-01', periods=2)
    return pd.DataFrame({
        'Open': [value, value + 1],
        'High': [value + 2, value + 3],
        'Low': [value - 1, value],
        'Close': [value + 1, value + 2],
        'Adj Close': [value + 1, value + 2],
        'Volume': [100, 200],
    }, index=index)


def test_batch_fetch_maps_nse_symbols_and_limits_yfinance_threads(monkeypatch):
    combined = pd.concat({'AAA.NS': _prices(10), 'BBB.NS': _prices(20)}, axis=1)
    call = {}

    def fake_download(**kwargs):
        call.update(kwargs)
        return combined

    monkeypatch.setattr('classes.Fetcher.yf.download', fake_download)

    result = Fetcher(None).fetchStockDataBatch(
        ['AAA', 'BBB'], '300d', '1d', tickerOption=12, threads=2
    )

    assert call['tickers'] == ['AAA.NS', 'BBB.NS']
    assert call['threads'] == 2
    assert call['group_by'] == 'ticker'
    assert set(result) == {'AAA', 'BBB'}
    assert all(dtype == 'float64' for dtype in result['AAA'].dtypes)


def test_batch_consumer_retries_only_missing_symbols(monkeypatch):
    consumer = object.__new__(StockConsumer)
    prefetched = _prices(10)
    fetcher = SimpleNamespace(
        fetchStockDataBatch=lambda *args, **kwargs: {'AAA': prefetched}
    )
    config = SimpleNamespace(period='300d', duration='1d')
    tasks = []
    for stock in ('AAA', 'BBB'):
        task = [None] * 20
        task[0] = 12
        task[10] = config
        task[11] = fetcher
        task[14] = stock
        tasks.append(tuple(task))

    calls = []

    def fake_screen(*args, prefetchedData=None):
        calls.append((args[14], prefetchedData))
        return args[14]

    monkeypatch.setattr(consumer, 'screenStocks', fake_screen)

    assert consumer.screenStockBatch(tasks) == ['AAA', 'BBB']
    assert calls[0][0] == 'AAA' and calls[0][1][0] is prefetched
    assert calls[1] == ('BBB', None)
