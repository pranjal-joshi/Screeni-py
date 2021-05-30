#!/usr/bin/python3

# Pyinstaller compile Windows: pyinstaller --onefile --icon=src\icon.ico src\screenipy.py  --hidden-import cmath --hidden-import talib.stream
# Pyinstaller compile Linux  : pyinstaller --onefile --icon=src/icon.ico src/screenipy.py  --hidden-import cmath --hidden-import talib.stream

# Keep module imports prior to classes
import multiprocessing
multiprocessing.freeze_support()
from time import sleep
from tabulate import tabulate
from datetime import datetime
import pandas as pd
import numpy as np
import urllib
import sys
import platform
import os
from alive_progress import alive_bar
from classes.Changelog import VERSION
from classes.ParallelProcessing import StockConsumer
from classes.CandlePatterns import CandlePatterns
from classes.OtaUpdater import OTAUpdater
from classes.ColorText import colorText
import classes.Utility as Utility
import classes.Screener as Screener
import classes.ConfigManager as ConfigManager
import classes.Fetcher as Fetcher

# Try Fixing bug with this symbol
TEST_STKCODE = "SBIN"

# Constants
np.seterr(divide='ignore', invalid='ignore')

# Global Variabls
screenCounter = None
screenResultsCounter = None
stockDict = None
keyboardInterruptEvent = None
loadedStockData = False
loadCount = 0

