import duckdb

con = duckdb.connect()
df = con.execute("SELECT * FROM 'data/gold/kpi_campaign_roi_sensitivity.parquet'").fetchdf()
print(df.to_string())
