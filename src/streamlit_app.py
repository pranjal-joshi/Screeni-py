import random
import streamlit as st
import requests
import os
import configparser
import urllib
import datetime
from num2words import num2words
from time import sleep
from pathlib import Path
from threading import Thread
from math import floor
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

st.set_page_config(layout="wide", page_title="Screeni-py", page_icon="📈")

os.environ["TERM"] = "xterm"

# Suppress noisy Streamlit internal warnings that appear when Streamlit APIs
# are called from worker threads / multiprocessing subprocesses that don't
# carry a ScriptRunContext (these are harmless and expected in our setup).
import logging as _logging
_logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(_logging.ERROR)
_logging.getLogger("streamlit.runtime.scriptrunner").setLevel(_logging.ERROR)

# ── Startup splash — shown immediately before heavy imports ───────────────────
_startup_placeholder = st.empty()
if not st.session_state.get('_app_loaded'):
    with _startup_placeholder.container():
        st.markdown("""
        <style>
          /* Hide default Streamlit elements during load */
          header[data-testid="stHeader"] { visibility: hidden; }
        </style>
        """, unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex;flex-direction:column;align-items:center;"
            "justify-content:center;height:80vh;gap:1.2rem;'>"
            "<div style='font-size:3.5rem;'>📈</div>"
            "<div style='font-size:1.6rem;font-weight:700;letter-spacing:0.04em;'>Screeni-py</div>"
            "<div style='color:#888;font-size:0.95rem;'>Loading, please wait…</div>"
            "</div>",
            unsafe_allow_html=True,
        )

import pandas as pd
import classes.ConfigManager as ConfigManager
import classes.Utility as Utility
import classes.Fetcher as Fetcher
import classes.BrowserConfigStore as BrowserConfigStore
from screenipy import main as screenipy_main
from classes.OtaUpdater import OTAUpdater
from classes.Changelog import VERSION

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Enough top padding to clear Streamlit's fixed toolbar (~3.75rem) */
  .block-container { padding-top: 3rem; padding-bottom: 5rem; }

  /* Uniform tall buttons */
  .stButton>button, .stDownloadButton>button { height: 56px; }

  /* Table header alignment */
  th { text-align: left !important; }

  /* Tab font weight */
  button[data-baseweb="tab"] { font-weight: 600; }

  /* Section headers in Configure tab */
  .section-header {
    font-size: 1rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 1.2rem;
    margin-bottom: 0.2rem;
  }
