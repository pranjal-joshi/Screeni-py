#!/usr/bin/python3

# Pyinstaller compile: pyinstaller --onefile --icon=icon.ico screenipy.py  --hidden-import cmath --hidden-import talib.stream

import os
import sys
import urllib
import requests
import numpy as np
import pandas as pd
from tabulate import tabulate
from time import sleep
import platform
import datetime
import math
import classes.Fetcher as Fetcher
import classes.ConfigManager as ConfigManager
from classes.ColorText import colorText
from otaUpdater import OTAUpdater
from CandlePatterns import CandlePatterns

# Try Fixing bug with this symbol
TEST_STKCODE = "HAPPSTMNDS"

# Constants
DEBUG = False
VERSION = "1.07"
daysForInsideBar = 3
daysForLowestVolume = 30
lastScreened = 'last_screened_results.pkl'

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
[1.00 - Beta]
1. Initial Release for beta testing
2. Minor Bug fixes

[1.01]
1. Inside Bar detection added.
2. OTA Software Update Implemented.
3. Stock shuffling added while screening
4. Results will be now also stored in the excel (screenipy-result.xlsx) file.
5. UI cosmetic updates for pretty-printing!

[1.02]
1. Feature added to screen only STAGE-2 stocks.
2. OTA update download bug-fixed.
3. Auto generate default config if not found.
4. Minor bug-fixes.

[1.03]
1. Result excel file will not be overwritten now. Each result file will be saved with timestamp.
2. Candlestick pattern recognition added.

[1.04]
1. OTA Software Update bug-fixed.
2. Minor Improvements.

[1.05]
1. More candlestick pattern added for recognition.
2. Option added to find stock with lowest volume in last 'N'-days to early detect possibility of breakout.
3. Last screened results will be stored and can be viewed with Option > 7.
4. Minor Bug-fixes and improvements.

[1.06]
1. Option > 0 added - Screen stocks by enterning it's name (stock code).
2. Stability fixes and improvements.
3. Last screened results will be stored and can be viewed with Option > 7.

[1.07]
1. Program Window will not automatically close now.
2. Bug fixes and improvements.

