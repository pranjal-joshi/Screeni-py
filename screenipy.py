#!/usr/bin/python3

# Pyinstaller compile: pyinstaller --onefile screenipy.py  --hidden-import cmath

import os
import sys
import urllib
import requests
import yfinance as yf
from nsetools import Nse
import numpy as np
import pandas as pd
from tabulate import tabulate
import configparser
from time import sleep
import platform
import datetime
import math
import random

# Try Fixing bug with this symbol
TEST_STKCODE = "HAPPSTMNDS"

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

# Constants
DEBUG = False
VERSION = "1.01"
consolidationPercentage = 4
volumeRatio = 2.5
minLTP = 20.0
maxLTP = 50000
period = '365d'
duration = '1d'
daysToLookback = 20
daysForInsideBar = 4
shuffleEnabled = False

art = colorText.GREEN + '''
     .d8888b.                                             d8b                   
    d88P  Y88b                                            Y8P                   
    Y88b.                                                                       
     "Y888b.    .d8888b 888d888 .d88b.   .d88b.  88888b.  888 88888b.  888  888 
        "Y88b. d88P"    888P"  d8P  Y8b d8P  Y8b 888 "88b 888 888 "88b 888  888 
          "888 888      888    88888888 88888888 888  888 888 888  888 888  888 
    Y88b  d88P Y88b.    888    Y8b.     Y8b.     888  888 888 888 d88P Y88b 888 
     "Y8888P"   "Y8888P 888     "Y8888   "Y8888  888  888 888 88888P"   "Y88888 
                                                              888           888 
                                                              888      Y8b d88P 
                                                              888       "Y88P"  

''' + colorText.END

changelog = colorText.BOLD + '[ChangeLog]\n' + colorText.END + colorText.BLUE + '''
[1.01]
1. Inside Bar detection added.
2. OTA Software Update Implemented.
3. Stock shuffling added while screening
4. Results will be now also stored in the excel (screenipy-result.xlsx) file.
5. UI cosmetic updates for pretty-printing!

[1.00 - Beta]
1. Initial Release for beta testing
2. Minor Bug fixes

--- END ---
''' + colorText.END

nse = Nse()
np.seterr(divide='ignore', invalid='ignore')
parser = configparser.ConfigParser()
screenCounter = 1

# Global Variabls
screenResults = pd.DataFrame(columns=['Stock','Consolidating','Breaking-Out','MA-Signal','Volume','LTP','Pattern'])
saveResults = pd.DataFrame(columns=['Stock','Consolidating','Breaking-Out','MA-Signal','Volume','LTP','Pattern'])
screeningDictionary = {
    'Stock': "",
    'Consolidating': "",
    'Breaking-Out': "",
    'MA-Signal': "",
    'Volume': "",
    'LTP': 0,
    'Pattern': ""
}
saveDictionary = {
    'Stock': "",
    'Pattern': "",
    'Consolidating': "",
    'Breaking-Out': "",
    'MA-Signal': "",
    'Volume': "",
    'LTP': 0,
    'Pattern': ""
}
listStockCodes = []

# Get system wide proxy for networking
try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

def clearScreen():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')
    print(art)

# Fetch all stock codes from NSE
def fetchStockCodes():
    global listStockCodes
    print(colorText.BOLD + "[+] Getting Stock Codes From NSE... ", end='')
    listStockCodes = list(nse.get_stock_codes(cached=False))[1:]
    if len(listStockCodes) > 10:
        print(colorText.GREEN + ("=> Done! Fetched %d stock codes." % len(listStockCodes)) + colorText.END)
        if shuffleEnabled:
            random.shuffle(listStockCodes)
            print(colorText.WARN + "[+] Stock shuffling is active." + colorText.END)
        else:
            print(colorText.WARN + "[+] Stock shuffling is inactive." + colorText.END)
    else:
        print(colorText.FAIL + "=> Error getting stock codes from NSE!" + colorText.END)
        sys.exit("Exiting script..")

