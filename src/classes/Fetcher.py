'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for handling networking for fetching stock codes and data
'''

import sys
import urllib
import requests
import random
import yfinance as yf
import pandas as pd
from nsetools import Nse
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput

nse = Nse()

# Exception class if yfinance stock delisted
class StockDataEmptyException(Exception):
    pass

# This Class Handles Fetching of Stock Data over the internet


class tools:

    def __init__(self, configManager):
        self.configManager = configManager
        pass

    # Fetch all stock codes from NSE
    def fetchStockCodes(self, executeOption):
        listStockCodes = []
        if executeOption == 0:
            stockCode = None
            while stockCode == None or stockCode == "":
                stockCode = str(input(colorText.BOLD + colorText.BLUE +
                                      "[+] Enter Stock Code(s) for screening (Multiple codes should be seperated by ,): ")).upper()
            stockCode = stockCode.replace(" ", "")
            listStockCodes = stockCode.split(',')
        else:
            print(colorText.BOLD +
                  "[+] Getting Stock Codes From NSE... ", end='')
            listStockCodes = list(nse.get_stock_codes(cached=False))[1:]
            if len(listStockCodes) > 10:
                print(colorText.GREEN + ("=> Done! Fetched %d stock codes." %
                                         len(listStockCodes)) + colorText.END)
                if self.configManager.shuffleEnabled:
                    random.shuffle(listStockCodes)
                    print(colorText.BLUE +
                          "[+] Stock shuffling is active." + colorText.END)
                else:
                    print(colorText.FAIL +
                          "[+] Stock shuffling is inactive." + colorText.END)
                if self.configManager.stageTwo:
                    print(
                        colorText.BLUE + "[+] Screening only for the stocks in Stage-2! Edit User Config to change this." + colorText.END)
                else:
                    print(
                        colorText.FAIL + "[+] Screening only for the stocks in all Stages! Edit User Config to change this." + colorText.END)

            else:
                input(
                    colorText.FAIL + "=> Error getting stock codes from NSE! Press any key to exit!" + colorText.END)
                sys.exit("Exiting script..")

        return listStockCodes

    # Fetch stock price data from Yahoo finance
    def fetchStockData(self, stockCode, period, duration, proxyServer, screenResultsCounter, screenCounter, totalSymbols):
        with SuppressOutput(suppress_stdout=True, suppress_stderr=True):
            data = yf.download(
                tickers=stockCode+".NS",
                period=period,
                duration=duration,
                proxy=proxyServer,
                progress=False,
                threads=True
            )
        sys.stdout.write("\r\033[K")
        try:
            print(colorText.BOLD + colorText.GREEN + ("[%d%%] Screened %d, Found %d. Fetching data & Analyzing %s..." % (
                int((screenCounter.value/totalSymbols)*100), screenCounter.value, screenResultsCounter.value, stockCode)) + colorText.END, end='')
        except ZeroDivisionError:
            pass
        if len(data) == 0:
            print(colorText.BOLD + colorText.FAIL +
                  "=> Failed to fetch!" + colorText.END, end='\r', flush=True)
            raise StockDataEmptyException
            return None
        print(colorText.BOLD + colorText.GREEN + "=> Done!" +
              colorText.END, end='\r', flush=True)
        return data
