import json
import pandas as pd
import requests
import time
from web3 import Web3
import logging
import http.client, urllib.parse
import os
from dotenv import load_dotenv

load_dotenv(".env", override=True)
pushover_api_key = os.environ['MY_PUSHOVER_API_KEY']
pushover_user_key = os.environ['MY_WORK_PUSHOVER_USER_KEY']
gnosis_base_url = "https://safe-transaction-mainnet.safe.global/api/v1"


def send_pushover_alert(message, priority=0, user_key=pushover_user_key):
    if priority == 2:
        sound = "persistent"
    else:
        sound = "tugboat"

    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.parse.urlencode({
                     "token": pushover_api_key,
                     "user": user_key,
                     "message": message,
                     "priority": priority,
                     "retry": 30,
                     "expire": 600,
                     "sound": sound,
                 }), {"Content-type": "application/x-www-form-urlencoded"})
    print(conn.getresponse().read())
    return None


def get_safe_txs(safe):
    response = requests.get(f"{gnosis_base_url}/safes/{safe}/multisig-transactions")
    if response.status_code == 200:
        data = response.json()
        return data['results']
    else:
        raise Exception(f'{response.status_code}: {response.text}')


def detect_new_txs():
    logging.basicConfig(
        filename='./data/safes.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    check_interval = 1

    safes = {
        '0xfef30c262676de9af5e5e9ba999cf774000b14b4': 'eth',
        '0xee7f7f53f0d0c8c56a38e97c5a58e4d321a174dc': 'eth',
        '0xf32e3596f555546acc4ad6ef67e1abf36b134748': 'eth',
        '0x5be9a4959308a0d0c7bc0870e319314d8d957dbb': 'eth',
        '0x000000000000000000000000000000000A11B004': 'plasma',
        '0x000000000000000000000000000000000A11b001': 'plasma',
        '0x000000000000000000000000000000000A11b002': 'plasma',
        '0x000000000000000000000000000000000a11b003': 'plasma',
    }
    seen_hashes = []

    for safe in safes:
        checksum_safe = str(Web3.to_checksum_address(safe))
        s = get_safe_txs(checksum_safe)
        unexecuted_txs = [t['safeTxHash'] for t in s if not t['isExecuted']]
        for t in unexecuted_txs:
            seen_hashes.append(t)
            time.sleep(check_interval)

    while True:
        for safe in safes:
            try:
                time.sleep(check_interval)
                s = get_safe_txs(str(Web3.to_checksum_address(safe)))
                unexecuted_txs = [t['safeTxHash'] for t in s if not t['isExecuted']]
                result = ''
                for t in unexecuted_txs:
                    if t not in seen_hashes:
                        chain = safes[safe]
                        link = f'https://app.safe.global/transactions/tx?safe={chain}:{safe}&id=multisig_{safe}_{t}'
                        send_pushover_alert(f'New safe tx: {link}', priority=2)
                        seen_hashes.append(t)
                        result += f'new tx {t}'
                message = f'checked {safe} {result}'
                logging.info(message)
            except Exception as e:
                logging.info(f'{e} for {safe}')


if __name__ == "__main__":
    detect_new_txs()