# Fetch stock price data from Yahoo finance
def fetchStockData(stockCode):
    global screenCounter
    data = yf.download(
        tickers = stockCode+".NS",
        period = period,
        duration = duration,
        proxy = proxyServer,
        progress=False
    )
    sys.stdout.write("\r\033[K")
    print(colorText.BOLD + colorText.GREEN + ("[%d%%] Fetching data & Analyzing %s..." % (int(screenCounter/len(listStockCodes)*100), stockCode)) + colorText.END, end='')
    if len(data) == 0:
        print(colorText.BOLD + colorText.FAIL + "=> Failed to fetch!" + colorText.END, end='\r', flush=True)
        return None
    print(colorText.BOLD + colorText.GREEN + "=> Done!" + colorText.END, end='\r', flush=True)
    screenCounter += 1
    return data

# Preprocess the acquired data
def preprocessData(data, daysToLookback=daysToLookback):
    sma = data.rolling(window=50).mean()
    lma = data.rolling(window=200).mean()
    vol = data.rolling(window=20).mean()
    data.insert(6,'SMA',sma['Close'])
    data.insert(7,'LMA',lma['Close'])
    data.insert(8,'VolMA',vol['Volume'])
    data = data[::-1]               # Reverse the dataframe
    data = data.head(daysToLookback)
    data = data.replace(np.nan, 0)
    if DEBUG:
        print(data)
    return data

# Linear regression
def showBoxfitLine(data,daysToLookback=daysToLookback, stockCode=''):
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
def showBoxfitLineAverage(data,daysToLookback=daysToLookback, stockCode=''):
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

# Validate LTP within limits
def validateLTP(data, dict, saveDict, minLTP=minLTP, maxLTP=maxLTP):
    recent = data.head(1)
    ltp = round(recent['Close'][0],2)
    saveDict['LTP'] = str(ltp)
    if(ltp >= minLTP and ltp <= maxLTP):
        dict['LTP'] = colorText.GREEN + ("%.2f" % ltp) + colorText.END
        return True
    else:
        dict['LTP'] = colorText.FAIL + ("%.2f" % ltp) + colorText.END
        return False

# Validate if share prices are consolidating
def validateConsolidation(data, dict, saveDict, percentage=2.5):
    hc = data.describe()['Close']['max']
    lc = data.describe()['Close']['min']
    if ((hc - lc) <= (hc*percentage/100) and (hc - lc != 0)):
        dict['Consolidating'] = colorText.BOLD + colorText.GREEN + "Range = " + str(round((abs((hc-lc)/hc)*100),2))+"%" + colorText.END
        if DEBUG:
            print("Consolidation => Valid!")
    else:
        if DEBUG:
            print("Consolidation => Invalid!")
        dict['Consolidating'] = colorText.BOLD + colorText.FAIL + "Range = " + str(round((abs((hc-lc)/hc)*100),2)) + "%" + colorText.END
    saveDict['Consolidating'] = str(round((abs((hc-lc)/hc)*100),2))+"%"
    return round((abs((hc-lc)/hc)*100),2)

# Validate Moving averages
def validateMovingAverages(data, dict, saveDict):
    recent = data.head(1)
    if(recent['SMA'][0] > recent['LMA'][0] and recent['Close'][0] > recent['SMA'][0]):
        dict['MA-Signal'] = colorText.BOLD + colorText.GREEN + 'Bullish' + colorText.END
        saveDict['MA-Signal'] = 'Bullish'
    elif(recent['SMA'][0] < recent['LMA'][0]):
        dict['MA-Signal'] = colorText.BOLD + colorText.FAIL + 'Bearish' + colorText.END
        saveDict['MA-Signal'] = 'Bearish'
    else:
        dict['MA-Signal'] = colorText.BOLD + colorText.WARN + 'Neutral' + colorText.END
        saveDict['MA-Signal'] = 'Neutral'

