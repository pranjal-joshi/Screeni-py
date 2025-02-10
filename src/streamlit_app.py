import random
import streamlit as st
import streamlit.components.v1 as components
import requests
import os
import configparser
import urllib
import datetime
from num2words import num2words
from time import sleep
from pathlib import Path
from threading import Thread
from time import sleep
from math import floor
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import classes.ConfigManager as ConfigManager
import classes.Utility as Utility
import classes.Fetcher as Fetcher

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

# Start webserver to serve static files - js/css
def start_static_file_server():

  class ThreadedHTTPServer(TCPServer):
      allow_reuse_address = True  # Allow immediate reuse of the address

  server = ThreadedHTTPServer(("0.0.0.0", 8000), SimpleHTTPRequestHandler)

  def serve():
      with server: 
          print("Static File WebServer started on port 8000")
          server.serve_forever()

  server_thread = threading.Thread(target=serve, daemon=True)
  server_thread.start()
  return server

try:
  staticFileServer = start_static_file_server()
except OSError as e:
  if e.errno == 98:
    pass
  else:
     raise(e)

isDevVersion, guiUpdateMessage = None, None

@st.cache_data(ttl='1h', show_spinner=False)
def check_updates():
  isDevVersion, guiUpdateMessage = OTAUpdater.checkForUpdate(proxyServer, VERSION)
  return isDevVersion, guiUpdateMessage

isDevVersion, guiUpdateMessage = check_updates()

execute_inputs = []

def show_df_as_result_table():
  try:
    df:pd.DataFrame = pd.read_pickle('last_screened_unformatted_results.pkl')
    ac, cc, bc = st.columns([6,1,1])
    ac.markdown(f'#### 🔍 Found {len(df)} Results')
    clear_cache_btn = cc.button(
       label='Clear Cached Data',
       use_container_width=True,
       key=random.randint(1,999999999),
    )
    if clear_cache_btn:
       os.system('rm stock_data_*.pkl')
       st.toast('Stock Cache Deleted!', icon='🗑️')
    bc.download_button(
        label="Download Results",
        data=df.to_csv().encode('utf-8'),
        file_name=f'screenipy_results_{datetime.datetime.now().strftime("%H:%M:%S_%d-%m-%Y")}.csv',
        mime='text/csv',
        type='secondary',
        use_container_width=True
    )       
    if type(execute_inputs[0]) == str or int(execute_inputs[0]) < 15:
      df.index = df.index.map(lambda x: "https://in.tradingview.com/chart?symbol=NSE%3A" + x)
      df.index = df.index.map(lambda x: f'<a href="{x}" target="_blank">{x.split("%3A")[-1]}</a>')
    elif execute_inputs[0] == '16':
      try:
        fetcher = Fetcher.tools(configManager=ConfigManager.tools())
        url_dict_reversed = {key.replace('^','').replace('.NS',''): value for key, value in fetcher.getAllNiftyIndices().items()}
        url_dict_reversed = {v: k for k, v in url_dict_reversed.items()}
        df.index = df.index.map(lambda x: "https://in.tradingview.com/chart?symbol=NSE%3A" + url_dict_reversed[x])
        url_dict_reversed = {v: k for k, v in url_dict_reversed.items()}
        df.index = df.index.map(lambda x: f'<a href="{x}" target="_blank">{url_dict_reversed[x.split("%3A")[-1]]}</a>')
      except KeyError:
         pass
    else:
      df.index = df.index.map(lambda x: "https://in.tradingview.com/chart?symbol=" + x)
      df.index = df.index.map(lambda x: f'<a href="{x}" target="_blank">{x.split("=")[-1]}</a>')
    df['Stock'] = df.index
    stock_column = df.pop('Stock')  # Remove 'Age' column and store it separately
    df.insert(0, 'Stock', stock_column)
    st.components.v1.html(f"""
      {df.to_html(escape=False, index=False, index_names=False, table_id='resultTable')}
      <script src="http://localhost:8000/static/tablefilter/tablefilter.js"></script>
      <script>
        var filtersConfig = {{
            base_path: 'http://localhost:8000/static/tablefilter/',
            col_0: 'none',
            col_2: 'none',
            col_5: 'checklist',
            col_7: 'checklist',
            col_8: 'checklist',
            sticky_headers: true,
            popup_filters: true,
            auto_filter: {{
                delay: 1000 //ms
            }},
            state: {{
                types: ['local_storage'],				// Possible values: 'local_storage' 'hash' or 'cookie'  
                filters: true,						// Persist filters values, enabled by default  
            }},
            rows_counter: {{
                text: 'Filtered Stocks: ' 
            }},
            btn_reset: true,
            status_bar: true,
            msg_filter: 'Filtering Stocks...',
        }};
        var tf = new TableFilter(document.querySelector('#resultTable'), filtersConfig);
        tf.init();
      </script>
    """, height=500, scrolling=True)
  except FileNotFoundError:
    st.error('Last Screened results are not available at the moment')
  except Exception as e:
    st.error('No Dataframe found for last_screened_results.pkl')
    st.exception(e)

