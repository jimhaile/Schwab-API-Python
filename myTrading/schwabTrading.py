from dotenv import load_dotenv

from schwabdev import api, Client
import os
import myStuff
from datetime import datetime, timedelta
from time import sleep
import json
import numpy as np
longComboQty = 7
longCondorQty = 16
shortComboQty = 10

shortCondorQty = 8
shortCondorMQty = 15




accts = [
    {
        "nickName": "PM",
        "accountNumber": "24212118",
        "hashValue": "FE7045AD8FA2BACB58DF515FE403C99E6CD842014966215E65062D783EBBA2F4"
    },
    {
        "nickName": "IRA",
        "accountNumber": "39452254",
        "hashValue": "A1A6FA4FFD9279DDBCEB82BB7CD98C3AE6A50C8E672628C8D64A40ABD9D1B06D"
    }
]


def get_hash_value(accts, nickname):
    for acct in accts:
        if acct["nickName"] == nickname:
            return acct["hashValue"]
    return None
def load_client_data():
    client = Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # update tokens automatically (except refresh token)
    linked_accounts = client.account_linked().json()
    account_hash = linked_accounts[0].get('hashValue')
    return client, account_hash

def fetch_and_print_quotes(client, symList):
    myquote = client.quotes(symList).json()
    mark_dict = {symbol: myquote[symbol]['quote']['mark'] for symbol in symList}
    putSpreadPrice = abs(myStuff.round_to_nearest_nickel(mark_dict.get(symList[0]) - mark_dict.get(symList[1])))
    callSpreadPrice = abs(myStuff.round_to_nearest_nickel(mark_dict.get(symList[2]) - mark_dict.get(symList[3])))
    #putSpreadPrice = abs(round(mark_dict.get(symList[0]) - mark_dict.get(symList[1]), 2))
    #callSpreadPrice = abs(round(mark_dict.get(symList[2]) - mark_dict.get(symList[3]), 2))
    print("Put Spread ", putSpreadPrice)
    print("Call Spread ", callSpreadPrice)
    return putSpreadPrice, callSpreadPrice
def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
def main():
    # exit()
    print(datetime.now().strftime('%H:%M:%S'))
    load_dotenv()  # load environment variables from .env file
    client, account_hash = load_client_data()
    #myStuff.getUltraPlusNP()
    goList, strikeList, symList, priceList, days = myStuff.read_unpp_file()
    print(goList, strikeList, symList, priceList, days)

    putSpreadPrice, callSpreadPrice = fetch_and_print_quotes(client, symList)
    resp = None

# condors
    if (sign(goList[0]) == sign(goList[1])):
        if goList[0] < 0:
            debitCredit = "NET_CREDIT"
            spreadPrice = round(putSpreadPrice + callSpreadPrice - 0.05,2)
            if days > 2:
                qty = shortCondorMQty
            else:
                qty = shortCondorQty
        else:
            debitCredit = "NET_DEBIT"
            spreadPrice = round(putSpreadPrice + callSpreadPrice + 0.05,2)
            qty = longCondorQty

        condorOrder = myStuff.createCondorOrder(debitCredit, symList, qty, spreadPrice)
        print(datetime.now().strftime('%H:%M:%S'))
        print("Placing Condor Order")
        resp = client.order_place(account_hash, condorOrder)
        print(f"Condor order response: {resp}")
        condorOrderID = resp.headers.get('location', '/').split('/')[-1]
        print(f"CondorOrderID: {condorOrderID}")
        print(datetime.now().strftime('%H:%M:%S'))

        exit()
#combos
    if goList[0] < 0:
        print("This is a long combo")
        #print("Temporarily not trading combos")
        #exit()
        spreadPrice = myStuff.round_to_nearest_nickel(putSpreadPrice - callSpreadPrice )
        if spreadPrice > -1.0: #changed this from 0.0
            comboOrder = myStuff.createComboOrder("NET_CREDIT", goList[0], symList, longComboQty, spreadPrice)
            print(datetime.now().strftime('%H:%M:%S'))
            print("Placing Long Combo Order")
            resp = client.order_place(account_hash, comboOrder)
        else:
            print("Long Combo not a credit. No trade.")
            exit()

    else:
        print("This is a short combo")
        #print("Temporarily not trading combos")
        #exit()
        spreadPrice = myStuff.round_to_nearest_nickel(callSpreadPrice - putSpreadPrice )
        if spreadPrice > -1.0:   #changed this from 0
            comboOrder = myStuff.createComboOrder("NET_CREDIT", goList[0], symList, shortComboQty, spreadPrice)
            print(datetime.now().strftime('%H:%M:%S'))
            print("Placing Short Combo Order")
            resp = client.order_place(account_hash, comboOrder)
        else:
            print("Short Combo not a credit. No trade.")
            exit()

    order_id = resp.headers.get('location', '/').split('/')[-1]
    print(f"Order id: {order_id}")
    print(datetime.now().strftime('%H:%M:%S'))

    # get specific order details
    print("|\n|client.order_details(account_hash, order_id).json()", end="\n|")
    print(client.order_details(account_hash, order_id).json())
    #sleep(10)
    #client.order_cancel(account_hash, order_id)
    #order_replace(self, account_hash, order_id, order)





if __name__ == '__main__':
    print("Welcome to the unofficial Schwab api interface!\nGithub: https://github.com/tylerebowers/Schwab-API-Python")
    #api.initialize()  # checks tokens & loads variables
    #api.updateTokensAutomatic()  # starts thread to update tokens automatically
    load_dotenv()
    client = Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # update tokens automatically (except refresh token)
    # stream.startManual()  # start the stream manually
    #    api._RefreshTokenUpdate()
    main()  # call the user code above