--- END ---
''' + colorText.END

candlePatterns = CandlePatterns()
np.seterr(divide='ignore', invalid='ignore')
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

# Preprocess the acquired data
def preprocessData(data, daysToLookback=ConfigManager.daysToLookback):
    sma = data.rolling(window=50).mean()
    lma = data.rolling(window=200).mean()
    vol = data.rolling(window=20).mean()
    data.insert(6,'SMA',sma['Close'])
    data.insert(7,'LMA',lma['Close'])
    data.insert(8,'VolMA',vol['Volume'])
    data = data[::-1]               # Reverse the dataframe
    fullData = data
    trimmedData = data.head(daysToLookback)
    data = data.replace(np.nan, 0)
    if DEBUG:
        print(data)
    return (fullData, trimmedData)

# Validate LTP within limits
def validateLTP(data, dict, saveDict, minLTP=ConfigManager.minLTP, maxLTP=ConfigManager.maxLTP):
    global stageTwo
    recent = data.head(1)
    ltp = round(recent['Close'][0],2)
    saveDict['LTP'] = str(ltp)
    verifyStageTwo = True
    if(stageTwo):
        yearlyLow = data.head(300).min()['Low']
        if ltp < (2 * yearlyLow):
            verifyStageTwo = False
    if(ltp >= minLTP and ltp <= maxLTP and verifyStageTwo):
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

# Validate if recent volume is lowest of last 'N' Days
def validateLowestVolume(data, daysForLowestVolume):
    if daysForLowestVolume == None:
        daysForLowestVolume = 30
    data = data.head(daysForLowestVolume)
    recent = data.head(1)
    if((recent['Volume'][0] <= data.describe()['Volume']['min']) and recent['Volume'][0] != np.nan):
        return True
    return False

# Save last screened result to pickle file
def setLastScreenedResults(df):
    try:
        df.sort_values(by=['Stock'], ascending=True, inplace=True)
        df.to_pickle(lastScreened)
    except:
        input(colorText.BOLD + colorText.FAIL + '[+] Failed to save recently screened result table on disk! Skipping..' + colorText.END)

# Load last screened result to pickle file
def getLastScreenedResults():
    try:
        df = pd.read_pickle(lastScreened)
        print(colorText.BOLD + colorText.GREEN + '\n[+] Showing recently screened results..\n' + colorText.END)
        print(tabulate(df, headers='keys', tablefmt='psql'))
        input(colorText.BOLD + colorText.GREEN + '[+] Press any key to continue..' + colorText.END)
    except:
        print(colorText.BOLD + colorText.FAIL + '[+] Failed to load recently screened result table from disk! Skipping..' + colorText.END)


# Manage Execution flow
def initExecution():
    print(colorText.BOLD + colorText.WARN + '[+] Press a number to start stock screening: ' + colorText.END)
    print(colorText.BOLD + '''    0 > Screen stocks by stock name (NSE Stock Code)
    1 > Screen stocks for Breakout or Consolidation
    2 > Screen for the stocks with recent Breakout & Volume
    3 > Screen for the Consolidating stocks
    4 > Screen for the stocks with Lowest Volume in last 'N'-days (Early Breakout Detection)
    5 > Edit user configuration
    6 > Show user configuration
    7 > Show Last Screened Results
    8 > About Developer
    9 > Exit''' + colorText.END
    )
    result = input(colorText.BOLD + colorText.FAIL + '[+] Select option: ')
    print(colorText.END, end='')
    try:
        result = int(result)
        if(result < 0 or result > 9):
            raise ValueError
        return result
    except:
        print(colorText.BOLD + colorText.FAIL + '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        clearScreen()
        return initExecution()

# Print about developers and repository
def showDevInfo():
        print('\n'+changelog)
        print(colorText.BOLD + colorText.WARN + "\n[+] Developer: Pranjal Joshi." + colorText.END)
        print(colorText.BOLD + colorText.WARN + ("[+] Version: %s" % VERSION) + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] More: https://github.com/pranjal-joshi/Screeni-py" + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] Post Feedback/Issues here: https://github.com/pranjal-joshi/Screeni-py/issues" + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] Download latest software from https://github.com/pranjal-joshi/Screeni-py/releases/latest" + colorText.END)
        input('')

# Main function
def main():
    global daysForLowestVolume, screenResults, saveResults, screenCounter
    screenCounter = 1
    screenResults = pd.DataFrame(columns=['Stock','Consolidating','Breaking-Out','MA-Signal','Volume','LTP','Pattern'])
    saveResults = pd.DataFrame(columns=['Stock','Consolidating','Breaking-Out','MA-Signal','Volume','LTP','Pattern'])
    executeOption = initExecution()
    if executeOption == 4:
        try:
            daysForLowestVolume = int(input(colorText.BOLD + colorText.WARN + '\n[+] The Volume should be lowest since last how many candles? '))
        except ValueError:
            print(colorText.END)
            print(colorText.BOLD + colorText.FAIL + '[+] Error: Non-numeric value entered! Screening aborted.' + colorText.END)
            input('')
            main()
        print(colorText.END)
    if executeOption == 5:
        ConfigManager.tools.setConfig(ConfigManager.parser)
        main()
    if executeOption == 6:
        ConfigManager.tools.showConfigFile()
        main()
    if executeOption == 7:
        getLastScreenedResults()
        main()
    if executeOption == 8:
        showDevInfo()
        main()
    if executeOption == 9:
        print(colorText.BOLD + colorText.FAIL + "[+] Script terminated by the user." + colorText.END)
        sys.exit(0)
    if executeOption >= 0 and executeOption < 5:
        ConfigManager.tools.getConfig(ConfigManager.parser)
        try:
            Fetcher.tools.fetchStockCodes(executeOption)
        except urllib.error.URLError:
            print(colorText.BOLD + colorText.FAIL + "\n\n[+] Oops! It looks like you don't have an Internet connectivity at the moment! Press any key to exit!" + colorText.END)
            input('')
            sys.exit(0)
        print(colorText.BOLD + colorText.WARN + "[+] Starting Stock Screening.. Press Ctrl+C to stop!\n")
        for stock in Fetcher.listStockCodes:
            try:
                data = Fetcher.tools.fetchStockData(stock, 
                            ConfigManager.period,
                            ConfigManager.duration,
                            proxyServer,
                            screenResults
                        )
                fullData, processedData = preprocessData(data, daysToLookback=ConfigManager.daysToLookback)
                if not processedData.empty:
                    screeningDictionary['Stock'] = colorText.BOLD + colorText.BLUE + stock + colorText.END
                    saveDictionary['Stock'] = stock
                    consolidationValue = validateConsolidation(processedData, screeningDictionary, saveDictionary, percentage=consolidationPercentage)
                    validateMovingAverages(processedData, screeningDictionary, saveDictionary)
                    isVolumeHigh = validateVolume(processedData, screeningDictionary, saveDictionary, volumeRatio=volumeRatio)
                    isBreaking = findBreakout(processedData, screeningDictionary, saveDictionary, daysToLookback=daysToLookback)
                    isLtpValid = validateLTP(fullData, screeningDictionary, saveDictionary, minLTP=minLTP, maxLTP=maxLTP)
                    isLowestVolume = validateLowestVolume(processedData, daysForLowestVolume)
                    isCandlePattern = candlePatterns.findPattern(processedData, screeningDictionary, saveDictionary)
                    if executeOption == 0:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if (executeOption == 1 or executeOption == 2) and isBreaking and isVolumeHigh and isLtpValid:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if (executeOption == 1 or executeOption == 3) and (consolidationValue <= consolidationPercentage and consolidationValue != 0) and isLtpValid:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if executeOption == 4 and isLtpValid and isLowestVolume:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
            except KeyboardInterrupt:
                print(colorText.BOLD + colorText.FAIL + "\n[+] Script terminated by the user." + colorText.END)
                break
            except Exception as e:
                print(colorText.FAIL + ("[+] Exception Occured while Screening %s! Skipping this stock.." % stock) + colorText.END)
                print(e)
                raise(e)
        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        print(tabulate(screenResults, headers='keys', tablefmt='psql'))
        filename = 'screenipy-result_'+datetime.datetime.now().strftime("%d-%m-%y_%H.%M.%S")+".xlsx"
        saveResults.to_excel(filename)
        setLastScreenedResults(screenResults)
        print(colorText.BOLD + colorText.GREEN + "[+] Results saved to screenipy-result.xlsx" + colorText.END)
        print(colorText.BOLD + colorText.GREEN + "[+] Screening Completed! Happy Trading! :)" + colorText.END)
        input('')
        main()

if __name__ == "__main__":
    clearScreen()
    OTAUpdater.checkForUpdate(proxyServer, VERSION)
    main()