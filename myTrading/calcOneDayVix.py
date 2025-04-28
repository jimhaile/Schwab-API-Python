from schwabdev import api, Client
from datetime import datetime, timedelta
from dotenv import load_dotenv
from time import sleep
import os
import math
import json
import csv
import pandas as pd
from getDollarSpreads import getDollarSpreads

useTestFile = False


verbose = 0
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)


def is_holiday(date):
    # Example list of holidays, you can modify this as needed
    holidays = [
        datetime(2025, 1, 1),  # New Year's Day
        datetime(2025,1, 9),
        datetime(2025, 1, 20),
        datetime(2025,2,17),
        datetime(2025,4,18),
        datetime(2025, 5, 26),
        datetime(2025, 6, 19),
        datetime(2025, 7, 4),
        datetime(2025, 9, 1),
        datetime(2025, 11, 27),
        datetime(2025, 12, 25)

    ]
    return date.date() in [holiday.date() for holiday in holidays]


def next_business_day():
    now = datetime.now()
    if now.time() > datetime.strptime("13:15", "%H:%M").time():
        now += timedelta(days=1)

    next_day = now + timedelta(days=1)

    while next_day.weekday() >= 5 or is_holiday(next_day):  # Saturday = 5, Sunday = 6
        next_day += timedelta(days=1)

    return next_day

def minutes_until_expiration(expiration_date_str):
    expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
    expiration_datetime = datetime.combine(expiration_date, datetime.strptime("13:15", "%H:%M").time())
    now = datetime.now()
    delta = expiration_datetime - now
    total_minutes = delta.total_seconds() // 60
    #print(total_minutes)
    return max(total_minutes, 0)

# Example usage
nextBizDay = next_business_day()
#print(f'The next business day is: {nextBizDay}')

