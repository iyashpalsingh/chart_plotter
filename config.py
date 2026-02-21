#config.py

TEMP_CSV = "parsed_temp.csv"
MAX_PLOT_ROWS = 200_000
HALL_THRESHOLD = 0.05

GROUPS = {
    "Time": ["Timestamp", "Time(Sec)"],
    "Voltage (Cells 1-24)": [f"Cell{i}" for i in range(1, 25)],
    "Current & Capacity": ["Current", "Capacity", "SOC"],
    "Temperature (T1-T14)": [f"T{i}" for i in range(1, 15)],
    "Imbalance (IB1-IB28)": [f"IB{i}" for i in range(1, 29)],
    "Ignition & Status": ["IG_Status", "VehicleState", "ActiveFaults"],
    "Software Version": ["SwVMajor", "SwVMinor", "SwVSub"],
    "Identification": ["SerialNumber"]
}