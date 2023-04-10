| |
| :-: |
| ![Screeni-py](https://user-images.githubusercontent.com/6128978/217816268-74c40180-fc47-434d-938b-3639898ee3e0.png) |
| [![GitHub release (latest by date)](https://img.shields.io/github/v/release/pranjal-joshi/Screeni-py?style=for-the-badge)](https://github.com/pranjal-joshi/Screeni-py/releases/latest) [![GitHub all releases](https://img.shields.io/github/downloads/pranjal-joshi/Screeni-py/total?color=Green&label=Downloads&style=for-the-badge)](#) [![GitHub](https://img.shields.io/github/license/pranjal-joshi/Screeni-py?style=for-the-badge)](https://github.com/pranjal-joshi/Screeni-py/blob/main/LICENSE) [![CodeFactor](https://www.codefactor.io/repository/github/pranjal-joshi/screeni-py/badge?style=for-the-badge)](https://www.codefactor.io/repository/github/pranjal-joshi/screeni-py) [![MADE-IN-INDIA](https://img.shields.io/badge/MADE%20WITH%20%E2%9D%A4%20IN-INDIA-orange?style=for-the-badge)](https://en.wikipedia.org/wiki/India) [![BADGE](https://img.shields.io/badge/PULL%20REQUEST-GUIDELINES-red?style=for-the-badge)](https://github.com/pranjal-joshi/Screeni-py/blob/new-features/CONTRIBUTING.md) |
| [![Screenipy Test - New Features](https://github.com/pranjal-joshi/Screeni-py/actions/workflows/workflow-test.yml/badge.svg?branch=new-features)](https://github.com/pranjal-joshi/Screeni-py/actions/workflows/workflow-test.yml) [![Screenipy Build - New Release](https://github.com/pranjal-joshi/Screeni-py/actions/workflows/workflow-build-matrix.yml/badge.svg)](https://github.com/pranjal-joshi/Screeni-py/actions/workflows/workflow-build-matrix.yml) |
| ![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white) ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) ![Mac OS](https://img.shields.io/badge/mac%20os-D3D3D3?style=for-the-badge&logo=apple&logoColor=000000) |
| <img width="240" src="https://user-images.githubusercontent.com/6128978/217814499-7934edf6-fcc3-46d7-887e-7757c94e1632.png"><h2>Scan QR Code to join [Official Telegram Group](https://t.me/+0Tzy08mR0do0MzNl) for Additional Discussions</h2> |

| **Download** | **Discussion** | **Bugs/Issues** | **Documentation** |
| :---: | :---: | :---: | :---: |
| [![cloud-computing (1)](https://user-images.githubusercontent.com/6128978/149935359-ca0a7155-d1e3-4e47-98e8-67f879e707e7.png)](https://github.com/pranjal-joshi/Screeni-py/releases/latest) | [![meeting](https://user-images.githubusercontent.com/6128978/149935812-31266023-cc5b-4c98-a416-1d4cf8800c0c.png)](https://github.com/pranjal-joshi/Screeni-py/discussions) | [![warning](https://user-images.githubusercontent.com/6128978/149936142-04d7cf1c-5bc5-45c1-a8e4-015454a2de48.png)](https://github.com/pranjal-joshi/Screeni-py/issues?q=is%3Aissue) | [![help](https://user-images.githubusercontent.com/6128978/149937331-5ee5c00a-748d-4fbf-a9f9-e2273480d8a2.png)](https://github.com/pranjal-joshi/Screeni-py/blob/main/README.md#what-is-screeni-py) |
| Download the Latest Version | Join/Read the Community Discussion | Raise an Issue about a Problem | Get Help about Usage |

<!-- ## [**Click to Download the Latest Version**](https://github.com/pranjal-joshi/Screeni-py/releases/latest) -->

---

## What is Screeni-py?

### A Python-based stock screener for NSE, India.

**Screenipy** is an advanced stock screener to find potential breakout stocks from NSE and tell it's possible breakout values. It also helps to find the stocks which are consolidating and may breakout, or the particular chart patterns that you're looking specifically to make your decisions.
Screenipy is totally customizable and it can screen stocks with the settings that you have provided.

## How to use?
* Download the suitable file according to your OS.
* Linux & Mac users should make sure that the `screenipy.bin or screenipy.run` is having `execute` permission.
* **Run** the file. Following window will appear after a brief delay.

![home](https://raw.githubusercontent.com/pranjal-joshi/Screeni-py/new-features/screenshots/screenipy_demo.gif)

* **Configure** the parameters as per your requirement using `Option > 8`.

![config](https://raw.githubusercontent.com/pranjal-joshi/Screeni-py/new-features/screenshots/config.png)

* Following are the screenshots of screening and output results.

![screening](https://raw.githubusercontent.com/pranjal-joshi/Screeni-py/new-features/screenshots/screening.png)
![results](https://raw.githubusercontent.com/pranjal-joshi/Screeni-py/new-features/screenshots/results.png)
![done](https://raw.githubusercontent.com/pranjal-joshi/Screeni-py/new-features/screenshots/done.png)

* Once done, you can also save the results in an excel file.

## Understanding the Result Table:

The Result table contains a lot of different parameters which can be pretty overwhelming to the new users, so here's the description and significance of each parameter.

| Sr | Parameter | Description | Example |
|:---:|:---:|:---|:---|
|1|**Stock**|This is a NSE scrip symbol. If your OS/Terminal supports unicode, You can directly open **[TradingView](https://in.tradingview.com/)** charts by pressing `Ctrl+Click` on the stock name.|[TATAMOTORS](https://in.tradingview.com/chart?symbol=NSE%3ATATAMOTORS)|
|2|**Consolidating**|It gives the price range in which stock is trading since last `N` days. `N` is configurable and can be modified by executing `Edit User Configuration` option.|If stock is trading between price 100-120 in last 30 days, Output will be `Range = 20.0 %`|
|3|**Breakout (N Days)**|This is pure magic! The `BO` is Breakout level in last N days while `R` is the next resistance level if available. Investor should consider both BO & R level to decide entry/exits in their trades.|`B:302, R:313`(Breakout level is 100 & Next resistance is 102)|
|4|**LTP**|LTP is the Last Traded Price of an asset traded on NSE.|`298.7` (Stock is trading at this price)|
|5|**Volume**|Volume shows the relative volume of the recent candle with respect to 20 period MA of Volume. It could be `Unknown` for newly listed stocks.|if 20MA(Volume) is 1M and todays Volume is 2.8M, then `Volume = 2.8x`|
|6|**MA-Signal**|It describes the price trend of an asset by analysing various 50-200 MA/EMA crossover strategies.|`200MA-Support`,`BullCross-50MA` etc|
|7|**RSI**|For the momentum traders, it describes 14-period RSI for quick decision making about their trading plans|`0 to 100`|
|8|**Trend**|By using advance algorithms, the average trendlines are computed for `N` days and their strenght is displayed depending on steepness of trendlines. (This does NOT show any trendline on chart, it is calculated internally)|`Strong Up`, `Weak Down` etc.|
|9|**Pattern**|If the chart or the candle itself forming any important pattern in the recent timeframe or as per the selected screening option, various important patterns will be indicated here.|`Momentum Gainer`, `Inside Bar (N)`,`Bullish Engulfing` etc.|

## Hack it your way:
Feel free to Edit the parameters in the `screenipy.ini` file which will be generated by the application.
```
[config]
period = 300d
daystolookback = 30
duration = 1d
minprice = 30
maxprice = 10000
volumeratio = 2
consolidationpercentage = 10
shuffle = y
cachestockdata = y
onlystagetwostocks = y
useema = n
```
Try to tweak this parameters as per your trading styles. For example, If you're comfortable with weekly charts, make `duration=5d` and so on.

## Contributing:
* Please feel free to Suggest improvements bugs by creating an issue.
* Please follow the [Guidelines for Contributing](https://github.com/pranjal-joshi/Screeni-py/blob/new-features/CONTRIBUTING.md) while making a Pull Request.

## Disclaimer:
* DO NOT use the result provided by the software 'solely' to make your trading decisions.
* Always backtest and analyze the stocks manually before you trade.
* The Author and the software will not be held liable for your losses.
