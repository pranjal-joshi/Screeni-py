#!/bin/bash

echo "[+] Pranjal -> Setting up dependencies for TA-Lib"
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install