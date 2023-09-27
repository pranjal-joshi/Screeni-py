import streamlit as st
import streamlit.components.v1 as components
import requests
import os
import sys
import subprocess
import configparser
import urllib
from time import sleep
from pathlib import Path
import classes.ConfigManager as ConfigManager

st.set_page_config(layout="wide", page_title="Screeni-py", page_icon="📈")

# Set protobuf to python to avoid TF error (This is a Slower infernece)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["TERM"] = "xterm"

import pandas as pd
from screenipy import main as screenipy_main
from classes.OtaUpdater import OTAUpdater
from classes.Changelog import VERSION

# Get system wide proxy for networking
try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

isDevVersion, guiUpdateMessage = OTAUpdater.checkForUpdate(proxyServer, VERSION)

execute_inputs = []

def on_config_change():
    configManager = ConfigManager.tools()
    configManager.period = period
    configManager.daysToLookback = daystolookback
    configManager.duration = duartion
    configManager.minLTP, configManager.maxLTP = minprice, maxprice
    configManager.volumeRatio, configManager.consolidationPercentage = volumeratio, consolidationpercentage
    configManager.shuffle = shuffle
    configManager.cacheEnabled = cache
    configManager.stageTwo = stagetwo
    configManager.useEMA = useema
    configManager.setConfig(configparser.ConfigParser(strict=False), default=True, showFileCreatedText=False)
    st.toast('Configuration Saved', icon='💾')

def on_start_button_click():
    global execute_inputs
    st.info(f'Received inputs (Debug only): {execute_inputs}')
    with st.spinner('Screening stocks for you...'):
      # with patch('builtins.input', side_effect=execute_inputs):
        try:
            screenipy_main(execute_inputs=execute_inputs)
        except StopIteration:
            pass

def get_extra_inputs(tickerOption, executeOption, c_index=None, c_criteria=None, start_button=None):
    global execute_inputs
    if not tickerOption.isnumeric():
        execute_inputs = [tickerOption, 0, 'N']
    elif int(tickerOption) == 0 or tickerOption is None:
        stock_codes = c_index.text_input('Enter Stock Code(s) (Multiple codes should be seperated by ,)', placeholder='SBIN, INFY, ITC')
        if stock_codes:
            execute_inputs = [tickerOption, executeOption, stock_codes, 'N']
        else:
            c_index.error("Stock codes can't be left blank!")
    elif int(executeOption) >= 0 and int(executeOption) < 4:
        execute_inputs = [tickerOption, executeOption, 'N']
    elif int(executeOption) == 4:
        num_candles = c_criteria.text_input('The Volume should be lowest since last how many candles?', value='20')
        if num_candles:
            execute_inputs = [tickerOption, executeOption, num_candles, 'N']
        else:
            c_criteria.error("Number of Candles can't be left blank!")    
    elif int(executeOption) == 5:
        min_rsi, max_rsi = c_criteria.columns((1,1))
        min_rsi = min_rsi.number_input('Min RSI', min_value=0, max_value=100, value=50, step=1, format="%d")
        max_rsi = max_rsi.number_input('Max RSI', min_value=0, max_value=100, value=70, step=1, format="%d")
        if min_rsi >= max_rsi:
            c_criteria.warning('WARNING: Min RSI ≥ Max RSI')
        else:
            execute_inputs = [tickerOption, executeOption, min_rsi, max_rsi, 'N']
    elif int(executeOption) == 6:
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
    elif int(executeOption) == 7:
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

ac, bc = st.columns([13,1])

ac.title('📈 Screeni-py')
ac.subheader('in Beta Release 🚧  (Scan QR to Report Bugs / Request Features)')

if isDevVersion:
    ac.warning(guiUpdateMessage, icon='⚠️')
elif guiUpdateMessage != "":
    ac.success(guiUpdateMessage, icon='❇️')

telegram_url = "https://user-images.githubusercontent.com/6128978/217814499-7934edf6-fcc3-46d7-887e-7757c94e1632.png"
bc.divider()
bc.image(telegram_url, width=96)

tab_screen, tab_config, tab_about = st.tabs(['Screen Stocks', 'Configuration', 'About'])

