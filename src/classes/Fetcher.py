'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for handling networking for fetching stock codes and data
'''

import sys
import urllib.request
import csv
import requests
import random
import os
import yfinance as yf
import pandas as pd
from nsetools import Nse
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput
from classes.Utility import isDocker

nse = Nse()

# Exception class if yfinance stock delisted


class StockDataEmptyException(Exception):
    pass

# This Class Handles Fetching of Stock Data over the internet


class tools:

    def __init__(self, configManager):
        self.configManager = configManager
        pass

    def fetchCodes(self, tickerOption,proxyServer=None):
        listStockCodes = []
        if tickerOption == 12:
            url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
            return list(pd.read_csv(url)['SYMBOL'].values)
        if tickerOption == 15:
            return ["MMM", "ABT", "ABBV", "ABMD", "ACN", "ATVI", "ADBE", "AMD", "AAP", "AES", "AFL", "A", "APD", "AKAM", "ALK", "ALB", "ARE", "ALXN", "ALGN", "ALLE", "AGN", "ADS", "LNT", "ALL", "GOOGL", "GOOG", "MO", "AMZN", "AMCR", "AEE", "AAL", "AEP", "AXP", "AIG", "AMT", "AWK", "AMP", "ABC", "AME", "AMGN", "APH", "ADI", "ANSS", "ANTM", "AON", "AOS", "APA", "AIV", "AAPL", "AMAT", "APTV", "ADM", "ARNC", "ANET", "AJG", "AIZ", "ATO", "T", "ADSK", "ADP", "AZO", "AVB", "AVY", "BKR", "BLL", "BAC", "BK", "BAX", "BDX", "BRK.B", "BBY", "BIIB", "BLK", "BA", "BKNG", "BWA", "BXP", "BSX", "BMY", "AVGO", "BR", "BF.B", "CHRW", "COG", "CDNS", "CPB", "COF", "CPRI", "CAH", "KMX", "CCL", "CAT", "CBOE", "CBRE", "CDW", "CE", "CNC", "CNP", "CTL", "CERN", "CF", "SCHW", "CHTR", "CVX", "CMG", "CB", "CHD", "CI", "XEC", "CINF", "CTAS", "CSCO", "C", "CFG", "CTXS", "CLX", "CME", "CMS", "KO", "CTSH", "CL", "CMCSA", "CMA", "CAG", "CXO", "COP", "ED", "STZ", "COO", "CPRT", "GLW", "CTVA", "COST", "COTY", "CCI", "CSX", "CMI", "CVS", "DHI", "DHR", "DRI", "DVA", "DE", "DAL", "XRAY", "DVN", "FANG", "DLR", "DFS", "DISCA", "DISCK", "DISH", "DG", "DLTR", "D", "DOV", "DOW", "DTE", "DUK", "DRE", "DD", "DXC", "ETFC", "EMN", "ETN", "EBAY", "ECL", "EIX", "EW", "EA", "EMR", "ETR", "EOG", "EFX", "EQIX", "EQR", "ESS", "EL", "EVRG", "ES", "RE", "EXC", "EXPE", "EXPD", "EXR", "XOM", "FFIV", "FB", "FAST", "FRT", "FDX", "FIS", "FITB", "FE", "FRC", "FISV", "FLT", "FLIR", "FLS", "FMC", "F", "FTNT", "FTV", "FBHS", "FOXA", "FOX", "BEN", "FCX", "GPS", "GRMN", "IT", "GD", "GE", "GIS", "GM", "GPC", "GILD", "GL", "GPN", "GS", "GWW", "HRB", "HAL", "HBI", "HOG", "HIG", "HAS", "HCA", "PEAK", "HP", "HSIC", "HSY", "HES", "HPE", "HLT", "HFC", "HOLX", "HD", "HON", "HRL", "HST", "HPQ", "HUM", "HBAN", "HII", "IEX", "IDXX", "INFO", "ITW", "ILMN", "IR", "INTC", "ICE", "IBM", "INCY", "IP", "IPG", "IFF", "INTU", "ISRG", "IVZ", "IPGP", "IQV", "IRM", "JKHY", "J", "JBHT", "SJM", "JNJ", "JCI", "JPM", "JNPR", "KSU", "K", "KEY", "KEYS", "KMB", "KIM", "KMI", "KLAC", "KSS", "KHC", "KR", "LB", "LHX", "LH", "LRCX", "LW", "LVS", "LEG", "LDOS", "LEN", "LLY", "LNC", "LIN", "LYV", "LKQ", "LMT", "L", "LOW", "LYB", "MTB", "M", "MRO", "MPC", "MKTX", "MAR", "MMC", "MLM", "MAS", "MA", "MKC", "MXIM", "MCD", "MCK", "MDT", "MRK", "MET", "MTD", "MGM", "MCHP", "MU", "MSFT", "MAA", "MHK", "TAP", "MDLZ", "MNST", "MCO", "MS", "MOS", "MSI", "MSCI", "MYL", "NDAQ", "NOV", "NTAP", "NFLX", "NWL", "NEM", "NWSA", "NWS", "NEE", "NLSN", "NKE", "NI", "NBL", "JWN", "NSC", "NTRS", "NOC", "NLOK", "NCLH", "NRG", "NUE", "NVDA", "NVR", "ORLY", "OXY", "ODFL", "OMC", "OKE", "ORCL", "PCAR", "PKG", "PH", "PAYX", "PYPL", "PNR", "PBCT", "PEP", "PKI", "PRGO", "PFE", "PM", "PSX", "PNW", "PXD", "PNC", "PPG", "PPL", "PFG", "PG", "PGR", "PLD", "PRU", "PEG", "PSA", "PHM", "PVH", "QRVO", "PWR", "QCOM", "DGX", "RL", "RJF", "RTN", "O", "REG", "REGN", "RF", "RSG", "RMD", "RHI", "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SBAC", "SLB", "STX", "SEE", "SRE", "NOW", "SHW", "SPG", "SWKS", "SLG", "SNA", "SO", "LUV", "SWK", "SBUX", "STT", "STE", "SYK", "SIVB", "SYF", "SNPS", "SYY", "TMUS", "TROW", "TTWO", "TPR", "TGT", "TEL", "FTI", "TFX", "TXN", "TXT", "TMO", "TIF", "TJX", "TSCO", "TDG", "TRV", "TFC", "TWTR", "TSN", "UDR", "ULTA", "USB", "UAA", "UA", "UNP", "UAL", "UNH", "UPS", "URI", "UTX", "UHS", "UNM", "VFC", "VLO", "VAR", "VTR", "VRSN", "VRSK", "VZ", "VRTX", "VIAC", "V", "VNO", "VMC", "WRB", "WAB", "WMT", "WBA", "DIS", "WM", "WAT", "WEC", "WCG", "WFC", "WELL", "WDC", "WU", "WRK", "WY", "WHR", "WMB", "WLTW", "WYNN", "XEL", "XRX", "XLNX", "XYL", "YUM", "ZBRA", "ZBH", "ZION", "ZTS"]
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

        return listStockCodes

    # Fetch all stock codes from NSE
    def fetchStockCodes(self, tickerOption, proxyServer=None):
        listStockCodes = []
        if tickerOption == 0:
            stockCode = None
            while stockCode == None or stockCode == "":
                stockCode = str(input(colorText.BOLD + colorText.BLUE +
                                      "[+] Enter Stock Code(s) for screening (Multiple codes should be seperated by ,): ")).upper()
            stockCode = stockCode.replace(" ", "")
            listStockCodes = stockCode.split(',')
        else:
            print(colorText.BOLD +
                  "[+] Getting Stock Codes From NSE... ", end='')
            listStockCodes = self.fetchCodes(tickerOption,proxyServer=proxyServer)
            if len(listStockCodes) > 10:
                print(colorText.GREEN + ("=> Done! Fetched %d stock codes." %
                                         len(listStockCodes)) + colorText.END)
                if self.configManager.shuffleEnabled:
                    random.shuffle(listStockCodes)
                    print(colorText.BLUE +
                          "[+] Stock shuffling is active." + colorText.END)
                else:
                    print(colorText.FAIL +
                          "[+] Stock shuffling is inactive." + colorText.END)
                if self.configManager.stageTwo:
                    print(
                        colorText.BLUE + "[+] Screening only for the stocks in Stage-2! Edit User Config to change this." + colorText.END)
                else:
                    print(
                        colorText.FAIL + "[+] Screening only for the stocks in all Stages! Edit User Config to change this." + colorText.END)

            else:
                input(
                    colorText.FAIL + "=> Error getting stock codes from NSE! Press any key to exit!" + colorText.END)
                sys.exit("Exiting script..")

        return listStockCodes

    # Fetch stock price data from Yahoo finance
    def fetchStockData(self, stockCode, period, duration, proxyServer, screenResultsCounter, screenCounter, totalSymbols, printCounter=False, tickerOption=None):
        with SuppressOutput(suppress_stdout=True, suppress_stderr=True):
            append_exchange = ".NS"
            if tickerOption == 15:
                append_exchange = ""
            data = yf.download(
                tickers=stockCode + append_exchange,
                period=period,
                interval=duration,
                proxy=proxyServer,
                progress=False,
                timeout=10
            )
        if printCounter:
            sys.stdout.write("\r\033[K")
            try:
                print(colorText.BOLD + colorText.GREEN + ("[%d%%] Screened %d, Found %d. Fetching data & Analyzing %s..." % (
                    int((screenCounter.value/totalSymbols)*100), screenCounter.value, screenResultsCounter.value, stockCode)) + colorText.END, end='')
            except ZeroDivisionError:
                pass
            if len(data) == 0:
                print(colorText.BOLD + colorText.FAIL +
                      "=> Failed to fetch!" + colorText.END, end='\r', flush=True)
                raise StockDataEmptyException
                return None
            print(colorText.BOLD + colorText.GREEN + "=> Done!" +
                  colorText.END, end='\r', flush=True)
        return data

    # Get Daily Nifty 50 Index:
    def fetchLatestNiftyDaily(self, proxyServer=None):
        data = yf.download(
                tickers="^NSEI",
                period='5d',
                interval='1d',
                proxy=proxyServer,
                progress=False,
                timeout=10
            )
        return data

    # Get Data for Five EMA strategy
    def fetchFiveEmaData(self, proxyServer=None):
        nifty_sell = yf.download(
                tickers="^NSEI",
                period='5d',
                interval='5m',
                proxy=proxyServer,
                progress=False,
                timeout=10
            )
        banknifty_sell = yf.download(
                tickers="^NSEBANK",
                period='5d',
                interval='5m',
                proxy=proxyServer,
                progress=False,
                timeout=10
            )
        nifty_buy = yf.download(
                tickers="^NSEI",
                period='5d',
                interval='15m',
                proxy=proxyServer,
                progress=False,
                timeout=10
            )
        banknifty_buy = yf.download(
                tickers="^NSEBANK",
                period='5d',
                interval='15m',
                proxy=proxyServer,
                progress=False,
                timeout=10
            )
        return nifty_buy, banknifty_buy, nifty_sell, banknifty_sell

    # Load stockCodes from the watchlist.xlsx
    def fetchWatchlist(self):
        createTemplate = False
        data = pd.DataFrame()
        try:
            data = pd.read_excel('watchlist.xlsx')
        except FileNotFoundError:
            print(colorText.BOLD + colorText.FAIL +
                  f'[+] watchlist.xlsx not found in f{os.getcwd()}' + colorText.END)
            createTemplate = True
        try:
            if not createTemplate:
                data = data['Stock Code'].values.tolist()
        except KeyError:
            print(colorText.BOLD + colorText.FAIL +
                  '[+] Bad Watchlist Format: First Column (A1) should have Header named "Stock Code"' + colorText.END)
            createTemplate = True
        if createTemplate:
            if isDocker():
                print(colorText.BOLD + colorText.FAIL +
                  f'[+] This feature is not available with dockerized application. Try downloading .exe/.bin file to use this!' + colorText.END)
                return None
            sample = {'Stock Code': ['SBIN', 'INFY', 'TATAMOTORS', 'ITC']}
            sample_data = pd.DataFrame(sample, columns=['Stock Code'])
            sample_data.to_excel('watchlist_template.xlsx',
                                 index=False, header=True)
            print(colorText.BOLD + colorText.BLUE +
                  f'[+] watchlist_template.xlsx created in {os.getcwd()} as a referance template.' + colorText.END)
            return None
        return data
