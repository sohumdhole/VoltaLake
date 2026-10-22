# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # VoltaLake: 02 - Silver Lakeflow Declarative Pipeline & GDPR Governance
# MAGIC **Catalog:** `voltalake` | **Schema:** `silver`
# MAGIC 
# MAGIC ### Purpose & Production Design
# MAGIC The Silver layer enforces rigorous schema conformance, unit standardisation, data quality expectations,
# MAGIC quarantine isolation, Slowly Changing Dimensions (SCD Type 2), and Enterprise GDPR compliance.
# MAGIC 
# MAGIC ### Design Decisions: Architectural Decisions
# MAGIC 1. **Why Lakeflow Declarative Pipelines (DLT) with `@dlt.expect_or_quarantine`?**
# MAGIC    Silent data corruption is unacceptable in customer analytics. Instead of dropping bad rows silently (`expect_or_drop`) or failing the entire batch (`expect_or_fail`), routing malformed records to quarantine tables ensures zero data loss, enables root-cause debugging, and tracks quality metrics over time.
# MAGIC 2. **Why Unit Conformance to kWh?**
# MAGIC    CSO reports in GWh, DESNZ reports in both GWh and kWh per meter, and smart meters record in kWh/half-hour. Standardising to `kWh` at Silver eliminates cognitive overhead and unit-mismatch bugs across downstream analytics.
# MAGIC 3. **Why Salted SHA-256 for Pseudonymisation?**
# MAGIC    Under GDPR Article 4(5) and Recital 26, simple unsalted hashing (MD5/SHA1) is vulnerable to dictionary and rainbow-table attacks. Salted SHA-256 with secure key rotation satisfies cryptographic pseudonymisation standards.
# MAGIC 4. **Why Unity Catalog Dynamic Column Masks and Row Filters?**
# MAGIC    Instead of maintaining separate views or duplicate pipelines for different teams (e.g. Ireland compliance vs GB operations), Unity Catalog enforces fine-grained ABAC (Attribute-Based Access Control) natively in the storage engine at query execution time.

# COMMAND ----------
import dlt
from pyspark.sql.functions import (
    col, when, lit, sha2, concat, to_date, current_timestamp,
    monotonically_increasing_id, round as spark_round, upper, trim
)

CATALOG = "voltalake"
GDPR_SALT = "VoltaLake_2026_Secure_Salt_Customer_Data_Specialist"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Silver Expectations & Quarantine: Building Energy Ratings (SEAI)

# COMMAND ----------
# SEAI BER Expectations
ber_rules = {
    "valid_energy_rating": "energyrating RLIKE '^[A-G][0-9]?$'",
    "valid_floor_area": "`groundfloorarea(sq_m)` > 10.0 AND `groundfloorarea(sq_m)` < 1500.0",
    "valid_construction_year": "year_of_construction >= 1800 AND year_of_construction <= 2026",
    "valid_ber_numeric": "berrating > 0.0 AND berrating < 2000.0"
}

