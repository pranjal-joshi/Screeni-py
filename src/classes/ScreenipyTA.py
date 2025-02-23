import numpy as np
import os

if 'STREAMLIT_APP' in os.environ:
    import pandas_ta as talib
    print('[+] Importing pandas_ta as we are running on Streamlit cloud app')
else:
    try:
        import talib
    except ImportError:
        import pandas_ta as talib


class ScreenerTA:

    @staticmethod
    def EMA(close, timeperiod):
        try:
            return talib.ema(close,timeperiod)
        except Exception as e:
            return talib.EMA(close.to_numpy().reshape(-1),timeperiod)

    @staticmethod
    def SMA(close, timeperiod):
        try:
            return talib.sma(close,timeperiod)
        except Exception as e:
            return talib.SMA(close.to_numpy().reshape(-1),timeperiod)
        
    @staticmethod
    def MA(close, timeperiod):
        try:
            return talib.ma(close,timeperiod)
        except Exception as e:
            return talib.MA(close.to_numpy().reshape(-1),timeperiod)

    @staticmethod
    def MACD(close, fast, slow, signal):
        try:
            return talib.macd(close,fast,slow,signal)
        except Exception as e:
            return talib.MACD(close.to_numpy().reshape(-1),fast.to_numpy().reshape(-1),slow.to_numpy().reshape(-1),signal.to_numpy().reshape(-1))

    @staticmethod
    def RSI(close, timeperiod):
        try:
            return talib.rsi(close,timeperiod)
        except Exception as e:
            return talib.RSI(close.to_numpy().reshape(-1),timeperiod)
    
    @staticmethod
    def CCI(high, low, close, timeperiod):
        try:
            return talib.cci(high, low, close,timeperiod)
        except Exception as e:
            return talib.CCI(high.to_numpy().reshape(-1), low.to_numpy().reshape(-1), close.to_numpy().reshape(-1),timeperiod)
    
   
    @staticmethod
    def CDLMORNINGSTAR(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'morningstar').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLMORNINGSTAR(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False

    @staticmethod
    def CDLMORNINGDOJISTAR(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'morningdojistar').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLMORNINGDOJISTAR(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLEVENINGSTAR(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'eveningstar').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLEVENINGSTAR(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLEVENINGDOJISTAR(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'eveningdojistar').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLEVENINGDOJISTAR(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLLADDERBOTTOM(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'ladderbottom').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLLADDERBOTTOM(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDL3LINESTRIKE(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'3linestrike').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDL3LINESTRIKE(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDL3BLACKCROWS(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'3blackcrows').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDL3BLACKCROWS(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDL3INSIDE(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'3inside').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDL3INSIDE(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDL3OUTSIDE(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'3outside').tail(1).values[0][0]
            except Exception as e:
                return talib.CDL3OUTSIDE(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDL3WHITESOLDIERS(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'3whitesoldiers').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDL3WHITESOLDIERS(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLHARAMI(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'harami').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLHARAMI(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLHARAMICROSS(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'haramicross').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLHARAMICROSS(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLMARUBOZU(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'marubozu').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLMARUBOZU(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLHANGINGMAN(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'hangingman').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLHANGINGMAN(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLHAMMER(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'hammer').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLHAMMER(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLINVERTEDHAMMER(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'invertedhammer').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLINVERTEDHAMMER(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLSHOOTINGSTAR(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'shootingstar').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLSHOOTINGSTAR(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLDRAGONFLYDOJI(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'dragonflydoji').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLDRAGONFLYDOJI(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLGRAVESTONEDOJI(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'gravestonedoji').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLGRAVESTONEDOJI(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
    
    @staticmethod
    def CDLDOJI(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'doji').tail(1).values[0][0] != 0
            except Exception as e:
                return talib.CDLDOJI(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
        
    
    @staticmethod
    def CDLENGULFING(open, high, low, close):
        try:
            try:
                return talib.cdl_pattern(open,high,low,close,'engulfing').tail(1).values[0][0]
            except Exception as e:
                return talib.CDLENGULFING(open.to_numpy().reshape(-1), high.to_numpy().reshape(-1), low.to_numpy().reshape(-1) ,close.to_numpy().reshape(-1)).tail(1).item() != 0
        except AttributeError:
            return False
        