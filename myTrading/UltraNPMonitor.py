import time
from datetime import datetime, time as dt_time, date
import requests
import pandas as pd
from termcolor import colored
import subprocess
import json

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 500)

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def getVIXOne():
    """
    Runs calcOneDayVix.py and returns (VIX, VIXOne, SPX, Forward) as strings.
    If there's any error (empty output or JSON parse error),
    return four empty strings.
    """
    result = subprocess.run(
        [
            '/Users/jim/PycharmProjects/Schwab-API-Python/.venv/bin/python',
            '/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/calcOneDayVix.py'
        ],
        cwd="/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/",
        capture_output=True,
        text=True
    )

    output_string = result.stdout.strip()
    #print(output_string)


    if not output_string:
        print("Could not decode JSON from calcOneDayVix.py. Output was empty!")
        return "", "", "", ""

    try:
        data = json.loads(output_string)
    except json.JSONDecodeError as e:
        print(f"Could not decode JSON from calcOneDayVix.py. Output was:\n{repr(output_string)}")
        return "", "", "", ""

    # Default values
    VIX = data.get("VIX", "")
    VIXOne_val = data.get("VIXOne", 0.0)

    SPX = data.get("SPX", 0.0)
    Forward_val = data.get("Forward", 0.0)

    # Convert to strings as needed
    #VIXOne_str = "{:.2f}".format(VIXOne_val) if isinstance(VIXOne_val, (int, float)) else ""
    VIXOne_str = VIXOne_val

    #Forward_str = "{:.2f}".format(Forward_val) if isinstance(Forward_val, (int, float)) else ""
    Forward_str = Forward_val
    return VIX, VIXOne_val, SPX, Forward_val
    #Fix this later

def getUltraPlusNP():
    today = date.today()
    # url = 'https://gandalf.gammawizard.com/rapi/GetUltraNP'
    #url = 'https://gandalf.gammawizard.com/rapi/GetUltraPureConstantStable'
    url = 'https://gandalf.gammawizard.com/rapi/GetUltraPureConstantStableTuned'
    f = open('/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/gandalf_token.txt', 'r')
    bearer = f.read()
    headers = {'Authorization': bearer}

    retries = 3
    tries = 0

    while True:
        try:
            UltraPlusNP = requests.get(url, headers=headers)
            # If we reach here, the request succeeded
            break
        except requests.exceptions.RequestException as e:  # (Fix #3: more specific exception)
            print(f"Try number: {tries}, request error: {e}")
            tries += 1
            if tries >= retries:
                print("Maximum retries hit")
                # If you have a routine to refresh tokens, call it here
                # get_gandalf_token.login()
                # get_gandalf_token.get_token()
                # get_gandalf_token.driver.close()
                exit()
            time.sleep(10)

    try:
        z = UltraPlusNP.json()
        #print(z)
        if "Trade" in z and len(z["Trade"]) > 0:
            trade_info = z["Trade"][0]
            trade_fields = {
                "tdate": trade_info["Date"],
                "exp": trade_info["TDate"],
                "putStrike": trade_info["Limit"],
                "callStrike": trade_info["CLimit"],
                "putSpreadPrice": trade_info["Put"],
                "callSpreadPrice": trade_info["Call"],
                "leftGo": trade_info["LeftGo"],
                "rightGo": trade_info["RightGo"],
            }
        else:
            trade_fields = {}
            print("No 'Trade' data found in the API response!")
            return  # Stop execution here or handle it as needed.

        df = pd.DataFrame([trade_fields])
        now = datetime.now()
        d = (now.strftime("%H:%M:%S"))

        putStrike = trade_fields['putStrike']
        callStrike = trade_fields['callStrike']
        putSpreadPrice = trade_fields['putSpreadPrice']
        callSpreadPrice = trade_fields['callSpreadPrice']
        leftGo_val = float(trade_fields['leftGo'])
        rightGo_val = float(trade_fields['rightGo'])

        # Determine trade type and price
        if sign(leftGo_val) == sign(rightGo_val):
            trade = "Condor"
            price = sign(leftGo_val) * putSpreadPrice + sign(rightGo_val) * callSpreadPrice
            if leftGo_val < 0:
                BS = "Short"
                color = 'yellow'
            else:
                BS = "Long "
                color = 'blue'
        else:
            trade = "Combo "
            if leftGo_val < 0:
                BS = "Long "
                price = callSpreadPrice - putSpreadPrice
                color = 'green'
            else:
                BS = "Short"
                price = putSpreadPrice - callSpreadPrice
                color = 'red'

        if price < 0:
            DC = "Credit"
        elif price == 0:
            DC = "Even  "
        else:
            DC = "Debit "

        price = abs(price)

        # Get VIX, VIXOne, SPX, Forward
        VIX, VIXOne, SPX, Forward = getVIXOne()

        fForward = safe_float(Forward, 0.0)
        fSPX = safe_float(SPX, 0.0)
        diff = "{:.2f}".format(fForward - fSPX)

        leftGo = "{:.2f}".format(leftGo_val)
        rightGo = "{:.2f}".format(rightGo_val)

        output = (
            f"{datetime.now().strftime('%H:%M:%S')} {BS} {trade} {putStrike} {callStrike} "
            f"{float(price):.2f}  {DC} {VIX} {VIXOne} {SPX} {Forward} {diff} {leftGo} {rightGo}"
        )
        file_path = "/Users/jim/npmonitor.txt"

        with open(file_path, "a") as f:
            f.write(output + "\n")

        colored_output = colored(output, color)

        if (abs(leftGo_val) > 0.25) and (abs(rightGo_val) > 0.25):
            print(colored_output)
            df.to_csv('/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/UltraPlusNP.csv', index=False)

    except Exception as e:
        print(f"Exception parsing UltraPlusNP: {e}")
        # Optionally log 'where' or 'trade_info' if needed
        print(trade_info)
        time.sleep(15)

def run_function_between_times(start_time, end_time, interval_seconds):
    while True:
        current_time = datetime.now().time()

        # Check if current time is within the specified range
        if start_time <= current_time <= end_time:
            getUltraPlusNP()
        else:
            print("Current time is outside the specified range. Waiting to start...")

        # Wait for the specified interval
        time.sleep(interval_seconds)

if __name__ == "__main__":
    start_time = dt_time(6, 30)  # 6:30 AM
    end_time = dt_time(15, 25)   # 1:25 PM
    interval_seconds = 15
    run_function_between_times(start_time, end_time, interval_seconds)