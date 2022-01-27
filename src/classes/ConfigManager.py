'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for managing the user configuration
'''

import sys
import os
import glob
import configparser
from datetime import date
from classes.ColorText import colorText

parser = configparser.ConfigParser(strict=False)

# Default attributes for Downloading Cache from Git repo
default_period = '300d'
default_duration = '1d'

# This Class manages read/write of user configuration
class tools:

    def __init__(self):
        self.consolidationPercentage = 10
        self.volumeRatio = 2
        self.minLTP = 20.0
        self.maxLTP = 50000
        self.period = '300d'
        self.duration = '1d'
        self.daysToLookback = 30
        self.shuffleEnabled = True
        self.cacheEnabled = True
        self.stageTwo = False
        self.useEMA = False

    def deleteStockData(self,excludeFile=None):
        for f in glob.glob('stock_data*.pkl'):
            if excludeFile is not None:
                if not f.endswith(excludeFile):
                    os.remove(f)
            else:
                os.remove(f)

    # Handle user input and save config

    def setConfig(self, parser, default=False, showFileCreatedText=True):
        if default:
            parser.add_section('config')
            parser.set('config', 'period', self.period)
            parser.set('config', 'daysToLookback', str(self.daysToLookback))
            parser.set('config', 'duration', self.duration)
            parser.set('config', 'minPrice', str(self.minLTP))
            parser.set('config', 'maxPrice', str(self.maxLTP))
            parser.set('config', 'volumeRatio', str(self.volumeRatio))
            parser.set('config', 'consolidationPercentage',
                       str(self.consolidationPercentage))
            parser.set('config', 'shuffle', 'y')
            parser.set('config', 'cacheStockData', 'y')
            parser.set('config', 'onlyStageTwoStocks', 'y')
            parser.set('config', 'useEMA', 'n')
            try:
                fp = open('screenipy.ini', 'w')
                parser.write(fp)
                fp.close()
                if showFileCreatedText:
                    print(colorText.BOLD + colorText.GREEN +
                        '[+] Default configuration generated as user configuration is not found!' + colorText.END)
                    print(colorText.BOLD + colorText.GREEN +
                        '[+] Use Option > 5 to edit in future.' + colorText.END)
                    print(colorText.BOLD + colorText.GREEN +
                        '[+] Close and Restart the program now.' + colorText.END)
                    input('')
                    sys.exit(0)
            except IOError:
                print(colorText.BOLD + colorText.FAIL +
                      '[+] Failed to save user config. Exiting..' + colorText.END)
                input('')
                sys.exit(1)
        else:
            parser = configparser.ConfigParser(strict=False)
            parser.add_section('config')
            print('')
            print(colorText.BOLD + colorText.GREEN +
                  '[+] Screeni-py User Configuration:' + colorText.END)
            self.period = input(
                '[+] Enter number of days for which stock data to be downloaded (Days)(Optimal = 365): ')
            self.daysToLookback = input(
                '[+] Number of recent days (TimeFrame) to screen for Breakout/Consolidation (Days)(Optimal = 20): ')
            self.duration = input(
                '[+] Enter Duration of each candle (Days)(Optimal = 1): ')
            self.minLTP = input(
                '[+] Minimum Price of Stock to Buy (in RS)(Optimal = 20): ')
            self.maxLTP = input(
                '[+] Maximum Price of Stock to Buy (in RS)(Optimal = 50000): ')
            self.volumeRatio = input(
                '[+] How many times the volume should be more than average for the breakout? (Number)(Optimal = 2.5): ')
            self.consolidationPercentage = input(
                '[+] How many % the price should be in range to consider it as consolidation? (Number)(Optimal = 10): ')
            self.shuffle = str(input(
                '[+] Shuffle stocks rather than screening alphabetically? (Y/N): ')).lower()
            self.cacheStockData = str(input(
                '[+] Enable High-Performance and Data-Saver mode? (This uses little bit more CPU but performs High Performance Screening) (Y/N): ')).lower()
            self.stageTwoPrompt = str(input(
                '[+] Screen only for Stage-2 stocks?\n(What are the stages? => https://www.investopedia.com/articles/trading/08/stock-cycle-trend-price.asp)\n(Y/N): ')).lower()
            self.useEmaPrompt = str(input(
                '[+] Use EMA instead of SMA? (EMA is good for Short-term & SMA for Mid/Long-term trades)[Y/N]: ')).lower()
            parser.set('config', 'period', self.period + "d")
            parser.set('config', 'daysToLookback', self.daysToLookback)
            parser.set('config', 'duration', self.duration + "d")
            parser.set('config', 'minPrice', self.minLTP)
            parser.set('config', 'maxPrice', self.maxLTP)
            parser.set('config', 'volumeRatio', self.volumeRatio)
            parser.set('config', 'consolidationPercentage',
                       self.consolidationPercentage)
            parser.set('config', 'shuffle', self.shuffle)
            parser.set('config', 'cacheStockData', self.cacheStockData)
            parser.set('config', 'onlyStageTwoStocks', self.stageTwoPrompt)
            parser.set('config', 'useEMA', self.useEmaPrompt)

            # delete stock data due to config change
            self.deleteStockData()
            print(colorText.BOLD + colorText.FAIL + "[+] Cached Stock Data Deleted." + colorText.END)

            try:
                fp = open('screenipy.ini', 'w')
                parser.write(fp)
                fp.close()
                print(colorText.BOLD + colorText.GREEN +
                      '[+] User configuration saved.' + colorText.END)
                print(colorText.BOLD + colorText.GREEN +
                      '[+] Restart the Program to start Screening...' + colorText.END)
                input('')
                sys.exit(0)
            except IOError:
                print(colorText.BOLD + colorText.FAIL +
                      '[+] Failed to save user config. Exiting..' + colorText.END)
                input('')
                sys.exit(1)

    # Load user config from file
    def getConfig(self, parser):
        if len(parser.read('screenipy.ini')):
            try:
                self.duration = parser.get('config', 'duration')
                self.period = parser.get('config', 'period')
                self.minLTP = float(parser.get('config', 'minprice'))
                self.maxLTP = float(parser.get('config', 'maxprice'))
                self.volumeRatio = float(parser.get('config', 'volumeRatio'))
                self.consolidationPercentage = float(
                    parser.get('config', 'consolidationPercentage'))
                self.daysToLookback = int(
                    parser.get('config', 'daysToLookback'))
                if 'n' not in str(parser.get('config', 'shuffle')).lower():
                    self.shuffleEnabled = True
                if 'n' not in str(parser.get('config', 'cachestockdata')).lower():
                    self.cacheEnabled = True
                if 'n' not in str(parser.get('config', 'onlyStageTwoStocks')).lower():
                    self.stageTwo = True
                if 'y' not in str(parser.get('config', 'useEMA')).lower():
                    self.useEMA = False
            except configparser.NoOptionError:
                input(colorText.BOLD + colorText.FAIL +
                      '[+] Screenipy requires user configuration again. Press enter to continue..' + colorText.END)
                parser.remove_section('config')
                self.setConfig(parser, default=False)
        else:
            self.setConfig(parser, default=True)

    # Print config file
    def showConfigFile(self):
        try:
            f = open('screenipy.ini', 'r')
            print(colorText.BOLD + colorText.GREEN +
                  '[+] Screeni-py User Configuration:' + colorText.END)
            print("\n"+f.read())
            f.close()
            input('')
        except:
            print(colorText.BOLD + colorText.FAIL +
                  "[+] User Configuration not found!" + colorText.END)
            print(colorText.BOLD + colorText.WARN +
                  "[+] Configure the limits to continue." + colorText.END)
            self.setConfig(parser)

    # Check if config file exists
    def checkConfigFile(self):
        try:
            f = open('screenipy.ini','r')
            f.close()
            return True
        except FileNotFoundError:
            return False
