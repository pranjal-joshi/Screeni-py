'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   11/04/2021
 *  Description         :   Class for analyzing candle-stick patterns
'''

import pandas as pd
import talib
from ColorText import colorText

class CandlePatterns:
    def __init__(self):
        pass

    # Find candle-stick patterns
    # Arrange if statements with max priority from top to bottom
    def findPattern(self, data, dict, saveDict):
        data = data.head(4)
        data = data[::-1]

        check = talib.CDLMORNINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Morning Star' + colorText.END
            saveDict['Pattern'] = 'Morning Star'
            return True
        
        check = talib.CDLEVENINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Evening Star' + colorText.END
            saveDict['Pattern'] = 'Evening Star'
            return True

        check = talib.CDL3LINESTRIKE(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            if(check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 Line Strike' + colorText.END
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Line Strike' + colorText.END
            saveDict['Pattern'] = '3 Line Strike'
            return True
        
        check = talib.CDL3BLACKCROWS(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Black Crows' + colorText.END
            saveDict['Pattern'] = '3 Black Crows'
            return True

        check = talib.CDL3OUTSIDE(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            if(check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 Outside Up' + colorText.END
                saveDict['Pattern'] = '3 Outside Up'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + '3 Outside Down' + colorText.END
                saveDict['Pattern'] = '3 Outside Down'
            return True

        check = talib.CDL3WHITESOLDIERS(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + '3 White Soldiers' + colorText.END
            saveDict['Pattern'] = '3 White Soldiers'
            return True

        check = talib.CDLENGULFING(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            if(check.tail(1).item() > 0):
                dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Bullish Engulfing' + colorText.END
                saveDict['Pattern'] = 'Bullish Engulfing'
            else:
                dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Bearish Engulfing' + colorText.END
                saveDict['Pattern'] = 'Bearish Engulfing'
            return True
        
        check = talib.CDLHAMMER(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Hammer' + colorText.END
            saveDict['Pattern'] = 'Hammer'
            return True

        check = talib.CDLINVERTEDHAMMER(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + colorText.FAIL + 'Inverted Hammer' + colorText.END
            saveDict['Pattern'] = 'Inverted Hammer'
            return True

        
        check = talib.CDLDOJI(data['Open'], data['High'], data['Low'], data['Close'])
        if(check.tail(1).item() != 0):
            dict['Pattern'] = colorText.BOLD + 'Doji' + colorText.END
            saveDict['Pattern'] = 'Doji'
            return True
        dict['Pattern'] = ''
        saveDict['Pattern'] = ''
        return False
