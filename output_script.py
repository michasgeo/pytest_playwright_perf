import os
import pandas as pd

def parse_csv_files(root_folder):
    records = []

    for dirpath, _, filenames in os.walk(root_folder):
        for file in filenames:
            if file.endswith(".csv"):
                full_path = os.path.join(dirpath, file)
                try:
                    df = pd.read_csv(full_path, header=None, dtype=str)
                except Exception as e:
                    print(f"Failed to read {full_path}: {e}")
                    continue

                for idx, row in df.iterrows():
                    # Skip empty or incomplete rows
                    if len(row) < 3 or pd.isna(row.iloc[0]) or pd.isna(row.iloc[1]):
                        continue

                    start_time = row.iloc[0]
                    user = row.iloc[1]
                    status_raw = str(row.iloc[2]) if len(row) > 2 else ""
                    duration = row.iloc[3] if len(row) > 3 and pd.notna(row.iloc[3]) else ""

                    # Clean status
                    if "Success" in status_raw:
                        status = "Success"
                    elif "Failed" in status_raw or "Error" in status_raw:
                        status = "error"
                    else:
                        status = status_raw.strip()

                    records.append(f"{start_time} - {user} - {status} - {duration}")

    return records

# Example usage
folder_path = r"C:\Repos\pytest_playwright_perf"
consolidated_records = parse_csv_files(folder_path)

# Output result
with open("consolidated_output.txt", "w", encoding="utf-8") as f:
    for record in consolidated_records:
        f.write(record + "\n")
