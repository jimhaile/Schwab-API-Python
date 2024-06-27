from dotenv import load_dotenv

from schwabdev import api, Client
import os
import myStuff
from datetime import datetime, timedelta
from time import sleep
import json

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


def main():
    # place your app key and app secret in the .env file
    load_dotenv()  # load environment variables from .env file

    client = Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # update tokens automatically (except refresh token)

    print("\n\nAccounts and Trading - Accounts.")

    # get account number and hashes for linked accounts
    print("|\n|client.account_linked().json()", end="\n|")
    linked_accounts = client.account_linked().json()
    print(linked_accounts)
    # this will get the first linked account
    #account_hash = linked_accounts[0].get('hashValue')
    linked_accounts = client.account_linked().json()
    print(linked_accounts)
    # this will get the first linked account
    account_hash = linked_accounts[0].get('hashValue')
    print(account_hash)

    myStuff.getUltraPlusNP()
    goList, strikeList, symList, priceList = myStuff.read_unpp_file()
    print(goList, strikeList, symList, priceList)

    if (goList[0] == goList[1]):
        if goList[0] < 0:
            debitCredit = "NET_CREDIT"
        else:
            debitCredit = "NET_DEBIT"

        myquote = client.quotes(symList).content
        data_str = myquote.decode('utf-8')

        print("data str", data_str)
        data_dict = json.loads(data_str)
        mark_dict = {symbol: data_dict[symbol]['quote']['mark'] for symbol in symList}
        putSpreadPrice = abs(round(mark_dict.get(symList[0]) - mark_dict.get(symList[1]), 2))
        callSpreadPrice = abs(round(mark_dict.get(symList[2]) - mark_dict.get(symList[3]), 2))
        condorOrder = myStuff.createCondorOrder(debitCredit, symList, 1, round((putSpreadPrice + callSpreadPrice), 2))
        print("Placing Short Condor Order")
        resp = client.order_place(account_hash, condorOrder)
        print(f"Place put order response: {resp}")
        putOrderID = resp.headers.get('location', '/').split('/')[-1]
        print(f"PutOrderID: {putOrderID}")

        if goList[0] < 0:
            exit()  #this is a long combo

        else:
            exit()
        #this is a short combo
    print(symList)
    myquote = client.quotes(symList).json()
    print(myquote)
    data_str = myquote.decode('utf-8')
    print("data str", data_str)
    data_dict = json.loads(data_str)
    mark_dict = {symbol: data_dict[symbol]['quote']['mark'] for symbol in symList}
    putSpreadPrice = abs(round(mark_dict.get(symList[0]) - mark_dict.get(symList[1]), 2))
    callSpreadPrice = abs(round(mark_dict.get(symList[2]) - mark_dict.get(symList[3]), 2))
    print(mark_dict)
    print(putSpreadPrice)
    print(callSpreadPrice)
    putPriceList = [mark_dict.get(symList[0]), mark_dict.get(symList[1])]
    callPriceList = [mark_dict.get(symList[2]), mark_dict.get(symList[3])]

    myPutOrder = myStuff.createOrder(debitCredit, symList[0], symList[1], 1, putSpreadPrice)
    print("MyPutOrder -", myPutOrder)

    if goList[1] < 0:
        debitCredit = "NET_CREDIT"
    else:
        debitCredit = "NET_DEBIT"

    myCallOrder = myStuff.createOrder(debitCredit, symList[2], symList[3], 1, callSpreadPrice)
    print("MyCallOrder -", myCallOrder)

    # get accounts numbers for linked accounts
    #    print(api.accounts.accountNumbers().json())

    # get positions for linked accounts
    # Get the hash value for the 'IRA' account
    ira_hash_value = get_hash_value(accts, "IRA")
    pm_hash_value = get_hash_value(accts, "PM")
    print(f"The hash value for the IRA account is: {ira_hash_value}")
    print(f"The hash value for the PM account is: {pm_hash_value}")

    print("Credentials: ", api.credentials.accountNumber)

    print(api.accounts.getAllAccounts().json())

    #    print(api.accounts.getAccount(fields="positions").json())

    # get up to 3000 orders for an account for the past week
    #    print(api.orders.getOrders(3000, datetime.now() - timedelta(days=3), datetime.now()).json())

    # place an order (uncomment to test)
    print("Placing Put Order")

    resp = api.orders.placeOrder(myPutOrder)

    print(f"Place put order response: {resp}")
    putOrderID = resp.headers.get('location', '/').split('/')[-1]
    print(f"PutOrderID: {putOrderID}")

    # get a specific order
    print(api.orders.getOrder(putOrderID).json())

    print("Placing Call Order")
    resp = api.orders.placeOrder(myCallOrder)

    print(f"Place call order response: {resp}")
    callOrderID = resp.headers.get('location', '/').split('/')[-1]
    print(f"CallOrderID: {callOrderID}")

    # get a specific order
    print(api.orders.getOrder(putOrderID).json())
    print(api.orders.getOrder(callOrderID).json())

    sleep(10)
    # cancel specific order
    #    print(api.orders.cancelOrder(putOrderID))
    #    print(api.orders.cancelOrder(callOrderID))

    # replace specific order
    # api.orders.replaceOrder(orderID, order)

    # get up to 3000 orders for all accounts for the past week
    #    print(api.orders.getAllOrders(3000, datetime.now() - timedelta(days=1), datetime.now()).json())

    # preview order (not implemented by Schwab yet
    # api.orders.previewOrder(orderObject)

    # get all transactions for an account
    #    print(api.transactions.transactions(datetime.now() - timedelta(days=7), datetime.now(), "TRADE").json())

    # get details for a specific transaction
    # print(api.transactions.details(transactionId).json())

    # get user preferences for an account
    #    print(api.userPreference.userPreference().json())

    # get a list of quotes
    #    print(api.quotes.getList(symList).json())

    # get a single quote
    #    print(api.quotes.getSingle("$SPX").json())

    # get a option chains
    #    print(api.options.chains("AAPL").json())

    # get an option expiration chain
    #    print(api.options.expirationChain("$SPX").json())

    # get price history for a symbol
    # print(api.priceHistory.bySymbol("AAPL").json()) # there is a lot to print

    # get movers for an index
    #    print(api.movers.getMovers("$DJI").json())

    # get marketHours for a symbol
    #    print(api.marketHours.byMarkets("equity,option").json())

    # get marketHours for a market
    #    print(api.marketHours.byMarket("equity").json())

    # get instruments for a symbol
    #    print(api.instruments.bySymbol("AAPL", "search").json())

    # get instruments for a cusip
    #    print(api.instruments.byCusip("037833100").json())  # 037833100 = AAPL

    """
    # send a subscription request to the stream (uncomment if you start the stream below)
    stream.send(stream.utilities.basicRequest("CHART_EQUITY", "SUBS", parameters={"keys": "AMD,INTC", "fields": "0,1,2,3,4,5,6,7,8"}))

    # stop the stream after 30s
    stream.stop()
    """


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
