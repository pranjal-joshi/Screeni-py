#!/usr/bin/python3

# Pyinstaller compile Windows: pyinstaller --onefile --icon=src\icon.ico src\screenipy.py  --hidden-import cmath --hidden-import talib.stream --hidden-import numpy --hidden-import pandas --hidden-import alive-progress
# Pyinstaller compile Linux  : pyinstaller --onefile --icon=src/icon.ico src/screenipy.py  --hidden-import cmath --hidden-import talib.stream --hidden-import numpy --hidden-import pandas --hidden-import alive-progress

# Keep module imports prior to classes
import classes.Fetcher as Fetcher
import classes.ConfigManager as ConfigManager
import classes.Screener as Screener
import classes.Utility as Utility
from classes.ColorText import colorText
from classes.OtaUpdater import OTAUpdater
from classes.CandlePatterns import CandlePatterns
from classes.ParallelProcessing import StockConsumer
from classes.Changelog import VERSION
from alive_progress import alive_bar
import argparse
import os
import platform
import sys
import urllib
import numpy as np
import pandas as pd
from datetime import datetime
from time import sleep
from tabulate import tabulate
import multiprocessing
multiprocessing.freeze_support()

# Argument Parsing for test purpose
argParser = argparse.ArgumentParser()
argParser.add_argument('-t', '--testbuild', action='store_true', help='Run in test-build mode', required=False)
argParser.add_argument('-d', '--download', action='store_true', help='Only Download Stock data in .pkl file', required=False)
argParser.add_argument('-v', action='store_true')        # Dummy Arg for pytest -v
args = argParser.parse_args()

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
maLength = None
newlyListedOnly = False

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
    global newlyListedOnly
    print(colorText.BOLD + colorText.WARN +
          '[+] Select an Index for Screening: ' + colorText.END)
    print(colorText.BOLD + '''     W > Screen stocks from my own Watchlist
     0 > Screen stocks by the stock names (NSE Stock Code)
     1 > Nifty 50               2 > Nifty Next 50           3 > Nifty 100
     4 > Nifty 200              5 > Nifty 500               6 > Nifty Smallcap 50
     7 > Nifty Smallcap 100     8 > Nifty Smallcap 250      9 > Nifty Midcap 50
    10 > Nifty Midcap 100      11 > Nifty Midcap 150       13 > Newly Listed (IPOs in last 2 Year)
    Enter > All Stocks (default) ''' + colorText.END
          )
    try:
        tickerOption = input(
            colorText.BOLD + colorText.FAIL + '[+] Select option: ')
        print(colorText.END, end='')
        if tickerOption == '':
            tickerOption = 12
        elif tickerOption == 'W' or tickerOption == 'w':
            tickerOption = tickerOption.upper()
        else:
            tickerOption = int(tickerOption)
            if(tickerOption < 0 or tickerOption > 13):
                raise ValueError
            elif tickerOption == 13:
                newlyListedOnly = True
                tickerOption = 12
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        print(colorText.BOLD + colorText.FAIL +
              '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        Utility.tools.clearScreen()
        return initExecution()

    if tickerOption and tickerOption != 'W':
        print(colorText.BOLD + colorText.WARN +
            '\n[+] Select a Critera for Stock Screening: ' + colorText.END)
        print(colorText.BOLD + '''
    0 > Full Screening (Shows Technical Parameters without Any Criteria)
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
    11 > Help / About Developer
    12 > Exit''' + colorText.END
            )
    try:
        if tickerOption and tickerOption != 'W':
            executeOption = input(
                colorText.BOLD + colorText.FAIL + '[+] Select option: ')
            print(colorText.END, end='')
            if executeOption == '':
                executeOption = 0
            executeOption = int(executeOption)
            if(executeOption < 0 or executeOption > 12):
                raise ValueError
        else:
            executeOption = 0
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        print(colorText.BOLD + colorText.FAIL +
              '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        Utility.tools.clearScreen()
        return initExecution()
    return tickerOption, executeOption

# Main function
def main(testing=False, testBuild=False, downloadOnly=False):
    global screenCounter, screenResultsCounter, stockDict, loadedStockData, keyboardInterruptEvent, loadCount, maLength, newlyListedOnly
    screenCounter = multiprocessing.Value('i', 1)
    screenResultsCounter = multiprocessing.Value('i', 0)
    keyboardInterruptEvent = multiprocessing.Manager().Event()

    if stockDict is None:
        stockDict = multiprocessing.Manager().dict()
        loadCount = 0

    minRSI = 0
    maxRSI = 100
    insideBarToLookback = 7
    respChartPattern = 1
    daysForLowestVolume = 30
    reversalOption = None

    screenResults = pd.DataFrame(columns=[
                                 'Stock', 'Consolidating', 'Breaking-Out', 'LTP', 'Volume', 'MA-Signal', 'RSI', 'Trend', 'Pattern'])
    saveResults = pd.DataFrame(columns=[
                               'Stock', 'Consolidating', 'Breaking-Out', 'LTP', 'Volume', 'MA-Signal', 'RSI', 'Trend', 'Pattern'])

    
    if testBuild:
        tickerOption, executeOption = 1, 0
    elif downloadOnly:
        tickerOption, executeOption = 12, 2
    else:
        try:
            tickerOption, executeOption = initExecution()
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
        reversalOption, maLength = Utility.tools.promptReversalScreening()
        if reversalOption is None or reversalOption == 0:
            main()
    if executeOption == 7:
        respChartPattern, insideBarToLookback = Utility.tools.promptChartPatterns()
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

    if tickerOption == 'W' or (tickerOption >= 0 and tickerOption < 14):
        configManager.getConfig(ConfigManager.parser)
        try:
            if tickerOption == 'W':
                listStockCodes = fetcher.fetchWatchlist()
                if listStockCodes is None:
                    input(colorText.BOLD + colorText.FAIL +
                          f'[+] Create the watchlist.xlsx file in {os.getcwd()} and Restart the Program!' + colorText.END)
                    sys.exit(0)
            else:
                listStockCodes = fetcher.fetchStockCodes(tickerOption, proxyServer=proxyServer)
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

        items = [(executeOption, reversalOption, maLength, daysForLowestVolume, minRSI, maxRSI, respChartPattern, insideBarToLookback, len(listStockCodes),
                  configManager, fetcher, screener, candlePatterns, stock, newlyListedOnly, downloadOnly)
                 for stock in listStockCodes]

        tasks_queue = multiprocessing.JoinableQueue()
        results_queue = multiprocessing.Queue()

        totalConsumers = multiprocessing.cpu_count()
        if totalConsumers == 1:
            totalConsumers = 2      # This is required for single core machine
        if configManager.cacheEnabled is True and multiprocessing.cpu_count() > 2:
            totalConsumers -= 1
        consumers = [StockConsumer(tasks_queue, results_queue, screenCounter, screenResultsCounter, stockDict, proxyServer, keyboardInterruptEvent)
                     for _ in range(totalConsumers)]

        for worker in consumers:
            worker.daemon = True
            worker.start()

        if testing or testBuild:
            for item in items:
                tasks_queue.put(item)
                result = results_queue.get()
                if result is not None:
                    screenResults = screenResults.append(
                        result[0], ignore_index=True)
                    saveResults = saveResults.append(
                        result[1], ignore_index=True)
                    if testing or (testBuild and len(screenResults) > 2):
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
                with alive_bar(numStocks, bar=bar, spinner=spinner) as progressbar:
                    while numStocks:
                        result = results_queue.get()
                        if result is not None:
                            screenResults = screenResults.append(
                                result[0], ignore_index=True)
                            saveResults = saveResults.append(
                                result[1], ignore_index=True)
                        numStocks -= 1
                        progressbar.text(colorText.BOLD + colorText.GREEN +
                                         f'Found {screenResultsCounter.value} Stocks' + colorText.END)
                        progressbar()
            except KeyboardInterrupt:
                try:
                    keyboardInterruptEvent.set()
                except KeyboardInterrupt:
                    pass
                print(colorText.BOLD + colorText.FAIL +
                      "\n[+] Terminating Script, Please wait..." + colorText.END)
                for worker in consumers:
                    worker.terminate()

        print(colorText.END)
        # Exit all processes. Without this, it threw error in next screening session
        for worker in consumers:
            try:
                worker.terminate()
            except OSError as e:
                if e.winerror == 5:
                    pass

        # Flush the queue so depending processes will end
        from queue import Empty
        while True:
            try:
                _ = tasks_queue.get(False)
            except Exception as e:
                break

        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        screenResults.set_index('Stock', inplace=True)
        saveResults.set_index('Stock', inplace=True)
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
                'Breaking-Out': f'Breakout ({configManager.daysToLookback}Days)'
            },
            inplace=True
        )
        print(tabulate(screenResults, headers='keys', tablefmt='psql'))

        print(colorText.BOLD + colorText.GREEN +
                  f"[+] Found {len(screenResults)} Stocks." + colorText.END)
        if configManager.cacheEnabled and not Utility.tools.isTradingTime() and not testing:
            print(colorText.BOLD + colorText.GREEN +
                  "[+] Caching Stock Data for future use, Please Wait... " + colorText.END, end='')
            Utility.tools.saveStockData(
                stockDict, configManager, loadCount)

        Utility.tools.setLastScreenedResults(screenResults)
        if not testBuild and not downloadOnly:
            Utility.tools.promptSaveResults(saveResults)
            print(colorText.BOLD + colorText.WARN +
                "[+] Note: Trend calculation is based on number of days recent to screen as per your configuration." + colorText.END)
            print(colorText.BOLD + colorText.GREEN +
                "[+] Screening Completed! Press Enter to Continue.." + colorText.END)
            input('')
        newlyListedOnly = False


if __name__ == "__main__":
    Utility.tools.clearScreen()
    isDevVersion = OTAUpdater.checkForUpdate(proxyServer, VERSION)
    if not configManager.checkConfigFile():
        configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
    if args.testbuild:
        print(colorText.BOLD + colorText.FAIL +"[+] Started in TestBuild mode!" + colorText.END)
        main(testBuild=True)
    elif args.download:
        print(colorText.BOLD + colorText.FAIL +"[+] Download ONLY mode! Stocks will not be screened!" + colorText.END)
        main(downloadOnly=True)
    else:
        try:
            while True:
                main()
        except Exception as e:
            if isDevVersion == OTAUpdater.developmentVersion:
                raise(e)
            input(colorText.BOLD + colorText.FAIL +
                "[+] Press any key to Exit!" + colorText.END)
            sys.exit(0)
