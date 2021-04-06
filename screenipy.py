#!/usr/bin/python3

import os
import sys
import urllib
import requests
import yfinance as yf
from nsetools import Nse
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate
import configparser

# Constants
DEBUG = False
consolidationPercentage = 4
volumeRatio = 2.5
minLTP = 25.0
maxLTP = 5000
period = '6mo'
duration = '1d'
# Try Fixing bug with this symbol
TEST_STKCODE = "HAPPSTMNDS"

nse = Nse()
np.seterr(divide='ignore', invalid='ignore')
parser = configparser.ConfigParser()

# Decoration Class
class colorText:
	HEAD = '\033[95m'
	BLUE = '\033[94m'
	GREEN = '\033[92m'
	WARN = '\033[93m'
	FAIL = '\033[91m'
	END = '\033[0m'
	BOLD = '\033[1m'
	UNDR = '\033[4m'

# Global Variabls
screenResults = pd.DataFrame(columns=['Stock','Consolidating','Breaking-Out','MA-Signal','Volume','LTP'])
screeningDictionary = {
    'Stock': "",
    'Consolidating': "",
    'Breaking-Out': "",
    'MA-Signal': "",
    'Volume': "",
    'LTP': 0
}
listStockCodes = []

# Get system wide proxy for networking
try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

# Fetch all stock codes from NSE
def fetchStockCodes():
    global listStockCodes
    print("Getting Stock Codes From NSE... ", end='')
    listStockCodes = list(nse.get_stock_codes(cached=False))[1:]
    if len(listStockCodes) > 10:
        print("=> Done! Fetched %d stock codes." % len(listStockCodes))
    else:
        print("=> Error getting stock codes from NSE!")
        sys.exit("Exiting script..")

# Fetch stock price data from Yahoo finance
def fetchStockData(stockCode):
    data = yf.download(
        tickers = stockCode+".NS",
        period = period,
        duration = duration,
        proxy = proxyServer,
        progress=False
    )
    print("Fetching prices of %s..." % stockCode, end='')
    
    if len(data) == 0:
        print("=> Failed to fetch!", end='\r', flush=True)
        return None
    print("=> Done!", end='\r', flush=True)
    return data

# Preprocess the acquired data
def preprocessData(data, daysToLookback=30):
    sma = data.rolling(window=50).mean()
    lma = data.rolling(window=200).mean()
    vol = data.rolling(window=20).mean()
    data.insert(6,'SMA',sma['Close'])
    data.insert(7,'LMA',lma['Close'])
    data.insert(8,'VolMA',vol['Volume'])
    data = data[::-1]               # Reverse the dataframe
    data = data[1:]                 # Eliminate Headers
    data = data.head(daysToLookback)
    data = data.replace(np.nan, 0)
    if DEBUG:
        print(data)
    return data

# Analyze stock dataframe to determine possibility of box breakout
def findBoxBreakout(data):
    highest = []
    openclose = []
    for i in range(0,len(data)):
        highest.append(data.iloc[i]['High'])
        if data.iloc[i]['Close'] > data.iloc[i]['Open']:      # Green Candle
            openclose.append(data.iloc[i]['Close'])
        else:
            openclose.append(data.iloc[i]['Open'])            # Red Candle
    return (highest, openclose)

# Linear regression
def showBoxfitLine(data,daysToLookback=30, stockCode=''):
    x = np.arange(daysToLookback+1,1,-1)
    y = np.array(data)
    m,c = np.polyfit(x,y,1)
    print("Slope = %f\tIntercept = %f\tLine of angle with X-axis = %f" % (round(m,2),round(c,2),np.rad2deg(np.arctan(m))))
    plt.plot(x,y,'o')
    plt.plot(x,m*x+c)
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.title(stockCode)
    plt.show()