def on_config_change():
    configManager = ConfigManager.tools()
    configManager.period = period
    configManager.daysToLookback = daystolookback
    configManager.duration = duration
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
    if isDevVersion != None:
      st.info(f'Received inputs (Debug only): {execute_inputs}')

    def dummy_call():
      try:
          screenipy_main(execute_inputs=execute_inputs, isDevVersion=isDevVersion, backtestDate=backtestDate)
      except StopIteration:
          pass
      except requests.exceptions.RequestException:
          os.environ['SCREENIPY_REQ_ERROR'] = "TRUE"
    
    if Utility.tools.isBacktesting(backtestDate=backtestDate):
      st.write(f'Running in :red[**Backtesting Mode**] for *T = {str(backtestDate)}* (Y-M-D) : [Backtesting data is subjected to availability as per the API limits]')
      st.write('Backtesting is :red[Not Supported] for Intraday timeframes')
    t = Thread(target=dummy_call)
    t.start()

    st.markdown("""
      <style>
      .stProgress p {
          font-size: 17px;
      }
      </style>
      """, unsafe_allow_html=True)

    progress_text = "🚀 Preparing Screener, Please Wait! "
    progress_bar = st.progress(0, text=progress_text)

    os.environ['SCREENIPY_SCREEN_COUNTER'] = '0'
    while int(os.environ.get('SCREENIPY_SCREEN_COUNTER')) < 100:
      sleep(0.05)
      cnt = int(os.environ.get('SCREENIPY_SCREEN_COUNTER'))
      if cnt > 0:
        progress_text = "🔍 Screening stocks for you... "
        progress_bar.progress(cnt, text=progress_text + f"**:red[{cnt}%]** Done")
      if os.environ.get('SCREENIPY_REQ_ERROR') and "TRUE" in os.environ.get('SCREENIPY_REQ_ERROR'):
        ac, bc = st.columns([2,1])
        ac.error(':disappointed: Failed to reach Screeni-py server!')
        ac.info('This issue is related with your Internet Service Provider (ISP) - Many **Jio** users faced this issue as the screeni-py data cache server appeared to be not reachable for them!\n\nPlease watch the YouTube video attached here to resolve this issue on your local system\n\nTry with another ISP/Network or go through this thread carefully to resolve this error: https://github.com/pranjal-joshi/Screeni-py/issues/164', icon='ℹ️')
        bc.video('https://youtu.be/JADNADDNTmU')
        del os.environ['SCREENIPY_REQ_ERROR']
        break
    
    t.join()
    progress_bar.empty()

