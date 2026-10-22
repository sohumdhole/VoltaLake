import os
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "docs", "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

options = EdgeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1650,1150")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Edge(options=options)

def wait_for_streamlit_loaded(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stAppViewContainer']"))
    )
    time.sleep(3)

try:
    # 1. Executive KPIs (Global View)
    print("Capturing 01_executive_kpis.png...")
    driver.get("http://localhost:8501/?page=Executive+KPIs")
    wait_for_streamlit_loaded(driver)
    time.sleep(2)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "01_executive_kpis.png"))
    print("Saved 01_executive_kpis.png")

    # 2. Market Benchmarks
    print("Capturing 02_market_benchmarks.png...")
    driver.get("http://localhost:8501/?page=Market+Benchmarks")
    wait_for_streamlit_loaded(driver)
    time.sleep(2)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "02_market_benchmarks.png"))
    print("Saved 02_market_benchmarks.png")

    # 3. Opportunity Map
    print("Capturing 03_opportunity_map.png...")
    driver.get("http://localhost:8501/?page=Opportunity+Map")
    wait_for_streamlit_loaded(driver)
    time.sleep(3)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "03_opportunity_map.png"))
    print("Saved 03_opportunity_map.png")

    # 4. Customer Personas
    print("Capturing 04_customer_personas.png...")
    driver.get("http://localhost:8501/?page=Customer+Personas")
    wait_for_streamlit_loaded(driver)
    time.sleep(2)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "04_customer_personas.png"))
    print("Saved 04_customer_personas.png")

    # 5. Campaign Simulator
    print("Capturing 05_campaign_simulator.png...")
    driver.get("http://localhost:8501/?page=Campaign+ROI+Simulator")
    wait_for_streamlit_loaded(driver)
    time.sleep(2)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "05_campaign_simulator.png"))
    print("Saved 05_campaign_simulator.png")

    # 6. Data Health & Governance
    print("Capturing 06_data_health_governance.png...")
    driver.get("http://localhost:8501/?page=Data+Health+%26+Governance")
    wait_for_streamlit_loaded(driver)
    time.sleep(2)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "06_data_health_governance.png"))
    print("Saved 06_data_health_governance.png")

finally:
    driver.quit()

print("All 6 screenshots successfully captured and saved to docs/screenshots!")
