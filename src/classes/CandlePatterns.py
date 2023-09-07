'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   11/04/2021
 *  Description         :   Class for analyzing candle-stick patterns
'''

import pandas as pd
from classes.ScreenipyTA import ScreenerTA
from classes.ColorText import colorText

class CandlePatterns:

    reversalPatternsBullish = ['Morning Star', 'Morning Doji Star', '3 Inside Up', 'Hammer', '3 White Soldiers', 'Bullish Engulfing', 'Dragonfly Doji', 'Supply Drought', 'Demand Rise']
    reversalPatternsBearish = ['Evening Star', 'Evening Doji Star', '3 Inside Down', 'Inverted Hammer', 'Hanging Man', '3 Black Crows', 'Bearish Engulfing', 'Shooting Star', 'Gravestone Doji']

    def __init__(self):
        pass

    # Find candle-stick patterns
    # Arrange if statements with max priority from top to bottom
    def findPattern(self, data, dict, saveDict):
        data = data.head(4)
        data = data[::-1]

        check = ScreenerTA.CDLMORNINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Morning Star' + colorText.END
            saveDict['Pattern'] = 'Morning Star'
            return True

        check = ScreenerTA.CDLMORNINGDOJISTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Morning Doji Star' + colorText.END
            saveDict['Pattern'] = 'Morning Doji Star'
            return True
        
        check = ScreenerTA.CDLEVENINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Evening Star' + colorText.END
            saveDict['Pattern'] = 'Evening Star'
            return True

        check = ScreenerTA.CDLEVENINGDOJISTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Evening Doji Star' + colorText.END
            saveDict['Pattern'] = 'Evening Doji Star'
            return True

        check = ScreenerTA.CDLLADDERBOTTOM(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            if(check is not None and check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Ladder Bottom' + colorText.END
                saveDict['Pattern'] = 'Bullish Ladder Bottom'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Ladder Bottom' + colorText.END
                saveDict['Pattern'] = 'Bearish Ladder Bottom'
            return True

        check = ScreenerTA.CDL3LINESTRIKE(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            if(check is not None and check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 Line Strike' + colorText.END
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Line Strike' + colorText.END
            saveDict['Pattern'] = '3 Line Strike'
            return True
        
        check = ScreenerTA.CDL3BLACKCROWS(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Black Crows' + colorText.END
            saveDict['Pattern'] = '3 Black Crows'
            return True

        check = ScreenerTA.CDL3INSIDE(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            if(check is not None and check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 Outside Up' + colorText.END
                saveDict['Pattern'] = '3 Inside Up'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Outside Down' + colorText.END
                saveDict['Pattern'] = '3 Inside Down'
            return True

        check = ScreenerTA.CDL3OUTSIDE(data['Open'], data['High'], data['Low'], data['Close'])
        if(check > 0):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 Outside Up' + colorText.END
            saveDict['Pattern'] = '3 Outside Up'
            return True
        elif(check < 0):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Outside Down' + colorText.END
            saveDict['Pattern'] = '3 Outside Down'
            return True

        check = ScreenerTA.CDL3WHITESOLDIERS(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 White Soldiers' + colorText.END
            saveDict['Pattern'] = '3 White Soldiers'
            return True

        check = ScreenerTA.CDLHARAMI(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            if(check is not None and check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Bullish Harami' + colorText.END
                saveDict['Pattern'] = 'Bullish Harami'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Bearish Harami' + colorText.END
                saveDict['Pattern'] = 'Bearish Harami'
            return True

        check = ScreenerTA.CDLHARAMICROSS(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            if(check is not None and check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Bullish Harami Cross' + colorText.END
                saveDict['Pattern'] = 'Bullish Harami Cross'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Bearish Harami Cross' + colorText.END
                saveDict['Pattern'] = 'Bearish Harami Cross'
            return True

        check = ScreenerTA.CDLMARUBOZU(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            if(check is not None and check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Bullish Marubozu' + colorText.END
                saveDict['Pattern'] = 'Bullish Marubozu'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Bearish Marubozu' + colorText.END
                saveDict['Pattern'] = 'Bearish Marubozu'
            return True

        check = ScreenerTA.CDLHANGINGMAN(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Hanging Man' + colorText.END
            saveDict['Pattern'] = 'Hanging Man'
            return True
        
        check = ScreenerTA.CDLHAMMER(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Hammer' + colorText.END
            saveDict['Pattern'] = 'Hammer'
            return True

        check = ScreenerTA.CDLINVERTEDHAMMER(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Inverted Hammer' + colorText.END
            saveDict['Pattern'] = 'Inverted Hammer'
            return True

        check = ScreenerTA.CDLSHOOTINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Shooting Star' + colorText.END
            saveDict['Pattern'] = 'Shooting Star'
            return True

        check = ScreenerTA.CDLDRAGONFLYDOJI(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Dragonfly Doji' + colorText.END
            saveDict['Pattern'] = 'Dragonfly Doji'
            return True

        check = ScreenerTA.CDLGRAVESTONEDOJI(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Gravestone Doji' + colorText.END
            saveDict['Pattern'] = 'Gravestone Doji'
            return True

        check = ScreenerTA.CDLDOJI(data['Open'], data['High'], data['Low'], data['Close'])
        if(check):
            dict['Pattern'] = colorText.BOLD + 'Doji' + colorText.END
            saveDict['Pattern'] = 'Doji'
            return True

        check = ScreenerTA.CDLENGULFING(data['Open'], data['High'], data['Low'], data['Close'])
        if(check > 0):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Bullish Engulfing' + colorText.END
            saveDict['Pattern'] = 'Bullish Engulfing'
            return True
        elif(check < 0):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Bearish Engulfing' + colorText.END
            saveDict['Pattern'] = 'Bearish Engulfing'
            return True

        dict['Pattern'] = ''
        saveDict['Pattern'] = ''
        return False
