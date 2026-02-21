#main.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pandas as pd

from config import GROUPS
from database import get_connection
from parser_txt import stream_txt_to_csv
from data_processing import merge_date_time, detect_modes, assign_segments
from ui_panels import FilterableCheckboxPanel
from plotting import plot_data

con = get_connection()

data_ready = False


def load_file():

    path = filedialog.askopenfilename()

    if not path:
        return

    def worker():

        global data_ready

        try:

            if path.endswith(".csv"):
                con.execute(f"CREATE OR REPLACE TABLE data AS SELECT * FROM read_csv_auto('{path}')")

            df = con.execute("SELECT * FROM data").df()

            df = merge_date_time(df)

            if "Current" in df.columns:
                df = detect_modes(df)
                df = assign_segments(df)

            con.register("df", df)
            con.execute("CREATE OR REPLACE TABLE data AS SELECT * FROM df")

            data_ready = True

        except Exception as e:
            messagebox.showerror("Error", str(e))

    threading.Thread(target=worker).start()


def plot():

    if not data_ready:
        messagebox.showwarning("Warning", "Load data first")
        return

    x = x_panel.get_selected()
    y = y_panel.get_selected()

    if len(x) != 1:
        messagebox.showerror("Error", "Select one X axis")
        return

    df = con.execute("SELECT * FROM data").df()

    plot_data(df, x[0], y)


root = tk.Tk()
root.geometry("1400x800")
root.title("Battery Plotter")

top = ttk.Frame(root)
top.pack(fill="x")

ttk.Button(top, text="Load File", command=load_file).pack(side="left")

axis_frame = ttk.Frame(root)
axis_frame.pack(fill="both", expand=True)

x_panel = FilterableCheckboxPanel(axis_frame, GROUPS, True)
x_panel.pack(side="left")

y_panel = FilterableCheckboxPanel(axis_frame, GROUPS, False)
y_panel.pack(side="left")

ttk.Button(root, text="Plot", command=plot).pack()

root.mainloop()