def nifty_predict(col):
  with col.container():
    with st.spinner('🔮 Taking a Look into the Future, Please wait...'):
      import classes.Fetcher as Fetcher
      import classes.Screener as Screener
      configManager = ConfigManager.tools()
      fetcher = Fetcher.tools(configManager)
      screener = Screener.tools(configManager)
      os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
      prediction, trend, confidence, data_used = screener.getNiftyPrediction(
          data=fetcher.fetchLatestNiftyDaily(proxyServer=proxyServer), 
          proxyServer=proxyServer
      )
  if 'BULLISH' in trend:
      col.success(f'Market may Open **Gap Up** next day!\n\nProbability/Strength of Prediction = {confidence}%', icon='📈')
  elif 'BEARISH' in trend:
      col.error(f'Market may Open **Gap Down** next day!\n\nProbability/Strength of Prediction = {confidence}%', icon='📉')
  else:
      col.info("Couldn't determine the Trend. Try again later!")
  col.warning('The AI prediction should be executed After 3 PM or Around the Closing hours as the Prediction Accuracy is based on the Closing price!\n\nThis is Just a Statistical Prediction and There are Chances of **False** Predictions!', icon='⚠️')
  col.info("What's New in **v3**?\n\nMachine Learning model (v3) now uses Nifty, Crude and Gold Historical prices to Predict the Gap!", icon='🆕')
  col.markdown("**Following data is used to make above prediction:**")
  col.dataframe(data_used)
      
def find_similar_stocks(stockCode:str, candles:int):
  global execute_inputs
  stockCode = stockCode.upper()
  if ',' in stockCode or ' ' in stockCode or stockCode == '':
    st.error('Invalid Character in Stock Name!', icon='😾')
    return False
  else:
    execute_inputs = ['S', 0, stockCode, candles, 'N']
    on_start_button_click()
    st.toast('Screening Completed!', icon='🎉')
    sleep(2)
  return True

def get_extra_inputs(tickerOption, executeOption, c_index=None, c_criteria=None, start_button=None):
    global execute_inputs
    if not tickerOption.isnumeric():
        execute_inputs = [tickerOption, 0, 'N']
    elif int(tickerOption) == 0 or tickerOption is None:
        stock_codes:str = c_index.text_input('Enter Stock Code(s)', placeholder='SBIN, INFY, ITC')
        execute_inputs = [tickerOption, executeOption, stock_codes.upper(), 'N']
        return
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
                                '7 > Lorentzian Classifier (Machine Learning based indicator)',
                                '8 > RSI Crossing with 9 SMA of RSI itself'
                            ]
                        ).split(' ')[0])
        if select_reversal == 4:
            ma_length = c2.number_input('MA Length', value=44, step=1, format="%d")
            execute_inputs = [tickerOption, executeOption, select_reversal, ma_length, 'N']
        elif select_reversal == 6:
            range = c2.number_input('NR(x)',min_value=1, max_value=14, value=4, step=1, format="%d")
            execute_inputs = [tickerOption, executeOption, select_reversal, range, 'N']
        elif select_reversal == 7:
            signal = int(c2.selectbox('Signal Type',
                            options = [
                                '1 > Any',
                                '2 > Buy',
                                '3 > Sell',
                            ]
                        ).split(' ')[0])
            execute_inputs = [tickerOption, executeOption, select_reversal, signal, 'N']
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
            execute_inputs = [tickerOption, executeOption, select_pattern, int(num_candles), 'N']
        elif select_pattern == 3:
            confluence_percentage = c2.number_input('MA Confluence %', min_value=0.1, max_value=5.0, value=1.0, step=0.1, format="%1.1f")/100.0
            execute_inputs = [tickerOption, executeOption, select_pattern, confluence_percentage, 'N']
        else:
            execute_inputs = [tickerOption, executeOption, select_pattern, 'N']

header_padding = """
        <style>
        header {
        padding-bottom: 16px;
        }
        </style>
        """
st.markdown(header_padding, unsafe_allow_html=True)

ac, bc = st.columns([13,1])

ac.title('📈 Screeni-py')
if guiUpdateMessage == "":
  ac.subheader('Find Breakouts, Just in Time!')

