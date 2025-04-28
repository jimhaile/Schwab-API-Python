import pandas as pd
import numpy as np

def getDollarSpreads():
    # 1. Read CSV into DataFrame
    filepath = "/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/options_data.csv"
    df = pd.read_csv(
        filepath,
        header=None,
        names=["strike_price", "call_bid", "call_ask", "put_bid", "put_ask"]
    )

    # Ensure the DataFrame is sorted by strike_price
    df = df.sort_values(by="strike_price").reset_index(drop=True)

    # 2. Compute midpoint (mark) for calls and puts
    df["call_mark"] = (df["call_bid"] + df["call_ask"]) / 2
    df["put_mark"]  = (df["put_bid"]  + df["put_ask"])  / 2

    # 3. Create a DataFrame of spreads for adjacent strikes
    spreads = pd.DataFrame()
    spreads["lower_strike"]    = df["strike_price"][:-1].values
    spreads["upper_strike"]    = df["strike_price"][1:].values

    # Calculate the absolute difference in call marks
    spreads["lower_call_mark"] = df["call_mark"][:-1].values
    spreads["upper_call_mark"] = df["call_mark"][1:].values
    spreads["call_spread"]     = (
        spreads["lower_call_mark"] - spreads["upper_call_mark"]
    ).abs()

    # Calculate the absolute difference in put marks
    spreads["lower_put_mark"]  = df["put_mark"][:-1].values
    spreads["upper_put_mark"]  = df["put_mark"][1:].values
    spreads["put_spread"]      = (
        spreads["lower_put_mark"] - spreads["upper_put_mark"]
    ).abs()

    # 4. Find the call_spread and put_spread closest to $1.00
    call_idx = (spreads["call_spread"] - 1.0).abs().idxmin()
    put_idx  = (spreads["put_spread"]  - 1.0).abs().idxmin()

    closest_call_spread = spreads.loc[call_idx]
    closest_put_spread  = spreads.loc[put_idx]

    # 5. Print the requested fields on one line:
    #    UPPER_PUT_STRIKE LOWER_CALL_STRIKE CALL_SPREAD_MARK PUT_SPREAD_MARK
    return( int(closest_put_spread['upper_strike']),
            int(closest_call_spread['lower_strike']),
            format(closest_call_spread['call_spread'],".2f"),
            format(closest_put_spread['put_spread'],".2f")

    )

if __name__ == "__main__":
    # Main program simply calls the function

    print(getDollarSpreads())