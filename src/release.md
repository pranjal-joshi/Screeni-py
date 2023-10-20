[![MADE-IN-INDIA](https://img.shields.io/badge/MADE%20WITH%20%E2%9D%A4%20IN-INDIA-orange?style=for-the-badge)](https://en.wikipedia.org/wiki/India) [![GitHub release (latest by date)](https://img.shields.io/github/v/release/pranjal-joshi/Screeni-py?style=for-the-badge)](#) [![GitHub all releases](https://img.shields.io/github/downloads/pranjal-joshi/Screeni-py/total?color=Green&label=Downloads&style=for-the-badge)](#) ![Docker Pulls](https://img.shields.io/docker/pulls/joshipranjal/screeni-py?style=for-the-badge&logo=docker) [![MADE_WITH](https://img.shields.io/badge/BUILT%20USING-PYTHON-yellow?style=for-the-badge&logo=python&logoColor=yellow)](https://www.python.org/)
## What's New?

Screeni-py is now on **YouTube** for additional help! - Thank You for your support :tada:

🐳 **Docker containers are released for quick setup and easy usage!**

⚠️ **Executable files (.exe, .bin and .run) are now DEPRECATED! Please Switch to Docker**

1. **Artificial Intelligence v3 for Nifty 50 Prediction** - Predict Next day Gap-up/down using Nifty, Gold and Crude prices! - Try `Select Index for Screening > N`
2. **US S&P 500** Index added for scanning US markets.
3. **Search Similar Stocks** Added using Vector Similarity search - Try `Search Similar Stocks`.
4. Progressbar added for Screener in GUI mode!
5. New Index - **F&O Stocks Only** Added for F&O traders with modified screening criterias.
6. New Screener **Buy at Trendline** added for Swing/Mid/Long term traders - Try `Option > 7 > 5`.

## Installation Guide

[![Screeni-py - How to install Software Updates? | Screenipy - Python NSE Stock Screener](https://markdown-videos-api.jorgenkh.no/url?url=https%3A%2F%2Fyoutu.be%2FT41m13iMyJc)](https://youtu.be/T41m13iMyJc) 
[![Screeni-py - Detailed Installation Guide](https://markdown-videos-api.jorgenkh.no/url?url=https%3A%2F%2Fyoutu.be%2F2HMN0ac4H20)](https://youtu.be/2HMN0ac4H20)

## Downloads 
### Deprecated - Use Docker Method mentioned in next section

| Operating System | Executable File |
| :-: | --- |
| ![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white) | **[screenipy.exe](https://github.com/pranjal-joshi/Screeni-py/releases/download/2.02/screenipy.exe)** |
| ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) | **[screenipy.bin](https://github.com/pranjal-joshi/Screeni-py/releases/download/2.02/screenipy.bin)** |
| ![Mac OS](https://img.shields.io/badge/mac%20os-D3D3D3?style=for-the-badge&logo=apple&logoColor=000000) | **[screenipy.run](https://github.com/pranjal-joshi/Screeni-py/releases/download/2.02/screenipy.run)** ([Read Installation Guide](https://github.com/pranjal-joshi/Screeni-py/blob/main/INSTALLATION.md#for-macos)) |

## [Docker Releases](https://hub.docker.com/r/joshipranjal/screeni-py/tags)

| | Tag | Pull Command | Run Mode | Run Command |
|:-: | :-: | --- | --- | --- |
| ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) | `latest` | `docker pull joshipranjal/screeni-py:latest` | Command Line | `docker run -it --entrypoint /bin/bash joshipranjal/screeni-py:latest -c "run_screenipy.sh --cli"` |
| ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) | `latest` | `docker pull joshipranjal/screeni-py:latest` | GUI WebApp | `docker run -p 8501:8501 joshipranjal/screeni-py:latest` |
| ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) | `dev` | `docker pull joshipranjal/screeni-py:dev` | Command Line | `docker run -it --entrypoint /bin/bash joshipranjal/screeni-py:dev -c "run_screenipy.sh --cli"` |
| ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) | `dev` | `docker pull joshipranjal/screeni-py:dev` | GUI WebApp | `docker run -p 8501:8501 joshipranjal/screeni-py:dev` |

**Why we shifted to Docker from the Good old EXEs?**

| Executable/Binary File | Docker |
| :-- | :-- |
| [![GitHub all releases](https://img.shields.io/github/downloads/pranjal-joshi/Screeni-py/total?color=Green&label=Downloads&style=for-the-badge)](#) | ![Docker Pulls](https://img.shields.io/docker/pulls/joshipranjal/screeni-py?style=for-the-badge&logo=docker) |
| Download Directly from the [Release](https://github.com/pranjal-joshi/Screeni-py/releases/latest) page (DEPRECATED) | Need to Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) ⚠️|
| May take a long time to open the app | Loads quickly |
| Slower screening | Performance boosted as per your CPU capabilities |
| You may face errors/warnings due to different CPU arch of your system ⚠️ | Compatible with all x86_64/amd64/arm64 CPUs irrespective of OS (including Mac M1/M2) |
| Works only with Windows 10/11 ⚠️ | Works with older versions of Windows as well |
| Different file for each OS | Same container is compatible with everyone |
| Antivirus may block this as untrusted file ⚠️ | No issues with Antivirus | 
| Need to download new file for every update | Updates quickly with minimal downloading |
| No need of commands/technical knowledge | Very basic command execution skills may be required |
| Incompatible with Vector Database ⚠️ | Compatible with all Python libraries |


## How to use?

[**Click Here**](https://github.com/pranjal-joshi/Screeni-py) to read the documentation.

## Join our Community Discussion

[**Click Here**](https://github.com/pranjal-joshi/Screeni-py/discussions) to join the community discussion and see what other users are doing!

## Facing an Issue? Found a Bug?

[**Click Here**](https://github.com/pranjal-joshi/Screeni-py/issues/new/choose) to open an Issue so we can fix it for you!

## Want to Contribute?

[**Click Here**](https://github.com/pranjal-joshi/Screeni-py/blob/main/CONTRIBUTING.md) before you start working with us on new features!

## Disclaimer:
* DO NOT use the result provided by the software solely to make your trading decisions.
* Always backtest and analyze the stocks manually before you trade.
* The Author(s) and the software will not be held liable for any losses.