</style>
""", unsafe_allow_html=True)

# ── Proxy ─────────────────────────────────────────────────────────────────────
try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

# ── Static file server (js/css for TableFilter) ───────────────────────────────
def start_static_file_server():
    class ThreadedHTTPServer(TCPServer):
        allow_reuse_address = True

    server = ThreadedHTTPServer(("0.0.0.0", 8000), SimpleHTTPRequestHandler)

    def serve():
        with server:
            server.serve_forever()

    threading.Thread(target=serve, daemon=True).start()
    return server

try:
    staticFileServer = start_static_file_server()
except OSError as e:
    if e.errno not in (98, 10048):   # already in use on Linux / Windows
        raise

# ── Update check (cached 1 h) ─────────────────────────────────────────────────
@st.cache_data(ttl='1h', show_spinner=False)
def check_updates():
    return OTAUpdater.checkForUpdate(proxyServer, VERSION)

isDevVersion, guiUpdateMessage = check_updates()

# All slow work done — clear the splash and mark loaded
st.session_state['_app_loaded'] = True
_startup_placeholder.empty()

execute_inputs = []

# ── Result table ──────────────────────────────────────────────────────────────
def _tv_url(ticker: str, ticker_option) -> str:
    """Build TradingView chart URL for a given ticker."""
    try:
        if type(ticker_option) == str or int(ticker_option) < 15:
            return f"https://in.tradingview.com/chart?symbol=NSE%3A{ticker}"
        elif ticker_option == '16':
            return f"https://in.tradingview.com/chart?symbol=NSE%3A{ticker}"
        else:
            return f"https://in.tradingview.com/chart?symbol={ticker}"
    except Exception:
        return f"https://in.tradingview.com/chart?symbol=NSE%3A{ticker}"


def _style_result_df(df: pd.DataFrame):
    """Apply background colour highlights to key columns."""
    GREEN = 'background-color: #1a4d2e; color: #6fcf97'
    RED = 'background-color: #4d1a1a; color: #eb5757'
    AMBER = 'background-color: #3d3000; color: #f2c94c'
    RESET = ''

    def colour_signal(val):
        v = str(val).lower()
        if any(k in v for k in ('bull', 'buy', 'breakout', 'up', 'strong', 'stage-2', 'above')):
            return GREEN
        if any(k in v for k in ('bear', 'sell', 'breakdown', 'down', 'weak', 'below')):
            return RED
        if any(k in v for k in ('neutral', 'sideways', 'consolidat', 'watch')):
            return AMBER
        return RESET

    signal_cols = [c for c in df.columns if c in (
        'MA-Signal', 'Trend (30Days)', 'Breakout (30Days)', 'Consolidating', 'Pattern'
    )]
    style = df.style
    for col in signal_cols:
        style = style.applymap(colour_signal, subset=[col])
    return style.set_properties(**{'font-size': '0.85rem'})


def show_df_as_result_table():
    try:
        df: pd.DataFrame = pd.read_pickle('last_screened_unformatted_results.pkl')

        # ── Header row ──────────────────────────────────────────────────────
        ac, cc, bc = st.columns([6, 1, 1])
        ac.markdown(f'#### 🔍 Found **{len(df)}** Results')

        if cc.button('🗑️ Clear Cache', use_container_width=True, key=random.randint(1, 999_999_999)):
            for p in Path.cwd().glob('stock_data_*.pkl'):
                p.unlink(missing_ok=True)
            st.toast('Stock cache deleted!', icon='🗑️')

        bc.download_button(
            label='⬇️ Export CSV',
            data=df.to_csv().encode('utf-8'),
            file_name=f'screenipy_{datetime.datetime.now().strftime("%H%M%S_%d%m%Y")}.csv',
            mime='text/csv',
            use_container_width=True,
        )

        # ── Build TradingView URL column ─────────────────────────────────────
        tv_col = 'Chart'
        ticker_opt = execute_inputs[0] if execute_inputs else 12
        try:
            if type(ticker_opt) == str or int(ticker_opt) < 15:
                df[tv_col] = [f"https://in.tradingview.com/chart?symbol=NSE%3A{t}" for t in df.index]
            elif ticker_opt == '16':
                try:
                    fetcher = Fetcher.tools(configManager=ConfigManager.tools())
                    url_map = {v: k.replace('^', '').replace('.NS', '')
                               for k, v in fetcher.getAllNiftyIndices().items()}
                    df[tv_col] = [
                        f"https://in.tradingview.com/chart?symbol=NSE%3A{url_map.get(t, t)}"
                        for t in df.index
                    ]
                except Exception:
                    df[tv_col] = [f"https://in.tradingview.com/chart?symbol=NSE%3A{t}" for t in df.index]
            else:
                df[tv_col] = [
                    f"https://in.tradingview.com/chart?symbol={t}" for t in df.index
                ]
        except Exception:
            df[tv_col] = [f"https://in.tradingview.com/chart?symbol=NSE%3A{t}" for t in df.index]

        # Reset index so stock name becomes a regular column
        df.index.name = 'Stock'
        df = df.reset_index()

        # Move Chart column right after Stock
        cols = ['Stock', tv_col] + [c for c in df.columns if c not in ('Stock', tv_col)]
        df = df[cols]

        # ── Column config ────────────────────────────────────────────────────
        col_cfg = {
            'Stock': st.column_config.TextColumn('Stock', width='small'),
            tv_col: st.column_config.LinkColumn(
                'Chart', display_text='📈 View', width='small'
            ),
            'LTP': st.column_config.TextColumn('LTP (₹)', width='small'),
            'RSI': st.column_config.TextColumn('RSI', width='small'),
            'Volume': st.column_config.TextColumn('Volume', width='small'),
            'MA-Signal': st.column_config.TextColumn('MA Signal', width='medium'),
            'Breakout (30Days)': st.column_config.TextColumn('Breakout', width='small'),
            'Consolidating': st.column_config.TextColumn('Consolidating', width='small'),
            'Trend (30Days)': st.column_config.TextColumn('Trend', width='medium'),
            'Pattern': st.column_config.TextColumn('Pattern', width='medium'),
        }
        # Only include configs for columns that exist in df
        col_cfg = {k: v for k, v in col_cfg.items() if k in df.columns}

        # ── Styled dataframe ─────────────────────────────────────────────────
        st.dataframe(
            _style_result_df(df),
            use_container_width=True,
            hide_index=True,
            height=min(48 + len(df) * 36, 640),
            column_config=col_cfg,
        )

    except FileNotFoundError:
        st.info('Run a screen first — results will appear here.', icon='📊')
    except Exception as e:
        st.error(f'Could not load results: {e}')


# ── Config save callback ───────────────────────────────────────────────────────
def on_config_change():
    cm = ConfigManager.tools()
    cm.period = st.session_state.get('cfg_period', cm.period)
    cm.daysToLookback = st.session_state.get('cfg_lookback', cm.daysToLookback)
    cm.duration = st.session_state.get('cfg_duration', cm.duration)
    cm.minLTP = st.session_state.get('cfg_minprice', cm.minLTP)
    cm.maxLTP = st.session_state.get('cfg_maxprice', cm.maxLTP)
    cm.volumeRatio = st.session_state.get('cfg_volratio', cm.volumeRatio)
    cm.consolidationPercentage = st.session_state.get('cfg_consolpct', cm.consolidationPercentage)
    cm.shuffle = st.session_state.get('cfg_shuffle', cm.shuffleEnabled)
    cm.cacheEnabled = st.session_state.get('cfg_cache', cm.cacheEnabled)
    cm.stageTwo = st.session_state.get('cfg_stagetwo', cm.stageTwo)
    cm.useEMA = st.session_state.get('cfg_useema', cm.useEMA)
    data = {
        "period": cm.period,
        "daysToLookback": cm.daysToLookback,
        "duration": cm.duration,
        "minLTP": cm.minLTP,
        "maxLTP": cm.maxLTP,
        "volumeRatio": cm.volumeRatio,
        "consolidationPercentage": cm.consolidationPercentage,
        "shuffleEnabled": cm.shuffleEnabled,
        "cacheEnabled": cm.cacheEnabled,
        "stageTwo": cm.stageTwo,
        "useEMA": cm.useEMA,
    }
    BrowserConfigStore.save_screening_config(data, cm)
    st.toast('Configuration saved!', icon='💾')


# ── LLM config persistence helpers ───────────────────────────────────────────
def _find_screenipy_yaml():
    """Locate screenipy.yaml adjacent to this file or in the repo root."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'screenipy.yaml'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenipy.yaml'),
        'screenipy.yaml',
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.exists(p):
            return p
    # Return first candidate as default write target even if it doesn't exist yet
    return os.path.abspath(candidates[0])


