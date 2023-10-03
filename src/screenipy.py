#!/usr/bin/python3

# Pyinstaller compile Windows: pyinstaller --onefile --icon=src\icon.ico src\screenipy.py  --hidden-import cmath --hidden-import talib.stream --hidden-import numpy --hidden-import pandas --hidden-import alive-progress --hidden-import chromadb
# Pyinstaller compile Linux  : pyinstaller --onefile --icon=src/icon.ico src/screenipy.py  --hidden-import cmath --hidden-import talib.stream --hidden-import numpy --hidden-import pandas --hidden-import alive-progress --hidden-import chromadb

# Keep module imports prior to classes
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import platform
import sys
import classes.Fetcher as Fetcher
import classes.ConfigManager as ConfigManager
import classes.Screener as Screener
import classes.Utility as Utility
from classes.ColorText import colorText
from classes.OtaUpdater import OTAUpdater
from classes.CandlePatterns import CandlePatterns
from classes.ParallelProcessing import StockConsumer
from classes.Changelog import VERSION
from classes.Utility import isDocker, isGui
from alive_progress import alive_bar
import argparse
import urllib
import numpy as np
import pandas as pd
from datetime import datetime
from time import sleep
from tabulate import tabulate
import multiprocessing
multiprocessing.freeze_support()
try:
    import chromadb
    CHROMA_AVAILABLE = True
except:
    CHROMA_AVAILABLE = False

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
vectorSearch = False

CHROMADB_PATH = "chromadb_store/"

configManager = ConfigManager.tools()
fetcher = Fetcher.tools(configManager)
screener = Screener.tools(configManager)
candlePatterns = CandlePatterns()

# Get system wide proxy for networking
try:
    proxyServer = urllib.request.getproxies()['http']
except KeyError:
    proxyServer = ""

# Clear chromadb store initially
if CHROMA_AVAILABLE:
    chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH)
    try:
        chroma_client.delete_collection("nse_stocks")
    except:
        pass


# Manage Execution flow


