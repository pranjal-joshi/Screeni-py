import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from tabulate import tabulate


st.set_page_config(layout="wide")

st.title('Screeni-py: UI Development')

df = pd.read_pickle('last_screened_results.pkl')

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

components.html(ticker_tape_url)

with st.container():
    st.markdown(tabulate(df, headers='keys', tablefmt='github'))
