import schwabdev
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import pandas as pd
import re


def parse_expiration(symbol):
    """
    Parses the expiration date from an option symbol.
    Assumes the symbol contains a 6-digit date (YYMMDD) immediately before a 'C' or 'P'.
    Returns the date in MM/DD/YY format.
    For example, "SPXW  250311C05690000" -> "03/11/25".
    """
    if not isinstance(symbol, str):
        return None
    symbol = symbol.strip()
    match = re.search(r'(\d{6})(?=[CP])', symbol)
    if match:
        exp_str = match.group(1)
        return f"{exp_str[2:4]}/{exp_str[4:6]}/{exp_str[0:2]}"
    return None


def format_currency(x):
    """Formats a numeric value as currency (e.g., $1,234.56)."""
    try:
        return "${:,.2f}".format(float(x))
    except Exception:
        return x


def main():
    # Configure Pandas to display all columns.
    pd.set_option('display.max_columns', None)

    # Load environment variables from your .env file.
    load_dotenv("/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/.env")

    # Initialize the Schwab API client.
    client = schwabdev.Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()

    # Retrieve linked accounts.
    linked_accounts = client.account_linked().json()

    # Define the date range: last 30 days.
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    # Use the specified transaction types.
    transaction_types = (
        "TRADE,RECEIVE_AND_DELIVER, CASH_RECEIPT,CASH_DISBURSEMENT,JOURNAL,MEMORANDUM"
    )

    # Aggregate transactions from all linked accounts.
    all_transactions = []
    for account in linked_accounts:
        account_hash = account.get('hashValue')
        if not account_hash:
            continue
        response = client.transactions(account_hash, start_date, end_date, transaction_types)
        if response.ok:
            transactions = response.json()
            if isinstance(transactions, dict) and 'transactions' in transactions:
                transactions = transactions['transactions']
            for txn in transactions:
                txn['account_hash'] = account_hash
            all_transactions.extend(transactions)

    if not all_transactions:
        print("No transactions found.")
        return

    # Flatten the nested 'transferItems' to extract trade details.
    df_flat = pd.json_normalize(
        all_transactions,
        record_path=['transferItems'],
        meta=['tradeDate', 'accountNumber', 'netAmount'],
        errors='ignore'
    )

    # Define the desired columns.
    desired_columns = [
        'tradeDate', 'instrument.symbol', 'instrument.expirationDate',
        'amount', 'cost', 'price', 'positionEffect', 'accountNumber', 'netAmount'
    ]

    # Subset the DataFrame to the desired columns.
    available_columns = [col for col in desired_columns if col in df_flat.columns]
    df_subset = df_flat[available_columns].copy()

    # Convert tradeDate to datetime.
    if 'tradeDate' in df_subset.columns:
        df_subset['tradeDate'] = pd.to_datetime(df_subset['tradeDate'], errors='coerce')

    # Split the DataFrame into trades and fees.
    if 'instrument.symbol' in df_subset.columns:
        df_fees = df_subset[df_subset['instrument.symbol'].str.contains("CURRENCY_USD", na=False)].copy()
        df_trades = df_subset[~df_subset['instrument.symbol'].str.contains("CURRENCY_USD", na=False)].copy()
    else:
        df_trades = df_subset.copy()
        df_fees = pd.DataFrame()

    # Parse expiration date from instrument.symbol and store in a new column.
    if 'instrument.symbol' in df_trades.columns:
        df_trades.loc[:, 'parsedExpiration'] = df_trades['instrument.symbol'].apply(parse_expiration)

    # Order the trades by tradeDate.
    if 'tradeDate' in df_trades.columns:
        df_trades.sort_values(by='tradeDate', inplace=True)

    # Write the trades DataFrame to CSV.
    trades_csv_path = "/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/myTrades.csv"
    df_trades.to_csv(trades_csv_path, index=False, header=True)
    print(f"Trades DataFrame written to {trades_csv_path}")

    # Write the fees DataFrame to CSV.
    fees_csv_path = "/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/myFees.csv"
    if not df_fees.empty:
        df_fees.sort_values(by='tradeDate', inplace=True)
        df_fees.to_csv(fees_csv_path, index=False, header=True)
        print(f"Fees DataFrame written to {fees_csv_path}")
    else:
        print("No fees (CURRENCY_USD entries) found.")

    # --- Profit & Loss by Date (from trades only) ---
    if 'tradeDate' in df_trades.columns and 'netAmount' in df_trades.columns:
        df_trades['trade_date_only'] = df_trades['tradeDate'].dt.date
        pl_df = df_trades.groupby('trade_date_only')['netAmount'].sum().reset_index()
        pl_df.rename(columns={'trade_date_only': 'Trade Date', 'netAmount': 'Total Profit/Loss'}, inplace=True)
        pl_df.sort_values(by='Trade Date', inplace=True)
        # Format the Total Profit/Loss column as currency.
        pl_df['Total Profit/Loss'] = pl_df['Total Profit/Loss'].apply(format_currency)

        pl_csv_path = "/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/myTradePL.csv"
        pl_df.to_csv(pl_csv_path, index=False, header=True)
        print(f"Profit and Loss by Date DataFrame written to {pl_csv_path}")
    else:
        print("Missing required columns for profit and loss calculation.")

    # --- Group Net Amount by Account and Parsed Expiration Date ---
    if ('accountNumber' in df_trades.columns and
            'parsedExpiration' in df_trades.columns and
            'netAmount' in df_trades.columns):

        df_trades['netAmount'] = pd.to_numeric(df_trades['netAmount'], errors='coerce')
        exp_group_df = df_trades.groupby(['accountNumber', 'parsedExpiration'])['netAmount'].sum().reset_index()
        exp_group_df.rename(columns={'netAmount': 'Total P&L'}, inplace=True)
        exp_group_df.sort_values(by=['accountNumber', 'parsedExpiration'], inplace=True)
        # Format the Total P&L column as currency.
        exp_group_df['Total P&L'] = exp_group_df['Total P&L'].apply(format_currency)

        exp_csv_path = "/Users/jim/PycharmProjects/Schwab-API-Python/myTrading/myTradeByExpiration.csv"
        exp_group_df.to_csv(exp_csv_path, index=False, header=True)
        print(f"Trade P&L grouped by account and expiration date written to {exp_csv_path}")
    else:
        print("Missing required columns for grouping by expiration date from symbol.")


if __name__ == '__main__':
    main()