def _load_llm_defaults_from_yaml():
    """Read llm config from localStorage (with YAML fallback) and pre-populate session_state (once per session)."""
    if st.session_state.get('_llm_defaults_loaded'):
        return
    st.session_state['_llm_defaults_loaded'] = True
    try:
        llm = BrowserConfigStore.load_llm_config()
        if 'ai_provider' not in st.session_state:
            st.session_state['ai_provider'] = llm.get('provider', 'openai')
        if 'ai_model' not in st.session_state:
            st.session_state['ai_model'] = llm.get('model', 'gpt-4o')
        if 'ai_base_url' not in st.session_state:
            st.session_state['ai_base_url'] = llm.get('base_url') or 'http://localhost:11434/v1'
        if 'ai_api_key' not in st.session_state:
            # Use remembered key from localStorage if user opted in, else fall back to env var
            remembered_key = llm.get('api_key', '') if llm.get('remember_api_key') else ''
            st.session_state['ai_api_key'] = remembered_key or os.environ.get('SCREENIPY_API_KEY', '')
        if 'ai_remember_key' not in st.session_state:
            st.session_state['ai_remember_key'] = llm.get('remember_api_key', False)
    except Exception:
        pass


def _save_llm_config_to_yaml():
    """Persist LLM config to localStorage and mirror safe fields to screenipy.yaml."""
    data = {
        "provider": st.session_state.get('ai_provider', 'openai'),
        "model": st.session_state.get('ai_model', 'gpt-4o'),
        "base_url": st.session_state.get('ai_base_url', None),
        "api_key": st.session_state.get('ai_api_key', ''),
    }
    remember_key = st.session_state.get('ai_remember_key', False)
    try:
        BrowserConfigStore.save_llm_config(data, remember_api_key=remember_key)
        st.toast('LLM configuration saved!', icon='🤖')
    except Exception as e:
        st.toast(f'Could not save LLM config: {e}', icon='⚠️')


# ── Screener start ─────────────────────────────────────────────────────────────
def on_start_button_click():
    if isDevVersion is not None:
        st.info(f'Debug inputs: {execute_inputs}')

    def _run():
        try:
            screenipy_main(execute_inputs=execute_inputs, isDevVersion=isDevVersion, backtestDate=backtestDate)
        except StopIteration:
            pass
        except requests.exceptions.RequestException:
            os.environ['SCREENIPY_REQ_ERROR'] = "TRUE"

    if Utility.tools.isBacktesting(backtestDate=backtestDate):
        st.write(f'Running in :red[**Backtesting Mode**] for *T = {backtestDate}* (Y-M-D)')
        st.write('Backtesting is :red[not supported] for intraday timeframes.')

    t = Thread(target=_run)
    # Propagate Streamlit's script run context to the worker thread so it
    # doesn't emit "missing ScriptRunContext" warnings.
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            add_script_run_ctx(t, ctx)
    except Exception:
        pass

    t.start()

    progress_bar = st.progress(0, text="🚀 Preparing screener, please wait…")
    os.environ['SCREENIPY_SCREEN_COUNTER'] = '0'

    while int(os.environ.get('SCREENIPY_SCREEN_COUNTER', '0')) < 100:
        sleep(0.05)
        cnt = int(os.environ.get('SCREENIPY_SCREEN_COUNTER', '0'))
        if cnt > 0:
            progress_bar.progress(cnt, text=f"🔍 Screening stocks… **:red[{cnt}%]** done")
        if os.environ.get('SCREENIPY_REQ_ERROR') == "TRUE":
            col_a, col_b = st.columns([2, 1])
            col_a.error(':disappointed: Failed to reach Screeni-py server!')
            col_a.info(
                'This may be an ISP issue (common with Jio). '
                'Try another network or see: https://github.com/pranjal-joshi/Screeni-py/issues/164',
                icon='ℹ️',
            )
            col_b.video('https://youtu.be/JADNADDNTmU')
            del os.environ['SCREENIPY_REQ_ERROR']
            break

    t.join()
    progress_bar.empty()


