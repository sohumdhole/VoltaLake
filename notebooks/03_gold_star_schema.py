# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # VoltaLake: 03 - Gold Star Schema Dimensional Modelling
# MAGIC **Catalog:** `voltalake` | **Schema:** `gold`
# MAGIC 
# MAGIC ### Purpose & Production Design
# MAGIC The Gold schema delivers an enterprise star schema optimized for fast analytical aggregations,
# MAGIC Databricks Serverless SQL Warehouse queries, BI visualization in Streamlit, and Databricks Genie conversational AI.
# MAGIC 
# MAGIC ### Design Decisions: Architectural Decisions
# MAGIC 1. **Why Kimball Dimensional Star Schema over wide flat tables?**
# MAGIC    While wide flat tables are common in ad-hoc queries, an enterprise dimensional star schema:
# MAGIC    - Separates business entities (Dimensions: `dim_region`, `dim_date`, `dim_tariff`) from transactional events (Facts: `fact_household_load`, `fact_consumption_region`).
# MAGIC    - Enforces consistent business definitions across Ireland and GB.
# MAGIC    - Enables Databricks SQL query compiler to leverage **Dynamic File Pruning (DFP)** and **Z-Order Clustering** across dimension keys.
# MAGIC 2. **Why Unity Catalog Primary/Foreign Key Constraints?**
# MAGIC    Unity Catalog constraints (`RELY` / `NOT ENFORCED`) provide critical semantic metadata to Databricks cost-based query optimizer (CBO) and **Databricks Genie**, enabling Genie to automatically generate correct table joins without hallucinating relationships.
# MAGIC 3. **Why Liquid Clustering (`CLUSTER BY`) over traditional Hive Partitioning?**
# MAGIC    Traditional partitioning creates small-file skew problems (e.g., partitioning by `county` creates thousands of tiny files). Databricks Liquid Clustering automatically balances file sizes, accommodates evolving query patterns, and allows clustering on multiple keys (e.g. `jurisdiction, date_key`).

