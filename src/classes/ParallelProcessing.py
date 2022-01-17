
'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi, Swar Patel
 *  Created             :   18/05/2021
 *  Description         :   Class for managing multiprocessing
'''

import multiprocessing
import pandas as pd
import numpy as np
import sys
import os
import pytz
from queue import Empty
from datetime import datetime
import classes.Fetcher as Fetcher
import classes.Screener as Screener
import classes.Utility as Utility
from classes.CandlePatterns import CandlePatterns
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput

if sys.platform.startswith('win'):
    import multiprocessing.popen_spawn_win32 as forking
else:
    import multiprocessing.popen_fork as forking


class StockConsumer(multiprocessing.Process):

    def __init__(self, task_queue, result_queue, screenCounter, screenResultsCounter, stockDict, proxyServer, keyboardInterruptEvent):
        multiprocessing.Process.__init__(self)
        self.multiprocessingForWindows()
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.screenCounter = screenCounter
        self.screenResultsCounter = screenResultsCounter
        self.stockDict = stockDict
        self.proxyServer = proxyServer
        self.keyboardInterruptEvent = keyboardInterruptEvent
        self.isTradingTime = Utility.tools.isTradingTime()

    def run(self):
        # while True:
        try:
            while not self.keyboardInterruptEvent.is_set():
                try:
                    next_task = self.task_queue.get()
                except Empty:
                    continue
                if next_task is None:
                    self.task_queue.task_done()
                    break
                answer = self.screenStocks(*(next_task))
                self.task_queue.task_done()
                self.result_queue.put(answer)
        except Exception as e:
            sys.exit(0)

    def screenStocks(self, executeOption, reversalOption, maLength, daysForLowestVolume, minRSI, maxRSI, respChartPattern, insideBarToLookback, totalSymbols,
                     configManager, fetcher, screener, candlePatterns, stock, newlyListedOnly, printCounter=False):
        screenResults = pd.DataFrame(columns=[
            'Stock', 'Consolidating', 'Breaking-Out', 'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])
        screeningDictionary = {'Stock': "", 'Consolidating': "",  'Breaking-Out': "",
                               'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}
        saveDictionary = {'Stock': "", 'Consolidating': "", 'Breaking-Out': "",
                          'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}

        try:
            period = configManager.period

            # Data download adjustment for Newly Listed only feature
            if newlyListedOnly:
                if int(configManager.period[:-1]) > 250:
                    period = '250d'
                else:
                    period = configManager.period

            if (self.stockDict.get(stock) is None) or (configManager.cacheEnabled is False) or self.isTradingTime:
                data = fetcher.fetchStockData(stock,
                                              period,
                                              configManager.duration,
                                              self.proxyServer,
                                              self.screenResultsCounter,
                                              self.screenCounter,
                                              totalSymbols)
                if configManager.cacheEnabled is True and not self.isTradingTime and (self.stockDict.get(stock) is None):
                    self.stockDict[stock] = data.to_dict('split')
            else:
                if printCounter:
                    try:
                        print(colorText.BOLD + colorText.GREEN + ("[%d%%] Screened %d, Found %d. Fetching data & Analyzing %s..." % (
                            int((self.screenCounter.value / totalSymbols) * 100), self.screenCounter.value, self.screenResultsCounter.value, stock)) + colorText.END, end='')
                        print(colorText.BOLD + colorText.GREEN + "=> Done!" +
                              colorText.END, end='\r', flush=True)
                    except ZeroDivisionError:
                        pass
                    sys.stdout.write("\r\033[K")
                data = self.stockDict.get(stock)
                data = pd.DataFrame(
                    data['data'], columns=data['columns'], index=data['index'])

            fullData, processedData = screener.preprocessData(
                data, daysToLookback=configManager.daysToLookback)

            if newlyListedOnly:
                if not screener.validateNewlyListed(fullData, period):
                    raise Screener.NotNewlyListed

            with self.screenCounter.get_lock():
                self.screenCounter.value += 1
            if not processedData.empty:
                screeningDictionary['Stock'] = colorText.BOLD + \
                     colorText.BLUE + f'\x1B]8;;https://in.tradingview.com/chart?symbol=NSE%3A{stock}\x1B\\{stock}\x1B]8;;\x1B\\' + colorText.END
                saveDictionary['Stock'] = stock
                consolidationValue = screener.validateConsolidation(
                    processedData, screeningDictionary, saveDictionary, percentage=configManager.consolidationPercentage)
                isMaReversal = screener.validateMovingAverages(
                    processedData, screeningDictionary, saveDictionary, maRange=1.25)
                isVolumeHigh = screener.validateVolume(
                    processedData, screeningDictionary, saveDictionary, volumeRatio=configManager.volumeRatio)
                isBreaking = screener.findBreakout(
                    processedData, screeningDictionary, saveDictionary, daysToLookback=configManager.daysToLookback)
                isLtpValid = screener.validateLTP(
                    fullData, screeningDictionary, saveDictionary, minLTP=configManager.minLTP, maxLTP=configManager.maxLTP)
                isLowestVolume = screener.validateLowestVolume(
                    processedData, daysForLowestVolume)
                isValidRsi = screener.validateRSI(
                    processedData, screeningDictionary, saveDictionary, minRSI, maxRSI)
                try:
                    with SuppressOutput(suppress_stderr=True, suppress_stdout=True):
                        currentTrend = screener.findTrend(
                            processedData,
                            screeningDictionary,
                            saveDictionary,
                            daysToLookback=configManager.daysToLookback,
                            stockName=stock)
                except np.RankWarning:
                    screeningDictionary['Trend'] = 'Unknown'
                    saveDictionary['Trend'] = 'Unknown'
                isCandlePattern = candlePatterns.findPattern(
                    processedData, screeningDictionary, saveDictionary)
                
                isConfluence = False
                isInsideBar = False
                isIpoBase = screener.validateIpoBase(stock, fullData, screeningDictionary, saveDictionary)
                if respChartPattern == 3 and executeOption == 7:
                    isConfluence = screener.validateConfluence(stock, processedData, screeningDictionary, saveDictionary, percentage=insideBarToLookback)
                else:
                    isInsideBar = screener.validateInsideBar(processedData, screeningDictionary, saveDictionary, chartPattern=respChartPattern, daysToLookback=insideBarToLookback)
                
                isMomentum = screener.validateMomentum(processedData, screeningDictionary, saveDictionary)
                isVSA = screener.validateVolumeSpreadAnalysis(processedData, screeningDictionary, saveDictionary)
                if maLength is not None and executeOption == 6:
                    isMaSupport = screener.findReversalMA(fullData, screeningDictionary, saveDictionary, maLength)

                with self.screenResultsCounter.get_lock():
                    if executeOption == 0:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if (executeOption == 1 or executeOption == 2) and isBreaking and isVolumeHigh and isLtpValid:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
                    if (executeOption == 1 or executeOption == 3) and (consolidationValue <= configManager.consolidationPercentage and consolidationValue != 0) and isLtpValid:
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
                        elif reversalOption == 3 and isMomentum:
                            self.screenResultsCounter.value += 1
                            return screeningDictionary, saveDictionary
                        elif reversalOption == 4 and isMaSupport:
                            self.screenResultsCounter.value += 1
                            return screeningDictionary, saveDictionary
                        elif reversalOption == 5 and isVSA and saveDictionary['Pattern'] in CandlePatterns.reversalPatternsBullish:
                            self.screenResultsCounter.value += 1
                            return screeningDictionary, saveDictionary
                    if executeOption == 7 and isLtpValid:
                        if respChartPattern < 3 and isInsideBar:
                            self.screenResultsCounter.value += 1
                            return screeningDictionary, saveDictionary
                        if isConfluence:
                            self.screenResultsCounter.value += 1
                            return screeningDictionary, saveDictionary
                        if isIpoBase:
                            self.screenResultsCounter.value += 1
                            return screeningDictionary, saveDictionary
        except KeyboardInterrupt:
            # Capturing Ctr+C Here isn't a great idea
            pass
        except Fetcher.StockDataEmptyException:
            pass
        except Screener.NotNewlyListed:
            pass
        except KeyError:
            pass
        except Exception as e:
            if printCounter:
                print(colorText.FAIL +
                      ("\n[+] Exception Occured while Screening %s! Skipping this stock.." % stock) + colorText.END)
        return

    def multiprocessingForWindows(self):
        if sys.platform.startswith('win'):

            class _Popen(forking.Popen):
                def __init__(self, *args, **kw):
                    if hasattr(sys, 'frozen'):
                        os.putenv('_MEIPASS2', sys._MEIPASS)
                    try:
                        super(_Popen, self).__init__(*args, **kw)
                    finally:
                        if hasattr(sys, 'frozen'):
                            if hasattr(os, 'unsetenv'):
                                os.unsetenv('_MEIPASS2')
                            else:
                                os.putenv('_MEIPASS2', '')

            forking.Popen = _Popen