def get_extra_inputs(tickerOption, executeOption, c_index=None, c_criteria=None):
    global execute_inputs
    if not tickerOption.isnumeric():
        execute_inputs = [tickerOption, 0, 'N']
    elif int(tickerOption) == 0 or tickerOption is None:
        stock_codes = c_index.text_input('Enter Stock Code(s)', placeholder='SBIN, INFY, ITC')
        execute_inputs = [tickerOption, executeOption, stock_codes.upper(), 'N']
        return
    elif int(executeOption) >= 0 and int(executeOption) < 4:
        execute_inputs = [tickerOption, executeOption, 'N']
    elif int(executeOption) == 4:
        num_candles = c_criteria.text_input('Volume lowest since last how many candles?', value='20')
        if num_candles:
            execute_inputs = [tickerOption, executeOption, num_candles, 'N']
        else:
            c_criteria.error("Number of candles can't be blank!")
    elif int(executeOption) == 5:
        min_col, max_col = c_criteria.columns(2)
        min_rsi = min_col.number_input('Min RSI', min_value=0, max_value=100, value=50, step=1)
        max_rsi = max_col.number_input('Max RSI', min_value=0, max_value=100, value=70, step=1)
        if min_rsi >= max_rsi:
            c_criteria.warning('Min RSI must be less than Max RSI')
        else:
            execute_inputs = [tickerOption, executeOption, min_rsi, max_rsi, 'N']
    elif int(executeOption) == 6:
        c1, c2 = c_criteria.columns([7, 2])
        select_reversal = int(c1.selectbox(
            'Select Reversal Type',
            options=[
                '1 > Buy Signal (Bullish Reversal)',
                '2 > Sell Signal (Bearish Reversal)',
                '3 > Momentum Gainers (Rising Bullish Momentum)',
                '4 > Reversal at Moving Average (Bullish Reversal)',
                '5 > Volume Spread Analysis (Bullish VSA Reversal)',
                '6 > Narrow Range (NRx) Reversal',
                '8 > RSI Crossing with 9-SMA of RSI',
            ],
        ).split(' ')[0])
        if select_reversal == 4:
            ma_length = c2.number_input('MA Length', value=44, step=1)
            execute_inputs = [tickerOption, executeOption, select_reversal, ma_length, 'N']
        elif select_reversal == 6:
            nr = c2.number_input('NR(x)', min_value=1, max_value=14, value=4, step=1)
            execute_inputs = [tickerOption, executeOption, select_reversal, nr, 'N']
        else:
            execute_inputs = [tickerOption, executeOption, select_reversal, 'N']
    elif int(executeOption) == 7:
        c1, c2 = c_criteria.columns([11, 4])
        select_pattern = int(c1.selectbox(
            'Select Chart Pattern',
            options=[
                '1 > Bullish Inside Bar (Flag) Pattern',
                '2 > Bearish Inside Bar (Flag) Pattern',
                '3 > Confluence (50 & 200 MA/EMA)',
                '4 > VCP (Experimental)',
                '5 > Buying at Trendline (Swing/Mid/Long term)',
            ],
        ).split(' ')[0])
        if select_pattern in (1, 2):
            num_candles = c2.number_input('Lookback Candles', min_value=1, max_value=25, value=12, step=1)
            execute_inputs = [tickerOption, executeOption, select_pattern, int(num_candles), 'N']
        elif select_pattern == 3:
            confluence_pct = c2.number_input('MA Confluence %', min_value=0.1, max_value=5.0, value=1.0, step=0.1, format="%1.1f") / 100.0
            execute_inputs = [tickerOption, executeOption, select_pattern, confluence_pct, 'N']
        else:
            execute_inputs = [tickerOption, executeOption, select_pattern, 'N']


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
col_title, col_badge = st.columns([13, 1])
col_title.title('📈 Screeni-py')

if guiUpdateMessage == "":
    col_title.caption('Open-source NSE stock screener — find breakouts, just in time.')
elif isDevVersion:
    col_title.warning(guiUpdateMessage, icon='⚠️')
else:
    col_title.success(guiUpdateMessage, icon='✅')

col_badge.image(
    "https://user-images.githubusercontent.com/6128978/217814499-7934edf6-fcc3-46d7-887e-7757c94e1632.png",
    width=72,
)

# ══════════════════════════════════════════════════════════════════════════════
# TABS  (removed: Search Similar Stocks, Nifty-50 Gap Prediction)
# ══════════════════════════════════════════════════════════════════════════════
tab_screen, tab_ai, tab_config, tab_psc, tab_about = st.tabs([
    '📊 Classic Screen',
    '🤖 AI Native',
    '⚙️ Configuration',
    '💸 Position Size Calculator',
    'ℹ️ About',
])

