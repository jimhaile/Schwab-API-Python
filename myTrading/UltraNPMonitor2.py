import sys
import os
import pickle
import numpy as np
import pandas as pd
import importlib
import time

# Define model file path
MODEL_FILE = "/Users/jim/PycharmProjects/NP/qrf_model.pkl"


# Function to load the trained model without retraining
def load_trained_model():
    """Loads the trained model from file."""
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(f"Trained model file not found: {MODEL_FILE}")
    with open(MODEL_FILE, "rb") as f:
        return pickle.load(f)


# Load the model once at startup
model = load_trained_model()


def getLatestData():
    """Reads the last row from /Users/jim/npmonitor.txt and extracts the time, strike prices, Forward, and VIXOne."""
    file_path = "/Users/jim/npmonitor.txt"

    if not os.path.exists(file_path):
        print(f"{time_token} {strike1} {strike2} {forward:.2f} {vix_one:.2f} File not found: {file_path}")
        return None

    with open(file_path, "r") as file:
        lines = file.readlines()
        if lines:
            last_line = lines[-1].strip()
            words = last_line.split()
            if len(words) >= 11:  # Ensure the line has enough words
                time_token = words[0]
                strike1, strike2 = float(words[3]), float(words[4])
                vix_one = float(words[8])
                forward = float(words[10])
                return time_token, strike1, strike2, forward, vix_one

    return None


def predict_spx_levels(vix_one, forward):
    """Uses the trained model to predict SPX 20th and 80th percentiles based on VIXOne and Forward."""
    new_X = pd.DataFrame({"VIX": [vix_one / 100]})  # Normalize VIXOne for prediction

    # Predict 20th and 80th percentile SPX levels
    predictions_downside = np.atleast_2d(model.predict(new_X, quantiles=[0.196]))
    predictions_upside = np.atleast_2d(model.predict(new_X, quantiles=[0.837]))

    # Ensure predictions are 2D and transpose if necessary
    if predictions_downside.shape[0] == 1:
        predictions_downside = predictions_downside.T
    if predictions_upside.shape[0] == 1:
        predictions_upside = predictions_upside.T

    spx_20th = forward * np.exp(predictions_downside[0, 0])  # 20th percentile
    spx_80th = forward * np.exp(predictions_upside[0, 0])  # 80th percentile

    return spx_20th, spx_80th


def determine_trade_label(putBS, callBS):
    """Determines trade label based on putBS and callBS values."""
    if putBS == 1 and callBS == 1:
        return "LongCondor"
    elif putBS == -1 and callBS == -1:
        return "ShortCondor"
    elif putBS == -1 and callBS == 1:
        return "LongCombo"
    elif putBS == 1 and callBS == -1:
        return "ShortCombo"
    return "Unknown"


if __name__ == "__main__":
    while True:
        latest_data = getLatestData()
        if latest_data:
            time_token, strike1, strike2, forward, vix_one = latest_data
            spx_20th, spx_80th = predict_spx_levels(vix_one, forward)

            # Compute putBS and callBS
            putBS = -1 if spx_20th > strike1 else 1
            callBS = -1 if spx_80th < strike2 else 1

            # Determine trade label
            trade_label = determine_trade_label(putBS, callBS)

            print(f"{time_token}  {trade_label} {strike1} {strike2} {forward:.2f} {vix_one:.2f} "
                  f"|  {spx_20th:.2f} {spx_80th:.2f}  {putBS}  {callBS} ")

        time.sleep(15)  # Check for updates every 15 seconds