if isDevVersion:
    ac.warning(guiUpdateMessage, icon='⚠️')
elif guiUpdateMessage != "":
    ac.success(guiUpdateMessage, icon='❇️')

telegram_url = "https://user-images.githubusercontent.com/6128978/217814499-7934edf6-fcc3-46d7-887e-7757c94e1632.png"
bc.divider()
bc.image(telegram_url, width=96)

tab_screen, tab_similar, tab_nifty, tab_config, tab_psc, tab_about = st.tabs(['Screen Stocks', 'Search Similar Stocks', 'Nifty-50 Gap Prediction', 'Configuration', 'Position Size Calculator', 'About'])

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
                  .stDownloadButton>button {
                      height: 70px;
                  }
                  th {
                      text-align: left;
                  }
          </style>
          """,
          unsafe_allow_html=True)

  list_index = [
    'All Stocks (Default)',
    # 'W > Screen stocks from my own Watchlist',
    # 'N > Nifty Prediction using Artifical Intelligence (Use for Gap-Up/Gap-Down/BTST/STBT)',
    # 'E > Live Index Scan : 5 EMA for Intraday',
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
    '13 > Newly Listed (IPOs in last 2 Year)',
    '14 > F&O Stocks Only',
    '15 > US S&P 500',
    '16 > Sectoral Indices (NSE)'
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

  configManager = ConfigManager.tools()
  configManager.getConfig(parser=ConfigManager.parser)

  c_index, c_datepick, c_criteria, c_button_start = st.columns((2,1,4,1))

  tickerOption = c_index.selectbox('Select Index', options=list_index).split(' ')
  tickerOption = str(12 if '>' not in tickerOption else int(tickerOption[0]) if tickerOption[0].isnumeric() else str(tickerOption[0]))
  picked_date = c_datepick.date_input(label='Screen/Backtest For', max_value=datetime.date.today(), value=datetime.date.today())
  if picked_date:
     backtestDate = picked_date

  executeOption = str(c_criteria.selectbox('Select Screening Criteria', options=list_criteria).split(' ')[0])

  start_button = c_button_start.button('Start Screening', type='primary', key='start_button', use_container_width=True)

  get_extra_inputs(tickerOption=tickerOption, executeOption=executeOption, c_index=c_index, c_criteria=c_criteria, start_button=start_button)

  if start_button:
    on_start_button_click()
    st.toast('Screening Completed!', icon='🎉')
    sleep(2)

  with st.container():
    show_df_as_result_table()
        
with tab_config:
  configManager = ConfigManager.tools()
  configManager.getConfig(parser=ConfigManager.parser)

  ac, bc = st.columns([10,2])
  ac.markdown('### 🔧 Screening Configuration')
  bc.download_button(
    label="Export Configuration",
    data=Path('screenipy.ini').read_text(),
    file_name='screenipy.ini',
    mime='text/plain',
    type='primary',
    use_container_width=True
)

  ac, bc, cc = st.columns([1,1,1])

  period_options = ['15d','60d','300d','52wk','3y','5y','max']
  duration_options = ['5m','15m','1h','4h','1d','1wk']

  # period = ac.text_input('Period', value=f'{configManager.period}', placeholder='300d / 52wk ')
  period = ac.selectbox('Period', options=period_options, index=period_options.index(configManager.period), placeholder='300d / 52wk')
  daystolookback = bc.number_input('Lookback Period (Number of Candles)', value=configManager.daysToLookback, step=1)
  # duration = cc.text_input('Candle Duration', value=f'{configManager.duration}', placeholder='15m / 1d / 1wk')
  duration = cc.selectbox('Candle Duration', options=duration_options, index=duration_options.index(configManager.duration), placeholder='15m / 1d / 1wk')
  if 'm' in duration or 'h' in duration:
    cc.write('For Intraday duartion, Max :red[value of period <= 60d]')

  ac, bc = st.columns([1,1])
  minprice = ac.number_input('Minimum Price (Stocks below this will be ignored)', value=float(configManager.minLTP), step=0.1)
  maxprice = bc.number_input('Maximum Price (Stocks above this will be ignored)', value=float(configManager.maxLTP), step=0.1)

  ac, bc = st.columns([1,1])
  volumeratio = ac.number_input('Volume multiplier for Breakout confirmation', value=float(configManager.volumeRatio), step=0.1)
  consolidationpercentage = bc.number_input('Range consolidation (%)', value=int(configManager.consolidationPercentage), step=1)

  ac, bc, cc, dc = st.columns([1,1,1,1])
  shuffle = ac.checkbox('Shuffle stocks while screening', value=configManager.shuffleEnabled, disabled=True)
  cache = bc.checkbox('Enable caching of stock data after market hours', value=configManager.cacheEnabled, disabled=True)
  stagetwo = cc.checkbox('Screen only for [Stage-2](https://www.investopedia.com/articles/investing/070715/trading-stage-analysis.asp#:~:text=placed%20stops.-,Stage%202%3A%20Uptrends,-Image%20by%20Sabrina) stocks', value=configManager.stageTwo)
  useema = dc.checkbox('Use EMA instead of SMA', value=configManager.useEMA)

  save_button = st.button('Save Configuration', on_click=on_config_change, type='primary', use_container_width=True)
  
  st.markdown('### Import Your Own Configuration:')
  uploaded_file = st.file_uploader('Upload screenipy.ini file')

  if uploaded_file is not None:      
    bytes_data = uploaded_file.getvalue()
    with open('screenipy.ini', 'wb') as f: 
      f.write(bytes_data)
    st.toast('Configuration Imported', icon='⚙️')

with tab_nifty:
    ac, bc = st.columns([9,1])

    ac.subheader('🧠 AI-based prediction for Next Day Nifty-50 Gap Up / Gap Down')
    bc.button('**Predict**', type='primary', on_click=nifty_predict, args=(ac,), use_container_width=True)

with tab_similar:
   
  st.subheader('🕵🏻 Find Stocks forming Similar Chart Patterns')
  ac, bc, cc = st.columns([4,2,1])   

  stockCode = ac.text_input('Enter Stock Name and Press Enter', placeholder='HDFCBANK')
  candles = bc.number_input('Lookback Period (No. of Candles)', min_value=1, step=1, value=int(configManager.daysToLookback))
  similar_search_button = cc.button('**Search**', type='primary', use_container_width=True)

  if similar_search_button:
    result = find_similar_stocks(stockCode, candles)
    if result:
      with st.container():
        show_df_as_result_table()
        st.write('Click [**here**](https://medium.com/@joshi.pranjal5/spot-your-favourite-trading-setups-using-vector-databases-1651d747fbf0) to know How this Works? 🤔')

with tab_about:
  from classes.Changelog import VERSION, changelog

  st.success(f'Screeni-py v{VERSION}', icon='🔍')
  ac, bc = st.columns([2,1])
  ac.info("""