# ── Classic Screen ─────────────────────────────────────────────────────────────
with tab_screen:
    list_index = [
        'All Stocks (Default)',
        '0 > By Stock Names (NSE Stock Code)',
        '1 > Nifty 50',
        '2 > Nifty Next 50',
        '3 > Nifty 100',
        '4 > Nifty 200',
        '5 > Nifty 500',
        '6 > Nifty Smallcap 50',
        '7 > Nifty Smallcap 100',
        '8 > Nifty Smallcap 250',
        '9 > Nifty Midcap 50',
        '10 > Nifty Midcap 100',
        '11 > Nifty Midcap 150',
        '13 > Newly Listed (IPOs in last 2 Years)',
        '14 > F&O Stocks Only',
        '15 > US S&P 500',
        '16 > Sectoral Indices (NSE)',
    ]

    list_criteria = [
        '0 > Full Screening (All Technical Parameters)',
        '1 > Breakout or Consolidation',
        '2 > Recent Breakout with Volume',
        '3 > Consolidating Stocks',
        '4 > Lowest Volume in last N Days (Early Breakout Detection)',
        '5 > RSI Range Filter',
        '6 > Reversal Signals',
        '7 > Chart Patterns',
    ]

    configManager = ConfigManager.tools()
    configManager.getConfig(parser=ConfigManager.parser)

    c_index, c_datepick, c_criteria, c_btn = st.columns((2, 1, 4, 1))

    tickerOption = c_index.selectbox('Index', options=list_index).split(' ')
    tickerOption = str(12 if '>' not in tickerOption else int(tickerOption[0]) if tickerOption[0].isnumeric() else str(tickerOption[0]))

    picked_date = c_datepick.date_input('Screen / Backtest For', max_value=datetime.date.today(), value=datetime.date.today())
    backtestDate = picked_date

    executeOption = str(c_criteria.selectbox('Screening Criteria', options=list_criteria).split(' ')[0])

    start_button = c_btn.button('▶ Start', type='primary', key='start_button', use_container_width=True)

    get_extra_inputs(tickerOption=tickerOption, executeOption=executeOption, c_index=c_index, c_criteria=c_criteria)

    if start_button:
        if int(tickerOption) == 0 and not execute_inputs[2].strip():
            st.warning('Please enter at least one stock code before starting.', icon='⚠️')
        else:
            on_start_button_click()
            st.toast('Screening completed!', icon='🎉')

    with st.container():
        show_df_as_result_table()

# ── AI Native ──────────────────────────────────────────────────────────────────
with tab_ai:
    try:
        import sys as _sys
        _src = os.path.dirname(os.path.abspath(__file__))
        if _src not in _sys.path:
            _sys.path.insert(0, _src)
        from ui.ai_native_tab import render as render_ai
        render_ai()
    except Exception as _ai_e:
        st.error(f'AI Native tab failed to load: {_ai_e}')
        st.info('Ensure `openai-agents` and `pyyaml` are installed.')

