'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   21/04/2021
 *  Description         :   Class for handling OTA updates
'''

from ColorText import colorText
import requests
import os
import platform
import sys

class OTAUpdater:
    # Check for update and download if available
    def checkForUpdate(proxyServer, VERSION="1.0"):
        try:
            resp = None
            now = float(VERSION)
            if proxyServer:
                resp = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest",proxies={'https':proxyServer})
            else:
                resp = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest")
            if(float(resp.json()['tag_name']) > now):
                url = resp.json()['assets'][1]['browser_download_url']
                size = int(resp.json()['assets'][1]['size']/(1024*1024))
                if platform.system() != 'Windows':
                    url = resp.json()['assets'][0]['browser_download_url']
                    size = int(resp.json()['assets'][0]['size']/(1024*1024))
                action = str(input(colorText.BOLD + colorText.WARN + ('\n[+] New Software update (v%s) available. Download Now (Size: %dMB)? [Y/N]: ' % (str(resp.json()['tag_name']),size)))).lower()
                if(action == 'y'):
                    try:
                        print(colorText.BOLD + colorText.WARN + ('Downloading Update of %dMBs, This may take a few minutes, Please Wait...' % size) + colorText.END)
                        download = requests.get(url, proxies={'https':proxyServer})
                        fn = 'screenipy.exe'
                        if platform.system() != 'Windows':
                            fn = 'screenipy.bin'
                        if os.path.exists(fn):
                            os.remove(fn)
                        with open(fn,'wb') as f:
                            f.write(download.content)
                        print(colorText.BOLD + colorText.GREEN + '[+] Update Completed.\n[+] Restart the program now.' + colorText.END)
                        if platform.system() != 'Windows':
                            os.system('chmod +x screenipy.bin')
                        input('')
                        sys.exit(0)
                    except Exception as e:
                        print(colorText.BOLD + colorText.WARN + '[+] Error occured while updating!' + colorText.END)
                        raise(e)
                        input('')
                        sys.exit(1)
            elif(float(resp.json()['tag_name']) < now):
                print(colorText.BOLD + colorText.FAIL + ('[+] This version (v%s) is in Development mode and unreleased!' % VERSION) + colorText.END)
        except Exception as e:
            print("[+] Failure while checking update due to error.")
            print(e)
