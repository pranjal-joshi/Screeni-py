import streamlit as st
import requests
import os
import sys
import subprocess

# check if the library folder already exists, to avoid building everytime you load the pahe
if not os.path.isdir("/tmp/ta-lib"):

    # Download ta-lib to disk
    with open("/tmp/ta-lib-0.4.0-src.tar.gz", "wb") as file:
        response = requests.get(
            "http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz"
        )
        file.write(response.content)
    # get our current dir, to configure it back again. Just house keeping
    default_cwd = os.getcwd()
    os.chdir("/tmp")
    # untar
    os.system("tar -zxvf ta-lib-0.4.0-src.tar.gz")
    os.chdir("/tmp/ta-lib")
    os.system("ls -la /app/equity/")
    # build
    os.system("./configure --prefix=/home/appuser")
    os.system("make")
    # install
    os.system("make install")
    # back to the cwd
    os.chdir(default_cwd)
    sys.stdout.flush()

# add the library to our current environment
from ctypes import *

lib = CDLL("/home/appuser/lib/libta_lib.so.0.0.0")
# import library
try:
    import talib
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--global-option=build_ext", "--global-option=-L/home/appuser/lib/", "--global-option=-I/home/appuser/include/", "ta-lib==0.4.24", "protobuf==3.20.0"])
finally:
    import talib

import streamlit as st
import pandas as pd
from unittest.mock import patch
from screenipy import main as screenipy_main

execute_inputs = []

def on_start_button_click():
    global execute_inputs
    my_bar = st.progress(0, text="Starting Stocks Screening...")
    with patch('builtins.input', side_effect=execute_inputs):
        try:
            screenipy_main()
        except StopIteration:
            pass
    for percent_complete in range(100):
        progress_text = f'Screening stocks: {percent_complete}/100'
        my_bar.progress(percent_complete + 1, text=progress_text)
    my_bar.empty()

def get_extra_inputs(tickerOption, executeOption, c_index=None, c_criteria=None, start_button=None):
    global execute_inputs
    if int(tickerOption) == 0:
        stock_codes = c_index.text_input('Enter Stock Code(s) (Multiple codes should be seperated by ,)', placeholder='SBIN, INFY, ITC')
        if stock_codes:
            execute_inputs = [tickerOption, executeOption, stock_codes, 'N']
        else:
            c_index.error("Stock codes can't be left blank!")
    if int(executeOption) == 4:
        num_candles = c_criteria.text_input('The Volume should be lowest since last how many candles?', value='20')
        if num_candles:
            execute_inputs = [tickerOption, executeOption, num_candles, 'N']
        else:
            c_criteria.error("Number of Candles can't be left blank!")    
    if int(executeOption) == 5:
        min_rsi, max_rsi = c_criteria.columns((1,1))
        min_rsi = min_rsi.number_input('Min RSI', min_value=0, max_value=100, value=50, step=1, format="%d")
        max_rsi = max_rsi.number_input('Max RSI', min_value=0, max_value=100, value=70, step=1, format="%d")
        if min_rsi >= max_rsi:
            c_criteria.warning('WARNING: Min RSI ≥ Max RSI')
        else:
            execute_inputs = [tickerOption, executeOption, min_rsi, max_rsi, 'N']
    if int(executeOption) == 6:
        c1, c2 = c_criteria.columns((7,2))
        select_reversal = int(c1.selectbox('Select Type of Reversal',
                            options = [
                                '1 > Buy Signal (Bullish Reversal)',
                                '2 > Sell Signal (Bearish Reversal)',
                                '3 > Momentum Gainers (Rising Bullish Momentum)',
                                '4 > Reversal at Moving Average (Bullish Reversal)',
                                '5 > Volume Spread Analysis (Bullish VSA Reversal)',
                                '6 > Narrow Range (NRx) Reversal',
                            ]
                        ).split(' ')[0])
        if select_reversal == 4:
            ma_length = c2.number_input('MA Length', value=50, step=1, format="%d")
            execute_inputs = [tickerOption, executeOption, select_reversal, ma_length, 'N']
        elif select_reversal == 6:
            range = c2.number_input('NR(x)',min_value=1, max_value=14, value=4, step=1, format="%d")
            execute_inputs = [tickerOption, executeOption, select_reversal, range, 'N']
        else:
            execute_inputs = [tickerOption, executeOption, select_reversal, 'N']
    if int(executeOption) == 7:
        c1, c2 = c_criteria.columns((11,4))
        select_pattern = int(c1.selectbox('Select Chart Pattern',
                            options = [
                                '1 > Bullish Inside Bar (Flag) Pattern',
                                '2 > Bearish Inside Bar (Flag) Pattern',
                                '3 > Confluence (50 & 200 MA/EMA)',
                                '4 > VCP (Experimental)',
                                '5 > Buying at Trendline (Ideal for Swing/Mid/Long term)',
                            ]
                        ).split(' ')[0])
        if select_pattern == 1 or select_pattern == 2:
            num_candles = c2.number_input('Lookback Candles', min_value=1, max_value=25, value=12, step=1, format="%d")
            execute_inputs = [tickerOption, executeOption, select_pattern, num_candles, 'N']
        elif select_pattern == 3:
            confluence_percentage = c2.number_input('MA Confluence %', min_value=0.1, max_value=3.0, value=1.0, step=0.1, format="%1.1f")
            execute_inputs = [tickerOption, executeOption, select_pattern, confluence_percentage, 'N']
        else:
            execute_inputs = [tickerOption, executeOption, select_pattern, 'N']



            

    

