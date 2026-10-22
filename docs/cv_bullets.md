# VoltaLake: Verified CV Bullet Points
### Role Alignment: Customer Data Specialist / Analytics Engineer (SSE Energy Customer Solutions, Dublin)
*(Audited & Verified Implementation — Zero-Fabrication Standard)*

These 3 resume bullet points are engineered specifically for SSE Energy Customer Solutions and Irish enterprise BI/Data Engineering roles. Every technology, metric, volume, and finding reflects production-quality pipelines and statistical models built and executed locally in Python/DuckDB, with companion Databricks Lakehouse assets authored and prepared for deployment.

---

```markdown
• Built a medallion data pipeline (Python/DuckDB) unifying 3.5M+ real energy records from SEAI, CSO, DESNZ, CRU and UK Power Networks, with 6 automated data-quality checks, quarantine routing and GDPR pseudonymisation; Databricks/Lakeflow version prepared for deployment.

• Created a retrofit propensity index for Ireland's 26 counties using BER, Census 2022, CSO demand and EV data, and ran a Difference-in-Differences test on 61 smart-meter households to evaluate Time-of-Use tariff response.

• Delivered a 6-page Streamlit/Plotly dashboard benchmarking CRU vs DESNZ switching (Ireland 16.6% → 11.7%, 2022–23) and a campaign ROI/CPA simulator for non-technical stakeholders.
```

---

### Interview Defense Cheat Sheet (Fast Recall)

| CV Dimension | Key Numbers to State | Architectural Rationale to Defend |
| :--- | :--- | :--- |
| **Data Volumes & Stack** | 3.5M+ rows, 1.45M BER certs, 2.05M smart-meter readings; Python, DuckDB, Streamlit; Databricks Lakehouse assets prepared for deployment. | Bronze is immutable raw with ingestion metadata (`_source_file`, `_ingested_at`, `_jurisdiction`); Silver cleans, enforces constraints, routes bad records to quarantine; Gold is star-schema with conformed analytical facts. |
| **Data Integrity & GDPR** | 6 evaluated data expectations, 100% domain pass rate (99.93% deduplication); Salted HMAC SHA-256 for household IDs. | GDPR compliance: pseudo-anonymisation at Silver prevents rainbow table re-identification attacks. Unity Catalog dynamic column masks and jurisdiction row filters restrict regional visibility upon cloud deployment. |
| **Statistical Rigour (DiD)** | DiD Effect: $+0.0169$ kWh/half-hour, $t = 1.4170, p = 0.1623$, Cohen's $d = +0.3676$, 95% CI $[-0.0070, +0.0407]$; $k=3$ selected (Silhouette 0.1773, DB 1.5744, exploratory segments). | Found no statistically significant peak reduction in this 61-household sample. Formulated the hypothesis that voluntary ToU tariffs require automated hardware (chargers/batteries/heat pumps) to shift peak load. |
| **Commercial Impact** | Ireland switching: like-for-like 16.57% (2022, 418,597 switches) to 11.67% (2023, 294,669 switches), alongside 19.51% (2022 report method); 21.0% in-contract renegotiations (all electricity customers); €100k campaign $\to$ 18,181 contacts, €531k LTV, €157.23 CPA, 431.4% ROI, 0.658% break-even. | Retention is critical in Ireland's concentrated market (Electric Ireland at 52.36% sites vs SSE Airtricity at 11.35%, 253,122 sites per CRU 2023 Report p.55). Capture customers at the 21% renegotiation window. |