# Simple Average
def showBoxfitLineAverage(data,daysToLookback=30, stockCode=''):
    x = np.arange(daysToLookback+1,1,-1)
    y = np.array(data)
    z = np.ones(daysToLookback) * y.mean()
    print("Intercept = %f" % z[0])
    plt.plot(x,y,'o')
    plt.plot(x,z)
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.title(stockCode)
    plt.show()

# Just a random function to plot averaged line
def r(daysToLookback=30):
    x = np.arange(1,daysToLookback+1)
    y = np.random.rand(daysToLookback)
    z = np.ones(daysToLookback) * y.mean()
    plt.plot(x,y,'o')
    plt.plot(x,z)
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.title("Randomized Price Action")
    plt.show()

# Validate LTP within limits
def validateLTP(data, dict, minLTP=minLTP, maxLTP=maxLTP):
    recent = data.head(1)
    ltp = round(recent['Close'][0],2)
    if(ltp >= minLTP and ltp <= maxLTP):
        dict['LTP'] = colorText.GREEN + str(ltp) + colorText.END
    else:
        dict['LTP'] = colorText.FAIL + str(ltp) + colorText.END

# Validate if share is in valid box
def validateBox(data,boxHeight=20):
    print("Validating Box conditions... ")
    hs = data.describe()['High']['max']
    hc = data.describe()['Close']['max']
    lc = data.describe()['Close']['min']
    ls = data.describe()['Low']['min']
    atp = data.describe()['Close']['min']
    #max = atp + atp*(boxHeight/200)
    #min = atp - atp*(boxHeight/200)
    max = hs
    min = ls
    if DEBUG :
        print("Max = %f\tMin = %f" % (max,min))
        print("HC = %f\tLC = %f\tHS = %f\tLS = %f" % (hc, lc, hs, ls))
    if(hc <= max and lc >= min):
        print("Box => Valid!")
        return True
    print("Box => Invalid!")
    return False

# Validate if share prices are consolidating
def validateConsolidation(data, dict, percentage=2.5):
    hc = data.describe()['Close']['max']
    lc = data.describe()['Close']['min']
    if ((hc - lc) <= (hc*percentage/100)):
        dict['Consolidating'] = colorText.BOLD + colorText.GREEN + "Range = " + str(round((abs((hc-lc)/hc)*100),2))+"%" + colorText.END
        if DEBUG:
            print("Consolidation => Valid!")
    else:
        if DEBUG:
            print("Consolidation => Invalid!")
        dict['Consolidating'] = colorText.BOLD + colorText.FAIL + "Range = " + str(round((abs((hc-lc)/hc)*100),2)) + "%" + colorText.END

# Validate Moving averages
def validateMovingAverages(data, dict):
    recent = data.head(1)
    if(recent['SMA'][0] > recent['LMA'][0] and recent['Close'][0] > recent['SMA'][0]):
        dict['MA-Signal'] = colorText.BOLD + colorText.GREEN + 'Bullish' + colorText.END
    elif(recent['SMA'][0] < recent['LMA'][0]):
        dict['MA-Signal'] = colorText.BOLD + colorText.FAIL + 'Bearish' + colorText.END
    else:
        dict['MA-Signal'] = colorText.BOLD + colorText.WARN + 'Neutral' + colorText.END

# Validate if volume of last day is higher than avg
def validateVolume(data, dict, volumeRatio=2.5):
    recent = data.head(1)
    ratio = recent['Volume'][0]/recent['VolMA'][0]
    if(ratio >= volumeRatio):
        dict['Volume'] = colorText.BOLD + colorText.GREEN + str(round(ratio,2)) + "x" + colorText.END
    else:
        dict['Volume'] = colorText.BOLD + colorText.FAIL + str(round(ratio,2)) + "x" + colorText.END

# Validate if stock is currently breaking out
def isBreakingOut(data, dict):
    recent = data.head(1)
    data = data[1:]
    hc = round(data.describe()['Close']['max'],2)
    if(recent['Close'][0] > hc):
        dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (Crossed " + str(hc) + ")" + colorText.END
    else:
        dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "No (Wait for " + str(hc) + ")" + colorText.END

