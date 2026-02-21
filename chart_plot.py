import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.dates as mdates
plt.rcParams["path.simplify"] = True
plt.rcParams["path.simplify_threshold"] = 1.0
plt.rcParams["agg.path.chunksize"] = 20000

# ================= CONFIG =================
TEMP_CSV = "parsed_temp.csv"
MAX_PLOT_ROWS = 200_000
HALL_THRESHOLD = 0.05  # threshold to detect charging/discharging from Hall_High

# ================= GROUP DEFINITIONS =================
GROUPS = {
            "Time": ["Timestamp", "Time(Sec)"],

            "Voltage (Cells 1-24)": [f"Cell{i}" for i in range(1, 25)],

            "Current & Capacity": [
                "Current",
                "Capacity",
                "SOC"
            ],

            "Temperature (T1-T14)": [f"T{i}" for i in range(1, 15)],

            "Imbalance (IB1-IB28)": [f"IB{i}" for i in range(1, 29)],

            "Ignition & Status": [
                "IG_Status",
                "VehicleState",
                "ActiveFaults"
            ],

            "Software Version": [
                "SwVMajor",
                "SwVMinor",
                "SwVSub"
            ],

            "Identification": [
                "SerialNumber"
            ]
        }

# ================= GLOBALS =================
con = duckdb.connect(database=':memory:')  # In-memory DB to avoid WAL issues
cancel_flag = False
data_ready = False
dynamic_segments = []  # store detected segments

# ================= TXT PARSER =================
def parse_txt_line(line):
    parts = line.strip().split()
    if len(parts) < 3:
        return None
    row = {"Timestamp": parts[0] + " " + parts[1]}
    for p in parts[2:]:
        if "=" in p:
            k, v = p.split("=", 1)
            try:
                row[k] = float(v)
            except:
                row[k] = v
    return row

# ================= PROGRESS =================
def update_progress(read_bytes, total_bytes):
    percent = int((read_bytes / total_bytes) * 100)
    progress["value"] = percent
    status.set(f"{percent}% ({read_bytes/1e6:.1f}/{total_bytes/1e6:.1f} MB)")

# ================= STREAM TXT =================
def stream_txt_to_csv(path):
    global cancel_flag
    total = os.path.getsize(path)
    read = 0
    header_written = False

    with open(path, "rb") as fin, open(TEMP_CSV, "w", encoding="utf-8") as fout:
        for raw in fin:
            if cancel_flag:
                return False
            read += len(raw)
            line = raw.decode("utf-8", "ignore")
            row = parse_txt_line(line)
            if not row:
                continue
            if not header_written:
                fout.write(",".join(row.keys()) + "\n")
                header_written = True
            fout.write(",".join(str(v) for v in row.values()) + "\n")
            root.after(0, update_progress, read, total)
    return True

# ================= FILTERABLE CHECKBOX PANEL =================
class FilterableCheckboxPanel(ttk.Frame):
    def __init__(self, parent, groups, single_select=False):
        super().__init__(parent)
        self.groups = groups
        self.single_select = single_select
        self.vars = {}  # column -> BooleanVar
        self.group_vars = {}  # group -> BooleanVar (Select All)

        for group, items in groups.items():
            ttk.Label(self, text=group, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5,0))
            gvar = tk.BooleanVar()
            self.group_vars[group] = gvar
            chk_all = ttk.Checkbutton(self, text="Select All", variable=gvar,
                                      command=lambda g=group: self.toggle_group(g))
            chk_all.pack(anchor="w", padx=10)
            btn = ttk.Button(self, text="Filter/Search", width=25,
                             command=lambda g=group: self.open_popup(g))
            btn.pack(anchor="w", padx=10, pady=(0,5))

    def toggle_group(self, group):
        state = self.group_vars[group].get()
        for col in self.groups[group]:
            if col not in self.vars:
                self.vars[col] = tk.BooleanVar()
            self.vars[col].set(state)

    def open_popup(self, group):
        popup = tk.Toplevel(self)
        popup.title(group)
        popup.geometry("250x300")
        popup.grab_set()

        search_var = tk.StringVar()
        ttk.Entry(popup, textvariable=search_var).pack(fill="x", padx=5, pady=5)

        frame = ttk.Frame(popup)
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for item in self.groups[group]:
            if item not in self.vars:
                self.vars[item] = tk.BooleanVar()
            ttk.Checkbutton(inner, text=item, variable=self.vars[item]).pack(anchor="w")

        def filter_items(*args):
            term = search_var.get().lower()
            for widget in inner.winfo_children():
                text = widget.cget("text").lower()
                widget.pack_forget()
                if term in text:
                    widget.pack(anchor="w")
        search_var.trace_add("write", filter_items)

    def get_selected(self):
        return [k for k, v in self.vars.items() if v.get()]