def initExecution():
    global newlyListedOnly
    print(colorText.BOLD + colorText.WARN +
          '[+] Select an Index for Screening: ' + colorText.END)
    print(colorText.BOLD + '''
     W > Screen stocks from my own Watchlist
     N > Nifty Prediction using Artifical Intelligence (Use for Gap-Up/Gap-Down/BTST/STBT)
     E > Live Index Scan : 5 EMA for Intraday
     S > Search for Similar Stocks (forming Similar Chart Pattern)

     0 > Screen stocks by the stock names (NSE Stock Code)
     1 > Nifty 50               2 > Nifty Next 50           3 > Nifty 100
     4 > Nifty 200              5 > Nifty 500               6 > Nifty Smallcap 50
     7 > Nifty Smallcap 100     8 > Nifty Smallcap 250      9 > Nifty Midcap 50
    10 > Nifty Midcap 100      11 > Nifty Midcap 150       13 > Newly Listed (IPOs in last 2 Year)
    14 > F&O Stocks Only 
    Enter > All Stocks (default) ''' + colorText.END
          )
    try:
        tickerOption = input(
            colorText.BOLD + colorText.FAIL + '[+] Select option: ')
        print(colorText.END, end='')
        if tickerOption == '':
            tickerOption = 12
        # elif tickerOption == 'W' or tickerOption == 'w' or tickerOption == 'N' or tickerOption == 'n' or tickerOption == 'E' or tickerOption == 'e':
        elif not tickerOption.isnumeric():
            tickerOption = tickerOption.upper()
        else:
            tickerOption = int(tickerOption)
            if(tickerOption < 0 or tickerOption > 14):
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

    if tickerOption == 'N' or tickerOption == 'E' or tickerOption == 'S':
        return tickerOption, 0

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
            if(executeOption < 0 or executeOption > 14):
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
def main(testing=False, testBuild=False, downloadOnly=False, execute_inputs:list = []):
    global screenCounter, screenResultsCounter, stockDict, loadedStockData, keyboardInterruptEvent, loadCount, maLength, newlyListedOnly, vectorSearch
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
            if execute_inputs != []:
                if not configManager.checkConfigFile():
                    configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
                try:
                    tickerOption, executeOption = int(execute_inputs[0]), int(execute_inputs[1])
                except:
                    tickerOption, executeOption = str(execute_inputs[0]), int(execute_inputs[1])
                if tickerOption == 13:
                    newlyListedOnly = True
                    tickerOption = 12
            else:
                tickerOption, executeOption = initExecution()
        except KeyboardInterrupt:
            if execute_inputs == [] and not isGui():
                input(colorText.BOLD + colorText.FAIL +
                    "[+] Press any key to Exit!" + colorText.END)
            sys.exit(0)

    if executeOption == 4:
        try:
            if execute_inputs != []:
                daysForLowestVolume = int(execute_inputs[2])
            else:
                daysForLowestVolume = int(input(colorText.BOLD + colorText.WARN +
                                            '\n[+] The Volume should be lowest since last how many candles? '))
        except ValueError:
            print(colorText.END)
            print(colorText.BOLD + colorText.FAIL +
                  '[+] Error: Non-numeric value entered! Screening aborted.' + colorText.END)
            if not isGui():
                input('')
                main()
        print(colorText.END)
    if executeOption == 5:
        if execute_inputs != []:
            minRSI, maxRSI = int(execute_inputs[2]), int(execute_inputs[3])
        else:
            minRSI, maxRSI = Utility.tools.promptRSIValues()
        if (not minRSI and not maxRSI):
            print(colorText.BOLD + colorText.FAIL +
                  '\n[+] Error: Invalid values for RSI! Values should be in range of 0 to 100. Screening aborted.' + colorText.END)
            if not isGui():
                input('')
                main()
    if executeOption == 6:
        if execute_inputs != []:
            reversalOption = int(execute_inputs[2])
            try:
                 maLength = int(execute_inputs[3])
            except ValueError:
                pass
        else:
            reversalOption, maLength = Utility.tools.promptReversalScreening()
        if reversalOption is None or reversalOption == 0:
            if not isGui():
                main()
    if executeOption == 7:
        if execute_inputs != []:
            respChartPattern = int(execute_inputs[2])
            try:
                insideBarToLookback = int(execute_inputs[3])
            except ValueError:
                pass
        else:
            respChartPattern, insideBarToLookback = Utility.tools.promptChartPatterns()
        if insideBarToLookback is None:
            if not isGui():
                main()
    if executeOption == 8:
        configManager.setConfig(ConfigManager.parser)
        if not isGui():
            main()
    if executeOption == 9:
        configManager.showConfigFile()
        if not isGui():
            main()
    if executeOption == 10:
        Utility.tools.getLastScreenedResults()
        if not isGui():
            main()
    if executeOption == 11:
        Utility.tools.showDevInfo()
        if not isGui():
            main()
    if executeOption == 12:
        if not isGui():
            input(colorText.BOLD + colorText.FAIL +
              "[+] Press any key to Exit!" + colorText.END)
        sys.exit(0)

    if tickerOption == 'W' or tickerOption == 'N' or tickerOption == 'E' or tickerOption == 'S' or (tickerOption >= 0 and tickerOption < 15):
        configManager.getConfig(ConfigManager.parser)
        try:
            if tickerOption == 'W':
                listStockCodes = fetcher.fetchWatchlist()
                if listStockCodes is None:
                    input(colorText.BOLD + colorText.FAIL +
                          f'[+] Create the watchlist.xlsx file in {os.getcwd()} and Restart the Program!' + colorText.END)
                    sys.exit(0)
            elif tickerOption == 'N':
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
                prediction = screener.getNiftyPrediction(
                    data=fetcher.fetchLatestNiftyDaily(proxyServer=proxyServer), 
                    proxyServer=proxyServer
                )
                input('\nPress any key to Continue...\n')
                return
            elif tickerOption == 'E':
                result_df = pd.DataFrame(columns=['Time','Stock/Index','Action','SL','Target','R:R'])
                last_signal = {}
                first_scan = True
                result_df = screener.monitorFiveEma(        # Dummy scan to avoid blank table on 1st scan
                        proxyServer=proxyServer,
                        fetcher=fetcher,
                        result_df=result_df,
                        last_signal=last_signal
                    )
                try:
                    while True:
                        Utility.tools.clearScreen()
                        last_result_len = len(result_df)
                        result_df = screener.monitorFiveEma(
                            proxyServer=proxyServer,
                            fetcher=fetcher,
                            result_df=result_df,
                            last_signal=last_signal
                        )
                        print(colorText.BOLD + colorText.WARN + '[+] 5-EMA : Live Intraday Scanner \t' + colorText.END + colorText.FAIL + f'Last Scanned: {datetime.now().strftime("%H:%M:%S")}\n' + colorText.END)
                        print(tabulate(result_df, headers='keys', tablefmt='psql'))
                        print('\nPress Ctrl+C to exit.')
                        if len(result_df) != last_result_len and not first_scan:
                            Utility.tools.alertSound(beeps=5)
                        sleep(60)
                        first_scan = False
                except KeyboardInterrupt:
                    if not isGui():
                        input('\nPress any key to Continue...\n')
                    return
            elif tickerOption == 'S':
                if not CHROMA_AVAILABLE:
                    print(colorText.BOLD + colorText.FAIL +
                  "\n\n[+] ChromaDB not available in your environment! You can't use this feature!\n" + colorText.END)
                else:
                    if execute_inputs != []:
                        stockCode, candles = execute_inputs[2], execute_inputs[3]
                    else:
                        stockCode, candles = Utility.tools.promptSimilarStockSearch()
                    vectorSearch = [stockCode, candles, True]
                    tickerOption, executeOption = 12, 1
                    listStockCodes = fetcher.fetchStockCodes(tickerOption, proxyServer=proxyServer)
            else:
                if tickerOption == 14:    # Override config for F&O Stocks
                    configManager.stageTwo = False
                    configManager.minLTP = 0.1
                    configManager.maxLTP = 999999999
                listStockCodes = fetcher.fetchStockCodes(tickerOption, proxyServer=proxyServer)
        except urllib.error.URLError:
            print(colorText.BOLD + colorText.FAIL +
                  "\n\n[+] Oops! It looks like you don't have an Internet connectivity at the moment! Press any key to exit!" + colorText.END)
            if not isGui():
                input('')
            sys.exit(0)

        if not Utility.tools.isTradingTime() and configManager.cacheEnabled and not loadedStockData and not testing:
            Utility.tools.loadStockData(stockDict, configManager, proxyServer)
            loadedStockData = True
        loadCount = len(stockDict)

        print(colorText.BOLD + colorText.WARN +
              "[+] Starting Stock Screening.. Press Ctrl+C to stop!\n")

        items = [(executeOption, reversalOption, maLength, daysForLowestVolume, minRSI, maxRSI, respChartPattern, insideBarToLookback, len(listStockCodes),
                  configManager, fetcher, screener, candlePatterns, stock, newlyListedOnly, downloadOnly, vectorSearch)
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
                bar, spinner = Utility.tools.getProgressbarStyle()
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

        if CHROMA_AVAILABLE and type(vectorSearch) == list and vectorSearch[2]:
            chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH)
            collection = chroma_client.get_collection(name="nse_stocks")
            query_embeddings= collection.get(ids = [stockCode], include=["embeddings"])["embeddings"]
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=4
            )['ids'][0]
            try:
                results.remove(stockCode)
            except ValueError:
                pass
            matchedScreenResults, matchedSaveResults = pd.DataFrame(columns=screenResults.columns), pd.DataFrame(columns=saveResults.columns)
            for stk in results:
                matchedScreenResults = matchedScreenResults.append(screenResults[screenResults['Stock'].str.contains(stk)])
                matchedSaveResults = matchedSaveResults.append(saveResults[saveResults['Stock'].str.contains(stk)])
            screenResults, saveResults = matchedScreenResults, matchedSaveResults
            

        screenResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        saveResults.sort_values(by=['Stock'], ascending=True, inplace=True)
        screenResults.set_index('Stock', inplace=True)
        saveResults.set_index('Stock', inplace=True)
        screenResults.rename(
            columns={
                'Trend': f'Trend ({configManager.daysToLookback}Days)',
                'Breaking-Out': f'Breakout ({configManager.daysToLookback}Days)',
                'LTP': 'LTP (%% Chng)'
            },
            inplace=True
        )
        saveResults.rename(
            columns={
                'Trend': f'Trend ({configManager.daysToLookback}Days)',
                'Breaking-Out': f'Breakout ({configManager.daysToLookback}Days)',
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
        Utility.tools.setLastScreenedResults(saveResults, unformatted=True)
        if not testBuild and not downloadOnly:
            Utility.tools.promptSaveResults(saveResults)
            print(colorText.BOLD + colorText.WARN +
                "[+] Note: Trend calculation is based on number of days recent to screen as per your configuration." + colorText.END)
            print(colorText.BOLD + colorText.GREEN +
                "[+] Screening Completed! Press Enter to Continue.." + colorText.END)
            if not isGui():
                input('')
        newlyListedOnly = False
        vectorSearch = False


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
            raise e
            if isDevVersion == OTAUpdater.developmentVersion:
                raise(e)
            input(colorText.BOLD + colorText.FAIL +
                "[+] Press any key to Exit!" + colorText.END)
            sys.exit(1)
