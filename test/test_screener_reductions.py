import os
import sys
from types import SimpleNamespace

import pandas as pd


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from classes.Screener import tools


def make_screener():
    config = SimpleNamespace(
        daysToLookback=30,
        minLTP=0,
        maxLTP=100_000,
        stageTwo=False,
        useEMA=False,
    )
    return tools(config)


def reject_describe(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("DataFrame.describe() should not be used for a min/max reduction")

    monkeypatch.setattr(pd.DataFrame, "describe", fail)


def test_consolidation_uses_direct_close_reductions(monkeypatch):
    reject_describe(monkeypatch)
    screener = make_screener()
    screen, saved = {}, {}

    result = screener.validateConsolidation(
        pd.DataFrame({"Close": [100.0, 95.0, 90.0]}),
        screen,
        saved,
        percentage=10,
    )

    assert result == 10.0
    assert saved["Consolidating"] == "10.0%"


def test_breakout_uses_direct_high_and_close_reductions(monkeypatch):
    reject_describe(monkeypatch)
    screener = make_screener()
    screen, saved = {}, {}
    data = pd.DataFrame(
        {
            "Open": [101.0, 99.0, 97.0],
            "High": [103.0, 105.0, 102.0],
            "Close": [102.0, 100.0, 98.0],
        }
    )

    assert screener.findBreakout(data, screen, saved, daysToLookback=30) is True
    assert saved["Breaking-Out"] == "100.0, 105.0"


def test_lowest_volume_uses_direct_volume_minimum(monkeypatch):
    reject_describe(monkeypatch)
    screener = make_screener()
    data = pd.DataFrame({"Volume": [50.0, 75.0, 100.0]})

    assert screener.validateLowestVolume(data, daysForLowestVolume=3) is True


def test_narrow_range_uses_direct_range_minimum(monkeypatch, mocker):
    reject_describe(monkeypatch)
    mocker.patch("classes.Screener.Utility.tools.isTradingTime", return_value=False)
    screener = make_screener()
    screen, saved = {}, {}
    data = pd.DataFrame(
        {
            "Open": [10.0, 10.0, 10.0, 10.0],
            "Close": [11.0, 13.0, 14.0, 15.0],
        }
    )

    assert screener.validateNarrowRange(data, screen, saved, nr=4) is True
    assert saved["Pattern"] == "NR4"


def test_ipo_base_uses_direct_high_maximum(monkeypatch):
    reject_describe(monkeypatch)
    screener = make_screener()
    screen, saved = {}, {}
    data = pd.DataFrame(
        {
            "Open": [108.0, 105.0, 100.0],
            "High": [115.0, 120.0, 105.0],
            "Close": [110.0, 105.0, 100.0],
        }
    )

    assert screener.validateIpoBase("TEST", data, screen, saved) is True
    assert saved["Pattern"] == "IPO Base (10.0 %)"
