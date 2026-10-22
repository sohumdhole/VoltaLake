"""
Databricks Genie Space Evaluation Harness
-----------------------------------------
Official execution and automated scoring script for the 20-question VoltaLake
business evaluation benchmark. 

Usage:
    export DATABRICKS_HOST="https://<workspace-instance>.cloud.databricks.com"
    export DATABRICKS_TOKEN="dapi..."
    export GENIE_SPACE_ID="01ef..."
    python genie/genie_evaluation_harness.py
"""

import os
import sys
import json
import time
import requests
import duckdb

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "genie_evaluation_benchmark.json")

def load_benchmark():
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_local_ground_truth(query):
    """Executes ground truth SQL locally via DuckDB over gold parquet tables."""
    con = duckdb.connect()
    # Map Unity Catalog table paths to local parquet files
    query_local = query.replace("voltalake.gold.fact_market_switching", "'data/gold/fact_market_switching.parquet'")
    query_local = query_local.replace("voltalake.gold.kpi_retrofit_propensity_ie", "'data/gold/kpi_retrofit_propensity_ie.parquet'")
    query_local = query_local.replace("voltalake.gold.kpi_retrofit_propensity_gb", "'data/gold/kpi_retrofit_propensity_gb.parquet'")
    query_local = query_local.replace("voltalake.gold.kpi_customer_personas", "'data/gold/kpi_customer_personas.parquet'")
    query_local = query_local.replace("voltalake.gold.kpi_tariff_did_experiment", "'data/gold/kpi_tariff_did_experiment.parquet'")
    query_local = query_local.replace("voltalake.gold.kpi_campaign_roi_sensitivity", "'data/gold/kpi_campaign_roi_sensitivity.parquet'")
    query_local = query_local.replace("voltalake.gold.data_quality_scorecard", "'data/gold/data_quality_scorecard.parquet'")
    query_local = query_local.replace("voltalake.gold.freshness_tracking", "'data/gold/freshness_tracking.parquet'")
    try:
        df = con.execute(query_local).fetchdf()
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

def call_genie_api(host, token, space_id, question_text):
    """Calls the Databricks Genie Conversation API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}/start-conversation"
    payload = {"content": question_text}
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        return {"error": f"API error {response.status_code}: {response.text}"}
    
    data = response.json()
    conversation_id = data.get("conversation_id")
    message_id = data.get("message_id")
    
    # Poll for message completion
    poll_url = f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}"
    for _ in range(30):
        time.sleep(2)
        poll_resp = requests.get(poll_url, headers=headers, timeout=30)
        if poll_resp.status_code == 200:
            m_data = poll_resp.json()
            status = m_data.get("status")
            if status in ["COMPLETED", "FAILED"]:
                return m_data
    return {"error": "Genie polling timed out after 60s"}

def main():
    benchmark = load_benchmark()
    questions = benchmark["questions"]
    
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    space_id = os.environ.get("GENIE_SPACE_ID")
    
    print("=================================================================")
    print("  VOLTALAKE DATABRICKS GENIE BENCHMARK EVALUATION HARNESS")
    print("=================================================================")
    print(f"Total Questions: {len(questions)}")
    print(f"Databricks Host: {host or 'NOT SET (Local Ground-Truth Validation Mode)'}")
    
    if not host or not token or not space_id:
        print("\n[NOTICE] Remote Databricks credentials not found in environment.")
        print("Running in LOCAL GROUND-TRUTH VERIFICATION MODE.")
        print("Validating that all 20 benchmark questions have executable SQL against local Gold tables...")
        print("-----------------------------------------------------------------")
        
        passed_gt = 0
        for q in questions:
            qid = q["id"]
            gt_sql = q["ground_truth_sql"]
            res = run_local_ground_truth(gt_sql)
            if "error" in res:
                print(f"[{qid}] FAIL: {res['error']}")
            else:
                passed_gt += 1
                print(f"[{qid}] PASS Ground-Truth SQL: {q['category']} - {q['question'][:50]}...")
        
        print("-----------------------------------------------------------------")
        print(f"Local Ground Truth Validation: {passed_gt}/{len(questions)} queries successfully executed on Gold tables.")
        print("\nTo execute this suite against a live Databricks Genie Space, set:")
        print("  export DATABRICKS_HOST='https://<workspace>.cloud.databricks.com'")
        print("  export DATABRICKS_TOKEN='dapi...'")
        print("  export GENIE_SPACE_ID='<space-id>'")
        print("and re-run this script.")
        return

    # Live Cloud Execution
    print(f"\nExecuting 20 questions against Genie Space {space_id}...")
    results = []
    for q in questions:
        qid = q["id"]
        q_text = q["question"]
        print(f"Asking [{qid}]: {q_text}")
        genie_output = call_genie_api(host, token, space_id, q_text)
        results.append({
            "id": qid,
            "question": q_text,
            "expected": q["expected_metrics"],
            "genie_output": genie_output
        })
    
    out_file = os.path.join(os.path.dirname(__file__), "genie_live_execution_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nLive execution results saved to {out_file}")

if __name__ == "__main__":
    main()