# Validate if volume of last day is higher than avg
def validateVolume(data, dict, saveDict, volumeRatio=2.5):
    recent = data.head(1)
    ratio = round(recent['Volume'][0]/recent['VolMA'][0],2)
    saveDict['Volume'] = str(ratio)+"x"
    if(ratio >= volumeRatio and ratio != np.nan and (not math.isinf(ratio)) and (ratio != 20)):
        dict['Volume'] = colorText.BOLD + colorText.GREEN + str(ratio) + "x" + colorText.END
        return True
    else:
        dict['Volume'] = colorText.BOLD + colorText.FAIL + str(ratio) + "x" + colorText.END
        return False

# Find accurate breakout value
def findBreakout(data, dict, saveDict, daysToLookback):
    recent = data.head(1)
    data = data[1:]
    hs = round(data.describe()['High']['max'],2)
    hc = round(data.describe()['Close']['max'],2)
    rc = round(recent['Close'][0],2)
    if hs > hc:
        if ((hs - hc) <= (hs*2/100)):
            saveDict['Breaking-Out'] = str(hc)
            if rc >= hc:
                dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                return True
            else:
                dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                return False
        else:    
            noOfHigherShadows = len(data[data.High > hc])
            if(daysToLookback/noOfHigherShadows <= 3):
                saveDict['Breaking-Out'] = str(hs)
                if rc >= hs:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hs) + ")" + colorText.END
                    return True
                else:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hs) + ")" + colorText.END
                    return False
            else:
                saveDict['Breaking-Out'] = str(hc) + ", " + str(hs)
                if rc >= hc:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                    return True
                else:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                    return False
    else:
        saveDict['Breaking-Out'] = str(hc)
        if rc >= hc:
            dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + ")" + colorText.END
            return True
        else:
            dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + ")" + colorText.END
            return False

# Validate 'Inside Bar' structure for recent days
def validateInsideBar(data, dict, saveDict, daysToLookback=4):
    data = data.head(daysToLookback)
    lowsData = data.sort_values(by=['Low'], ascending=False)
    highsData = data.sort_values(by=['High'], ascending=True)
    if(highsData.equals(lowsData)):
        dict['Pattern'] = colorText.BOLD + colorText.GREEN + ("Inside Bar (%d days)" % daysToLookback) + colorText.END
        saveDict['Pattern'] = "Inside Bar (%d days)" % daysToLookback
        return True
    dict['Pattern'] = ''
    saveDict['Pattern'] = ''
    return False


# Handle user input and save config
def setConfig(parser):
    parser.add_section('config')
    print('')
    print(colorText.BOLD + colorText.GREEN +'[+] Screeni-py User Configuration:' + colorText.END)
    period = input('[+] Enter number of days for which stock data to be downloaded (Days)(Default = 365): ')
    daysToLookback = input('[+] Number of recent days to screen for Breakout/Consolidation (Days)(Default = 45): ')
    duration = input('[+] Enter Duration of each candle (Days)(Default = 1): ')
    minLTP = input('[+] Minimum Price of Stock to Buy (in RS)(Default = 20): ')
    maxLTP = input('[+] Maximum Price of Stock to Buy (in RS)(Default = 50000): ')
    volumeRatio = input('[+] How many times the volume should be more than average for the breakout? (Number)(Default = 2.5): ')
    consolidationPercentage = input('[+] How many % the price should be in range to consider it as consolidation? (Number)(Default = 4): ')
    shuffle = str(input('[+] Shuffle stocks rather than screening alphabetically? (Y/N): ')).lower()
    parser.set('config','period',period + "d")
    parser.set('config','daysToLookback',daysToLookback)
    parser.set('config','duration',duration + "d")
    parser.set('config','minPrice',minLTP)
    parser.set('config','maxPrice',maxLTP)
    parser.set('config','volumeRatio',volumeRatio)
    parser.set('config','consolidationPercentage',consolidationPercentage)
    parser.set('config','shuffle',shuffle)
    try:
        fp = open('screenipy.ini','w')
        parser.write(fp)
        fp.close()
        print(colorText.BOLD + colorText.GREEN +'[+] User configuration saved.' + colorText.END)
        print(colorText.BOLD + colorText.GREEN +'[+] Restart the program now.' + colorText.END)
        input('')
        sys.exit(0)
    except:
        print(colorText.BOLD + colorText.FAIL +'[+] Failed to save user config. Aborting..' + colorText.END)
        sys.exit(1)