# ── Configuration ──────────────────────────────────────────────────────────────
with tab_config:
    configManager = ConfigManager.tools()
    configManager.getConfig(parser=ConfigManager.parser)

    # Load screening config: localStorage first, ConfigManager as fallback
    _sc = BrowserConfigStore.load_screening_config(configManager)

    hdr_col, exp_col = st.columns([10, 2])
    hdr_col.markdown('## ⚙️ Configuration')
    exp_col.download_button(
        label='Export Config',
        data=Path('screenipy.ini').read_text(),
        file_name='screenipy.ini',
        mime='text/plain',
        type='secondary',
        use_container_width=True,
    )

    # ── Screening settings ────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Screening Settings</p>', unsafe_allow_html=True)
    st.divider()

    period_options = ['15d', '60d', '300d', '52wk', '3y', '5y', 'max']
    duration_options = ['5m', '15m', '1h', '4h', '1d', '1wk']

    _sc_period = _sc.get('period', configManager.period)
    _sc_duration = _sc.get('duration', configManager.duration)
    _period_idx = period_options.index(_sc_period) if _sc_period in period_options else 2
    _duration_idx = duration_options.index(_sc_duration) if _sc_duration in duration_options else 4

    c1, c2, c3 = st.columns(3)
    period = c1.selectbox('Period', options=period_options,
                          index=_period_idx, key='cfg_period')
    daystolookback = c2.number_input('Lookback Candles',
                                     value=int(_sc.get('daysToLookback', configManager.daysToLookback)),
                                     step=1, key='cfg_lookback')
    duration = c3.selectbox('Candle Duration', options=duration_options,
                             index=_duration_idx, key='cfg_duration')
    if 'm' in duration or 'h' in duration:
        c3.caption(':orange[For intraday durations, period must be ≤ 60d]')

    c1, c2 = st.columns(2)
    c1.number_input('Min Price (₹)', value=float(_sc.get('minLTP', configManager.minLTP)), step=0.1, key='cfg_minprice',
                    help='Stocks below this price are ignored')
    c2.number_input('Max Price (₹)', value=float(_sc.get('maxLTP', configManager.maxLTP)), step=0.1, key='cfg_maxprice',
                    help='Stocks above this price are ignored')

    c1, c2 = st.columns(2)
    c1.number_input('Volume Multiplier (Breakout confirmation)',
                    value=float(_sc.get('volumeRatio', configManager.volumeRatio)),
                    step=0.1, key='cfg_volratio')
    c2.number_input('Consolidation Range (%)',
                    value=int(_sc.get('consolidationPercentage', configManager.consolidationPercentage)),
                    step=1, key='cfg_consolpct')

    c1, c2, c3, c4 = st.columns(4)
    c1.checkbox('Shuffle stocks', value=bool(_sc.get('shuffleEnabled', configManager.shuffleEnabled)),
                disabled=True, key='cfg_shuffle')
    c2.checkbox('Cache stock data', value=bool(_sc.get('cacheEnabled', configManager.cacheEnabled)),
                disabled=True, key='cfg_cache')
    c3.checkbox('Stage-2 stocks only', value=bool(_sc.get('stageTwo', configManager.stageTwo)),
                key='cfg_stagetwo', help='Only show stocks in Stage-2 uptrend')
    c4.checkbox('Use EMA (instead of SMA)', value=bool(_sc.get('useEMA', configManager.useEMA)),
                key='cfg_useema')

    st.button('💾 Save Screening Configuration', on_click=on_config_change,
              type='primary', use_container_width=True)

    st.markdown('<p class="section-header">Import Configuration</p>', unsafe_allow_html=True)
    st.divider()
    uploaded_file = st.file_uploader('Upload screenipy.ini', label_visibility='collapsed')
    if uploaded_file is not None:
        with open('screenipy.ini', 'wb') as f:
            f.write(uploaded_file.getvalue())
        st.toast('Configuration imported!', icon='⚙️')

    # ── LLM Configuration ────────────────────────────────────────────────────
    _load_llm_defaults_from_yaml()
    st.markdown('<p class="section-header">LLM Configuration (AI Native Tab)</p>', unsafe_allow_html=True)
    st.divider()
    st.caption('Config saved to browser localStorage (primary) and screenipy.yaml (CLI fallback). API key is session-only unless you enable "Remember API key" below.')

    lc1, lc2 = st.columns(2)
    lc1.selectbox(
        'Provider',
        options=['openai', 'anthropic', 'openai-compatible'],
        index=['openai', 'anthropic', 'openai-compatible'].index(
            st.session_state.get('ai_provider', 'openai')),
        key='ai_provider',
        help='Select your LLM provider',
    )
    lc2.text_input(
        'Model',
        key='ai_model',
    )

    api_key_val = st.text_input(
        'API Key',
        type='password',
        key='ai_api_key',
        help='Your API key — optionally remembered in browser localStorage if you enable the checkbox below.',
    )
    if api_key_val:
        st.caption('✅ API key is set for this session.')
    else:
        st.caption('⚠️ No API key set. The AI Native tab will not be able to run agents.')

    st.checkbox(
        'Remember API key on this device (stored in browser localStorage — only enable on trusted devices)',
        value=st.session_state.get('ai_remember_key', False),
        key='ai_remember_key',
        help='When enabled, your API key is persisted in this browser localStorage. '
             'Only use this on devices you trust and control.',
    )

    if st.session_state.get('ai_provider') == 'openai-compatible':
        st.text_input(
            'Base URL',
            key='ai_base_url',
            help='Base URL for OpenAI-compatible endpoint (e.g., Ollama)',
        )

    if st.button('💾 Save LLM Config', key='save_llm_btn', type='primary'):
        _save_llm_config_to_yaml()

    # ── Persona Editor ───────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Agent Personas</p>', unsafe_allow_html=True)
    st.divider()
    st.caption('Create, edit, or delete AI agent personas. Tool selection updates the YAML automatically.')

    _ALL_TOOLS_LIST = [
        'screen_breakout', 'screen_volume_breakout', 'screen_consolidation',
        'screen_rsi', 'screen_reversal', 'screen_chart_patterns', 'screen_vcp',
        'screen_momentum', 'screen_narrow_range', 'screen_ipo_base',
        'screen_confluence', 'screen_ma_reversal', 'screen_rsi_ma_cross',
    ]

    try:
        import yaml as _yaml
        from agents.agent_loader import AgentLoader as _AgentLoader
        _personas_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents', 'personas')
        _loader = _AgentLoader(_personas_dir)
        _all_personas = _loader.load_all()
        _persona_names = [p.get('name', 'Unknown') for p in _all_personas]
        _persona_files = _loader.list_persona_files()

        _edit_options = ['+ New Persona'] + _persona_names
        _selected_edit = st.selectbox('Select Persona to Edit', _edit_options, key='pe_selector')

        # Determine current persona data
        if _selected_edit == '+ New Persona':
            _current = {
                'name': 'MyPersona',
                'description': 'Describe what this persona does',
                'instructions': 'You are a ... analyst. Screen for ...\n',
                'tools': ['screen_breakout', 'screen_rsi', 'screen_momentum'],
                'index': 'Nifty 500',
            }
            _existing_file = None
        else:
            _pidx = _persona_names.index(_selected_edit)
            _existing_file = _persona_files[_pidx]
            with open(_existing_file, 'r') as _f:
                _current = _yaml.safe_load(_f.read()) or {}

        # Layout: left = structured fields + tool picker, right = instructions text area
        pe_left, pe_right = st.columns([1, 2])

        with pe_left:
            _pe_name = st.text_input('Persona Name', value=_current.get('name', ''), key='pe_name')
            _pe_desc = st.text_input('Description', value=_current.get('description', ''), key='pe_desc')

            _index_opts = ['Nifty 50', 'Nifty 100', 'Nifty 200', 'Nifty 500',
                           'Nifty Midcap 100', 'Nifty Smallcap 100', 'Nifty Microcap 250']
            _curr_idx = _current.get('index', 'Nifty 500')
            _idx_sel = _index_opts.index(_curr_idx) if _curr_idx in _index_opts else 3
            _pe_index = st.selectbox('Default Index', _index_opts, index=_idx_sel, key='pe_index')

            _curr_tools = _current.get('tools', [])
            _pe_tools = st.multiselect(
                'Allowed Tools',
                options=_ALL_TOOLS_LIST,
                default=[t for t in _curr_tools if t in _ALL_TOOLS_LIST],
                key='pe_tools',
                help='The agent will only be able to call the selected screening tools.',
            )

        with pe_right:
            _pe_instructions = st.text_area(
                'Instructions',
                value=_current.get('instructions', ''),
                height=260,
                key='pe_instructions',
                help='System prompt for the agent persona. Be specific about strategy, criteria, and output format.',
                placeholder=(
                    'You are a momentum analyst...\n'
                    'Screen for stocks with RSI > 60 and volume expansion...\n'
                    'For each stock provide: entry, stop loss, target.'
                ),
            )

            _preview_yaml = {
                'name': _pe_name,
                'description': _pe_desc,
                'instructions': _pe_instructions,
                'tools': _pe_tools,
                'index': _pe_index,
            }

            with st.expander('Preview YAML', expanded=False):
                st.code(_yaml.dump(_preview_yaml, default_flow_style=False, allow_unicode=True), language='yaml')

        # Save / Delete buttons
        btn_col1, btn_col2 = st.columns([3, 1])
        _save_label = '💾 Save New Persona' if _selected_edit == '+ New Persona' else '💾 Save Changes'
        if btn_col1.button(_save_label, key='pe_save', type='primary'):
            try:
                if not _pe_name.strip():
                    st.error('Persona name cannot be empty.')
                else:
                    _to_save = {
                        'name': _pe_name.strip(),
                        'description': _pe_desc.strip(),
                        'instructions': _pe_instructions,
                        'tools': _pe_tools,
                        'index': _pe_index,
                    }
                    if _existing_file:
                        _save_path = _existing_file
                    else:
                        _fname = _pe_name.strip().lower().replace(' ', '_')
                        _save_path = os.path.join(_personas_dir, f'{_fname}.yaml')
                    with open(_save_path, 'w') as _f:
                        _yaml.dump(_to_save, _f, default_flow_style=False, allow_unicode=True)
                    st.toast(f'Persona "{_pe_name}" saved!', icon='🎭')
                    st.rerun()
            except Exception as _e:
                st.error(f'Could not save persona: {_e}')

        if _selected_edit != '+ New Persona':
            if btn_col2.button('🗑️ Delete', use_container_width=True, key='pe_delete'):
                os.remove(_existing_file)
                st.toast(f'Persona "{_selected_edit}" deleted.', icon='🗑️')
                st.rerun()

    except Exception as _e:
        st.warning(f'Persona editor unavailable: {_e}')

    # ── Reset All Settings ──────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Reset</p>', unsafe_allow_html=True)
    st.divider()
    with st.popover('🗑️ Reset All Settings', use_container_width=False):
        st.warning(
            'This will clear all browser-stored config and LLM settings. '
            'Defaults will reload from screenipy.ini / screenipy.yaml on next page load.'
        )
        if st.button('⚠️ Confirm Reset', type='primary', key='confirm_reset_btn'):
            BrowserConfigStore.clear_all()
            st.success('All browser settings cleared. Reload the page to apply defaults.')