def main():
    #print(client.quote("$SPX").json())
    IRXPrice = (client.quote("$IRX").json())
    SPX = (client.quote("$SPX").json())
    VIX = (client.quote("$VIX").json())
    rate = IRXPrice['$IRX']['quote']['lastPrice']/1000
    tdate = datetime.now().strftime("%Y-%m-%d")
    exp = next_business_day().strftime("%Y-%m-%d")


    #print(f"Risk Free Rate: {risk_free_rate}")
    SPXQuote = f"SPX: {SPX['$SPX']['quote']['lastPrice']:.2f}"
    VIXQuote = f"VIX: {VIX['$VIX']['quote']['lastPrice']:.2f}"


    data = client.option_chains("$SPX", fromDate=nextBizDay, toDate=nextBizDay).json()


    csv_file = '/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/options_data.csv'


    # Open CSV file for writing
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Write the header row


        # Helper function to extract options data
        def extract_options(data, option_type):
            options = {}
            exp_date_map = data.get(f'{option_type}ExpDateMap', {})
            for exp_date, strikes in exp_date_map.items():
                for strike_price, option_list in strikes.items():
                    if option_list:
                        option = option_list[0]
                        options[strike_price] = (option['bid'], option['ask'])
            return options

        # Extract call and put options data
        call_options = extract_options(data, 'call')
        put_options = extract_options(data, 'put')

        # Collect all unique strike prices and sort them
        all_strike_prices = sorted(set(call_options.keys()).union(set(put_options.keys())))

        # Write data for each strike price
        for strike_price in all_strike_prices:
            call_bid, call_ask = call_options.get(strike_price, ('', ''))
            put_bid, put_ask = put_options.get(strike_price, ('', ''))
            writer.writerow([strike_price, call_bid, call_ask, put_bid, put_ask])

    #print(f'Data written to {csv_file}')


    column_names = ['strike_price', 'call_bid', 'call_ask', 'put_bid', 'put_ask']
    # Read the CSV file into a DataFrame without headers and add column names
    df = pd.read_csv(csv_file, header=None, names=column_names)
    #print(df)
    # Calculate minutes and years to expiration date

    expiration_date_str = next_business_day().strftime('%Y-%m-%d')
    Nt = minutes_until_expiration(expiration_date_str)
    T = Nt / (60 * 24 * 365)
    #rate = 0.044

    if verbose >= 1:
        print('Nt:', Nt)
        print('T:', T)

    # Step 1: Select the options to be used in the VIX Index calculation
    # Compute F for the near term
    df['mid_call'] = (df['call_bid'] + df['call_ask']) / 2
    df['mid_put'] = (df['put_bid'] + df['put_ask']) / 2
    df['diff'] = abs(df['mid_call'] - df['mid_put'])

    Fstrike = df.loc[df['diff'].idxmin(), 'strike_price']
    Fcall = df.loc[df['diff'].idxmin(), 'mid_call']
    Fput = df.loc[df['diff'].idxmin(), 'mid_put']
    F = Fstrike + math.exp(rate * T) * (Fcall - Fput)

    selectedoptions = []

    k0i = df[df['strike_price'] < F]['strike_price'].idxmax()
    k0 = df.loc[k0i, 'strike_price']

    #print(df.loc[k0i, 'mid_call'], df.loc[k0i, 'mid_put'])
    df.loc[k0i, 'mid_call'] = (df.loc[k0i, 'mid_call'] + df.loc[k0i, 'mid_put']) / 2
    #df.loc[k0i, 'mid_call'] = 22.775  I commented this out. I think it was a temp fix during debugging 11/20/24
    df.at[k0i, 'mid_put'] = df.at[k0i, 'mid_call']
    #df.at[k0i, 'mid_put'] = 22.775  I commented this out. I think it was a temp fix during debugging 11/20/24
    #print(df.at[k0i, 'mid_call'], df.at[k0i, 'mid_put'])

    # Collect out-of-the-money put options (including the put at k0)
    puts = []
    consecutive_zeros = 0
    for i in range(k0i, -1, -1):
        d = df.iloc[i]
        if d['put_bid'] > 0:
            puts.insert(0, [d['strike_price'], 'put', (d['put_bid'] + d['put_ask']) / 2])
            consecutive_zeros = 0
        else:
            if consecutive_zeros == 0:
                consecutive_zeros += 1
            else:
                break

    # Collect out-of-the-money call options (including the call at k0)
    calls = []
    consecutive_zeros = 0
    for i in range(k0i + 1, len(df)):
        d = df.iloc[i]
        if d['call_bid'] > 0:
            calls.append([d['strike_price'], 'call', (d['call_bid'] + d['call_ask']) / 2])
            consecutive_zeros = 0
        else:
            if consecutive_zeros == 0:
                consecutive_zeros += 1
            else:
                break

    # Append collected options to selectedoptions
    selectedoptions.extend(puts)
    selectedoptions.extend(calls)

    # Convert selected options back to a DataFrame for further processing
    selectedoptions = pd.DataFrame(selectedoptions, columns=['strike_price', 'type', 'mid'])

    selectedoptions = selectedoptions.sort_values(by='strike_price').reset_index(drop=True)

    if verbose == 2:
        print('selectedoptions:')
        print(selectedoptions)

    # Step 2: Calculate volatility for near-term options

    selectedoptions = selectedoptions.copy()
    # Calculate deltak as the average distance between the strike above and strike below
    selectedoptions['upperstrike'] = selectedoptions['strike_price'].shift(-1)
    selectedoptions['lowerstrike'] = selectedoptions['strike_price'].shift(1)
    selectedoptions['deltak'] = (selectedoptions['upperstrike'] - selectedoptions['lowerstrike']) / 2
    selectedoptions['deltak'] = selectedoptions['deltak'].bfill()
    selectedoptions['deltak'] = selectedoptions['deltak'].ffill()
    # print(selectedoptions)

    selectedoptions['contribution'] = (selectedoptions['deltak'] / (selectedoptions['strike_price'] ** 2)) * math.exp(
        rate * T) * selectedoptions['mid']

    if verbose == 2:
        print('contributions by strike:')
        print(selectedoptions[['strike_price', 'deltak', 'contribution']])

    # Aggregate the contributions by strike
    aggregatedcontributionbystrike = selectedoptions['contribution'].sum()
    aggregatedcontributionbystrike = (2 / T) * aggregatedcontributionbystrike

    sigmasquared = aggregatedcontributionbystrike - (1 / T) * ((F / k0 - 1) ** 2)

    if sigmasquared < 0:
        print("Error: sigma squared is negative, which should not happen. Please check the input data and calculations.")
    else:
        if verbose:
            print('sigmasquared:', sigmasquared)

        # Calculate the 1-day VIX
    N1 = Nt
    N30 = 30 * 1440
    N365 = 365 * 1440

    VIXOne = 100 * math.sqrt(sigmasquared * T * N365 / N1)

    #print(VIX['$VIX']['quote']['lastPrice'])
    #print(VIXOne)
    #print(SPX['$SPX']['quote']['lastPrice'])
    #print(F)
    putStrike, callStrike, callSpreadPrice, putSpreadPrice = getDollarSpreads()

    result = {
        "time": datetime.now().strftime('%H:%M:%S'),
        "tdate": tdate,
        "exp": exp,
        "VIX": format(VIX['$VIX']['quote']['lastPrice'],".2f"),
        "VIXOne": format(VIXOne,".2f"),
        "SPX": format(SPX['$SPX']['quote']['lastPrice'],".2f"),
        "Forward": format(F,".2f"),
        "putStrike": putStrike,
        "callStrike": callStrike,
        "callSpreadPrice": callSpreadPrice,
        "putSpreadPrice": putSpreadPrice
    }
    #print(result)
    # Print it as a single JSON line. Make sure no other prints occur.
    print(json.dumps(result))
    filename = "/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/VixOne.json"
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)


    #print(f"{datetime.now().strftime('%H:%M:%S')} {str(VIXQuote)} {str(f'VIX One: {VIXOne:.2f}')} {str(SPXQuote)} {str(f'Forward : {F:.2f}')}")

if __name__ == '__main__':
    #print("Welcome to the unofficial Schwab api interface!\nGithub: https://github.com/tylerebowers/Schwab-API-Python")
    #api.initialize()  # checks tokens & loads variables
    #api.updateTokensAutomatic()  # starts thread to update tokens automatically
    load_dotenv()
    client = Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # update tokens automatically (except refresh token)
    # stream.startManual()  # start the stream manually
    #    api._RefreshTokenUpdate()
    main()  # call the user code above
