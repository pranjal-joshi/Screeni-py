#!/usr/bin/python3

# Pyinstaller compile Windows: pyinstaller --onefile --icon=src\icon.ico src\screenipy.py  --hidden-import cmath --hidden-import talib.stream
# Pyinstaller compile Linux  : pyinstaller --onefile --icon=src/icon.ico src/screenipy.py  --hidden-import cmath --hidden-import talib.stream

import os
from queue import Empty
import sys
import urllib
import requests
import multiprocessing
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
from classes.SuppressOutput import SuppressOutput
from classes.Changelog import *

# Try Fixing bug with this symbol
TEST_STKCODE = "SBIN"

# Constants
np.seterr(divide='ignore', invalid='ignore')

# Global Variabls
candlePatterns = CandlePatterns()
screenCounter = None
screenResultsCounter = None

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
    try:
        result = input(colorText.BOLD + colorText.FAIL + '[+] Select option: ')
        print(colorText.END, end='')
        result = int(result)
        if(result < 0 or result > 12):
            raise ValueError
        return result
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        print(colorText.BOLD + colorText.FAIL +
              '\n[+] Please enter a valid numeric option & Try Again!' + colorText.END)
        sleep(2)
        Utility.tools.clearScreen()
        return initExecution()


class StockConsumer(multiprocessing.Process):

    def __init__(self, task_queue, result_queue, sc, src):
        global screenCounter, screenResultsCounter
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.screenCounter = sc
        self.screenResultsCounter = src

    def run(self):
        while True:
            next_task = self.task_queue.get()
            if next_task is None:
                self.task_queue.task_done()
                break
            answer = self.screenStocks(*(next_task))
            self.task_queue.task_done()
            self.result_queue.put(answer)

    def screenStocks(self, executeOption, reversalOption, daysForLowestVolume, minRSI, maxRSI, respBullBear, insideBarToLookback, totalSymbols, stock, minLTP, maxLTP):
        global screenCounter, screenResultsCounter
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
                                                self.screenResultsCounter, self.screenCounter, totalSymbols)
            fullData, processedData = Screener.tools.preprocessData(
                data, daysToLookback=ConfigManager.daysToLookback)

            with self.screenCounter.get_lock():
                self.screenCounter.value += 1

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
                    fullData, screeningDictionary, saveDictionary, minLTP=minLTP, maxLTP=maxLTP)
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

                with self.screenResultsCounter.get_lock():
                    if executeOption == 0:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if (executeOption == 1 or executeOption == 2) and isBreaking and isVolumeHigh and isLtpValid:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if (executeOption == 1 or executeOption == 3) and (consolidationValue <= ConfigManager.consolidationPercentage and consolidationValue != 0) and isLtpValid:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if executeOption == 4 and isLtpValid and isLowestVolume:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if executeOption == 5 and isLtpValid and isValidRsi:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if executeOption == 6 and isLtpValid:
                        if reversalOption == 1:
                            if saveDictionary['Pattern'] in CandlePatterns.reversalPatternsBullish or isMaReversal > 0:
                                self.screenResultsCounter.value += 1
                                return screeningDictionary, saveDictionary
                        elif reversalOption == 2:
                            if saveDictionary['Pattern'] in CandlePatterns.reversalPatternsBearish or isMaReversal < 0:
                                self.screenResultsCounter.value += 1
                                return screeningDictionary, saveDictionary
                    if executeOption == 7 and isLtpValid and isInsideBar:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
        except KeyboardInterrupt:
            # Clear Queues and append None
            try:
                while True:
                    self.task_queue.get()
            except Empty:
                for _ in range(multiprocessing.cpu_count()):
                    self.task_queue.put(None)
        except Fetcher.StockDataEmptyException:
            pass
        except Exception as e:
            print(colorText.FAIL +
                  ("\n[+] Exception Occured while Screening %s! Skipping this stock.." % stock) + colorText.END)
        return


# Main function

def main(testing=False):
    global screenCounter, screenResultsCounter

    screenCounter = multiprocessing.Value('i', 1)
    screenResultsCounter = multiprocessing.Value('i', 0)

    screenResults = pd.DataFrame(columns=[
        'Stock', 'Consolidating', 'Breaking-Out', 'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])
    saveResults = pd.DataFrame(columns=['Stock', 'Consolidating', 'Breaking-Out',
                                        'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])

    minRSI = 0
    maxRSI = 100
    insideBarToLookback = 7
    respBullBear = 1
    daysForLowestVolume = 30
    reversalOption = None
    try:
        executeOption = initExecution()
    except KeyboardInterrupt:
        input(colorText.BOLD + colorText.FAIL + "[+] Press any key to Exit!" + colorText.END)
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
        input(colorText.BOLD + colorText.FAIL + "[+] Press any key to Exit!" + colorText.END)
        sys.exit(0) 
    if executeOption >= 0 and executeOption < 8:
        ConfigManager.tools.getConfig(ConfigManager.parser)
        try:
            listStockCodes = Fetcher.tools.fetchStockCodes(executeOption)
        except urllib.error.URLError:
            print(colorText.BOLD + colorText.FAIL +
                  "\n\n[+] Oops! It looks like you don't have an Internet connectivity at the moment! Press any key to exit!" + colorText.END)
            input('')
            sys.exit(0)
        print(colorText.BOLD + colorText.WARN +
              "[+] Starting Stock Screening.. Press Ctrl+C to stop!\n")

        items = [(executeOption, reversalOption, daysForLowestVolume, minRSI, maxRSI, respBullBear, insideBarToLookback, len(listStockCodes), stock, ConfigManager.minLTP, ConfigManager.maxLTP)
                 for stock in listStockCodes]

        tasks_queue = multiprocessing.JoinableQueue()
        results_queue = multiprocessing.Queue()

        consumers = [StockConsumer(tasks_queue, results_queue, screenCounter, screenResultsCounter)
                     for _ in range(multiprocessing.cpu_count())]

        for worker in consumers:
            worker.start()

        if testing == True:
            for item in items:
                tasks_queue.put(item)
                result = results_queue.get()
                if result != None:
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
                while numStocks:
                    result = results_queue.get()
                    if result != None:
                        screenResults = screenResults.append(
                            result[0], ignore_index=True)
                        saveResults = saveResults.append(
                            result[1], ignore_index=True)
                    numStocks -= 1
            except KeyboardInterrupt:
                for worker in consumers:
                    worker.terminate()    
                print(colorText.BOLD + colorText.FAIL + "\n[+] Script terminated by the user." + colorText.END)
        
        # Exit all processes. Without this, it threw error in next screening session
        for worker in consumers:
            worker.terminate()

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
    try:
        main()
    except Exception as e:
        input(colorText.BOLD + colorText.FAIL + "[+] Press any key to Exit!" + colorText.END)
        sys.exit(0) 