@dlt.table(
    name="silver_seai_ber_clean",
    comment="Cleaned and validated SEAI Building Energy Ratings certificates",
    table_properties={"quality": "silver"}
)
@dlt.expect_all_or_quarantine(ber_rules)
def silver_seai_ber_clean():
    return (
        dlt.read("bronze.raw_seai_ber_certificates")
        .withColumn("county_clean", upper(trim(col("countyname"))))
        .withColumn("floor_area_sqm", col("`groundfloorarea(sq_m)`").cast("double"))
        .withColumn("ber_rating_kwh_m2_yr", col("berrating").cast("double"))
        .withColumn("construction_year", col("year_of_construction").cast("int"))
        .withColumn("is_d_or_worse", col("energyrating").substr(1, 1).isin(["D", "E", "F", "G"]))
        .withColumn("is_oil_heated", col("mainspaceheatingfuel").rlike("(?i)oil"))
        .withColumn("is_gas_heated", col("mainspaceheatingfuel").rlike("(?i)gas"))
        .withColumn("is_heat_pump", col("mainspaceheatingfuel").rlike("(?i)heat pump|electricity"))
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Silver Expectations: Metered Electricity Consumption (CSO MEC03 & DESNZ)

# COMMAND ----------
cso_rules = {
    "non_negative_consumption": "consumption_gwh >= 0.0",
    "reasonable_county_gwh": "consumption_gwh < 50000.0",
    "valid_year": "year >= 2010 AND year <= 2030"
}

@dlt.table(
    name="silver_cso_metered_consumption",
    comment="Cleaned CSO Metered Electricity Consumption with unit standardisation to kWh",
    table_properties={"quality": "silver"}
)
@dlt.expect_all_or_quarantine(cso_rules)
def silver_cso_metered_consumption():
    return (
        dlt.read("bronze.raw_cso_metered_electricity")
        .withColumn("county_clean", upper(trim(col("Counties & Dublin Postal Districts"))))
        .withColumn("sector_clean", trim(col("Sector")))
        .withColumn("consumption_gwh", col("VALUE").cast("double"))
        # Unit Conformance: 1 GWh = 1,000,000 kWh
        .withColumn("consumption_kwh", col("VALUE").cast("double") * 1_000_000.0)
        .withColumn("year", col("Year").cast("int"))
        .withColumn("currency", lit("EUR"))
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Silver Expectations & GDPR Pseudonymisation: London Smart Meter Half-Hourly

# COMMAND ----------
smart_meter_rules = {
    "valid_hh_consumption": "consumption_kwh_hh >= 0.0 AND consumption_kwh_hh < 15.0",
    "valid_half_hour_interval": "half_hour_interval >= 0 AND half_hour_interval <= 47",
    "valid_tariff_group": "tariff_group IN ('Std', 'ToU')"
}

@dlt.table(
    name="silver_london_smart_meters",
    comment="Half-hourly smart meter records with salted SHA-256 pseudonymisation and peak tagging",
    table_properties={"quality": "silver"}
)
@dlt.expect_all_or_quarantine(smart_meter_rules)
def silver_london_smart_meters():
    return (
        dlt.readStream("bronze.raw_london_smart_meters")
        # GDPR Article 4(5) Salted Pseudonymisation
        .withColumn("household_id_masked", sha2(concat(col("LCLid"), lit(GDPR_SALT)), 256).substr(1, 16))
        .withColumn("tariff_group", trim(col("stdorToU")))
        .withColumn("reading_timestamp", col("DateTime").cast("timestamp"))
        .withColumn("consumption_kwh_hh", col("`KWH/hh (per half hour) `").cast("double"))
        .withColumn("hour", col("reading_timestamp").substr(12, 2).cast("int"))
        .withColumn("minute", col("reading_timestamp").substr(15, 2).cast("int"))
        .withColumn("half_hour_interval", col("hour") * 2 + (col("minute") / 30).cast("int"))
        # Peak Window Definition: 16:00 to 20:00 (intervals 32 through 39)
        .withColumn("is_peak_window", (col("hour") >= 16) & (col("hour") < 20))
        .withColumn("currency", lit("GBP"))
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Slowly Changing Dimensions (SCD Type 2): Retail Market Reference Data

# COMMAND ----------
# Implement SCD Type 2 tracking on energy supplier market shares and reference metadata
# Changes over regulatory reporting periods are versioned with valid_from, valid_to, and is_current

dlt.create_streaming_table(
    name="silver_supplier_market_share_scd2",
    comment="SCD Type 2 tracking supplier market shares and regulatory licence status"
)

dlt.apply_changes(
    target="silver_supplier_market_share_scd2",
    source="bronze.raw_supplier_reference_feed",
    keys=["supplier_id", "jurisdiction"],
    sequence_by=col("reporting_date"),
    stored_as_scd_type="2",
    track_history_column_list=["domestic_market_share_pct", "licence_status", "tariff_portfolio_size"]
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Unity Catalog GDPR Access Control: Row-Level Security & Column Masking

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Unity Catalog Dynamic Column Masking Function for PII / Household Identifiers
# MAGIC CREATE OR REPLACE FUNCTION voltalake.silver.mask_household_id(id_val STRING)
# MAGIC RETURN CASE 
# MAGIC   WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_dpo_admin') THEN id_val
# MAGIC   WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_analytics_team') THEN CONCAT('PSEUDO-', SUBSTR(id_val, 1, 8))
# MAGIC   ELSE 'REDACTED-GDPR'
# MAGIC END;
# MAGIC 
# MAGIC -- Apply Mask to Household Identifier Column
# MAGIC ALTER TABLE voltalake.silver.silver_london_smart_meters 
# MAGIC ALTER COLUMN household_id_masked SET MASK voltalake.silver.mask_household_id;
# MAGIC 
# MAGIC -- Unity Catalog Row-Level Security: Jurisdiction Access Policy
# MAGIC CREATE OR REPLACE FUNCTION voltalake.silver.filter_jurisdiction_access(jurisdiction STRING)
# MAGIC RETURN CASE
# MAGIC   -- Executive / Leadership sees all jurisdictions
# MAGIC   WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_exec_global') THEN TRUE
# MAGIC   -- Ireland Customer Specialist sees IE data only
# MAGIC   WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_ireland_specialist') AND jurisdiction = 'IE' THEN TRUE
# MAGIC   -- GB Operations Analyst sees GB data only
# MAGIC   WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_gb_analyst') AND jurisdiction = 'GB' THEN TRUE
# MAGIC   ELSE FALSE
# MAGIC END;
# MAGIC 
# MAGIC -- Apply Row Filter to Consolidated Regional Consumption
# MAGIC ALTER TABLE voltalake.silver.silver_cso_metered_consumption 
# MAGIC SET ROW FILTER voltalake.silver.filter_jurisdiction_access ON (_jurisdiction);
