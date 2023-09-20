import pandas as pd
import streamlit as st
import urllib
import requests
import csv

listStockCodes = []
tickerOption = 8

try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

st.write(proxyServer)

tickerMapping = {
    1: "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    2: "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
    3: "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    4: "https://archives.nseindia.com/content/indices/ind_nifty200list.csv",
    5: "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    6: "https://archives.nseindia.com/content/indices/ind_niftysmallcap50list.csv",
    7: "https://archives.nseindia.com/content/indices/ind_niftysmallcap100list.csv",
    8: "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    9: "https://archives.nseindia.com/content/indices/ind_niftymidcap50list.csv",
    10: "https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv",
    11: "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    14: "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
}

url = tickerMapping.get(tickerOption)

try:
    if proxyServer:
        res = requests.get(url,proxies={'https':proxyServer})
    else:
        res = requests.get(url)
    st.write(f'fetchCodes Response -> {res}')
    
    cr = csv.reader(res.text.strip().split('\n'))
    
    if tickerOption == 14:
        for i in range(5):
            next(cr)  # skipping first line
        for row in cr:
            listStockCodes.append(row[1].strip())                
    else:
        next(cr)  # skipping first line
        for row in cr:
            listStockCodes.append(row[2])
except Exception as error:
    print(error)
st.write(f'Length of listStockCodes -> {len(listStockCodes)}')
st.write(listStockCodes)