# ================= DETECT MODES & SEGMENTS =================
def detect_modes(df, threshold=HALL_THRESHOLD):
    df['mode'] = 'Idle'
    df.loc[df['Current'] > threshold, 'mode'] = 'Charging'
    df.loc[df['Current'] < -threshold, 'mode'] = 'Discharging'
    return df

def assign_segments(df):
    df['segment'] = ""
    current_mode = None
    seg_counts = {'Idle':0, 'Charging':0, 'Discharging':0}
    for i, row in df.iterrows():
        mode = row['mode']
        if mode != current_mode:
            seg_counts[mode] +=1
            current_mode = mode
        df.at[i,'segment'] = f"{mode}_{seg_counts[mode]}"
    return df

def merge_date_time(df):
    if "Date" in df.columns and "Time" in df.columns:
        # Convert to string and handle the "D:M:Y" and "H:M:S:f" format
        date_str = df["Date"].astype(str)
        time_str = df["Time"].astype(str)
        
        # Replace colons with dashes for date and keep last colon for milliseconds
        # Your format: 20:2:2026 -> 2026-02-20
        df["Timestamp"] = pd.to_datetime(
            date_str + " " + time_str, 
            format="%d:%m:%Y %H:%M:%S:%f", 
            errors="coerce"
        )
        
        df.drop(columns=["Date", "Time"], inplace=True)
    
    # Critical: Drop rows where timestamp couldn't be parsed
    df = df.dropna(subset=["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)
    return df

# ================= LOAD FILE =================
def load_file():
    global data_ready, dynamic_segments
    data_ready = False

    path = filedialog.askopenfilename(filetypes=[("Supported", "*.txt *.csv *.xlsx *.xls")])
    if not path:
        return

    progress["value"] = 0
    status.set("Loading...")

    def worker():
        global data_ready, dynamic_segments
        try:
            con.execute("DROP TABLE IF EXISTS data")
            if path.endswith(".txt"):
                if not stream_txt_to_csv(path):
                    return
                con.execute(f"CREATE TABLE data AS SELECT * FROM read_csv_auto('{TEMP_CSV}')")
            elif path.endswith(".csv"):
                con.execute(f"CREATE TABLE data AS SELECT * FROM read_csv_auto('{path}')")
            else:
                df = pd.read_excel(path)
                con.register("df", df)
                con.execute("CREATE TABLE data AS SELECT * FROM df")

            # Detect modes & segments
            df = con.execute("SELECT * FROM data").df()
            
            #merge date & time if separate columns exist
            df = merge_date_time(df)
            
            # Convert all possible numeric columns to float
            for col in df.columns:
                if col != "Timestamp" and col != "mode" and col != "segment":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            #detect modes
            if "Current" in df.columns:
                df = detect_modes(df)
                df = assign_segments(df)
                dynamic_segments = df['segment'].unique().tolist()

            # Save back to DuckDB
            con.register("df", df)
            con.execute("DROP TABLE IF EXISTS data")
            con.execute("CREATE TABLE data AS SELECT * FROM df")

            # Add segment filters to right panel
            root.after(0, lambda: add_segment_checkboxes(dynamic_segments))

            data_ready = True
            root.after(0, lambda: status.set("Ready"))
        except Exception as e:
            err = str(e)
            root.after(0, lambda: messagebox.showerror("Error", err))

    threading.Thread(target=worker, daemon=True).start()

# ================= SIGNAL TYPE =================
def is_digital(col):
    try:
        uniq = con.execute(f'SELECT COUNT(DISTINCT "{col}") FROM data').fetchone()[0]
        return uniq <= 5
    except:
        return False

# ================= PLOT =================
def plot_data():
    if not data_ready:
        messagebox.showwarning("Warning", "Data not loaded yet")
        return

    x_sel = x_panel.get_selected()
    y_sel = y_panel.get_selected()

    if len(x_sel) != 1:
        messagebox.showerror("X Axis", "Select exactly ONE X axis")
        return
    if not y_sel:
        messagebox.showerror("Y Axis", "Select at least one Y axis")
        return

    x = x_sel[0]
    ys = y_sel

    # Fetch data directly into Pandas to verify it exists
    query = f'SELECT * FROM data ORDER BY "{x}"'
    df_plot = con.execute(query).df()

    if df_plot.empty:
        messagebox.showerror("Error", "The database table is empty.")
        return

    # Check if we have numeric data
    for y in ys:
        df_plot[y] = pd.to_numeric(df_plot[y], errors='coerce')
    
    df_plot = df_plot.dropna(subset=[x] + ys)

    # Simplified Plotting
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for y in ys:
        # We use standard plot() here to verify the data appears
        ax.plot(df_plot[x], df_plot[y], label=y, linewidth=1)

    # Styling
    ax.set_xlabel(x)
    ax.set_ylabel("Value")
    ax.set_title("Battery Data - Direct Plot")
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right')

    # Formatting X-axis if it's time
    if pd.api.types.is_datetime64_any_dtype(df_plot[x]):
        fig.autofmt_xdate()

    plt.tight_layout()
    plt.show()

# ================= UI =================
root = tk.Tk()
root.title("Large File Plotter – Segment Detection")
root.geometry("1600x800")

style = ttk.Style()
style.configure("Bold.TCheckbutton", font=("Segoe UI",10,"bold"))

top = ttk.Frame(root)
top.pack(fill="x", padx=10, pady=5)
ttk.Button(top, text="Load File", command=load_file).pack(side="left")
progress = ttk.Progressbar(top, length=300)
progress.pack(side="left", padx=10)
status = tk.StringVar(value="Idle")
ttk.Label(top, textvariable=status).pack(side="left")

# ---------------- Main Panels ----------------
axis_frame = ttk.Frame(root)
axis_frame.pack(fill="both", expand=True, padx=10, pady=5)

# Left: X-axis panel
x_panel_frame = ttk.Frame(axis_frame)
x_panel_frame.pack(side="left", fill="y", padx=5)
ttk.Label(x_panel_frame, text="X Axis (single select)").pack(anchor="w")
x_panel = FilterableCheckboxPanel(x_panel_frame, GROUPS, single_select=True)
x_panel.pack(fill="y", expand=True)

# Center: Y-axis panel
y_panel_frame = ttk.Frame(axis_frame)
y_panel_frame.pack(side="left", fill="y", padx=5)
ttk.Label(y_panel_frame, text="Y Axis (multi select)").pack(anchor="w")
y_panel = FilterableCheckboxPanel(y_panel_frame, GROUPS, single_select=False)
y_panel.pack(fill="y", expand=True)

# Right: Segment panel
segment_frame = ttk.Frame(axis_frame)
segment_frame.pack(side="left", fill="y", padx=5)
ttk.Label(segment_frame, text="Segments", font=("Segoe UI", 10, "bold")).pack(anchor="w")
segment_vars = {}
def add_segment_checkboxes(segments):
    for widget in segment_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.destroy()
    for seg in segments:
        if seg not in segment_vars:
            segment_vars[seg] = tk.BooleanVar(value=True)
        ttk.Checkbutton(segment_frame, text=seg, variable=segment_vars[seg]).pack(anchor="w")

ttk.Button(root, text="Plot", command=plot_data).pack(pady=5)

root.mainloop()
