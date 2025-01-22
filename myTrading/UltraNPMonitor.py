import time
from datetime import datetime, time as dt_time, date
import requests
import pandas as pd
from termcolor import colored
import subprocess
import json

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 500)

def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
def getVIXOne():
    """
    Runs calcOneDayVix.py and returns (VIX, VIXOne, SPX, Forward).
    If the subprocess output is invalid JSON or missing fields,
    set them to empty (or None) by default.
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

    # Strip out trailing newlines
    output_string = result.stdout.strip()
    #print(output_string)
    # Default values if parsing fails or keys are missing
    VIX = ""
    VIXOne = ""
    SPX = ""
    Forward = ""

    try:

        data = json.loads(output_string)

        # Safely extract values using .get()
        VIX = data.get("VIX", "")

        VIXOne = "{:.2f}".format(data.get("VIXOne", ""))
        SPX = data.get("SPX", 0.0)
        Forward = "{:.2f}".format(data.get("Forward", 0.0))

    except json.JSONDecodeError:
        # If we can't parse JSON, log or handle the error as needed
        print("Could not decode JSON from calcOneDayVix.py. Output was:")
        print(repr(output_string))

    return VIX, VIXOne, SPX, Forward

def getUltraPlusNP():
    #print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    today = date.today()
    #url = 'https://gandalf.gammawizard.com/rapi/GetUltraNP'
    url = 'https://gandalf.gammawizard.com/rapi/GetUltraPureConstantExperimental'
    f = open('/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/gandalf_token.txt', 'r')
    bearer = f.read()
    headers = {'Authorization': bearer}

    retries = 3
    tries = 0

    while True:
        try:
            UltraPlusNP = requests.get(url, headers=headers)

            # if this point is reached everything worked fine, so exit loop
            break
        except:
            print("Try number: ", tries)
            tries = tries + 1
            if tries >= retries:
                print("Maximum retries hit")
                #cmd = '/Users/jim/getGandalf'
                #os.system(cmd)
                get_gandalf_token.login()
                get_gandalf_token.get_token()
                get_gandalf_token.driver.close()
                exit()

            time.sleep(10)

    try:
        z = UltraPlusNP.json()

        # trade_info = z['Trade'][0]
        # tdate = trade_info['Date']
        #
        # # Collecting the desired fields for Trade
        # where = "TradeFields"
        # trade_fields = {
        #     'tdate': trade_info['Date'],
        #     'exp': trade_info['TDate'],
        #     'putStrike': trade_info['Limit'],
        #     'callStrike': trade_info['CLimit'],
        #     'putSpreadPrice': trade_info['Put'],
        #     'callSpreadPrice': trade_info['Call'],
        #     'leftGo': trade_info['LeftGo'],
        #     'rightGo': trade_info['RightGo']
        # }

        if "Trade" in z and len(z["Trade"]) > 0:
            trade_info = z["Trade"][0]
            # Continue as normal
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
            # Handle the case of no Trade data
            trade_fields = {}
            print("No 'Trade' data found in the API response!")
        df = pd.DataFrame([trade_fields])



        now = datetime.now()

        #d = (now.strftime("%Y-%m-%d %H:%M:%S"))
        d = (now.strftime("%H:%M:%S"))
        #tdate = z['Date']
        #tdate = trade_fields['tdate']


        #exp = trade_fields['exp']

        where = "putStrike"
        putStrike = trade_fields['putStrike']
        where = "callStrike"
        callStrike = trade_fields['callStrike']
        #print(callStrike)

        where = "putSpreadPrice"
        putSpreadPrice = trade_fields['putSpreadPrice']
        #print(putSpreadPrice)
        where = "callSpreadPrice"
        callSpreadPrice = trade_fields['callSpreadPrice']
        #print(callSpreadPrice)

        #leftGo = "{:.2f}".format(trade_fields['leftGo'])
        where = "leftGo"
        leftGo = float(trade_fields['leftGo'])
        where = "RightGo"
        rightGo = float(trade_fields['rightGo'])

        #print(leftGo)
        #print(rightGo)

        # df = pd.DataFrame({'date': [tdate],
        #                    'exp': [exp],
        #                    'putStrike': [putStrike],
        #                    'callStrike': [callStrike],
        #                    'putSpreadPrice': [putSpreadPrice],
        #                    'callSpreadPrice': [callSpreadPrice],
        #                    'leftGo': [leftGo],
        #                    'rightGo': [rightGo]
        #                    })
        where = "if"
        if sign(leftGo) == sign(rightGo):
            trade = "Condor"
            price = sign(leftGo) * putSpreadPrice + sign(rightGo) * callSpreadPrice
            if leftGo < 0:
                BS = "Short"
                color = 'yellow'
            else:
                BS = "Long "
                color = 'blue'
        else:
            trade = "Combo "
            if leftGo < 0:
                BS = "Long "
                price = callSpreadPrice - putSpreadPrice
                color = 'green'
            else:
                BS = "Short"
                price = putSpreadPrice - callSpreadPrice
                color = 'red'
        if price < 0:
            DC = "Credit"
        else:
            if price == 0:
                DC = "Even  "
            else:
                DC = "Debit "

        price = abs(price)
        #print(price)
        where = "getVixOne call"
        VIX, VIXOne,SPX,Forward = getVIXOne()
        #print(VIX)
        where = "formatting"

        diff = "{:.2f}".format(float(Forward) - float(SPX))
        leftGo = "{:.2f}".format(float(trade_fields['leftGo']))
        rightGo = "{:.2f}".format(float(trade_fields['rightGo']))
        #print(VIX, VIXOne,SPX,Forward)
        #output = (
        #    f"{datetime.now().strftime('%H:%M:%S')} {BS} {trade} {putStrike} {callStrike} {price:.2f} "
        #    f"{DC} {VIX} {VIXOne} {SPX} {Forward} {diff} {leftGo} {rightGo}"
        #)
        where = "output"
        output = (f"{datetime.now().strftime('%H:%M:%S')} {str(BS)} {str(trade)} {str(putStrike)} {str(callStrike)} {float(price):.2f}  "
                  f"{str(DC)} {str(VIX)} {str(VIXOne)}  {str(SPX)} {str(Forward)} {str(diff)} {str(leftGo)} {str(rightGo)}")
        colored_output = colored(output, color)
        where = "if"
        if((abs(float(trade_fields['leftGo'])) > 0.25) and abs(float(trade_fields['rightGo'])) > 0.25):
            print(colored_output)
            df.to_csv('/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/UltraPlusNP.csv', index=False)


    #    cmd = '/usr/local/mysql/bin/mysql -h localhost -u root -p --password=Xcal1ber < /Users/jim/NAS10.sql'
    #    os.system(cmd)

    except Exception as e:
        print(f"Exception parsing UltraPlusNP: {e}")
        print(where)
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
    # Define start and end times
    start_time = dt_time(6, 30)  # 6:30 AM
    end_time = dt_time(13, 25)   # 1:15 PM

    # Run the function every 15 seconds
    interval_seconds = 15
    run_function_between_times(start_time, end_time, interval_seconds)
