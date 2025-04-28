import pandas as pd
from datetime import datetime
from datetime import date
from pathlib import Path
import json
import time

import requests
import get_gandalf_token





def read_unpp_file():
    path = Path('/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/UltraPlusNP.csv')
    timestamp = date.fromtimestamp(path.stat().st_mtime)
    print(timestamp)

    if date.today() == timestamp:
        print("Today's file")
    else:
        print("File is old")
        exit()
    df = pd.read_csv(path,header=0)
    print(df.columns)

    highPutStrike = df["putStrike"].values[0]
    lowPutStrike = highPutStrike - 5.0
    lowCallStrike = df["callStrike"].values[0]
    highCallStrike = lowCallStrike + 5.0

    if (df["leftGo"].values[0] <= 0.0):
        longPutStrike = lowPutStrike
        shortPutStrike = highPutStrike
        df["putSpreadPrice"] -= .01
    else:
        longPutStrike = highPutStrike
        shortPutStrike = lowPutStrike
        df["putSpreadPrice"] += .01

    if (df["rightGo"].values[0] <= 0.0):
        shortCallStrike = lowCallStrike
        longCallStrike = highCallStrike
        df["callSpreadPrice"] -= .01
    else:
        longCallStrike = lowCallStrike
        shortCallStrike = highCallStrike
        df["callSpreadPrice"] += .01

    exp = df.exp.values[0]
    tradeDate = df.tdate.values[0]
    fmt = "%Y-%m-%d"
    d1 = datetime.strptime(tradeDate, fmt)
    d2 = datetime.strptime(exp, fmt)
    days = d2 - d1


    stringDate = exp[2:4] + exp[5:7] + exp[8:10]


    longPutSym = "SPXW  " + stringDate + "P" + str(int(longPutStrike*1000)).rjust(8,"0")
    shortPutSym = "SPXW  " + stringDate + "P" + str(int(shortPutStrike*1000)).rjust(8,"0")
    longCallSym = "SPXW  " + stringDate + "C" + str(int(longCallStrike*1000)).rjust(8,"0")
    shortCallSym = "SPXW  " + stringDate + "C" + str(int(shortCallStrike*1000)).rjust(8,"0")

    goList = [df["leftGo"].values[0],df["rightGo"].values[0]]
    strikeList = [df["putStrike"].values[0], df["callStrike"].values[0]]
    symList = [longPutSym, shortPutSym, longCallSym, shortCallSym]
    priceList = [round_to_nearest_nickel(df.putSpreadPrice.values[0]), round_to_nearest_nickel(df.callSpreadPrice.values[0])]
    return goList, strikeList, symList, priceList, days.days

def createOrder(dbCr, lsym, ssym, qty, price):
    x = {
        "orderType": dbCr,
        "session": "NORMAL",
        "price": price,
        "duration": "DAY",  # change this back to GOOD_TILL_CANCEL
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": "BUY_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": lsym,
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "SELL_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": ssym,
                    "assetType": "OPTION"
                }
            }
        ]
    }

    y = json.dumps(x)
    order_json = json.loads(y)
#    print(order_json)
    return order_json

def createCondorOrder(dbCr, symList, qty, price):
    x = {
        "orderType": dbCr,
        "session": "NORMAL",
        "price": price,
        "duration": "DAY",  # change this back to GOOD_TILL_CANCEL
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": "BUY_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": symList[0],
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "SELL_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": symList[1],
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "BUY_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": symList[2],
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "SELL_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": symList[3],
                    "assetType": "OPTION"
                }
            }
        ]
    }

    y = json.dumps(x)
    order_json = json.loads(y)
    print(order_json)
    return order_json

def createComboOrder(dbCr, goList, symList, qty, price):
    print("Combo Order")
    if goList < 0:
        buyCall = symList[2]
        sellCall = symList[3]
        buyPut = symList[0]
        sellPut = symList[1]
    else:
        buyCall = symList[2]
        sellCall = symList[3]
        buyPut = symList[0]
        sellPut = symList[1]


    x = {
        "orderType": dbCr,
        "session": "NORMAL",
        "price": price,
        "duration": "DAY",  # change this back to GOOD_TILL_CANCEL
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": "BUY_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": buyPut,
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "SELL_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": sellPut,
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "BUY_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": buyCall,
                    "assetType": "OPTION"
                }
            },
            {
                "instruction": "SELL_TO_OPEN",
                "quantity": qty,
                "instrument": {
                    "symbol": sellCall,
                    "assetType": "OPTION"
                }
            }
        ]
    }
    y = json.dumps(x)
    order_json = json.loads(y)
    print(order_json)
    return order_json
def round_to_nearest_nickel(amount):
    # Multiply the amount by 20, round it to the nearest whole number, and then divide by 20
    rounded_amount = round(amount * 20) / 20.0
    return rounded_amount

import requests
import time
import pandas as pd
from datetime import date, datetime
import json

# Make sure these imports exist in your project:
# import get_gandalf_token


def getUltraPlusNP():
    url = 'https://gandalf.gammawizard.com/rapi/GetUltraPureConstantStable'
    token_path = '/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/gandalf_token.txt'
    csv_path = '/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/UltraPlusNP.csv'

    # Read bearer token
    with open(token_path, 'r') as f:
        bearer = f.read().strip()
    headers = {'Authorization': bearer}

    # Attempt the request with up to 3 retries
    retries = 3
    tries = 0
    while True:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raises HTTPError if status != 200
            break  # If we got here, the GET worked; exit the retry loop
        except requests.RequestException as e:
            print(f"Try number {tries}: Request failed -> {e}")
            tries += 1
            if tries >= retries:
                print("Maximum retries hit. Attempting to refresh token and then stopping.")
                # Refresh the token:
                get_gandalf_token.login()
                get_gandalf_token.get_token()
                get_gandalf_token.driver.close()
                return  # or `exit()` if you want to fully stop

            time.sleep(5)  # Wait before next retry

    # Now parse the JSON
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Exception parsing UltraPlusNP: Invalid JSON response.")
        return  # or `exit()` if you want to stop entirely

    # Ensure the data is a list with at least one element
    if not isinstance(data, list) or len(data) == 0:
        print("No data returned or the response is not a list.")
        return

    # Grab the first element (dict) in the list
    z = data[0]
    # print(z)  # Debug if needed

    # Extract required fields. If any are missing, KeyError is raised.
    try:
        tdate = z['Date']
        exp = z['TDate']
        putStrike = z['Limit']
        callStrike = z['CLimit']
        putSpreadPrice = z['Put']
        callSpreadPrice = z['Call']
        leftGo = z['LeftGo']
        rightGo = z['RightGo']
    except KeyError as e:
        print(f"Missing key in UltraPlusNP response: {e}")
        print("Full object:", z)
        return

    # Print or log the date as confirmation
    print("UltraPlusNP Date:", tdate)

    # Build a DataFrame and save to CSV
    now = datetime.now()
    df = pd.DataFrame({
        'date': [tdate],
        'exp': [exp],
        'putStrike': [putStrike],
        'callStrike': [callStrike],
        'putSpreadPrice': [putSpreadPrice],
        'callSpreadPrice': [callSpreadPrice],
        'leftGo': [leftGo],
        'rightGo': [rightGo]
    })

    df.to_csv(csv_path, index=False)
    print(f"Data successfully saved to {csv_path}")


