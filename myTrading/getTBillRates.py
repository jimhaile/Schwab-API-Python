import requests
from datetime import datetime

def get_latest_t_bill_rate(api_key):
    """
    Fetches the latest 3-month T-Bill rate from FRED.

    Args:
        api_key (str): Your FRED API key.

    Returns:
        tuple: A tuple containing the date (str) and the T-Bill rate (float).
               Returns (None, None) if data is unavailable.
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "DTB3",
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",  # Get the latest observation first
        "limit": 1             # Limit to the latest observation
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()

        observations = data.get("observations", [])
        if not observations:
            print("No observations found in the response.")
            return None, None

        latest_observation = observations[0]
        rate_str = latest_observation.get("value")
        date_str = latest_observation.get("date")

        if rate_str == ".":
            print(f"No available data for {date_str}.")
            return date_str, None

        # Convert rate to float
        rate = float(rate_str)
        return date_str, rate

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
        return None, None
    except ValueError:
        print("Error converting the rate to a float.")
        return None, None

def main():
    # Replace 'YOUR_FRED_API_KEY' with your actual FRED API key
    api_key = "5dc3e10402815881bc6fa2f154773d43"

    date, rate = get_latest_t_bill_rate(api_key)
    if date and rate is not None:
        print(f"The latest 3-month T-Bill rate as of {date} is {rate}%.")
    elif date and rate is None:
        print(f"The latest T-Bill rate data for {date} is unavailable.")
    else:
        print("Failed to retrieve the latest T-Bill rate.")

if __name__ == "__main__":
    main()