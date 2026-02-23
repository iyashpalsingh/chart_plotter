#data_processing.py

import pandas as pd
from config import HALL_THRESHOLD


def merge_date_time(df):
    if "Date" in df.columns and "Time" in df.columns:

        date_str = df["Date"].astype(str)
        time_str = df["Time"].astype(str)

        df["Timestamp"] = pd.to_datetime(
            date_str + " " + time_str,
            format="%d:%m:%Y %H:%M:%S:%f",
            errors="coerce"
        )

        df.drop(columns=["Date", "Time"], inplace=True)

    if "Timestamp" in df.columns:
        df = df.sort_values("Timestamp")

    elif "Time(Sec)" in df.columns:
        df = df.sort_values("Time(Sec)")

    df = df.reset_index(drop=True)

    return df


def detect_modes(df):
    df['mode'] = 'Idle'
    df.loc[df['Current'] > HALL_THRESHOLD, 'mode'] = 'Charging'
    df.loc[df['Current'] < -HALL_THRESHOLD, 'mode'] = 'Discharging'
    return df


def assign_segments(df):

    df['segment'] = ""

    current_mode = None
    seg_counts = {'Idle':0, 'Charging':0, 'Discharging':0}

    for i, row in df.iterrows():

        mode = row['mode']

        if mode != current_mode:
            seg_counts[mode] += 1
            current_mode = mode

        df.at[i,'segment'] = f"{mode}_{seg_counts[mode]}"

    return df