'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for managing the user configuration
'''

import sys
import configparser
from classes.ColorText import colorText

consolidationPercentage = 10
volumeRatio = 2
minLTP = 20.0
maxLTP = 50000
period = '365d'
duration = '1d'
daysToLookback = 30
shuffleEnabled = False
stageTwo = False
useEMA = True

parser = configparser.ConfigParser(strict=False)

# This Class manages read/write of user configuration


class tools:

    # Handle user input and save config
    def setConfig(parser, default=False):
        if default:
            global duration, period, minLTP, maxLTP, volumeRatio, consolidationPercentage, daysToLookback
            parser.add_section('config')
            parser.set('config', 'period', period)
            parser.set('config', 'daysToLookback', str(daysToLookback))
            parser.set('config', 'duration', duration)
            parser.set('config', 'minPrice', str(minLTP))
            parser.set('config', 'maxPrice', str(maxLTP))
            parser.set('config', 'volumeRatio', str(volumeRatio))
            parser.set('config', 'consolidationPercentage',
                       str(consolidationPercentage))
            parser.set('config', 'shuffle', 'y')
            parser.set('config', 'onlyStageTwoStocks', 'y')
            parser.set('config', 'useEMA', 'y')
            try:
                fp = open('screenipy.ini', 'w')
                parser.write(fp)
                fp.close()
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
            parser.add_section('config')
            print('')
            print(colorText.BOLD + colorText.GREEN +
                  '[+] Screeni-py User Configuration:' + colorText.END)
            period = input(
                '[+] Enter number of days for which stock data to be downloaded (Days)(Optimal = 365): ')
            daysToLookback = input(
                '[+] Number of recent days (TimeFrame) to screen for Breakout/Consolidation (Days)(Optimal = 20): ')
            duration = input(
                '[+] Enter Duration of each candle (Days)(Optimal = 1): ')
            minLTP = input(
                '[+] Minimum Price of Stock to Buy (in RS)(Optimal = 20): ')
            maxLTP = input(
                '[+] Maximum Price of Stock to Buy (in RS)(Optimal = 50000): ')
            volumeRatio = input(
                '[+] How many times the volume should be more than average for the breakout? (Number)(Optimal = 2.5): ')
            consolidationPercentage = input(
                '[+] How many % the price should be in range to consider it as consolidation? (Number)(Optimal = 10): ')
            shuffle = str(input(
                '[+] Shuffle stocks rather than screening alphabetically? (Y/N): ')).lower()
            stageTwoPrompt = str(input(
                '[+] Screen only for Stage-2 stocks?\n(What are the stages? => https://www.investopedia.com/articles/trading/08/stock-cycle-trend-price.asp)\n(Y/N): ')).lower()
            useEmaPrompt = str(input(
                '[+] Use EMA instead of SMA? (EMA is good for Short-term & SMA for Mid/Long-term trades)[Y/N]: ')).lower()
            parser.set('config', 'period', period + "d")
            parser.set('config', 'daysToLookback', daysToLookback)
            parser.set('config', 'duration', duration + "d")
            parser.set('config', 'minPrice', minLTP)
            parser.set('config', 'maxPrice', maxLTP)
            parser.set('config', 'volumeRatio', volumeRatio)
            parser.set('config', 'consolidationPercentage',
                       consolidationPercentage)
            parser.set('config', 'shuffle', shuffle)
            parser.set('config', 'onlyStageTwoStocks', stageTwoPrompt)
            parser.set('config', 'useEMA', useEmaPrompt)
            try:
                fp = open('screenipy.ini', 'w')
                parser.write(fp)
                fp.close()
                print(colorText.BOLD + colorText.GREEN +
                      '[+] User configuration saved.' + colorText.END)
                print(colorText.BOLD + colorText.GREEN +
                      '[+] Restart the program now.' + colorText.END)
                input('')
                sys.exit(0)
            except IOError:
                print(colorText.BOLD + colorText.FAIL +
                      '[+] Failed to save user config. Exiting..' + colorText.END)
                input('')
                sys.exit(1)

    # Load user config from file
    def getConfig(parser):
        global duration, period, minLTP, maxLTP, volumeRatio, consolidationPercentage, daysToLookback, shuffleEnabled, stageTwo
        if len(parser.read('screenipy.ini')):
            try:
                duration = parser.get('config', 'duration')
                period = parser.get('config', 'period')
                minLTP = float(parser.get('config', 'minprice'))
                maxLTP = float(parser.get('config', 'maxprice'))
                volumeRatio = float(parser.get('config', 'volumeRatio'))
                consolidationPercentage = float(
                    parser.get('config', 'consolidationPercentage'))
                daysToLookback = int(parser.get('config', 'daysToLookback'))
                if not 'n' in str(parser.get('config', 'shuffle')).lower():
                    shuffleEnabled = True
                if not 'n' in str(parser.get('config', 'onlyStageTwoStocks')).lower():
                    stageTwo = True
                if not 'y' in str(parser.get('config', 'useEMA')).lower():
                    useEMA = False
                print(colorText.BOLD + colorText.GREEN +
                      '[+] User configuration loaded.' + colorText.END)
            except configparser.NoOptionError:
                input(colorText.BOLD + colorText.FAIL +
                      '[+] Screenipy requires user configuration again. Press enter to continue..' + colorText.END)
                parser.remove_section('config')
                tools.setConfig(parser, default=False)
        else:
            tools.setConfig(parser, default=True)

    # Print config file
    def showConfigFile():
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
            tools.setConfig(parser)