# ── Position Size Calculator ───────────────────────────────────────────────────
with tab_psc:
    left_col, result_col = st.columns([1, 1])

    with left_col:
        st.markdown('## 💸 Position Size Calculator')
        st.caption('Calculate the right quantity to risk a fixed percentage of your capital.')
        st.divider()

        capital = st.number_input('Capital Size (₹)', min_value=0, value=100000,
                                  help='Total amount available for this trade/investment')
        if capital:
            st.caption(f"Your capital: **Rs. {num2words(capital, lang='en_IN').title()}**")

        risk = st.number_input('Risk on Capital (%)', min_value=0.0, max_value=10.0,
                               step=0.1, value=0.5,
                               help='Max % of capital to lose if stoploss is hit. Keep ≤ 2%.')
        if risk:
            risk_rs = capital * (risk / 100.0)
            st.caption(f"Max loss for this trade: **Rs. {num2words(risk_rs, lang='en_IN').title()}**")

        st.divider()

        sl = st.number_input('Stoploss in Points (₹)', min_value=0.0, step=0.1,
                             help='Distance from entry to stoploss in rupees per share')

        st.markdown('<center><b>— OR —</b></center>', unsafe_allow_html=True)

        p1, p2 = st.columns(2)
        price = p1.number_input('Entry Price (₹)', min_value=0.0)
        pct_sl = p2.number_input('Stoploss (%)', min_value=0.0, max_value=100.0, value=5.0)

        calc_btn = st.button('📐 Calculate Quantity', type='primary', use_container_width=True)

    with result_col:
        st.markdown('## Result')
        st.divider()
        if calc_btn:
            if sl > 0:
                qty = floor(risk_rs / sl)
                result_col.metric('Quantity', qty, delta=f'Max Loss: ₹{qty * sl:.0f}', delta_color='inverse')
            elif price > 0 and pct_sl > 0:
                actual_sl = round(price * (pct_sl / 100), 2)
                qty = floor(risk_rs / actual_sl)
                result_col.metric('Quantity', qty, delta=f'Max Loss: ₹{qty * actual_sl:.0f}', delta_color='inverse')
            else:
                result_col.info('Enter stoploss values above and click Calculate.')
        else:
            result_col.info('Fill in the fields on the left and click **Calculate Quantity**.')

