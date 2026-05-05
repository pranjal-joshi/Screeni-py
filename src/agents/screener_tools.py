"""
Screener Tools for Screeni-py Agent Harness.
Wraps Screener methods as openai-agents function_tool instances.
Each tool accepts an index name, internally runs the screener, and returns results.
"""
import sys
import os
import logging
from typing import Optional

# Ensure src/ is in path for class imports
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

logger = logging.getLogger(__name__)

# Index name -> tickerOption mapping
INDEX_MAP = {
    "nifty 50": 1,
    "nifty50": 1,
    "nifty next 50": 2,
    "nifty 100": 3,
    "nifty 200": 4,
    "nifty 500": 5,
    "nifty500": 5,
    "nifty smallcap 50": 6,
    "nifty smallcap 100": 7,
    "nifty smallcap 250": 8,
    "nifty midcap 50": 9,
    "nifty midcap 100": 10,
    "nifty midcap 150": 11,
    "all nse": 12,
    "all": 12,
    "f&o stocks": 14,
    "f&o": 14,
    "fo": 14,
    "s&p 500": 15,
    "sp500": 15,
}


def _resolve_index(index: str) -> int:
    """Resolve a human-readable index name to a ticker option integer."""
    key = index.strip().lower()
    if key in INDEX_MAP:
        return INDEX_MAP[key]
    # Try numeric
    try:
        val = int(index)
        if 1 <= val <= 16:
            return val
    except (ValueError, TypeError):
        pass
    # Default to Nifty 500
    logger.warning(f"Unknown index '{index}', defaulting to Nifty 500 (option 5)")
    return 5


def _run_screen(ticker_option: int, execute_option: int, **extra_args) -> list:
    """
    Core screener runner. Returns list of result dicts.
    Instantiates ConfigManager, Fetcher, and runs ParallelProcessing.
    """
    try:
        import classes.ConfigManager as ConfigManager
        import classes.Fetcher as Fetcher
        import classes.Screener as Screener

        configManager = ConfigManager.tools()
        if not configManager.checkConfigFile():
            configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
        configManager.getConfig(ConfigManager.parser)

        fetcher = Fetcher.tools(configManager)
        stock_list = fetcher.fetchStockCodes(ticker_option)

        if not stock_list:
            return [{"error": f"No stocks found for ticker option {ticker_option}"}]

        screener = Screener.tools(configManager)
        results = []

        import pandas as pd
        screen_results = pd.DataFrame()
        save_results = pd.DataFrame()

        # We use a simplified serial loop for agent context (avoids multiprocessing complexity)
        for symbol in stock_list[:50]:  # Limit for agent responsiveness
            try:
                stock_data = fetcher.fetchStockData(
                    symbol,
                    configManager.period,
                    configManager.duration,
                    proxyServer="",
                    screenResultsCounter=None,
                    screenCounter=None,
                    totalSymbols=len(stock_list),
                )
                if stock_data is None or stock_data.empty:
                    continue

                full_data, trimmed_data = screener.preprocessData(stock_data, configManager.daysToLookback)

                screen_dict = {'Stock': symbol}
                save_dict = {'Stock': symbol}

                passed = True

                if execute_option == 1:  # Breakout
                    days = extra_args.get('days_lookback', configManager.daysToLookback)
                    if not screener.findBreakout(trimmed_data, screen_dict, save_dict, days):
                        passed = False
                elif execute_option == 2:  # Consolidation
                    pct = extra_args.get('percentage', configManager.consolidationPercentage)
                    if not screener.validateConsolidation(trimmed_data, screen_dict, save_dict, pct):
                        passed = False
                elif execute_option == 3:  # Volume breakout
                    vol_ratio = extra_args.get('volume_ratio', configManager.volumeRatio)
                    if not screener.validateVolume(trimmed_data, screen_dict, save_dict, vol_ratio):
                        passed = False
                elif execute_option == 4:  # RSI
                    min_rsi = extra_args.get('min_rsi', 40)
                    max_rsi = extra_args.get('max_rsi', 60)
                    if not screener.validateRSI(full_data, screen_dict, save_dict, min_rsi, max_rsi):
                        passed = False
                elif execute_option == 5:  # Reversal
                    ma_len = extra_args.get('ma_length', 9)
                    if not screener.findReversalMA(full_data, screen_dict, save_dict, ma_len):
                        passed = False
                elif execute_option == 6:  # Chart patterns
                    pattern = extra_args.get('pattern', 1)
                    if not screener.validateInsideBar(trimmed_data, screen_dict, save_dict, pattern):
                        passed = False
                elif execute_option == 7:  # VCP
                    window = extra_args.get('window', 3)
                    pct_top = extra_args.get('pct_from_top', 3.0)
                    if not screener.validateVCP(full_data, screen_dict, save_dict, stockName=symbol, window=window, percentageFromTop=pct_top):
                        passed = False
                elif execute_option == 8:  # Lorentzian
                    look_for = extra_args.get('look_for', 1)
                    if not screener.validateLorentzian(full_data, screen_dict, save_dict, lookFor=look_for):
                        passed = False
                elif execute_option == 9:  # Momentum
                    if not screener.validateMomentum(trimmed_data, screen_dict, save_dict):
                        passed = False
                elif execute_option == 10:  # Narrow range
                    nr = extra_args.get('nr', 4)
                    if not screener.validateNarrowRange(trimmed_data, screen_dict, save_dict, nr=nr):
                        passed = False
                elif execute_option == 11:  # IPO base
                    pct = extra_args.get('percentage', 0.3)
                    if not screener.validateIpoBase(symbol, full_data, screen_dict, save_dict, pct):
                        passed = False
                elif execute_option == 12:  # Confluence
                    pct = extra_args.get('percentage', 0.1)
                    if not screener.validateConfluence(symbol, full_data, screen_dict, save_dict, pct):
                        passed = False
                elif execute_option == 13:  # MA Reversal
                    ma_len = extra_args.get('ma_length', 50)
                    if not screener.findReversalMA(full_data, screen_dict, save_dict, ma_len):
                        passed = False
                elif execute_option == 14:  # RSI MA Cross
                    ma_len = extra_args.get('ma_length', 9)
                    if not screener.findRSICrossingMA(full_data, screen_dict, save_dict, ma_len):
                        passed = False

                if passed:
                    # Also validate LTP
                    screener.validateLTP(trimmed_data, screen_dict, save_dict)
                    results.append({k: v for k, v in save_dict.items()})

            except Exception as e:
                logger.debug(f"Skipping {symbol}: {e}")
                continue

        return results if results else [{"message": "No stocks matched the criteria."}]

    except Exception as e:
        logger.error(f"Screener error: {e}")
        return [{"error": str(e)}]