# COMMAND ----------
# MAGIC %sql
# MAGIC USE CATALOG voltalake;
# MAGIC CREATE SCHEMA IF NOT EXISTS gold COMMENT 'Enterprise dimensional star schema and KPI marts';

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Dimension Tables

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Dimension: Unified Date
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.dim_date (
# MAGIC   date_key INT NOT NULL,
# MAGIC   calendar_date DATE NOT NULL,
# MAGIC   year INT NOT NULL,
# MAGIC   quarter INT NOT NULL,
# MAGIC   quarter_name STRING,
# MAGIC   month INT NOT NULL,
# MAGIC   month_name STRING,
# MAGIC   day INT NOT NULL,
# MAGIC   day_of_week INT NOT NULL,
# MAGIC   day_name STRING,
# MAGIC   is_weekend BOOLEAN,
# MAGIC   season STRING,
# MAGIC   CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
# MAGIC )
# MAGIC COMMENT 'Enterprise calendar dimension covering 2000-2030'
# MAGIC CLUSTER BY (year, month);
# MAGIC 
# MAGIC -- Dimension: Jurisdiction-Aware Geography (IE County <-> GB Local Authority)
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.dim_region (
# MAGIC   region_key INT NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   region_code STRING NOT NULL,
# MAGIC   region_name STRING NOT NULL,
# MAGIC   region_level STRING NOT NULL,
# MAGIC   country STRING NOT NULL,
# MAGIC   currency STRING NOT NULL,
# MAGIC   CONSTRAINT pk_dim_region PRIMARY KEY (region_key)
# MAGIC )
# MAGIC COMMENT 'Standardised regional hierarchy for Ireland counties and GB Local Authorities'
# MAGIC CLUSTER BY (jurisdiction, region_level);
# MAGIC 
# MAGIC -- Dimension: Tariff Master
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.dim_tariff (
# MAGIC   tariff_key INT NOT NULL,
# MAGIC   tariff_code STRING NOT NULL,
# MAGIC   tariff_name STRING NOT NULL,
# MAGIC   tariff_type STRING NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   currency STRING NOT NULL,
# MAGIC   peak_window_active BOOLEAN,
# MAGIC   day_unit_rate_pence_cents DOUBLE,
# MAGIC   night_unit_rate_pence_cents DOUBLE,
# MAGIC   peak_unit_rate_pence_cents DOUBLE,
# MAGIC   description STRING,
# MAGIC   CONSTRAINT pk_dim_tariff PRIMARY KEY (tariff_key)
# MAGIC )
# MAGIC COMMENT 'Energy tariff portfolio dimensions for Ireland and GB';
# MAGIC 
# MAGIC -- Dimension: Property & Energy Efficiency Master
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.dim_property_type (
# MAGIC   property_type_key INT NOT NULL,
# MAGIC   dwelling_type STRING NOT NULL,
# MAGIC   ber_band STRING NOT NULL,
# MAGIC   efficiency_tier STRING NOT NULL,
# MAGIC   requires_retrofit BOOLEAN NOT NULL,
# MAGIC   CONSTRAINT pk_dim_property_type PRIMARY KEY (property_type_key)
# MAGIC )
# MAGIC COMMENT 'Housing archetypes and thermal efficiency classification bands';

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Fact Tables

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Fact: Regional Electricity Consumption (CSO & DESNZ)
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.fact_consumption_region (
# MAGIC   consumption_fact_key BIGINT NOT NULL,
# MAGIC   date_key INT NOT NULL,
# MAGIC   region_key INT NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   sector STRING NOT NULL,
# MAGIC   consumption_gwh DOUBLE,
# MAGIC   consumption_kwh DOUBLE NOT NULL,
# MAGIC   mean_consumption_kwh_per_meter DOUBLE,
# MAGIC   median_consumption_kwh_per_meter DOUBLE,
# MAGIC   meter_count DOUBLE,
# MAGIC   _source_system STRING,
# MAGIC   _ingested_at TIMESTAMP,
# MAGIC   CONSTRAINT pk_fact_consumption PRIMARY KEY (consumption_fact_key),
# MAGIC   CONSTRAINT fk_consumption_date FOREIGN KEY (date_key) REFERENCES voltalake.gold.dim_date (date_key),
# MAGIC   CONSTRAINT fk_consumption_region FOREIGN KEY (region_key) REFERENCES voltalake.gold.dim_region (region_key)
# MAGIC )
# MAGIC COMMENT 'Annual and periodic metered electricity consumption by jurisdiction, region, and sector'
# MAGIC CLUSTER BY (jurisdiction, date_key, region_key);
# MAGIC 
# MAGIC -- Fact: Half-Hourly Household Load (Low Carbon London Smart Meter Trial)
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.fact_household_load (
# MAGIC   household_fact_key BIGINT NOT NULL,
# MAGIC   household_id_masked STRING NOT NULL,
# MAGIC   tariff_key INT NOT NULL,
# MAGIC   date_key INT NOT NULL,
# MAGIC   reading_timestamp TIMESTAMP NOT NULL,
# MAGIC   half_hour_interval INT NOT NULL,
# MAGIC   is_peak_window BOOLEAN NOT NULL,
# MAGIC   is_weekend BOOLEAN NOT NULL,
# MAGIC   consumption_kwh_hh DOUBLE NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   _source_system STRING,
# MAGIC   _ingested_at TIMESTAMP,
# MAGIC   CONSTRAINT pk_fact_household_load PRIMARY KEY (household_fact_key),
# MAGIC   CONSTRAINT fk_load_date FOREIGN KEY (date_key) REFERENCES voltalake.gold.dim_date (date_key),
# MAGIC   CONSTRAINT fk_load_tariff FOREIGN KEY (tariff_key) REFERENCES voltalake.gold.dim_tariff (tariff_key)
# MAGIC )
# MAGIC COMMENT 'Granular half-hourly smart meter electricity demand profiles with GDPR pseudonymisation'
# MAGIC CLUSTER BY (date_key, half_hour_interval, tariff_key);
# MAGIC 
# MAGIC -- Fact: Harmonised Retail Market Switching & Churn Proxy (CRU & Ofgem)
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.fact_market_switching (
# MAGIC   switching_fact_key BIGINT NOT NULL,
# MAGIC   date_key INT NOT NULL,
# MAGIC   year INT NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   source STRING NOT NULL,
# MAGIC   electricity_switches BIGINT NOT NULL,
# MAGIC   avg_customers DOUBLE NOT NULL,
# MAGIC   switching_rate_pct DOUBLE NOT NULL,
# MAGIC   _ingested_at TIMESTAMP,
# MAGIC   CONSTRAINT pk_fact_switching PRIMARY KEY (switching_fact_key),
# MAGIC   CONSTRAINT fk_switching_date FOREIGN KEY (date_key) REFERENCES voltalake.gold.dim_date (date_key)
# MAGIC )
# MAGIC COMMENT 'Harmonised annual and quarterly customer switching metrics tracking churn proxy in Ireland and GB'
# MAGIC CLUSTER BY (jurisdiction, year);

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. KPI Marts & Data Governance Scorecards

# COMMAND ----------
# MAGIC %sql
# MAGIC -- KPI Mart: Ireland Retrofit & Heat-Pump Propensity
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.kpi_retrofit_propensity_ie (
# MAGIC   county STRING NOT NULL,
# MAGIC   total_certs BIGINT NOT NULL,
# MAGIC   c_or_better_count BIGINT,
# MAGIC   d_or_worse_count BIGINT,
# MAGIC   pct_d_or_worse DOUBLE,
# MAGIC   pct_fossil_fuel DOUBLE,
# MAGIC   pct_oil_dependent DOUBLE,
# MAGIC   pct_heat_pump DOUBLE,
# MAGIC   consumption_kwh DOUBLE,
# MAGIC   ev_penetration_pct DOUBLE,
# MAGIC   retrofit_propensity_score DOUBLE NOT NULL,
# MAGIC   propensity_tier STRING NOT NULL
# MAGIC )
# MAGIC COMMENT 'County-level multi-factor propensity index for heat-pump and deep retrofit targeting in Ireland'
# MAGIC CLUSTER BY (propensity_tier);
# MAGIC 
# MAGIC -- KPI Mart: GB Local Authority Retrofit Propensity
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.kpi_retrofit_propensity_gb (
# MAGIC   LA_Code STRING NOT NULL,
# MAGIC   Region STRING NOT NULL,
# MAGIC   LA STRING NOT NULL,
# MAGIC   Domestic_meters_thouasands DOUBLE,
# MAGIC   Domestic_consumption_GWh DOUBLE,
# MAGIC   pct_e7_meters DOUBLE,
# MAGIC   domestic_mean_kwh DOUBLE,
# MAGIC   gb_retrofit_propensity_score DOUBLE NOT NULL,
# MAGIC   gb_propensity_tier STRING NOT NULL
# MAGIC )
# MAGIC COMMENT 'Local Authority propensity index for off-peak electrification and retrofit in GB'
# MAGIC CLUSTER BY (gb_propensity_tier);
# MAGIC 
# MAGIC -- KPI Mart: Customer Load Personas (London Smart Meters)
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.kpi_customer_personas (
# MAGIC   household_id STRING NOT NULL,
# MAGIC   tariff_group STRING NOT NULL,
# MAGIC   total_recorded_kwh DOUBLE,
# MAGIC   avg_hh_kwh DOUBLE,
# MAGIC   peak_hh_kwh DOUBLE,
# MAGIC   offpeak_hh_kwh DOUBLE,
# MAGIC   peak_to_offpeak_ratio DOUBLE,
# MAGIC   cluster INT NOT NULL,
# MAGIC   persona_name STRING NOT NULL,
# MAGIC   target_proposition STRING NOT NULL
# MAGIC )
# MAGIC COMMENT 'Machine-learning segmented household archetypes mapped to tailored commercial propositions';
# MAGIC 
# MAGIC -- KPI Mart: Campaign ROI & CPA Sensitivity Simulator
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.kpi_campaign_roi_sensitivity (
# MAGIC   marketing_spend_eur DOUBLE NOT NULL,
# MAGIC   conversion_rate DOUBLE NOT NULL,
# MAGIC   contacts_reached BIGINT NOT NULL,
# MAGIC   customers_acquired BIGINT NOT NULL,
# MAGIC   cpa_eur DOUBLE NOT NULL,
# MAGIC   total_ltv_revenue_eur DOUBLE NOT NULL,
# MAGIC   roi_pct DOUBLE NOT NULL
# MAGIC )
# MAGIC COMMENT 'Pre-computed marketing acquisition sensitivity matrix across conversion rates and spend levels';
# MAGIC 
# MAGIC -- Governance Mart: Data Quality Scorecard
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.data_quality_scorecard (
# MAGIC   run_id STRING NOT NULL,
# MAGIC   dataset_name STRING NOT NULL,
# MAGIC   expectation_rule STRING NOT NULL,
# MAGIC   total_rows_evaluated BIGINT NOT NULL,
# MAGIC   passing_rows BIGINT NOT NULL,
# MAGIC   quarantined_rows BIGINT NOT NULL,
# MAGIC   pass_rate_pct DOUBLE NOT NULL,
# MAGIC   status STRING NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   evaluated_at TIMESTAMP NOT NULL
# MAGIC )
# MAGIC COMMENT 'Automated data quality expectation audit logs and quarantine statistics';
# MAGIC 
# MAGIC -- Governance Mart: Source Freshness Tracking
# MAGIC CREATE OR REPLACE TABLE voltalake.gold.freshness_tracking (
# MAGIC   source_system STRING NOT NULL,
# MAGIC   jurisdiction STRING NOT NULL,
# MAGIC   update_frequency STRING NOT NULL,
# MAGIC   sla_days INT NOT NULL,
# MAGIC   last_ingested TIMESTAMP NOT NULL,
# MAGIC   sla_status STRING NOT NULL,
# MAGIC   latency_hours DOUBLE NOT NULL
# MAGIC )
# MAGIC COMMENT 'Data freshness tracking against regulatory publication SLAs';
