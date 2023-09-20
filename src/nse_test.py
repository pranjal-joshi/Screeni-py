import pandas as pd
import streamlit as st

url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
codes = list(pd.read_csv(url)['SYMBOL'].values)
st.write(len(codes))
st.write(codes)