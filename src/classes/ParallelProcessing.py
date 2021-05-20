
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
import classes.Fetcher as Fetcher
from queue import Empty
from classes.CandlePatterns import CandlePatterns
from classes.ColorText import colorText

if sys.platform.startswith('win'):
    import multiprocessing.popen_spawn_win32 as forking
else:
    import multiprocessing.popen_fork as forking


class StockConsumer(multiprocessing.Process):

    def __init__(self, task_queue, result_queue, sc, src, proxyServer, keyboardInterruptEvent):
        global screenCounter, screenResultsCounter
        multiprocessing.Process.__init__(self)
        self.multiprocessingForWindows()
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.screenCounter = sc
        self.screenResultsCounter = src
        self.proxyServer = proxyServer
        self.keyboardInterruptEvent = keyboardInterruptEvent

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

    def screenStocks(self, executeOption, reversalOption, daysForLowestVolume, minRSI, maxRSI, respBullBear, insideBarToLookback, totalSymbols,
                    configManager, fetcher, screener, candlePatterns, stock):
        global screenCounter, screenResultsCounter
        screenResults = pd.DataFrame(columns=[
            'Stock', 'Consolidating', 'Breaking-Out', 'MA-Signal', 'Volume', 'LTP', 'RSI', 'Trend', 'Pattern'])
        screeningDictionary = {'Stock': "", 'Consolidating': "",  'Breaking-Out': "",
                               'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}
        saveDictionary = {'Stock': "", 'Pattern': "", 'Consolidating': "", 'Breaking-Out': "",
                          'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}

        try:
            data = fetcher.fetchStockData(stock,
                                                configManager.period,
                                                configManager.duration,
                                                self.proxyServer,
                                                self.screenResultsCounter,
                                                self.screenCounter,
                                                totalSymbols)
                                                
            fullData, processedData = screener.preprocessData(data, daysToLookback=configManager.daysToLookback)

            with self.screenCounter.get_lock():
                self.screenCounter.value += 1
            if not processedData.empty:
                screeningDictionary['Stock'] = colorText.BOLD + \
                    colorText.BLUE + stock + colorText.END
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
                    currentTrend = screener.findTrend(processedData, screeningDictionary, saveDictionary, daysToLookback=configManager.daysToLookback, stockName=stock)
                except np.RankWarning:
                    screeningDictionary['Trend'] = 'Unknown'
                    saveDictionary['Trend'] = 'Unknown'
                isCandlePattern = candlePatterns.findPattern(
                    processedData, screeningDictionary, saveDictionary)
                isInsideBar = screener.validateInsideBar(
                    processedData, screeningDictionary, saveDictionary, bullBear=respBullBear, daysToLookback=insideBarToLookback)
                isMomentum = screener.validateMomentum(processedData, screeningDictionary, saveDictionary)

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
                    if executeOption == 7 and isLtpValid and isInsideBar:
                        self.screenResultsCounter.value += 1
                        return screeningDictionary, saveDictionary
        except KeyboardInterrupt:
            # Capturing Ctr+C Here isn't a great idea
            pass
        except Fetcher.StockDataEmptyException:
            pass
        except KeyError:
            pass
        except Exception as e:
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