# ── About ──────────────────────────────────────────────────────────────────────
with tab_about:
    from classes.Changelog import VERSION, changelog

    st.markdown(f'## ℹ️ About Screeni-py v{VERSION}')
    st.divider()

    info_col, video_col = st.columns([2, 1])
    info_col.info("""
**👨🏻‍💻 Developer:** Pranjal Joshi

**🏠 Home Page:** https://github.com/pranjal-joshi/Screeni-py

**⚠️ Issues:** https://github.com/pranjal-joshi/Screeni-py/issues

**📣 Discussions:** https://github.com/pranjal-joshi/Screeni-py/discussions

**⬇️ Latest Release:** https://github.com/pranjal-joshi/Screeni-py/releases/latest

**💬 Telegram:** https://t.me/+0Tzy08mR0do0MzNl

**🎬 YouTube:** [Watch Playlist](https://youtube.com/playlist?list=PLsGnKKT_974J3UVS8M6bxqePfWLeuMsBi)
    """)

    video_col.write(
        '<iframe width="100%" height="240" src="https://www.youtube.com/embed/videoseries?list=PLsGnKKT_974J3UVS8M6bxqePfWLeuMsBi" '
        'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.warning(
        "**Disclaimer:** This tool is for analysis and study purposes only. "
        "We do **not** provide Buy/Sell advice for any securities. "
        "Authors will not be held liable for any financial losses. "
        "Please understand the risks of market investing before trading.",
        icon="⚠️",
    )

    st.divider()

    # ── Changelog — collapsible per version ────────────────────────────────────
    st.markdown('### ⚙️ Changelog')

    # Strip ANSI escape sequences and the outer header from the raw changelog string
    import re as _re
    _ansi_escape = _re.compile(r'\x1b\[[0-9;]*m')
    _raw_log = _ansi_escape.sub('', changelog)
    # Remove the leading "[ChangeLog]\n" banner (everything before the first version block)
    _first_bracket = _raw_log.find('[', _raw_log.find('[') + 1)  # second '[' = first version
    _raw_log = _raw_log[_first_bracket:].strip()

    # Parse into (version_label, [item_lines]) tuples
    _blocks = []
    _current_ver = None
    _current_items = []
    for _line in _raw_log.splitlines():
        _line = _line.strip()
        if not _line:
            continue
        _ver_match = _re.match(r'^\[([^\]]+)\]', _line)
        if _ver_match:
            if _current_ver is not None:
                _blocks.append((_current_ver, _current_items))
            _current_ver = _ver_match.group(1)
            _current_items = []
        else:
            _current_items.append(_line)
    if _current_ver is not None:
        _blocks.append((_current_ver, _current_items))

    # Controls row
    _ctrl_left, _ctrl_right = st.columns([1, 5])
    _expand_all = _ctrl_left.toggle('Expand All', value=False, key='cl_expand_all')

    # Render one expander per version (newest first — already ordered that way)
    for _i, (_ver, _items) in enumerate(_blocks):
        _is_latest = (_i == 0)
        _label = f'v{_ver}' + (' ✦ Latest' if _is_latest else '')
        with st.expander(_label, expanded=(_is_latest or _expand_all)):
            for _item in _items:
                # Numbered items → keep as-is; blank guards already stripped
                st.markdown(_item)