# ---- Try to import agents SDK function_tool ----
# Note: Our package is 'src/agents/' which shadows the openai-agents 'agents' package.
# We temporarily pop our local package from sys.modules, load the real one from
# site-packages, then restore our local package registration.
try:
    import sys as _sys
    import importlib as _il

    _SITE_PACKAGES = '/home/node/.local/lib/python3.11/site-packages'

    def _load_real_openai_agents():
        """Load openai-agents package bypassing local src/agents/ shadow."""
        import site as _site
        _sp_paths = []
        try:
            _sp_paths.extend(_site.getsitepackages())
        except Exception:
            pass
        try:
            _sp_paths.append(_site.getusersitepackages())
        except Exception:
            pass
        _sp_paths.append(_SITE_PACKAGES)

        # Temporarily remove our local 'agents' from sys.modules
        _our_agents = _sys.modules.pop('agents', None)
        # Add site-packages to front of path
        _valid_sp = [p for p in _sp_paths if __import__('os').path.exists(p)]
        for _sp in _valid_sp:
            _sys.path.insert(0, _sp)
        try:
            _mod = _il.import_module('agents')
            return _mod
        finally:
            # Restore our local agents package
            for _sp in _valid_sp:
                try:
                    _sys.path.remove(_sp)
                except ValueError:
                    pass
            if _our_agents is not None:
                _sys.modules['agents'] = _our_agents
            else:
                # Keep the real agents in sys.modules under a backup key
                _real = _sys.modules.get('agents')
                if _real:
                    _sys.modules['_screenipy_openai_agents_real'] = _real
                    _sys.modules.pop('agents', None)

    _openai_agents = _load_real_openai_agents()
    function_tool = _openai_agents.function_tool

    @function_tool
    def screen_breakout(index: str = "Nifty 500", days_lookback: int = 30) -> str:
        """Screen stocks breaking out of key resistance levels with volume confirmation.
        
        Args:
            index: Market index to screen (e.g., 'Nifty 50', 'Nifty 500', 'F&O Stocks')
            days_lookback: Number of days to look back for breakout analysis
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 1, days_lookback=days_lookback)
        if not results:
            return "No breakout stocks found."
        return f"Breakout stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_volume_breakout(index: str = "Nifty 500", volume_ratio: float = 2.5) -> str:
        """Screen stocks with unusual volume surges indicating institutional activity.
        
        Args:
            index: Market index to screen
            volume_ratio: Minimum ratio of current volume to 20-day average volume
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 3, volume_ratio=volume_ratio)
        if not results:
            return "No volume breakout stocks found."
        return f"Volume breakout stocks in {index} (ratio >= {volume_ratio}x):\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_consolidation(index: str = "Nifty 500", percentage: float = 10.0) -> str:
        """Screen stocks consolidating in a tight range, building a base for breakout.
        
        Args:
            index: Market index to screen
            percentage: Maximum percentage range for consolidation (tighter = stronger base)
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 2, percentage=percentage)
        if not results:
            return "No consolidating stocks found."
        return f"Consolidating stocks in {index} (within {percentage}%):\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_rsi(index: str = "Nifty 500", min_rsi: int = 40, max_rsi: int = 60) -> str:
        """Screen stocks with RSI in a specified range.
        
        Args:
            index: Market index to screen
            min_rsi: Minimum RSI value (0-100)
            max_rsi: Maximum RSI value (0-100)
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 4, min_rsi=min_rsi, max_rsi=max_rsi)
        if not results:
            return f"No stocks with RSI between {min_rsi} and {max_rsi} found."
        return f"Stocks in {index} with RSI {min_rsi}-{max_rsi}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_reversal(index: str = "Nifty 500", ma_length: int = 9) -> str:
        """Screen stocks showing potential reversal near moving average.
        
        Args:
            index: Market index to screen
            ma_length: Moving average period for reversal detection
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 5, ma_length=ma_length)
        if not results:
            return "No reversal stocks found."
        return f"Reversal stocks in {index} (MA {ma_length}):\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_chart_patterns(index: str = "Nifty 500", pattern: int = 1) -> str:
        """Screen stocks showing specific chart patterns (inside bars, etc.).
        
        Args:
            index: Market index to screen
            pattern: Pattern type (1=Inside Bar, 2=IPA Breakout, 3=Bullish Candle)
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 6, pattern=pattern)
        if not results:
            return "No chart pattern stocks found."
        return f"Chart pattern stocks in {index} (pattern={pattern}):\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_vcp(index: str = "Nifty 500", window: int = 3, pct_from_top: float = 3.0) -> str:
        """Screen stocks showing Volatility Contraction Pattern (VCP) - Mark Minervini's method.
        
        Args:
            index: Market index to screen
            window: Number of contraction cycles to look for
            pct_from_top: Maximum percentage from 52-week high for the base
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 7, window=window, pct_from_top=pct_from_top)
        if not results:
            return "No VCP stocks found."
        return f"VCP stocks in {index} (window={window}, {pct_from_top}% from top):\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_lorentzian(index: str = "Nifty 500", look_for: int = 1) -> str:
        """Screen stocks using Lorentzian Classification ML algorithm for buy/sell signals.
        
        Args:
            index: Market index to screen
            look_for: Signal type (1=Buy, 2=Sell, 3=Any)
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 8, look_for=look_for)
        if not results:
            return "No Lorentzian signal stocks found."
        signal_map = {1: "Buy", 2: "Sell", 3: "Any"}
        signal_str = signal_map.get(look_for, "Buy")
        return f"Lorentzian {signal_str} signals in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_momentum(index: str = "Nifty 500") -> str:
        """Screen stocks showing strong price momentum with increasing volume.
        
        Args:
            index: Market index to screen
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 9)
        if not results:
            return "No momentum stocks found."
        return f"Momentum stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_narrow_range(index: str = "Nifty 500", nr: int = 4) -> str:
        """Screen stocks showing Narrow Range (NR4/NR7) candlestick patterns.
        
        Args:
            index: Market index to screen
            nr: Narrow range lookback (4=NR4, 7=NR7)
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 10, nr=nr)
        if not results:
            return "No narrow range stocks found."
        return f"Narrow Range NR{nr} stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_ipo_base(index: str = "Nifty 500", percentage: float = 0.3) -> str:
        """Screen recently IPO'd stocks forming a base pattern.
        
        Args:
            index: Market index to screen
            percentage: Maximum percentage from IPO price for base formation
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 11, percentage=percentage)
        if not results:
            return "No IPO base stocks found."
        return f"IPO base stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_confluence(index: str = "Nifty 500", percentage: float = 0.1) -> str:
        """Screen stocks at confluence of multiple support/resistance levels.
        
        Args:
            index: Market index to screen
            percentage: Tolerance percentage for confluence zone
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 12, percentage=percentage)
        if not results:
            return "No confluence stocks found."
        return f"Confluence stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_ma_reversal(index: str = "Nifty 500", ma_length: int = 50) -> str:
        """Screen stocks reversing from a key moving average level.
        
        Args:
            index: Market index to screen
            ma_length: Moving average period (common: 20, 50, 200)
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 13, ma_length=ma_length)
        if not results:
            return "No MA reversal stocks found."
        return f"MA {ma_length} reversal stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    @function_tool
    def screen_rsi_ma_cross(index: str = "Nifty 500", ma_length: int = 9) -> str:
        """Screen stocks where RSI crosses its moving average (signal of momentum shift).
        
        Args:
            index: Market index to screen
            ma_length: RSI moving average period
        """
        ticker_opt = _resolve_index(index)
        results = _run_screen(ticker_opt, 14, ma_length=ma_length)
        if not results:
            return "No RSI MA cross stocks found."
        return f"RSI MA ({ma_length}) cross stocks in {index}:\n" + "\n".join(
            str(r) for r in results
        )

    ALL_TOOLS = [
        screen_breakout,
        screen_volume_breakout,
        screen_consolidation,
        screen_rsi,
        screen_reversal,
        screen_chart_patterns,
        screen_vcp,
        screen_lorentzian,
        screen_momentum,
        screen_narrow_range,
        screen_ipo_base,
        screen_confluence,
        screen_ma_reversal,
        screen_rsi_ma_cross,
    ]

    TOOL_MAP = {
        'screen_breakout': screen_breakout,
        'screen_volume_breakout': screen_volume_breakout,
        'screen_consolidation': screen_consolidation,
        'screen_rsi': screen_rsi,
        'screen_reversal': screen_reversal,
        'screen_chart_patterns': screen_chart_patterns,
        'screen_vcp': screen_vcp,
        'screen_lorentzian': screen_lorentzian,
        'screen_momentum': screen_momentum,
        'screen_narrow_range': screen_narrow_range,
        'screen_ipo_base': screen_ipo_base,
        'screen_confluence': screen_confluence,
        'screen_ma_reversal': screen_ma_reversal,
        'screen_rsi_ma_cross': screen_rsi_ma_cross,
    }

except ImportError:
    # Fallback if openai-agents not installed
    logger.warning("openai-agents not installed. Agent tools unavailable.")

    ALL_TOOLS = []
    TOOL_MAP = {}

    def screen_breakout(index="Nifty 500", days_lookback=30):
        """Stub: screen_breakout requires openai-agents package."""
        return _run_screen(_resolve_index(index), 1, days_lookback=days_lookback)

    def screen_volume_breakout(index="Nifty 500", volume_ratio=2.5):
        """Stub: screen_volume_breakout requires openai-agents package."""
        return _run_screen(_resolve_index(index), 3, volume_ratio=volume_ratio)

    def screen_consolidation(index="Nifty 500", percentage=10.0):
        """Stub: screen_consolidation requires openai-agents package."""
        return _run_screen(_resolve_index(index), 2, percentage=percentage)

    def screen_rsi(index="Nifty 500", min_rsi=40, max_rsi=60):
        """Stub: screen_rsi requires openai-agents package."""
        return _run_screen(_resolve_index(index), 4, min_rsi=min_rsi, max_rsi=max_rsi)

    def screen_reversal(index="Nifty 500", ma_length=9):
        """Stub: screen_reversal requires openai-agents package."""
        return _run_screen(_resolve_index(index), 5, ma_length=ma_length)

    def screen_chart_patterns(index="Nifty 500", pattern=1):
        """Stub: screen_chart_patterns requires openai-agents package."""
        return _run_screen(_resolve_index(index), 6, pattern=pattern)

    def screen_vcp(index="Nifty 500", window=3, pct_from_top=3.0):
        """Stub: screen_vcp requires openai-agents package."""
        return _run_screen(_resolve_index(index), 7, window=window, pct_from_top=pct_from_top)

    def screen_lorentzian(index="Nifty 500", look_for=1):
        """Stub: screen_lorentzian requires openai-agents package."""
        return _run_screen(_resolve_index(index), 8, look_for=look_for)

    def screen_momentum(index="Nifty 500"):
        """Stub: screen_momentum requires openai-agents package."""
        return _run_screen(_resolve_index(index), 9)

    def screen_narrow_range(index="Nifty 500", nr=4):
        """Stub: screen_narrow_range requires openai-agents package."""
        return _run_screen(_resolve_index(index), 10, nr=nr)

    def screen_ipo_base(index="Nifty 500", percentage=0.3):
        """Stub: screen_ipo_base requires openai-agents package."""
        return _run_screen(_resolve_index(index), 11, percentage=percentage)

    def screen_confluence(index="Nifty 500", percentage=0.1):
        """Stub: screen_confluence requires openai-agents package."""
        return _run_screen(_resolve_index(index), 12, percentage=percentage)

    def screen_ma_reversal(index="Nifty 500", ma_length=50):
        """Stub: screen_ma_reversal requires openai-agents package."""
        return _run_screen(_resolve_index(index), 13, ma_length=ma_length)

    def screen_rsi_ma_cross(index="Nifty 500", ma_length=9):
        """Stub: screen_rsi_ma_cross requires openai-agents package."""
        return _run_screen(_resolve_index(index), 14, ma_length=ma_length)