👨🏻‍💻 Developed and Maintained by: Pranjal Joshi
          
🏠 Home Page: https://github.com/pranjal-joshi/Screeni-py
          
⚠️ Read/Post Issues here: https://github.com/pranjal-joshi/Screeni-py/issues
          
📣 Join Community Discussions: https://github.com/pranjal-joshi/Screeni-py/discussions
          
⬇️ Download latest software from https://github.com/pranjal-joshi/Screeni-py/releases/latest
          
💬 Join Telegram Group for discussion: https://t.me/+0Tzy08mR0do0MzNl
          
🎬 YouTube Playlist: Watch [**Here**](https://youtube.com/playlist?list=PLsGnKKT_974J3UVS8M6bxqePfWLeuMsBi&si=b6JNMf03IbA_SsXs) [![YouTube Channel Subscribers](https://img.shields.io/youtube/channel/subscribers/UCb_4n0rRHCL2dUbmRvS7psA)](https://www.youtube.com/@PranjalJoshi)
          """)
  bc.write('<iframe width="445" height="295" src="https://www.youtube.com/embed/videoseries?si=aKXpyKKgwCcWIjhW&amp;list=PLsGnKKT_974J3UVS8M6bxqePfWLeuMsBi" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>', unsafe_allow_html=True)
  st.warning("ChangeLog:\n " + changelog[40:-3], icon='⚙️')
        
with tab_psc:
  ac, oc = st.columns([1, 1])
  ac, bc = ac.columns([4, 1]) 
  ac.subheader('💸 Position Size Calculator')
  calculate_qty_btn = bc.button('**Calculate Qty**', type='primary', use_container_width=True)

  ac, bc = st.columns([1, 1]) 
  capital = ac.number_input(label='Capital Size', min_value=0, value=100000, help='Total Amount used for Trading/Investing')
  if capital:
    in_words = num2words(capital, lang='en_IN').title()
    bc.write(f"<p style='margin-top:35px; font-weight: bold;'>Your Capital is Rs. {in_words}</p>", unsafe_allow_html=True)

  risk = ac.number_input(label="% Risk on Capital for this trade", min_value=0.0, max_value=10.0, step=0.1, value=0.5, help='How many percentage of your total capital you want to risk if your Stoploss hits? If you want a max loss of 1000 for an account value of 100,000 then your risk is 1%. It is not advised to take Risk more than 5% per trade! Think about your maximum loss before you trade!')
  if risk:
    risk_rs = capital * (risk/100.0)
    in_words = num2words(risk_rs, lang='en_IN').title()
    bc.write(f"<p style='margin-top:40px; font-weight: bold;'>Your Risk for this trade is Rs. {in_words}</p>", unsafe_allow_html=True)

  ac.divider()

  sl = ac.number_input(label="Stoploss in points", min_value=0.0, step=0.1, help='Stoploss in Points or Rupees calculated by you by analyzing the chart.')
  if sl > 0:
    in_words = num2words(sl, lang='en_IN').title()
    bc.write(f"<p style='margin-top:105px;'>Your SL is {in_words} Rs. per share.</p>", unsafe_allow_html=True)

  ac.write('<center><h5>OR</h5></center>', unsafe_allow_html=True)

  a1, a2 = ac.columns([1, 1])
  price = a1.number_input(label="Entry Price", min_value=0.0, help='Entry price for Long/Short position')
  percentage_sl = a2.number_input(label="% SL", min_value=0.0, max_value=100.0, value=5.0, help='Stoploss in %')
  if sl == 0 and (price > 0 and percentage_sl > 0):
    actual_sl = round(price * (percentage_sl / 100),2)
    in_words = num2words(actual_sl, lang='en_IN').title()
    bc.write(f"<p style='margin-top:230px;'>Your SL is Rs. {actual_sl} per share</p>", unsafe_allow_html=True)

  if calculate_qty_btn:
    if sl > 0:
      qty = floor(risk_rs / sl)
      oc.metric(label='Quantity', value=qty, delta=f'Max Loss: {(-1 * qty * sl)}', delta_color='inverse', help='Trade this Quantity to prevent excessive unplanned losses')
    elif price > 0 and percentage_sl > 0:
      qty = floor(risk_rs / actual_sl)
      oc.metric(label='Quantity', value=qty, delta=f'Max Loss: {(-1 * qty * actual_sl)}', delta_color='inverse', help='Trade this Quantity to prevent excessive unplanned losses')

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
	<marquee class="sampleMarquee" direction="left" scrollamount="7" behavior="scroll">This tool should be used only for Analysis/Study purposes. We do NOT provide any Buy/Sell advice for any Securities. Authors of this tool will not be held liable for any losses. Understand the Risks subjected with Markets before Investing.</marquee>
</body>
</html>
'''
components.html(marquee_html)