# Find accurate breakout value
def findBreakout(data, dict, daysToLookback):
    recent = data.head(1)
    data = data[1:]
    hs = round(data.describe()['High']['max'],2)
    hc = round(data.describe()['Close']['max'],2)
    rc = round(recent['Close'][0],2)
    if hs > hc:
        if ((hs - hc) <= (hs*2/100)):
            if rc >= hc:
                dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
            else:
                dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
        else:    
            noOfHigherShadows = len(data[data.High > hc])
            if(daysToLookback/noOfHigherShadows <= 3):
                if rc >= hs:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hs) + ")" + colorText.END
                else:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hs) + ")" + colorText.END
            else:
                if rc >= hc:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                else:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
    else:
        if rc >= hc:
            dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + ")" + colorText.END
        else:
            dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + ")" + colorText.END


# Handle user input and save config
def setConfig(parser):
    parser.add_section('config')
    print('[+] Screeni-py User Configuration:')
    period = input('[+] Enter number of days for historical screening (Days): ')
    duration = input('[+] Enter Duration of each candle (Days): ')
    minLTP = input('[+] Minimum Price of Stock to Buy (in RS): ')
    maxLTP = input('[+] Maximum Price of Stock to Buy (in RS): ')
    volumeRatio = input('[+] How many times the volume should be more than average for the breakout? (Number): ')
    consolidationPercentage = input('[+] How many %% the price should be in range to consider it as consolidation?: ')
    parser.set('config','period',period + "d")
    parser.set('config','duration',period + "d")
    parser.set('config','minPrice',minLTP)
    parser.set('config','maxPrice',maxLTP)
    parser.set('config','volumeRatio',volumeRatio)
    parser.set('config','consolidationPercentage',consolidationPercentage)
    fp = open('screenipy.ini','w')
    parser.write(fp)
    fp.close()

if __name__ == "__main__":
    os.system("clear")
    fetchStockCodes()
    for stock in listStockCodes:
        try:
            data = fetchStockData(stock)
            processedData = preprocessData(data, daysToLookback=14)
            if not processedData.empty:
                screeningDictionary['Stock'] = colorText.BOLD + colorText.BLUE + stock + colorText.END
                validateConsolidation(processedData, screeningDictionary, percentage=consolidationPercentage)
                validateMovingAverages(processedData, screeningDictionary)
                validateVolume(processedData, screeningDictionary, volumeRatio=volumeRatio)
                #isBreakingOut(processedData, screeningDictionary)
                findBreakout(processedData, screeningDictionary, daysToLookback=14)
                validateLTP(processedData, screeningDictionary, minLTP=minLTP, maxLTP=maxLTP)
                highest, openclose = findBoxBreakout(data)
                #validateBox(processedData)
                screenResults = screenResults.append(screeningDictionary,ignore_index=True)
        except KeyboardInterrupt:
            print(colorText.BOLD + colorText.FAIL + "[+] Script terminated by the user." + colorText.END)
            print(tabulate(screenResults, headers='keys', tablefmt='psql'))
            sys.exit(0)
        except Exception as e:
            print(colorText.FAIL + "[+] Exception Occured while Screening! Moving on.." + colorText.END)
            raise(e)
            sys.exit(1)
    print(colorText.BOLD + colorText.GREEN + "[+] Screening Completed! Happy Trading! :)" + colorText.END)
    print(tabulate(screenResults, headers='keys', tablefmt='psql'))
    sys.exit(0)
    #showBoxfitLine(highest, daysToLookback=20, stockCode=TEST_STKCODE)
    #showBoxfitLineAverage(highest, daysToLookback=20, stockCode=TEST_STKCODE)
    #showBoxfitLine(openclose, daysToLookback=20, stockCode=TEST_STKCODE)