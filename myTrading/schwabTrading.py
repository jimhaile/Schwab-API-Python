import os
import logging
import time
from dotenv import load_dotenv
from schwabdev import api, Client
import myStuff

# Setup basic logging (to console at INFO level)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Order quantity constants
LONG_COMBO_QTY = 6
LONG_CONDOR_QTY = 15
SHORT_COMBO_QTY = 16
SHORT_CONDOR_QTY = 14
SHORT_CONDOR_M_QTY = 14

# Initial bid/offer adjustment value
BUMP = 0.0


def sign(x):
    """Returns 1 if x > 0, -1 if x < 0, else 0."""
    return 1 if x > 0 else -1 if x < 0 else 0


def get_debit_credit_for_combo(spread_price):
    """
    Determine the debit/credit flag for combo orders.
    If spread_price is less than or equal to 0, it's NET_CREDIT; otherwise, NET_DEBIT.
    """
    return 'NET_CREDIT' if spread_price <= 0 else 'NET_DEBIT'


def place_order_for_all_accounts(client, account_hashes, order_type, order_params):
    """
    Create an order (condor or combo) using myStuff functions,
    then place that order for each account in 'account_hashes'.

    :param client: Schwab API client
    :param account_hashes: list of account hash strings
    :param order_type: 'condor' or 'combo'
    :param order_params: dict with required params:
        - For condor: debitCredit, symList, qty, spreadPrice
        - For combo:  debitCredit, goValue, symList, qty, spreadPrice
    :return: list of dicts with 'acct_hash', 'resp', 'order_id', 'details' for each successful placement
    """
    # Create the order using the appropriate function
    if order_type == 'condor':
        order = myStuff.createCondorOrder(
            order_params['debitCredit'],
            order_params['symList'],
            order_params['qty'],
            order_params['spreadPrice']
        )
    elif order_type == 'combo':
        order = myStuff.createComboOrder(
            order_params['debitCredit'],
            order_params['goValue'],
            order_params['symList'],
            order_params['qty'],
            order_params['spreadPrice']
        )
    else:
        logging.error(f"Unknown order_type: {order_type}. No orders placed.")
        return []

    logging.info(f"Placing {order_type.upper()} order for each account: {order_params}")

    results = []
    for acct_hash in account_hashes:
        try:
            resp = client.order_place(acct_hash, order)
            if resp.status_code >= 400:
                logging.error(f"Account {acct_hash} order failed with status code {resp.status_code}")
                logging.error(f"Response: {resp.text}")
                continue

            # Extract order_id from the location header
            order_id = resp.headers.get('location', '/').split('/')[-1]

            # Retrieve order details
            details_resp = client.order_details(acct_hash, order_id)
            details = details_resp.json() if details_resp.status_code == 200 else {
                "error": "Unable to fetch order details."}

            results.append({
                'acct_hash': acct_hash,
                'resp': resp,
                'order_id': order_id,
                'details': details
            })

            logging.info(f"Order placed for {acct_hash}. Order ID: {order_id}")
        except Exception as e:
            logging.error(f"Error placing order for account {acct_hash}: {e}", exc_info=True)
            continue

    return results


def load_client_data():
    """
    Connect to Schwab, fetch linked accounts, and return
    up to 4 account_hash values in a list.
    """
    client = Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # Refresh tokens automatically

    linked_accounts = client.account_linked().json()
    logging.info(f"Linked Accounts: {linked_accounts}")

    account_hashes = [
        acct['hashValue'] for i, acct in enumerate(linked_accounts) if i < 4 and 'hashValue' in acct
    ]

    if not account_hashes:
        logging.error("No linked accounts found! Exiting.")
        exit()

    logging.info(f"Using these account hashes: {account_hashes}")
    return client, account_hashes


def fetch_and_print_quotes(client, sym_list):
    """
    Fetch quotes for the symbols in sym_list, compute putSpreadPrice and callSpreadPrice,
    and log them.
    """
    quotes = client.quotes(sym_list).json()
    mark_dict = {}

    for symbol in sym_list:
        try:
            mark_dict[symbol] = quotes[symbol]['quote']['mark']
        except KeyError:
            logging.error(f"Missing quote data for {symbol}.")
            mark_dict[symbol] = 0.0

    put_spread_price = abs(myStuff.round_to_nearest_nickel(mark_dict.get(sym_list[0]) - mark_dict.get(sym_list[1])))
    call_spread_price = abs(myStuff.round_to_nearest_nickel(mark_dict.get(sym_list[2]) - mark_dict.get(sym_list[3])))

    logging.info(f"Put Spread: {put_spread_price}")
    logging.info(f"Call Spread: {call_spread_price}")
    return put_spread_price, call_spread_price