st.set_page_config(layout="wide")

st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
                .stButton>button {
                    height: 70px;
                }
                th {
                    text-align: left;
                }
        </style>
        """,
        unsafe_allow_html=True)

st.title('Screeni-py: UI Development')

ticker_tape_url = '''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <div class="tradingview-widget-copyright"><a href="https://in.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
  {
  "symbols": [
    {
      "description": "NIFTY 50",
      "proName": "NSE:NIFTY"
    },
    {
      "description": "NIFTY BANK",
      "proName": "NSE:BANKNIFTY"
    },
    {
      "description": "NIFTY IT",
      "proName": "NSE:CNXIT"
    },
    {
      "description": "NIFTY PHARMA",
      "proName": "NSE:CNXPHARMA"
    },
    {
      "description": "NIFTY METAL",
      "proName": "NSE:CNXMETAL"
    },
    {
      "description": "NIFTY AUTO",
      "proName": "NSE:CNXAUTO"
    },
    {
      "description": "NIFTY ENERGY",
      "proName": "NSE:CNXENERGY"
    },
    {
      "description": "NIFTY MIDCAP",
      "proName": "NSE:NIFTYMIDCAP50"
    },
    {
      "description": "NIFTY SMALLCAP",
      "proName": "NSE:CNXSMALLCAP"
    },
    {
      "description": "SENSEX",
      "proName": "BSE:SENSEX"
    }
  ],
  "showSymbolLogo": true,
  "colorTheme": "light",
  "isTransparent": false,
  "displayMode": "adaptive",
  "locale": "in"
}
  </script>
</div>
<!-- TradingView Widget END -->'''

# components.html(ticker_tape_url)

list_index = [
  'All Stocks (Default)',
  'W > Screen stocks from my own Watchlist',
  'N > Nifty Prediction using Artifical Intelligence (Use for Gap-Up/Gap-Down/BTST/STBT)',
  'E > Live Index Scan : 5 EMA for Intraday',
  '0 > Screen stocks by the stock names (NSE Stock Code)',
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
  '13 > Newly Listed (IPOs in last 2 Year)',
  '14 > F&O Stocks Only',
]

list_criteria = [
    '0 > Full Screening (Shows Technical Parameters without Any Criteria)',
    '1 > Screen stocks for Breakout or Consolidation',
    '2 > Screen for the stocks with recent Breakout & Volume',
    '3 > Screen for the Consolidating stocks',
    '4 > Screen for the stocks with Lowest Volume in last N-days (Early Breakout Detection)',
    '5 > Screen for the stocks with RSI',
    '6 > Screen for the stocks showing Reversal Signals',
    '7 > Screen for the stocks making Chart Patterns',
]

c_index, c_criteria, c_button_start = st.columns((4,4,1))

tickerOption = c_index.selectbox('Select Index', options=list_index).split(' ')
tickerOption = str(12 if '>' not in tickerOption else int(tickerOption[0]) if tickerOption[0].isnumeric() else str(tickerOption[0]))
executeOption = str(c_criteria.selectbox('Select Screening Criteria', options=list_criteria).split(' ')[0])

start_button = c_button_start.button('Start Screening', type='primary', key='start_button')

get_extra_inputs(tickerOption=tickerOption, executeOption=executeOption, c_index=c_index, c_criteria=c_criteria, start_button=start_button)

if start_button:
   on_start_button_click()

with st.container():
    try:
      df = pd.read_pickle('last_screened_unformatted_results.pkl')
      st.markdown(f'#### {len(df)} Results')
      df.index = df.index.map(lambda x: "https://in.tradingview.com/chart?symbol=NSE%3A" + x)
      df.index = df.index.map(lambda x: f'<a href="{x}" target="_blank">{x.split("%3A")[-1]}</a>')
      df['Stock'] = df.index
      stock_column = df.pop('Stock')  # Remove 'Age' column and store it separately
      df.insert(0, 'Stock', stock_column)
      st.write(df.to_html(escape=False, index=False, index_names=False), unsafe_allow_html=True)
    except Exception as e:
      st.error('No Dataframe found for last_screened_results.pkl')
      st.exception(e)