# Load user config from file
def getConfig(parser):
    global duration, period, minLTP, maxLTP, volumeRatio, consolidationPercentage, daysToLookback, shuffleEnabled
    if len(parser.read('screenipy.ini')):
        duration = parser.get('config','duration')
        period = parser.get('config','period')
        minLTP = float(parser.get('config','minprice'))
        maxLTP = float(parser.get('config','maxprice'))
        volumeRatio = float(parser.get('config','volumeRatio'))
        consolidationPercentage = float(parser.get('config','consolidationPercentage'))
        daysToLookback = int(parser.get('config','daysToLookback'))
        if str(parser.get('config','shuffle')).lower() == 'y':
            shuffleEnabled = True
        print(colorText.BOLD + colorText.GREEN +'[+] User configuration loaded.' + colorText.END)
    else:
        print(colorText.BOLD + colorText.FAIL + "[+] User config not found!" + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] Configure the limits to continue." + colorText.END)
        setConfig(parser)

# Manage Execution flow
def initExecution():
    print(colorText.BOLD + colorText.WARN + '[+] Press a number to start stock screening: ' + colorText.END)
    print(colorText.BOLD + '''    1 > Screen stocks for Breakout or Consolidation
    2 > Screen for the stocks with recent Breakout & Volume
    3 > Screen for the Consolidating stocks
    4 > Screen for the "Inside Bar" (Tight Flag) Pattern
    5 > Edit user configuration
    6 > Show user configuration
    7 > About Developer
    8 > Exit''' + colorText.END
    )
    result = input(colorText.BOLD + colorText.FAIL + '[+] Select option: ')
    print(colorText.END, end='')
    try:
        result = int(result)
        if(result < 0 or result > 8):
            raise ValueError
        return result
    except:
        print(colorText.BOLD + colorText.FAIL + '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        clearScreen()
        return initExecution()

# Print config file
def showConfigFile():
    try:
        f = open('screenipy.ini','r')
        print(colorText.BOLD + colorText.GREEN +'[+] Screeni-py User Configuration:' + colorText.END)
        print("\n"+f.read())
        f.close()
    except:
        print(colorText.BOLD + colorText.FAIL + "[+] User Configuration not found!" + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] Configure the limits to continue." + colorText.END)
        setConfig(parser)

# Download latest release from Github Release
def checkForUpdate():
    try:
        resp = None
        now = float(VERSION)
        if proxyServer:
            resp = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest",proxies={'https':proxyServer})
        else:
            resp = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest")
        if(float(resp.json()['tag_name']) > now):
            url = resp.json()['assets'][0]['browser_download_url']
            size = int(resp.json()['assets'][0]['size']/1024*1024)
            if platform.system() != 'Windows':
                url = resp.json()['assets'][1]['browser_download_url']
                size = int(resp.json()['assets'][1]['size']/(1024*1024))
            action = str(input(colorText.BOLD + colorText.WARN + ('\n[+] New Software update (v%s) available. Download Now (Size: %dMB)? [Y/N]: ' % (str(resp.json()['tag_name']),size)))).lower()
            if(action == 'y'):
                try:
                    print(colorText.BOLD + colorText.WARN + ('Downloading Update of %dMBs, This may take a few minutes, Please Wait...' % size) + colorText.END)
                    download = requests.get(url, proxies={'https':proxyServer})
                    fn = 'screenipy.exe'
                    if platform.system() != 'Windows':
                        fn = 'screenipy.bin'
                    with open(fn,'wb') as f:
                        f.write(download.content)
                    print(colorText.BOLD + colorText.GREEN + '[+] Update Completed.\n[+] Restart the program now.' + colorText.END)
                    if platform.system() != 'Windows':
                        os.system('chmod +x screenipy.bin')
                    input('')
                    sys.exit(0)
                except Exception as e:
                    print(colorText.BOLD + colorText.WARN + '[+] Error occured while updating!' + colorText.END)
                    raise(e)
                    input('')
                    sys.exit(1)
    except Exception as e:
        print("[+] Failure while checking update due to error.")
    
if __name__ == "__main__":
    clearScreen()
    checkForUpdate()
    executeOption = initExecution()
    if executeOption == 5:
        setConfig(parser)
    if executeOption == 6:
        showConfigFile()
    if executeOption == 7:
        print(colorText.BOLD + colorText.WARN + "\n[+] Developer: Pranjal Joshi." + colorText.END)
        print(colorText.BOLD + colorText.WARN + ("[+] Version: %s" % VERSION) + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] More: https://github.com/pranjal-joshi/Screeni-py" + colorText.END)
        print('\n'+changelog)
        input('')
    if executeOption == 8:
        print(colorText.BOLD + colorText.FAIL + "[+] Script terminated by the user." + colorText.END)
        sys.exit(0)
    if executeOption > 0 and executeOption < 5:
        getConfig(parser)
        try:
            daysForInsideBar = int(input(colorText.BOLD + colorText.WARN + '\n[+] Enter days to look back for formation of Inside Bar: '))
            print('')
        except:
            pass
        fetchStockCodes()
        print(colorText.BOLD + colorText.WARN + "[+] Starting Stock Screening.. Press Ctrl+C to stop!\n")
        for stock in listStockCodes:
            try:
                data = fetchStockData(stock)
                processedData = preprocessData(data, daysToLookback=daysToLookback)
                if not processedData.empty:
                    screeningDictionary['Stock'] = colorText.BOLD + colorText.BLUE + stock + colorText.END
                    saveDictionary['Stock'] = stock
                    consolidationValue = validateConsolidation(processedData, screeningDictionary, saveDictionary, percentage=consolidationPercentage)
                    validateMovingAverages(processedData, screeningDictionary, saveDictionary)
                    isVolumeHigh = validateVolume(processedData, screeningDictionary, saveDictionary, volumeRatio=volumeRatio)
                    isBreaking = findBreakout(processedData, screeningDictionary, saveDictionary, daysToLookback=daysToLookback)
                    isLtpValid = validateLTP(processedData, screeningDictionary, saveDictionary, minLTP=minLTP, maxLTP=maxLTP)
                    isInsideBar = validateInsideBar(processedData, screeningDictionary, saveDictionary, daysToLookback=daysForInsideBar)
                    if (executeOption == 1 or executeOption == 2) and isBreaking and isVolumeHigh and isLtpValid:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if (executeOption == 1 or executeOption == 3) and (consolidationValue <= consolidationPercentage and consolidationValue != 0) and isLtpValid:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if executeOption == 4 and isLtpValid and isInsideBar:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
            except KeyboardInterrupt:
                print(colorText.BOLD + colorText.FAIL + "\n[+] Script terminated by the user." + colorText.END)
                break
            except Exception as e:
                print(colorText.FAIL + ("[+] Exception Occured while Screening %s! Skipping this stock.." % stock) + colorText.END)
                print(e)
        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        print(tabulate(screenResults, headers='keys', tablefmt='psql'))
        saveResults.to_excel('screenipy-result.xlsx')
        print(colorText.BOLD + colorText.GREEN + "[+] Results saved to screenipy-result.xlsx" + colorText.END)
        print(colorText.BOLD + colorText.GREEN + "[+] Screening Completed! Happy Trading! :)" + colorText.END)
        input('')
        sys.exit(0)