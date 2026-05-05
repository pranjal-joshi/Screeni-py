"""
Classic Tab UI for Screeni-py Streamlit app.
Extracts the existing classic screening workflow into a reusable module.
100% functional parity with the original streamlit_app.py classic mode.
"""
import os
import sys
import random
import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import classes.ConfigManager as ConfigManager
import classes.Utility as Utility
import classes.Fetcher as Fetcher
from ui.charts import plot_ohlc_chart, plot_screening_summary


def render():
    """
    Render the Classic screening tab in the Streamlit UI.
    This is a functional extraction of the original streamlit_app.py rendering logic,
    with the results table updated to use st.dataframe for broader compatibility.
    """
    configManager = ConfigManager.tools()

    # ---- Results section ----
    _render_results(configManager)


def _render_results(configManager):
    """Render the last screened results table."""
    # Try loading from SQLite first (primary), then pickle (fallback)
    df = None
    try:
        from classes.Database import ScreeniDatabase
        db = ScreeniDatabase()
        df = db.get_last_scan_results(criteria='last_screened')
    except Exception:
        pass

    if df is None:
        try:
            df = pd.read_pickle('last_screened_unformatted_results.pkl')
        except FileNotFoundError:
            pass

    if df is None or df.empty:
        st.info("📊 No screening results yet. Run a scan first using the Classic mode controls below.")
        return

    # Action bar
    ac, cc, bc = st.columns([6, 1, 1])
    ac.markdown(f'#### 🔍 Found {len(df)} Results')

    clear_cache_btn = cc.button(
        label='Clear Cached Data',
        use_container_width=True,
        key=f'clear_cache_{random.randint(1, 999999999)}',
    )
    if clear_cache_btn:
        os.system('rm -f stock_data_*.pkl')
        st.toast('Stock Cache Deleted!', icon='🗑️')

    bc.download_button(
        label="Download Results",
        data=df.to_csv().encode('utf-8'),
        file_name=f'screenipy_results_{datetime.datetime.now().strftime("%H:%M:%S_%d-%m-%Y")}.csv',
        mime='text/csv',
        type='secondary',
        use_container_width=True,
    )

    # Results table - use st.dataframe for modern rendering
    st.dataframe(df, use_container_width=True)

    # ---- Summary chart ----
    with st.expander("📊 Trend Summary Chart", expanded=False):
        summary_fig = plot_screening_summary(df)
        st.plotly_chart(summary_fig, use_container_width=True)

    # ---- Stock Detail View ----
    with st.expander("🕯️ Stock OHLC Chart", expanded=False):
        _render_stock_detail(df, configManager)


def _render_stock_detail(results_df: pd.DataFrame, configManager):
    """Render a stock detail view with OHLC chart."""
    # Get list of stocks from results
    stock_col = None
    if 'Stock' in results_df.columns:
        stock_col = 'Stock'
    elif results_df.index.name == 'Stock':
        stock_col = None  # index

    stocks = []
    if stock_col:
        stocks = results_df['Stock'].tolist()
    else:
        stocks = results_df.index.tolist()

    if not stocks:
        st.info("No stocks available for charting.")
        return

    selected_stock = st.selectbox("Select stock to chart:", stocks, key='classic_stock_selector')

    if selected_stock and st.button("Load Chart", key='classic_load_chart'):
        with st.spinner(f"Loading {selected_stock} data..."):
            try:
                import yfinance as yf
                ticker = selected_stock + ".NS"
                data = yf.download(ticker, period=configManager.period, interval=configManager.duration, progress=False)
                if data is not None and not data.empty:
                    # Add SMA/LMA
                    data['SMA'] = data['Close'].rolling(window=50).mean()
                    data['LMA'] = data['Close'].rolling(window=200).mean()
                    data['VolMA'] = data['Volume'].rolling(window=20).mean()

                    ohlc_fig = plot_ohlc_chart(data, selected_stock)
                    st.plotly_chart(ohlc_fig, use_container_width=True)
                else:
                    st.error(f"No data available for {selected_stock}")
            except Exception as e:
                st.error(f"Failed to load chart: {e}")