with tab_screen:
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
    # 'W > Screen stocks from my own Watchlist',
    # 'N > Nifty Prediction using Artifical Intelligence (Use for Gap-Up/Gap-Down/BTST/STBT)',
    # 'E > Live Index Scan : 5 EMA for Intraday',
    # '0 > Screen stocks by the stock names (NSE Stock Code)',
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
    st.toast('Screening Completed!', icon='🎉')
    sleep(2)

  with st.container():
      try:
        df = pd.read_pickle('last_screened_unformatted_results.pkl')
        st.markdown(f'#### Found {len(df)} Results')
        df.index = df.index.map(lambda x: "https://in.tradingview.com/chart?symbol=NSE%3A" + x)
        df.index = df.index.map(lambda x: f'<a href="{x}" target="_blank">{x.split("%3A")[-1]}</a>')
        df['Stock'] = df.index
        stock_column = df.pop('Stock')  # Remove 'Age' column and store it separately
        df.insert(0, 'Stock', stock_column)
        st.write(df.to_html(escape=False, index=False, index_names=False), unsafe_allow_html=True)
        st.write(' ')
      except FileNotFoundError:
        st.error('Last Screened results are not available at the moment')
      except Exception as e:
        st.error('No Dataframe found for last_screened_results.pkl')
        st.exception(e)

with tab_config:
  configManager = ConfigManager.tools()
  configManager.getConfig(parser=ConfigManager.parser)

  ac, bc = st.columns([10,2])
  ac.markdown('### Screening Configuration')
  bc.download_button(
    label="Export Configuration",
    data=Path('screenipy.ini').read_text(),
    file_name='screenipy.ini',
    mime='text/plain',
    type='primary',
    use_container_width=True
)

  ac, bc, cc = st.columns([1,1,1])

  period = ac.text_input('Period', value=f'{configManager.period}', placeholder='300d / 52wk ')
  daystolookback = bc.number_input('Lookback Period (Number of Candles)', value=configManager.daysToLookback, step=1)
  duartion = cc.text_input('Candle Duration', value=f'{configManager.duration}', placeholder='15m / 1d / 1wk')

  ac, bc = st.columns([1,1])
  minprice = ac.number_input('Minimum Price (Stocks below this will be ignored)', value=float(configManager.minLTP), step=0.1)
  maxprice = bc.number_input('Maximum Price (Stocks above this will be ignored)', value=float(configManager.maxLTP), step=0.1)

  ac, bc = st.columns([1,1])
  volumeratio = ac.number_input('Volume multiplier for Breakout confirmation', value=float(configManager.volumeRatio), step=0.1)
  consolidationpercentage = bc.number_input('Range consolidation (%)', value=int(configManager.consolidationPercentage), step=1)

  ac, bc, cc, dc = st.columns([1,1,1,1])
  shuffle = ac.checkbox('Shuffle stocks while screening', value=configManager.shuffleEnabled, disabled=True)
  cache = bc.checkbox('Enable caching of stock data after market hours', value=configManager.cacheEnabled, disabled=True)
  stagetwo = cc.checkbox('Screen only for Stage-2 stocks', value=configManager.stageTwo)
  useema = dc.checkbox('Use EMA instead of SMA', value=configManager.useEMA)

  save_button = st.button('Save Configuration', on_click=on_config_change, type='primary', use_container_width=True)
  
  st.markdown('### Import Your Own Configuration:')
  uploaded_file = st.file_uploader('Upload screenipy.ini file')

  if uploaded_file is not None:      
    bytes_data = uploaded_file.getvalue()
    with open('screenipy.ini', 'wb') as f: 
      f.write(bytes_data)
    st.toast('Configuration Imported', icon='⚙️')

with tab_about:
  from classes.Changelog import VERSION, changelog

  st.success(f'Screeni-py v{VERSION}', icon='🔍')
  st.info("""
👨🏻‍💻 Developed and Maintained by: Pranjal Joshi
          
🏠 Home Page: https://github.com/pranjal-joshi/Screeni-py
          
⚠️ Read/Post Issues here: https://github.com/pranjal-joshi/Screeni-py/issues
          
📣 Join Community Discussions: https://github.com/pranjal-joshi/Screeni-py/discussions
          
⬇️ Download latest software from https://github.com/pranjal-joshi/Screeni-py/releases/latest
          
💬 Join Telegram Group for discussion: https://t.me/+0Tzy08mR0do0MzNl
          
🎬 YouTube Playlist: https://youtube.com/playlist?list=PLsGnKKT_974J3UVS8M6bxqePfWLeuMsBi&si=b6JNMf03IbA_SsXs
          """)
  st.warning("ChangeLog:\n " + changelog[40:-3], icon='⚙️')
        
    

marquee_html = '''
<!DOCTYPE html>
<html>
<head>
	<style>
		.sampleMarquee {
			color: #f63366;
			font-family: 'Ubuntu Mono', monospace;
			background-color: #ffffff;
			font-size: 18px;
			line-height: 30px;
			padding: px;
			font-weight: bold;
		}
	</style>
</head>
<body>
	<marquee class="sampleMarquee" direction="left" scrollamount="7" behavior="scroll">Released in Development mode. This tool should be used only for analysis/study purposes. We do NOT provide any Buy/Sell advice for any Securities. Authors of this tool will not be held liable for any losses. Understand the Risks subjected with Markets before Investing.</marquee>
</body>
</html>
'''
components.html(marquee_html)