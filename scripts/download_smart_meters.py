"""
Download UK Power Networks Low Carbon London Smart Meter Partitions
Sourced from London Datastore / Hugging Face mirror:
https://huggingface.co/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady
"""
import os
import urllib.request

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

PARTS = [
    (
        "lcl_smart_meters_part0.csv",
        "https://huggingface.co/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady/resolve/main/Partitioned%20LCL%20Data/Small%20LCL%20Data/LCL-June2015v2_0.csv"
    ),
    (
        "lcl_smart_meters_part140.csv",
        "https://huggingface.co/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady/resolve/main/Partitioned%20LCL%20Data/Small%20LCL%20Data/LCL-June2015v2_140.csv"
    )
]

def download_smart_meters():
    for filename, url in PARTS:
        dest = os.path.join(RAW_DIR, filename)
        if os.path.exists(dest):
            print(f"{filename} already exists at {dest} ({os.path.getsize(dest):,} bytes).")
            continue
        print(f"Downloading {filename} from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp, open(dest, 'wb') as out:
            while chunk := resp.read(1024 * 1024):
                out.write(chunk)
        print(f"Saved {dest} ({os.path.getsize(dest):,} bytes).")

if __name__ == "__main__":
    download_smart_meters()
