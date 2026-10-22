# VoltaLake: Data Dictionary & Catalog Reference
### Unity Catalog `voltalake` Schemas: Bronze, Silver, Gold, Semantic

---

## 1. Catalog Architecture Overview

```
voltalake (Catalog)
├── bronze (Schema: Immutable Raw Ingestion from Volumes)
│   ├── raw_seai_ber
│   ├── raw_cso_consumption
│   ├── raw_cso_ev_licensing
│   ├── raw_desnz_consumption
│   ├── raw_switching_benchmarks
│   └── raw_smart_meter_load
├── silver (Schema: Lakeflow Conformed, Quality Controlled & Governed)
│   ├── clean_ber_summary
│   ├── clean_cso_consumption
│   ├── clean_cso_ev_licensing
│   ├── clean_smart_meter_load
│   ├── quarantine_property_efficiency
│   └── dim_region_scd2
├── gold (Schema: Dimensional Star Schema & KPI Marts)
│   ├── dim_date
│   ├── dim_region
│   ├── dim_tariff
│   ├── dim_property_type
│   ├── fact_consumption_region
│   ├── fact_household_load
│   ├── fact_market_switching
│   ├── kpi_retrofit_propensity_ie
│   ├── kpi_retrofit_propensity_gb
│   ├── kpi_customer_personas
│   ├── kpi_tariff_did_experiment
│   ├── kpi_campaign_roi_sensitivity
│   ├── data_quality_scorecard
│   └── freshness_tracking
└── semantic (Schema: Metric Views Single Source of Truth)
    └── voltalake_metrics.yaml
```

---

## 2. Gold Layer Tables

### Table: `voltalake.gold.fact_market_switching`
* **Description:** Harmonized electricity switching statistics from Ireland CRU Annual Reports and Great Britain DESNZ Table 2.7.1.
* **Granularity:** One record per jurisdiction per calendar year.

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `jurisdiction` | STRING | No | Energy jurisdiction code (`IE` or `GB`) |
| `year` | INTEGER | No | Calendar reporting year (2018–2024) |
| `electricity_switches` | BIGINT | No | Total gross electricity supplier transfers |
| `avg_customers` | DOUBLE | No | Average active domestic customer meter base |
| `switching_rate_pct` | DOUBLE | No | Percentage of customer base switching suppliers |
| `renegotiation_rate_pct` | DOUBLE | Yes | Percentage of domestic customers renegotiating terms without switching (CRU, Ireland) |
| `source` | STRING | No | Originating source (`CRU Annual Report` or `DESNZ Table 2.7.1`) |
| `citation` | STRING | No | Exact regulatory filing title, table, and page number |
| `date_key` | INTEGER | No | Foreign key to `dim_date` (YYYYMMDD) |
| `switching_fact_key` | INTEGER | No | Primary surrogate key |
| `_source_system` | STRING | No | Ingestion source audit tag |
| `_ingested_at` | TIMESTAMP | No | UTC timestamp of ingestion |

---

### Table: `voltalake.gold.kpi_retrofit_propensity_ie`
* **Description:** Multi-criteria retrofit propensity index across the 26 conformed administrative counties of Ireland. Zero imputation.
* **Granularity:** One record per Irish county.

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `county` | STRING | No | Conformed Irish county name (Carlow, Cavan, ..., Wicklow) |
| `total_ber_certs` | DOUBLE | No | Total registered Building Energy Rating certificates (Hugging Face mirror of SEAI data) |
| `poor_ber_certs` | DOUBLE | No | Dwellings rated D1, D2, E1, E2, F, or G |
| `good_ber_certs` | DOUBLE | No | Dwellings rated A or B |
| `total_oil_heating` | DOUBLE | No | Homes using kerosene heating oil as primary system |
| `total_gas_heating` | DOUBLE | No | Homes using mains gas |
| `total_heatpump_elec` | DOUBLE | No | Homes using electric heat pumps |
| `avg_floor_area_sqm` | DOUBLE | No | Weighted mean total floor area (sqm) |
| `avg_ber_rating` | DOUBLE | No | Weighted mean energy value (kWh/sqm/yr) |
| `pct_d_or_worse` | DOUBLE | No | Thermal inefficiency percentage |
| `pct_oil_dependent` | DOUBLE | No | Primary oil heating dependence percentage |
| `residential_gwh` | DOUBLE | No | Total 2024 residential electricity consumption (CSO Table MEC03, Sector 10) |
| `residential_kwh_per_dwelling` | DOUBLE | No | Annual residential electricity consumption per dwelling |
| `bev_count` | DOUBLE | No | 2025 new electric car registrations (CSO Table TEM27) |
| `total_new_cars` | DOUBLE | No | 2025 all fuel new private car registrations |
| `bev_share_new_cars_pct` | DOUBLE | No | BEV share of new car registrations (2025) |
| `norm_inefficiency` | DOUBLE | No | Min-max scaled thermal deficiency |
| `norm_oil` | DOUBLE | No | Min-max scaled oil dependency |
| `norm_consumption` | DOUBLE | No | Min-max scaled consumption per dwelling |
| `norm_bev` | DOUBLE | No | Min-max scaled BEV registration share |
| `retrofit_propensity_score` | DOUBLE | No | Multi-criteria weighted propensity index (0–100) |
| `propensity_tier` | STRING | No | Classification tier (`Prime Target`, `High`, `Moderate`, `Low`) |
| `jurisdiction` | STRING | No | Jurisdiction code (`IE`) |
| `_source_system` | STRING | No | Source audit tag |
| `_ingested_at` | TIMESTAMP | No | UTC ingestion timestamp |

