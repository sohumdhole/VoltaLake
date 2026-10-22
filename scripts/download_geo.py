"""
Download GeoJSON boundaries for Ireland Counties and GB Local Authorities
"""
import os
import requests

GEO_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "geo")
os.makedirs(GEO_DIR, exist_ok=True)

def download_file(url, target_name):
    path = os.path.join(GEO_DIR, target_name)
    if not os.path.exists(path):
        print(f"Downloading {target_name} from {url}...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
        print(f"Saved {target_name} ({len(resp.content)} bytes)")
    else:
        print(f"{target_name} already exists.")

if __name__ == "__main__":
    # Ireland Counties GeoJSON
    download_file(
        "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/ireland-counties.geojson",
        "ireland_counties.geojson"
    )
    # GB LAD GeoJSON
    download_file(
        "https://raw.githubusercontent.com/martinjc/UK-GeoJSON/master/json/administrative/gb/lad.json",
        "gb_lad.geojson"
    )
    print("GeoJSON download complete.")
