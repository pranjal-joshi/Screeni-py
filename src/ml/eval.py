import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.compose import ColumnTransformer
import joblib
import keras
import matplotlib.pyplot as plt

import tensorflow as tf
physical_devices = tf.config.list_physical_devices('GPU')
try:
  # Disable all GPUS
  tf.config.set_visible_devices([], 'GPU')
  visible_devices = tf.config.get_visible_devices()
  for device in visible_devices:
    assert device.device_type != 'GPU'
except:
  # Invalid device or cannot modify virtual devices once initialized.
  pass

TEST_DAYS = 50
PERIOD = '5y'

INCLUDE_COMMODITIES = True

def preprocessBeforeScaling(df):
    df['High'] = df['High'].pct_change() * 100
    df['Low'] = df['Low'].pct_change() * 100
    df['Open'] = df['Open'].pct_change() * 100
    df['Close'] = df['Close'].pct_change() * 100 

    if INCLUDE_COMMODITIES:
        df['gold_High'] = df['gold_High'].pct_change() * 100
        df['gold_Low'] = df['gold_Low'].pct_change() * 100
        df['gold_Open'] = df['gold_Open'].pct_change() * 100
        df['gold_Close'] = df['gold_Close'].pct_change() * 100

        df['crude_High'] = df['crude_High'].pct_change() * 100
        df['crude_Low'] = df['crude_Low'].pct_change() * 100
        df['crude_Open'] = df['crude_Open'].pct_change() * 100
        df['crude_Close'] = df['crude_Close'].pct_change() * 100
    return df

metrics = {
    "TP": 0, "FP": 0, "TN": 0, "FN": 0
}

endpoint = keras.models.load_model('nifty_model_v3.h5')
try:
    scaler
except NameError:
    pkl = joblib.load('nifty_model_v3.pkl')
    scaler = pkl['scaler']
today = yf.download(
                tickers="^NSEI",
                period=f'{TEST_DAYS}d',
                interval='1d',
                progress=False,
                timeout=10
            )
if INCLUDE_COMMODITIES:
    gold = yf.download(
                    tickers="GC=F",
                    period=f'{TEST_DAYS}d',
                    interval='1d',
                    progress=False,
                    timeout=10
                ).add_prefix(prefix='gold_')
    crude = yf.download(
                tickers="CL=F",
                period=f'{TEST_DAYS}d',
                interval='1d',
                progress=False,
                timeout=10
            ).add_prefix(prefix='crude_')

    today = pd.concat([today, gold, crude], axis=1)
    today = today.drop(columns=['Adj Close', 'Volume', 'gold_Adj Close', 'gold_Volume', 'crude_Adj Close', 'crude_Volume'])
else:
    today = today.drop(columns=['Adj Close', 'Volume'])

###
today = preprocessBeforeScaling(today)
today = today.drop(columns=['gold_Open', 'gold_High', 'gold_Low', 'crude_Open', 'crude_High', 'crude_Low'])
###

cnt_correct, cnt_wrong = 0, 0
for i in range(-TEST_DAYS,0):
    df = today.iloc[i]
    twr = today.iloc[i+1]['Close']
    df = scaler.transform([df])
    pred = endpoint.predict([df], verbose=0)

    if twr > today.iloc[i]['Open']:
        fact = "BULLISH"
    else:
        fact = "BEARISH"

    if pred > 0.5:
        out = "BEARISH"
    else:
        out = "BULLISH"

    if out == fact:
        cnt_correct += 1
        if out == "BULLISH":
            metrics["TP"] += 1
        else:
            metrics["TN"] += 1
    else:
        cnt_wrong += 1
        if out == "BULLISH":
            metrics["FN"] += 1
        else:
            metrics["FP"] += 1

        
    print("{} Nifty Prediction -> Market may Close {} on {}! Actual -> {}, Prediction -> {}, Pred = {}".format(
            today.iloc[i].name.strftime("%d-%m-%Y"),
            out,
            (today.iloc[i].name + pd.Timedelta(days=1)).strftime("%d-%m-%Y"),
            fact,
            "Correct" if fact == out else "Wrong",
            str(np.round(pred[0][0], 2))
            )
        )

print("Correct: {}, Wrong: {}, Accuracy: {}".format(cnt_correct, cnt_wrong, cnt_correct/(cnt_correct+cnt_wrong)))
print(metrics)