---

### Table: `voltalake.gold.kpi_customer_personas`
* **Description:** K-Means customer persona segmentation on 48 normalized half-hourly daily load profiles from London smart meters ($k=3$ selected; exploratory segments).
* **Granularity:** One record per smart-meter household ($n=63$).

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `household_id` | STRING | No | Salted SHA-256 pseudonymised household identifier |
| `tariff_group` | STRING | No | Trial tariff allocation (`Std` or `ToU`) |
| `cluster` | INTEGER | No | Cluster assignment (0, 1, 2) |
| `persona_name` | STRING | No | Distinct persona: `Overnight EV & Storage Charger`, `Daytime Active Occupier`, `Balanced Baseline Consumer` |
| `target_proposition` | STRING | No | Commercial energy proposition mapping |
| `total_recorded_kwh` | DOUBLE | No | Total recorded consumption during trial |
| `avg_hh_kwh` | DOUBLE | No | Mean consumption per half-hour (kWh) |
| `peak_hh_kwh` | DOUBLE | No | Mean consumption during peak window (16:00–20:00) |
| `offpeak_hh_kwh` | DOUBLE | No | Mean consumption outside peak window |
| `peak_to_offpeak_ratio` | DOUBLE | No | Ratio of peak to off-peak demand intensity |
| `silhouette_score` | DOUBLE | No | Cluster cohesion metric ($k=3$: 0.7125) |
| `davies_bouldin_index` | DOUBLE | No | Cluster separation metric ($k=3$: 0.3038) |
| `_source_system` | STRING | No | Source audit tag |
| `_ingested_at` | TIMESTAMP | No | UTC timestamp |

---

### Table: `voltalake.gold.kpi_tariff_did_experiment`
* **Description:** Difference-in-Differences household-level peak consumption evaluation comparing 2012 baseline pre-period to 2013 ToU trial period.
* **Granularity:** One record per household observed across both 2012 and 2013 ($n=61$).

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `household_id` | STRING | No | Masked household identifier |
| `tariff_group` | STRING | No | Trial group: `Std` ($n=29$) or `ToU` ($n=32$) |
| `peak_2012` | DOUBLE | No | Mean peak consumption in 2012 baseline pre-period (kWh/half-hour) |
| `peak_2013` | DOUBLE | No | Mean peak consumption in 2013 ToU trial period (kWh/half-hour) |
| `delta_peak_kwh` | DOUBLE | No | Individual household change: `peak_2013 - peak_2012` |
| `_source_system` | STRING | No | Source audit tag |
| `_ingested_at` | TIMESTAMP | No | UTC timestamp |

---

### Table: `voltalake.gold.kpi_campaign_roi_sensitivity`
* **Description:** Pre-computed marketing campaign sensitivity grid evaluating reach, acquired customers, CPA, customer lifetime value, and ROI across budgets and conversion rates.
* **Granularity:** One record per marketing spend $\times$ conversion rate combination.

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `marketing_spend_eur` | INTEGER | No | Campaign budget (€50k to €500k) |
| `cost_per_contact_eur` | DOUBLE | No | Channel unit cost per contact (€5.50) |
| `contacts_reached` | INTEGER | No | Reach: `marketing_spend_eur / cost_per_contact_eur` |
| `conversion_rate` | DOUBLE | No | Assumed conversion rate (0.015 to 0.060) |
| `customers_acquired` | INTEGER | No | Acquired customer volume: `contacts_reached * conversion_rate` |
| `cpa_eur` | DOUBLE | No | Cost per acquisition: `marketing_spend_eur / customers_acquired` |
| `customer_ltv_eur` | DOUBLE | No | Composite customer lifetime value (€835.50) |
| `total_ltv_revenue_eur` | DOUBLE | No | Total revenue generated: `customers_acquired * customer_ltv_eur` |
| `roi_pct` | DOUBLE | No | Percentage return on investment |
| `break_even_conversion_rate` | DOUBLE | No | Break-even threshold: `cost_per_contact_eur / customer_ltv_eur` (0.658%) |

---

### Table: `voltalake.gold.data_quality_scorecard`
* **Description:** Automated evaluation results of Lakeflow pipeline expectations executed on conformed data.

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `expectation_name` | STRING | No | Data quality rule name |
| `target_dataset` | STRING | No | Dataset being evaluated |
| `total_evaluated` | BIGINT | No | Total records inspected |
| `passed_records` | BIGINT | No | Records satisfying the rule |
| `failed_records` | BIGINT | No | Records violating the rule |
| `pass_rate_pct` | DOUBLE | No | Percentage of valid records |
| `quarantine_action` | STRING | No | Enforcement action (`REJECT_ROW`, `ROUTE_TO_QUARANTINE`, `DEDUPLICATE`) |
| `_evaluated_at` | TIMESTAMP | No | UTC timestamp of quality evaluation |

---

### Table: `voltalake.gold.freshness_tracking`
* **Description:** Ingestion freshness audit against defined regulatory SLAs.

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `source_system` | STRING | No | Clean system name |
| `jurisdiction` | STRING | No | `IE` or `GB` |
| `update_frequency` | STRING | No | Update cadence (Monthly, Quarterly, Annual) |
| `sla_days` | INTEGER | No | Maximum permissible latency |
| `last_ingested` | TIMESTAMP | No | Last refresh timestamp |
| `sla_status` | STRING | No | SLA status (`MET`, `BREACHED`) |
| `latency_hours` | DOUBLE | No | Processing latency |
