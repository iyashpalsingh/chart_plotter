#plotting.py

import matplotlib.pyplot as plt
import pandas as pd


def plot_data(df, x, ys):

    fig, ax = plt.subplots(figsize=(12,6))

    for y in ys:
        ax.plot(df[x], df[y], label=y, linewidth=1)

    ax.set_xlabel(x)
    ax.set_ylabel("Value")
    ax.set_title("Battery Data")
    ax.grid(True, alpha=0.3)
    ax.legend()

    if pd.api.types.is_datetime64_any_dtype(df[x]):
        fig.autofmt_xdate()

    plt.tight_layout()
    plt.show()