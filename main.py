# main.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pandas as pd
import os

from config import GROUPS
from database import get_connection
from parser_txt import stream_txt_to_csv
from data_processing import merge_date_time, detect_modes, assign_segments
from ui_panels import FilterableCheckboxPanel
from plotting import plot_data


con = get_connection()

data_ready = False
current_file = None


# -------------------------------
# FILE LOADING
# -------------------------------
def load_file():

    global data_ready, current_file

    file_path = filedialog.askopenfilename(
        filetypes=[
            ("Data files", "*.csv *.xlsx *.xls *.txt"),
            ("All files", "*.*"),
        ]
    )

    if not file_path:
        return

    current_file = file_path
    data_ready = False

    status_label.config(text="Loading file...", foreground="blue")
    progress["value"] = 0

    plot_button.config(state="disabled")

    thread = threading.Thread(target=worker_load_file, args=(file_path,), daemon=True)
    thread.start()


# -------------------------------
# WORKER THREAD
# -------------------------------
def worker_load_file(file_path):

    try:

        root.after(0, lambda: progress.config(value=5))

        file_path = file_path.replace("\\", "/")

        # LOAD FILE
        if file_path.endswith(".csv"):

            con.execute(
                f"CREATE OR REPLACE TABLE data AS SELECT * FROM read_csv_auto('{file_path}')"
            )

        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):

            df = pd.read_excel(file_path)
            con.register("excel_df", df)
            con.execute("CREATE OR REPLACE TABLE data AS SELECT * FROM excel_df")

        elif file_path.endswith(".txt"):

            stream_txt_to_csv(file_path)

            from config import TEMP_CSV

            con.execute(
                f"CREATE OR REPLACE TABLE data AS SELECT * FROM read_csv_auto('{TEMP_CSV}')"
            )

        root.after(0, lambda: progress.config(value=30))

        df = con.execute("SELECT * FROM data").df()

        root.after(0, lambda: progress.config(value=55))

        for col in df.columns:
            if col not in ["Timestamp", "Date", "Time", "SerialNumber"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        root.after(0, lambda: progress.config(value=70))

        df = merge_date_time(df)

        if "Current" in df.columns:
            df = detect_modes(df)
            df = assign_segments(df)

        root.after(0, lambda: progress.config(value=90))

        con.register("df", df)
        con.execute("CREATE OR REPLACE TABLE data AS SELECT * FROM df")

        root.after(0, finish_loading)

    except Exception as e:
        root.after(0, lambda: show_error(e))


# -------------------------------
# FINISH LOADING
# -------------------------------
def finish_loading():

    global data_ready

    data_ready = True

    progress["value"] = 100

    plot_button.config(state="normal")

    status_label.config(
        text=f"Loaded: {os.path.basename(current_file)} ✔",
        foreground="green"
    )


# -------------------------------
# ERROR HANDLING
# -------------------------------
def show_error(e):

    status_label.config(
        text="Failed to load file",
        foreground="red",
    )

    messagebox.showerror("Error", str(e))


# -------------------------------
# PLOT
# -------------------------------
def plot():

    if not data_ready:
        messagebox.showwarning("Warning", "Load data first")
        return

    x = x_panel.get_selected()
    y = y_panel.get_selected()

    if len(x) != 1:
        messagebox.showerror("Error", "Select exactly one X axis")
        return

    df = con.execute("SELECT * FROM data").df()

    plot_data(df, x[0], y)


# -------------------------------
# UI
# -------------------------------
root = tk.Tk()
root.geometry("1400x800")
root.title("Battery Data Plotter")

top = ttk.Frame(root)
top.pack(fill="x", pady=5)

load_button = ttk.Button(top, text="Load File", command=load_file)
load_button.pack(side="left", padx=5)

plot_button = ttk.Button(top, text="Plot", command=plot, state="disabled")
plot_button.pack(side="left", padx=5)


# Progress bar
progress = ttk.Progressbar(
    root,
    orient="horizontal",
    length=400,
    mode="determinate",
    maximum=100
)

progress.pack(pady=5)


# Status text
status_label = ttk.Label(root, text="No file loaded", foreground="gray")
status_label.pack()


# Axis panels
axis_frame = ttk.Frame(root)
axis_frame.pack(fill="both", expand=True, pady=10)

x_panel = FilterableCheckboxPanel(axis_frame, GROUPS, True)
x_panel.pack(side="left", fill="y", padx=10)

y_panel = FilterableCheckboxPanel(axis_frame, GROUPS, False)
y_panel.pack(side="left", fill="y", padx=10)


root.mainloop()