configManager = ConfigManager.tools()
fetcher = Fetcher.tools(configManager)
screener = Screener.tools(configManager)
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
    print(colorText.BOLD + '''     W > Screen stocks from the Watchlist
     0 > Screen stocks by stock name (NSE Stock Code)
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
    try:
        result = input(colorText.BOLD + colorText.FAIL + '[+] Select option: ')
        print(colorText.END, end='')
        if isinstance(result, str) and result.upper() == 'W':
            return result.upper()
        result = int(result)
        if(result < 0 or result > 12):
            raise ValueError
        return result
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        print(colorText.BOLD + colorText.FAIL +
              '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        Utility.tools.clearScreen()
        return initExecution()

# Main function


def main(testing=False):
    global screenCounter, screenResultsCounter, stockDict, loadedStockData, keyboardInterruptEvent, loadCount
    screenCounter = multiprocessing.Value('i', 1)
    screenResultsCounter = multiprocessing.Value('i', 0)
    keyboardInterruptEvent = multiprocessing.Manager().Event()

    if stockDict is None:
        stockDict = multiprocessing.Manager().dict()
        loadCount = 0

    minRSI = 0
    maxRSI = 100
    insideBarToLookback = 7
    respBullBear = 1
    daysForLowestVolume = 30
    reversalOption = None

    screenResults = pd.DataFrame(columns=[
                                 'Stock', 'Consolidating', 'Breaking-Out', 'LTP', 'Volume', 'MA-Signal', 'RSI', 'Trend', 'Pattern'])
    saveResults = pd.DataFrame(columns=[
                               'Stock', 'Consolidating', 'Breaking-Out', 'LTP', 'Volume', 'MA-Signal', 'RSI', 'Trend', 'Pattern'])

    try:
        executeOption = initExecution()
    except KeyboardInterrupt:
        input(colorText.BOLD + colorText.FAIL +
              "[+] Press any key to Exit!" + colorText.END)
        sys.exit(0)

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
        if reversalOption is None or reversalOption == 0:
            main()
    if executeOption == 7:
        respBullBear, insideBarToLookback = Utility.tools.promptChartPatterns()
        if insideBarToLookback is None:
            main()
    if executeOption == 8:
        configManager.setConfig(ConfigManager.parser)
        main()
    if executeOption == 9:
        configManager.showConfigFile()
        main()
    if executeOption == 10:
        Utility.tools.getLastScreenedResults()
        main()
    if executeOption == 11:
        Utility.tools.showDevInfo()
        main()
    if executeOption == 12:
        input(colorText.BOLD + colorText.FAIL +
              "[+] Press any key to Exit!" + colorText.END)
        sys.exit(0)
    if executeOption == 'W' or (executeOption >= 0 and executeOption < 8):
        configManager.getConfig(ConfigManager.parser)
        try:
            if executeOption == 'W':
                listStockCodes = fetcher.fetchWatchlist()
                if listStockCodes is None:
                    input(colorText.BOLD + colorText.FAIL + f'[+] Create the watchlist.xlsx file in {os.getcwd()} and Restart the Program!' + colorText.END)                    
                    sys.exit(0)
            else:
                listStockCodes = fetcher.fetchStockCodes(executeOption)
        except urllib.error.URLError:
            print(colorText.BOLD + colorText.FAIL +
                  "\n\n[+] Oops! It looks like you don't have an Internet connectivity at the moment! Press any key to exit!" + colorText.END)
            input('')
            sys.exit(0)
        
        if not Utility.tools.isTradingTime() and configManager.cacheEnabled and not loadedStockData and not testing:
            Utility.tools.loadStockData(stockDict)
            loadedStockData = True
        loadCount = len(stockDict)

        print(colorText.BOLD + colorText.WARN +
              "[+] Starting Stock Screening.. Press Ctrl+C to stop!\n")

        items = [(executeOption, reversalOption, daysForLowestVolume, minRSI, maxRSI, respBullBear, insideBarToLookback, len(listStockCodes),
                  configManager, fetcher, screener, candlePatterns, stock)
                 for stock in listStockCodes]

        tasks_queue = multiprocessing.JoinableQueue()
        results_queue = multiprocessing.Queue()

        totalConsumers = multiprocessing.cpu_count()
        if totalConsumers == 1:
            totalConsumers = 2      # This is required for single core machine
        if configManager.cacheEnabled is True and multiprocessing.cpu_count() != 1:
            totalConsumers -= 1
        consumers = [StockConsumer(tasks_queue, results_queue, screenCounter, screenResultsCounter, stockDict, proxyServer, keyboardInterruptEvent)
                     for _ in range(totalConsumers)]

        for worker in consumers:
            worker.daemon = True
            worker.start()

        if testing:
            for item in items:
                tasks_queue.put(item)
                result = results_queue.get()
                if result is not None:
                    screenResults = screenResults.append(
                        result[0], ignore_index=True)
                    saveResults = saveResults.append(
                        result[1], ignore_index=True)
                    break
        else:
            for item in items:
                tasks_queue.put(item)
            # Append exit signal for each process indicated by None
            for _ in range(multiprocessing.cpu_count()):
                tasks_queue.put(None)
            try:
                numStocks = len(listStockCodes)
                print(colorText.END+colorText.BOLD)
                bar = 'smooth'
                spinner = 'waves'
                if 'Windows' in platform.platform():
                    bar = 'classic2'
                    spinner = 'dots_recur'
                with alive_bar(numStocks,bar=bar,spinner=spinner) as progressbar:
                    while numStocks:
                        result = results_queue.get()
                        if result is not None:
                            screenResults = screenResults.append(
                                result[0], ignore_index=True)
                            saveResults = saveResults.append(
                                result[1], ignore_index=True)
                        numStocks -= 1
                        progressbar.text(colorText.BOLD + colorText.GREEN + f'Found {screenResultsCounter.value} Stocks' + colorText.END)
                        progressbar()
            except KeyboardInterrupt:
                try:
                    keyboardInterruptEvent.set()
                except KeyboardInterrupt:
                    pass
                print(colorText.BOLD + colorText.FAIL +"\n[+] Terminating Script, Please wait..." + colorText.END)
                for worker in consumers:
                    worker.terminate()
        
        print(colorText.END)
        # Exit all processes. Without this, it threw error in next screening session
        for worker in consumers:
            worker.terminate()

        # Flush the queue so depending processes will end
        from queue import Empty
        while True:
            try:
                _ = tasks_queue.get(False)
            except Exception as e:
                break

        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        screenResults.rename(
            columns={
                'Trend': f'Trend ({configManager.daysToLookback}Days)',
                'Breaking-Out': f'Breakout ({configManager.daysToLookback}Days)'
            },
            inplace=True
        )
        saveResults.rename(
            columns={
                'Trend': f'Trend ({configManager.daysToLookback}Days)',
                'Breaking-Out': 'Breakout ({configManager.daysToLookback}Days)'
            },
            inplace=True
        )
        print(tabulate(screenResults, headers='keys', tablefmt='psql'))

        if executeOption != 0 and configManager.cacheEnabled and not Utility.tools.isTradingTime() and not testing:
            print(colorText.BOLD + colorText.GREEN + "[+] Caching Stock Data for future use, Please Wait... " + colorText.END, end='')
            Utility.tools.saveStockData(stockDict, configManager, loadCount, screenCounter.value)

        Utility.tools.setLastScreenedResults(screenResults)
        Utility.tools.promptSaveResults(saveResults)
        print(colorText.BOLD + colorText.WARN +
              "[+] Note: Trend calculation is based on number of days recent to screen as per your configuration." + colorText.END)
        print(colorText.BOLD + colorText.GREEN +
              "[+] Screening Completed! Press Enter to Continue.." + colorText.END)
        input('')


if __name__ == "__main__":
    Utility.tools.clearScreen()
    isDevVersion = OTAUpdater.checkForUpdate(proxyServer, VERSION)
    try:
        while True:
            main()
    except Exception as e:
        if isDevVersion == OTAUpdater.developmentVersion:
            raise(e)
        input(colorText.BOLD + colorText.FAIL +
              "[+] Press any key to Exit!" + colorText.END)
        sys.exit(0)