def main():
    logging.info("***** Script start *****")
    load_dotenv()

    # 1) Initialize client & accounts
    client, account_hashes = load_client_data()

    # 2) Read data from file
    go_list, strike_list, sym_list, price_list, days = myStuff.read_unpp_file()
    logging.info(
        f"Read from unpp file:\n  go_list={go_list}\n  strike_list={strike_list}\n  sym_list={sym_list}\n"
        f"  price_list={price_list}\n  days={days}"
    )

    if len(sym_list) < 4:
        logging.error("sym_list must have at least 4 symbols for the spreads. Exiting.")
        return

    # 3) Fetch quote prices
    put_spread_price, call_spread_price = fetch_and_print_quotes(client, sym_list)

    # 4) Decide order type (condor or combo) based on go_list signs
    if sign(go_list[0]) == sign(go_list[1]):
        # Condor order
        order_type = 'condor'
        if go_list[0] < 0:
            # Short condor
            debit_credit = "NET_CREDIT"
            spread_price = round(put_spread_price + call_spread_price - BUMP, 2)
            qty = SHORT_CONDOR_M_QTY if days > 2 else SHORT_CONDOR_QTY
        else:
            # Long condor
            debit_credit = "NET_DEBIT"
            spread_price = round(put_spread_price + call_spread_price + BUMP, 2)
            qty = LONG_CONDOR_QTY

        order_params = {
            'debitCredit': debit_credit,
            'symList': sym_list,
            'qty': qty,
            'spreadPrice': spread_price
        }
    else:
        # Combo order
        order_type = 'combo'
        if go_list[0] < 0:
            # Long combo
            spread_price = myStuff.round_to_nearest_nickel(call_spread_price - put_spread_price)
            if spread_price <= -1.0:
                logging.warning("Long Combo not a credit. No trade.")
                return
            debit_credit = get_debit_credit_for_combo(spread_price)
            order_params = {
                'debitCredit': debit_credit,
                'goValue': go_list[0],
                'symList': sym_list,
                'qty': LONG_COMBO_QTY,
                'spreadPrice': spread_price
            }
        else:
            # Short combo
            spread_price = myStuff.round_to_nearest_nickel(put_spread_price - call_spread_price)
            if spread_price <= -1.0:
                logging.warning("Short Combo not a credit. No trade.")
                return
            debit_credit = get_debit_credit_for_combo(spread_price)
            order_params = {
                'debitCredit': debit_credit,
                'goValue': go_list[0],
                'symList': sym_list,
                'qty': SHORT_COMBO_QTY,
                'spreadPrice': spread_price
            }

    # 5) Place order for all accounts
    results = place_order_for_all_accounts(client, account_hashes, order_type, order_params)
    logging.info(f"Order placement results: {results}")

    # 6) Wait 30 seconds, then update bump, recalc spreadPrice, modify & replace the order
    logging.info("Waiting 30 seconds before order replacement...")
    time.sleep(30)

    updated_bump = 0.05
    for res in results:
        acct_hash = res['acct_hash']
        order_id = res['order_id']

        # Recalculate new spreadPrice based on order type and updated bump
        if order_type == 'condor':
            if go_list[0] < 0:
                new_spread_price = round(put_spread_price + call_spread_price - updated_bump, 2)
            else:
                new_spread_price = round(put_spread_price + call_spread_price + updated_bump, 2)
            new_order = myStuff.createCondorOrder(order_params['debitCredit'], sym_list, order_params['qty'],
                                                  new_spread_price)
        elif order_type == 'combo':
            if go_list[0] < 0:
                new_spread_price = myStuff.round_to_nearest_nickel(
                    (call_spread_price - put_spread_price) + updated_bump)
            else:
                new_spread_price = myStuff.round_to_nearest_nickel(
                    (put_spread_price - call_spread_price) + updated_bump)
            new_dc = get_debit_credit_for_combo(new_spread_price)
            new_order = myStuff.createComboOrder(new_dc, go_list[0], sym_list, order_params['qty'], new_spread_price)

        try:
            replace_resp = client.order_replace(acct_hash, order_id, new_order)
            if replace_resp.status_code >= 400:
                logging.error(
                    f"Order replacement for account {acct_hash} failed with status code {replace_resp.status_code}")
            else:
                logging.info(f"Order replaced for account {acct_hash} with new spread price: {new_spread_price}")
        except Exception as e:
            logging.error(f"Error replacing order for account {acct_hash}: {e}", exc_info=True)
            continue

    logging.info("***** Script end *****")

# 7) Wait 30 more seconds, then update bump, recalc spreadPrice, modify & replace the order
    logging.info("Waiting 30 seconds before order replacement...")
    time.sleep(30)

    updated_bump = 0.10
    for res in results:
        acct_hash = res['acct_hash']
        order_id = res['order_id']

        # Recalculate new spreadPrice based on order type and updated bump
        if order_type == 'condor':
            if go_list[0] < 0:
                new_spread_price = round(put_spread_price + call_spread_price - updated_bump, 2)
            else:
                new_spread_price = round(put_spread_price + call_spread_price + updated_bump, 2)
            new_order = myStuff.createCondorOrder(order_params['debitCredit'], sym_list, order_params['qty'],
                                                  new_spread_price)
        elif order_type == 'combo':
            if go_list[0] < 0:
                new_spread_price = myStuff.round_to_nearest_nickel(
                    (call_spread_price - put_spread_price) + updated_bump)
            else:
                new_spread_price = myStuff.round_to_nearest_nickel(
                    (put_spread_price - call_spread_price) + updated_bump)
            new_dc = get_debit_credit_for_combo(new_spread_price)
            new_order = myStuff.createComboOrder(new_dc, go_list[0], sym_list, order_params['qty'], new_spread_price)

        try:
            replace_resp = client.order_replace(acct_hash, order_id, new_order)
            if replace_resp.status_code >= 400:
                logging.error(
                    f"Order replacement for account {acct_hash} failed with status code {replace_resp.status_code}")
            else:
                logging.info(f"Order replaced for account {acct_hash} with new spread price: {new_spread_price}")
        except Exception as e:
            logging.error(f"Error replacing order for account {acct_hash}: {e}", exc_info=True)
            continue

    logging.info("***** Script end *****")

if __name__ == '__main__':
    main()