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
import multiprocessing
import platform
import datetime
import classes.Fetcher as Fetcher
import classes.ConfigManager as ConfigManager
import classes.Screener as Screener
import classes.Utility as Utility
from classes.ColorText import colorText
from classes.OtaUpdater import OTAUpdater
from classes.CandlePatterns import CandlePatterns
from classes.SuppressOutput import SuppressOutput
from classes.Changelog import *

# Try Fixing bug with this symbol
TEST_STKCODE = "SBIN"

# Constants
np.seterr(divide='ignore', invalid='ignore')

# Global Variabls
candlePatterns = CandlePatterns()


# Get system wide proxy for networking
try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

# Manage Execution flow


def initExecution():
    print(colorText.BOLD + colorText.WARN +
          '[+] Press a number to start stock screening: ' + colorText.END)
    print(colorText.BOLD + '''     0 > Screen stocks by stock name (NSE Stock Code)
     1 > Screen stocks for Breakout or Consolidation
     2 > Screen for the stocks with recent Breakout & Volume
     3 > Screen for the Consolidating stocks
     4 > Screen for the stocks with Lowest Volume in last 'N'-days (Early Breakout Detection)
     5 > Screen for the stocks with RSI
     6 > Screen for the stocks showing Reversal Signals
     7 > Screen for the stocks making Chart Patterns
     8 > Edit user configuration
     9 > Show user configuration
    10 > Show Last Screened Results
    11 > About Developer
    12 > Exit''' + colorText.END
          )
    result = input(colorText.BOLD + colorText.FAIL + '[+] Select option: ')
    print(colorText.END, end='')
    try:
        result = int(result)
        if(result < 0 or result > 12):
            raise ValueError
        return result
    except:
        print(colorText.BOLD + colorText.FAIL +
              '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        Utility.tools.clearScreen()
        return initExecution()


def screenStocks(executeOption, reversalOption, daysForLowestVolume, minRSI, maxRSI, respBullBear, insideBarToLookback, stock):
    screenResults = pd.DataFrame(columns=[
        'Stock', 'Consolidating', 'Breaking-Out', 'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])
    screeningDictionary = {'Stock': "", 'Consolidating': "",  'Breaking-Out': "",
                           'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}
    saveDictionary = {'Stock': "", 'Pattern': "", 'Consolidating': "", 'Breaking-Out': "",
                      'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}

    try:
        data = Fetcher.tools.fetchStockData(stock,
                                            ConfigManager.period,
                                            ConfigManager.duration,
                                            proxyServer,
                                            screenResults)
        fullData, processedData = Screener.tools.preprocessData(
            data, daysToLookback=ConfigManager.daysToLookback)
        if not processedData.empty:
            screeningDictionary['Stock'] = colorText.BOLD + \
                colorText.BLUE + stock + colorText.END
            saveDictionary['Stock'] = stock
            consolidationValue = Screener.tools.validateConsolidation(
                processedData, screeningDictionary, saveDictionary, percentage=ConfigManager.consolidationPercentage)
            isMaReversal = Screener.tools.validateMovingAverages(
                processedData, screeningDictionary, saveDictionary, range=1.25)
            isVolumeHigh = Screener.tools.validateVolume(
                processedData, screeningDictionary, saveDictionary, volumeRatio=ConfigManager.volumeRatio)
            isBreaking = Screener.tools.findBreakout(
                processedData, screeningDictionary, saveDictionary, daysToLookback=ConfigManager.daysToLookback)
            isLtpValid = Screener.tools.validateLTP(
                fullData, screeningDictionary, saveDictionary, minLTP=ConfigManager.minLTP, maxLTP=ConfigManager.maxLTP)
            isLowestVolume = Screener.tools.validateLowestVolume(
                processedData, daysForLowestVolume)
            isValidRsi = Screener.tools.validateRSI(
                processedData, screeningDictionary, saveDictionary, minRSI, maxRSI)
            currentTrend = Screener.tools.findTrend(
                processedData, screeningDictionary, saveDictionary, daysToLookback=ConfigManager.daysToLookback, stockName=stock)
            isCandlePattern = candlePatterns.findPattern(
                processedData, screeningDictionary, saveDictionary)
            isInsideBar = Screener.tools.validateInsideBar(
                processedData, screeningDictionary, saveDictionary, bullBear=respBullBear, daysToLookback=insideBarToLookback)

            if executeOption == 0:
                return screeningDictionary, saveDictionary
            if (executeOption == 1 or executeOption == 2) and isBreaking and isVolumeHigh and isLtpValid:
                return screeningDictionary, saveDictionary
            if (executeOption == 1 or executeOption == 3) and (consolidationValue <= ConfigManager.consolidationPercentage and consolidationValue != 0) and isLtpValid:
                return screeningDictionary, saveDictionary
            if executeOption == 4 and isLtpValid and isLowestVolume:
                return screeningDictionary, saveDictionary
            if executeOption == 5 and isLtpValid and isValidRsi:
                return screeningDictionary, saveDictionary
            if executeOption == 6 and isLtpValid:
                if reversalOption == 1:
                    if saveDictionary['Pattern'] in CandlePatterns.reversalPatternsBullish or isMaReversal > 0:
                        return screeningDictionary, saveDictionary
                elif reversalOption == 2:
                    if saveDictionary['Pattern'] in CandlePatterns.reversalPatternsBearish or isMaReversal < 0:
                        return screeningDictionary, saveDictionary
            if executeOption == 7 and isLtpValid and isInsideBar:
                return screeningDictionary, saveDictionary
    except KeyboardInterrupt:
        print(colorText.BOLD + colorText.FAIL +
              "\n[+] Script terminated by the user." + colorText.END)
    except Fetcher.StockDataEmptyException:
        pass
    except Exception as e:
        print(colorText.FAIL +
              ("\n[+] Exception Occured while Screening %s! Skipping this stock.." % stock) + colorText.END)
    return

# Main function


def main(testing=False):

    screenResults = pd.DataFrame(columns=[
        'Stock', 'Consolidating', 'Breaking-Out', 'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])
    saveResults = pd.DataFrame(columns=['Stock', 'Consolidating', 'Breaking-Out',
                                        'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])
    Fetcher.screenCounter = 1
    minRSI = 0
    maxRSI = 100
    insideBarToLookback = 7
    respBullBear = 1
    daysForLowestVolume = 30
    reversalOption = None

    executeOption = initExecution()
    if executeOption == 4:
        try:
            daysForLowestVolume = int(input(colorText.BOLD + colorText.WARN +
                                            '\n[+] The Volume should be lowest since last how many candles? '))
        except ValueError:
            print(colorText.END)
            print(colorText.BOLD + colorText.FAIL +
                  '[+] Error: Non-numeric value entered! Screening aborted.' + colorText.END)
            input('')
            main()
        print(colorText.END)
    if executeOption == 5:
        minRSI, maxRSI = Utility.tools.promptRSIValues()
        if (not minRSI and not maxRSI):
            print(colorText.BOLD + colorText.FAIL +
                  '\n[+] Error: Invalid values for RSI! Values should be in range of 0 to 100. Screening aborted.' + colorText.END)
            input('')
            main()
    if executeOption == 6:
        reversalOption = Utility.tools.promptReversalScreening()
        if reversalOption == None or reversalOption == 0:
            main()
    if executeOption == 7:
        respBullBear, insideBarToLookback = Utility.tools.promptChartPatterns()
        if insideBarToLookback == None:
            main()
    if executeOption == 8:
        ConfigManager.tools.setConfig(ConfigManager.parser)
        main()
    if executeOption == 9:
        ConfigManager.tools.showConfigFile()
        main()
    if executeOption == 10:
        Utility.tools.getLastScreenedResults()
        main()
    if executeOption == 11:
        Utility.tools.showDevInfo()
        main()
    if executeOption == 12:
        print(colorText.BOLD + colorText.FAIL +
              "[+] Script terminated by the user." + colorText.END)
        sys.exit(0)
    if executeOption >= 0 and executeOption < 8:
        ConfigManager.tools.getConfig(ConfigManager.parser)
        try:
            Fetcher.tools.fetchStockCodes(executeOption)
        except urllib.error.URLError:
            print(colorText.BOLD + colorText.FAIL +
                  "\n\n[+] Oops! It looks like you don't have an Internet connectivity at the moment! Press any key to exit!" + colorText.END)
            input('')
            sys.exit(0)
        print(colorText.BOLD + colorText.WARN +
              "[+] Starting Stock Screening.. Press Ctrl+C to stop!\n")

        items = [(executeOption, reversalOption, daysForLowestVolume, minRSI, maxRSI, respBullBear, insideBarToLookback, stock)
                 for stock in Fetcher.listStockCodes]
        results = pool.starmap(screenStocks, items)
        results = list(filter(None, results))
        for x, y in results:
            screenResults = screenResults.append(x, ignore_index=True)
            saveResults = saveResults.append(y, ignore_index=True)

        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        screenResults.rename(
            columns={
                'Trend': f'Trend ({ConfigManager.daysToLookback}Days)',
                'Breaking-Out': 'Breakout-Levels'
            },
            inplace=True
        )
        saveResults.rename(
            columns={
                'Trend': f'Trend ({ConfigManager.daysToLookback}Days)',
                'Breaking-Out': 'Breakout-Levels'
            },
            inplace=True
        )
        print(tabulate(screenResults, headers='keys', tablefmt='psql'))
        Utility.tools.setLastScreenedResults(screenResults)
        Utility.tools.promptSaveResults(saveResults)
        print(colorText.BOLD + colorText.WARN +
              "[+] Note: Trend calculation is based on number of days recent to screen as per your configuration." + colorText.END)
        print(colorText.BOLD + colorText.GREEN +
              "[+] Screening Completed! Happy Trading! :)" + colorText.END)
        input('')
        main()


if __name__ == "__main__":
    Utility.tools.clearScreen()
    OTAUpdater.checkForUpdate(proxyServer, VERSION)
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    main()
