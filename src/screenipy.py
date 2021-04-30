#!/usr/bin/python3

# Pyinstaller compile Windows: pyinstaller --onefile --icon=src\icon.ico src\screenipy.py  --hidden-import cmath --hidden-import talib.stream
# Pyinstaller compile Linux  : pyinstaller --onefile --icon=src/icon.ico src/screenipy.py  --hidden-import cmath --hidden-import talib.stream

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
import classes.Fetcher as Fetcher
import classes.ConfigManager as ConfigManager
import classes.Screener as Screener
import classes.Utility as Utility
from classes.ColorText import colorText
from classes.OtaUpdater import OTAUpdater
from classes.CandlePatterns import CandlePatterns
from classes.Changelog import *

# Try Fixing bug with this symbol
TEST_STKCODE = "SBIN"

# Constants
daysForLowestVolume = 30
np.seterr(divide='ignore', invalid='ignore')

# Global Variabls
candlePatterns = CandlePatterns()
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
        Utility.tools.clearScreen()
        return initExecution()

# Main function
def main(testing=False):
    global daysForLowestVolume, screenResults, saveResults
    Fetcher.screenCounter = 1
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
        Utility.tools.getLastScreenedResults()
        main()
    if executeOption == 8:
        Utility.tools.showDevInfo()
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
                fullData, processedData = Screener.tools.preprocessData(data, daysToLookback=ConfigManager.daysToLookback)
                if not processedData.empty:
                    screeningDictionary['Stock'] = colorText.BOLD + colorText.BLUE + stock + colorText.END
                    saveDictionary['Stock'] = stock
                    consolidationValue = Screener.tools.validateConsolidation(processedData, screeningDictionary, saveDictionary, percentage=ConfigManager.consolidationPercentage)
                    Screener.tools.validateMovingAverages(processedData, screeningDictionary, saveDictionary)
                    isVolumeHigh = Screener.tools.validateVolume(processedData, screeningDictionary, saveDictionary, volumeRatio=ConfigManager.volumeRatio)
                    isBreaking = Screener.tools.findBreakout(processedData, screeningDictionary, saveDictionary, daysToLookback=ConfigManager.daysToLookback)
                    isLtpValid = Screener.tools.validateLTP(fullData, screeningDictionary, saveDictionary, minLTP=ConfigManager.minLTP, maxLTP=ConfigManager.maxLTP)
                    isLowestVolume = Screener.tools.validateLowestVolume(processedData, daysForLowestVolume)
                    isCandlePattern = candlePatterns.findPattern(processedData, screeningDictionary, saveDictionary)
                    if executeOption == 0:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if (executeOption == 1 or executeOption == 2) and isBreaking and isVolumeHigh and isLtpValid:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if (executeOption == 1 or executeOption == 3) and (consolidationValue <= ConfigManager.consolidationPercentage and consolidationValue != 0) and isLtpValid:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                    if executeOption == 4 and isLtpValid and isLowestVolume:
                        screenResults = screenResults.append(screeningDictionary,ignore_index=True)
                        saveResults = saveResults.append(saveDictionary, ignore_index=True)
                if testing and len(screenResults):
                    break
            except KeyboardInterrupt:
                print(colorText.BOLD + colorText.FAIL + "\n[+] Script terminated by the user." + colorText.END)
                break
            except Exception as e:
                print(colorText.FAIL + ("[+] Exception Occured while Screening %s! Skipping this stock.." % stock) + colorText.END)
                if testing:
                    raise e
        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        print(tabulate(screenResults, headers='keys', tablefmt='psql'))
        filename = 'screenipy-result_'+datetime.datetime.now().strftime("%d-%m-%y_%H.%M.%S")+".xlsx"
        saveResults.to_excel(filename)
        Utility.tools.setLastScreenedResults(screenResults)
        print(colorText.BOLD + colorText.GREEN + "[+] Results saved to screenipy-result.xlsx" + colorText.END)
        print(colorText.BOLD + colorText.GREEN + "[+] Screening Completed! Happy Trading! :)" + colorText.END)
        input('')
        main()

if __name__ == "__main__":
    Utility.tools.clearScreen()
    OTAUpdater.checkForUpdate(proxyServer, VERSION)
    main()