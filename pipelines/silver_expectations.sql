-- ============================================================================
-- VoltaLake: Silver Layer Data Expectations & Quarantine Routing
-- Dialect: Databricks SQL / Delta Live Tables (DLT)
-- ============================================================================

-- 1. SEAI Building Energy Ratings Expectations
CREATE OR REFRESH STREAMING TABLE voltalake.silver.silver_seai_ber_certificates (
  CONSTRAINT valid_rating EXPECT (energyrating RLIKE '^[A-G][0-9]?$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_floor_area EXPECT (`groundfloorarea(sq_m)` > 10.0 AND `groundfloorarea(sq_m)` < 1500.0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_numeric_ber EXPECT (berrating > 0.0 AND berrating < 2000.0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_construction_year EXPECT (year_of_construction >= 1800 AND year_of_construction <= 2026) ON VIOLATION DROP ROW
)
COMMENT 'Validated SEAI Building Energy Rating certificates with bad records dropped to quarantine'
AS SELECT 
  UPPER(TRIM(countyname)) AS county,
  dwellingtypedescr AS dwelling_type,
  year_of_construction AS construction_year,
  energyrating,
  berrating AS ber_kwh_m2_yr,
  `groundfloorarea(sq_m)` AS floor_area_sqm,
  co2rating AS co2_rating,
  mainspaceheatingfuel AS space_heating_fuel,
  mainwaterheatingfuel AS water_heating_fuel,
  _source_file,
  _ingested_at,
  _jurisdiction
FROM STREAM(voltalake.bronze.raw_seai_ber_certificates);

-- Quarantine Table for Malformed BER records
CREATE OR REFRESH STREAMING TABLE voltalake.silver.quarantine_seai_ber (
  CONSTRAINT is_quarantine EXPECT (
    energyrating NOT RLIKE '^[A-G][0-9]?$' OR
    `groundfloorarea(sq_m)` <= 10.0 OR `groundfloorarea(sq_m)` >= 1500.0 OR
    berrating <= 0.0 OR berrating >= 2000.0 OR
    year_of_construction < 1800 OR year_of_construction > 2026
  ) ON VIOLATION DROP ROW
)
COMMENT 'Quarantined SEAI records violating thermal energy rating standards'
AS SELECT *, current_timestamp() AS _quarantined_at
FROM STREAM(voltalake.bronze.raw_seai_ber_certificates);

-- 2. CSO Metered Electricity Consumption Expectations
CREATE OR REFRESH STREAMING TABLE voltalake.silver.silver_cso_metered_consumption (
  CONSTRAINT non_negative_consumption EXPECT (VALUE >= 0.0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_reporting_year EXPECT (Year >= 2010 AND Year <= 2030) ON VIOLATION DROP ROW,
  CONSTRAINT valid_county EXPECT (`Counties & Dublin Postal Districts` IS NOT NULL) ON VIOLATION DROP ROW
)
AS SELECT 
  Year AS year,
  UPPER(TRIM(`Counties & Dublin Postal Districts`)) AS county,
  TRIM(Sector) AS sector,
  CAST(VALUE AS DOUBLE) AS consumption_gwh,
  -- Standardise to kWh: 1 GWh = 1,000,000 kWh
  CAST(VALUE AS DOUBLE) * 1000000.0 AS consumption_kwh,
  'EUR' AS currency,
  _source_file,
  _ingested_at,
  _jurisdiction
FROM STREAM(voltalake.bronze.raw_cso_metered_electricity);

-- 3. London Smart Meter Half-Hourly Expectations
CREATE OR REFRESH STREAMING TABLE voltalake.silver.silver_london_smart_meters (
  CONSTRAINT valid_half_hour_kwh EXPECT (`KWH/hh (per half hour) ` >= 0.0 AND `KWH/hh (per half hour) ` < 15.0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_tariff_type EXPECT (stdorToU IN ('Std', 'ToU')) ON VIOLATION DROP ROW
)
AS SELECT 
  -- Salted SHA-256 GDPR pseudonymisation
  SUBSTR(SHA2(CONCAT(LCLid, 'VoltaLake_2026_Secure_Salt_Customer_Data_Specialist'), 256), 1, 16) AS household_id_masked,
  stdorToU AS tariff_group,
  CAST(DateTime AS TIMESTAMP) AS reading_timestamp,
  CAST(`KWH/hh (per half hour) ` AS DOUBLE) AS consumption_kwh_hh,
  HOUR(CAST(DateTime AS TIMESTAMP)) * 2 + INT(MINUTE(CAST(DateTime AS TIMESTAMP)) / 30) AS half_hour_interval,
  CASE 
    WHEN HOUR(CAST(DateTime AS TIMESTAMP)) >= 16 AND HOUR(CAST(DateTime AS TIMESTAMP)) < 20 THEN TRUE 
    ELSE FALSE 
  END AS is_peak_window,
  CASE 
    WHEN DAYOFWEEK(CAST(DateTime AS TIMESTAMP)) IN (1, 7) THEN TRUE 
    ELSE FALSE 
  END AS is_weekend,
  'GBP' AS currency,
  _source_file,
  _ingested_at,
  _jurisdiction
FROM STREAM(voltalake.bronze.raw_london_smart_meters);
