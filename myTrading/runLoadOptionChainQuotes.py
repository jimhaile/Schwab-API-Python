import datetime
import time
import subprocess

def wait_until(hour, minute):
    """
    Blocks execution until local time matches the specified hour and minute.
    """
    while True:
        now = datetime.datetime.now()
        print(now, now.hour, now.minute)

        # If we've reached or passed the desired time this day, break.
        # (You can decide whether to skip times that have already passed.)
        if now.hour == hour and now.minute == minute:
            break
        # Sleep some seconds before checking again.
        time.sleep(15)

def main():
    # List of (hour, minute) tuples in 24-hour format
    execution_times = [
        (12, 45), # 12:45
        (13, 15), # 13:15
    ]

    for hour, minute in execution_times:
        print(f"Waiting until {hour:02d}:{minute:02d}...")
        wait_until(hour, minute)
        print(f"Time reached ({hour:02d}:{minute:02d}). Now running runLoadOptionChainQuotes.py.")
        # Execute another Python program
        subprocess.run(["/Users/jim/PycharmProjects/Schwab-API-Python/.venv/bin/python",
                        "/Users/jim/PycharmProjects/getOptionsChain/LoadOptionChainQuotes.py"])

    print("All scheduled tasks have been executed. Exiting.")
    exit()

if __name__ == "__main__":
    main()