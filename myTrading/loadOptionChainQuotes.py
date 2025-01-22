import json
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime, timedelta
from dotenv import load_dotenv
from schwabdev import api, Client
import os
from datetime import datetime, timezone


def is_holiday(date):
    # Example list of holidays, you can modify this as needed
    holidays = [
        datetime(2025, 1, 1),  # New Year's Day
        datetime(2025, 1, 9),
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
    print(now)
    if now.time() > datetime.strptime("23:00", "%H:%M").time():
        now += timedelta(days=1)

    next_day = now + timedelta(days=1)

    while next_day.weekday() >= 5 or is_holiday(next_day):  # Saturday = 5, Sunday = 6
        next_day += timedelta(days=1)

    return next_day
def ms_to_mysql_datetime(ms):
    """
    Convert a millisecond timestamp to a Python datetime (local).
    If you need a local timezone, adjust accordingly.
    """
    if not ms:
        return None
    # Convert ms to seconds, then to datetime
    seconds = datetime.utcfromtimestamp(ms(ms) / 1000)
    dt_utc = datetime.utcfromtimestamp(seconds)
    dt_aware_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_aware_utc.astimezone()
    return dt_local.strftime('%Y-%m-%d %H:%M')


def get_quote_time_in_long(tda_json):
    # First, try calls
    call_map = tda_json.get("callExpDateMap", {})
    for exp_date_str, strikes_dict in call_map.items():
        for strike_str, contracts_list in strikes_dict.items():
            for contract_data in contracts_list:
                q_time = contract_data.get("quoteTimeInLong")
                if q_time:
                    return q_time

    # If not found in calls, try puts
    put_map = tda_json.get("putExpDateMap", {})
    for exp_date_str, strikes_dict in put_map.items():
        for strike_str, contracts_list in strikes_dict.items():
            for contract_data in contracts_list:
                q_time = contract_data.get("quoteTimeInLong")
                if q_time:
                    return q_time

    # If we never found it, return None
    return None

def convert_quote_ts_to_localtime(quote_ts):
    """
    Convert a UTC timestamp in milliseconds (quoteTimeInLong) to
    a local datetime string: 'YYYY-MM-DD HH:MM'
    """
    seconds = int(quote_ts) / 1000
    dt_utc = datetime.utcfromtimestamp(seconds)
    dt_aware_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_aware_utc.astimezone()
    return dt_local.strftime('%Y-%m-%d %H:%M')

def parse_tda_option_chain(tda_json, quote_date):
    """
    Parses TDA option chain JSON into a list of dictionaries
    where each dict matches the columns of the 'quotes' table.
    """

    # Example: we assume tda_json might have top-level callExpDateMap/putExpDateMap, etc.
    # This is just an illustrative skeleton—adapt to your real data structure.

    # We’ll store all resulting rows in a list:
    rows = []

    # Suppose you gather the underlying root/symbol from tda_json:
    root = tda_json.get("symbol")
    # If there's a separate underlyingPrice, store that:
    und_mark = tda_json.get("underlyingPrice")

    # Get the TDA option maps
    call_map = tda_json.get("callExpDateMap", {})
    put_map  = tda_json.get("putExpDateMap", {})

    # We’re also retrieving the "quoteTimeInLong" if you have that top-level:
    #quote_timestamp = tda_json.get("quoteTimeInLong")



    # Helper to parse each contract map
    def parse_options(exp_map, option_type):
        for exp_key, strikes in exp_map.items():
            # exp_key might look like "2025-01-06:2" => Just want "2025-01-06"
            # If you need only the date portion, you can split:
            expiration_ymd = exp_key.split(":")[0]
            # Convert "YYYY-MM-DD" to a Python date object
            try:
                expiration_date = datetime.strptime(expiration_ymd, "%Y-%m-%d").date()
            except ValueError:
                # fallback or error-handling
                expiration_date = None

            for strike, options_list in strikes.items():
                # TDA might store multiple option objects per strike
                for opt in options_list:
                    row = {
                        "quote_date" : quote_date,           # DATETIME
                        "root"       : opt.get("symbol")[:4],      #root,
                        "symbol"     : opt.get("symbol"),
                        "und_mark"   : und_mark,
                        "expiration" : expiration_date,      # DATE
                        "strike"     : float(strike),
                        "option_type": option_type.upper(),  # "CALL" or "PUT"
                        "volume"     : opt.get("totalVolume"),
                        "bid_size"   : opt.get("bidSize"),
                        "ask_size"   : opt.get("askSize"),
                        "bid"        : opt.get("bid"),
                        "ask"        : opt.get("ask"),
                        "mark"       : opt.get("mark"),
                        "iv"         : opt.get("volatility"),
                        "delta"      : opt.get("delta"),
                        "gamma"      : opt.get("gamma"),
                        "theta"      : opt.get("theta"),
                        "vega"       : opt.get("vega"),
                        "rho"        : opt.get("rho"),
                        "oi"         : opt.get("openInterest")
                    }

                    rows.append(row)

    # Parse calls
    parse_options(call_map, "CALL")
    # Parse puts
    parse_options(put_map, "PUT")

    return rows

def insert_quotes_into_mysql(records, db_config):
    """
    Inserts rows into the 'quotes' table.
    'records' is a list of dictionaries, each containing keys matching
    the 'quotes' table columns.
    'db_config' is a dict with 'host','user','password','database' for MySQL connection.
    """

    # Connect to MySQL
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Prepare the INSERT statement
    sql_insert = """
    INSERT INTO quotes (
        quote_date, root, symbol, und_mark, expiration, strike, option_type,
        volume, bid_size, ask_size, bid, ask, mark,
        iv, delta, gamma, theta, vega, rho, oi
    )
    VALUES (
        %(quote_date)s, %(root)s, %(symbol)s, %(und_mark)s, %(expiration)s,
        %(strike)s, %(option_type)s,
        %(volume)s, %(bid_size)s, %(ask_size)s, %(bid)s, %(ask)s, %(mark)s,
        %(iv)s, %(delta)s, %(gamma)s, %(theta)s, %(vega)s, %(rho)s, %(oi)s
    )
    """

    # Insert each record
    for record in records:
        try:
            cursor.execute(sql_insert, record)
        except mysql.connector.IntegrityError as err:
            # Check if it's a duplicate entry error
            if err.errno == errorcode.ER_DUP_ENTRY:
                print(f"Duplicate entry for symbol {record.get('symbol', '')}. Skipping insertion.")
            else:
                # Re-raise if it's some other integrity error
                raise
        except mysql.connector.Error as err:
            # Catch any other MySQL error
            print(f"MySQL error: {err}")
            raise
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # 1) Load or mock your TDA JSON:
    load_dotenv()
    client = Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # update tokens automatically (except refresh token)

    nextBizDay = next_business_day()

    tda_json = client.option_chains("$SPX", fromDate=nextBizDay, toDate=nextBizDay).json()

    quote_time_in_long = get_quote_time_in_long(tda_json)
#    if quote_time_in_long is not None:
 #       print("quoteTimeInLong =", quote_time_in_long)
  #  else:
   #     print("No quoteTimeInLong found in the JSON.")

    # Convert that to a datetime with hh:mm
    quote_date = convert_quote_ts_to_localtime(quote_time_in_long)

    print(quote_date)

    #tda_json = json.loads(tda_json)

    # 2) Parse JSON into table rows
    option_rows = parse_tda_option_chain(tda_json,  quote_date)

    # 3) Insert into MySQL
    # Adjust your DB connection credentials here
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "Xcal1ber!",
        "database": "trade"
    }

    insert_quotes_into_mysql(option_rows, db_config)
    print("Rows inserted successfully.")