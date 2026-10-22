-- ============================================================================
-- VoltaLake: Databricks Genie Trusted Benchmark Queries
-- Pre-validated SQL queries providing ground-truth answers for Genie
-- ============================================================================

-- Query 1: Annual switching rate comparison between Ireland and Great Britain
SELECT 
  year,
  jurisdiction,
  source,
  electricity_switches,
  avg_customers,
  ROUND(switching_rate_pct, 2) AS annual_switching_rate_pct
FROM voltalake.gold.fact_market_switching
WHERE year >= 2018
ORDER BY year DESC, jurisdiction;

-- Query 2: Top 5 Prime Target Counties in Ireland for Deep Retrofit & Heat Pumps
SELECT 
  county,
  total_certs,
  d_or_worse_count AS sub_standard_ber_count,
  ROUND(pct_d_or_worse, 1) AS pct_ber_d_or_worse,
  ROUND(pct_oil_dependent, 1) AS pct_oil_heated,
  ROUND(ev_penetration_pct, 2) AS ev_adoption_pct,
  ROUND(retrofit_propensity_score, 1) AS propensity_score,
  propensity_tier
FROM voltalake.gold.kpi_retrofit_propensity_ie
WHERE propensity_tier = 'Prime Target'
ORDER BY retrofit_propensity_score DESC
LIMIT 5;

-- Query 3: Household Personas Breakdown with Peak Demand Intensity
SELECT 
  persona_name,
  target_proposition,
  COUNT(*) AS household_count,
  ROUND(AVG(avg_hh_kwh), 3) AS avg_half_hourly_kwh,
  ROUND(AVG(peak_hh_kwh), 3) AS avg_peak_kwh_16_20,
  ROUND(AVG(peak_to_offpeak_ratio), 2) AS peak_to_offpeak_ratio
FROM voltalake.gold.kpi_customer_personas
GROUP BY persona_name, target_proposition
ORDER BY household_count DESC;

-- Query 4: Peak Demand Comparison: Dynamic Time-of-Use vs Standard Flat Tariffs
SELECT 
  tariff_group,
  COUNT(*) AS sample_size_households,
  ROUND(AVG(peak_hh_kwh), 4) AS mean_peak_kwh_hh,
  ROUND(AVG(offpeak_hh_kwh), 4) AS mean_offpeak_kwh_hh,
  ROUND(AVG(peak_to_offpeak_ratio), 3) AS mean_peak_ratio
FROM voltalake.gold.kpi_customer_personas
GROUP BY tariff_group;

-- Query 5: Campaign Acquisition Cost (CPA) and ROI at €100,000 Marketing Spend
SELECT 
  marketing_spend_eur,
  ROUND(conversion_rate * 100, 1) AS conversion_rate_pct,
  contacts_reached,
  customers_acquired,
  cpa_eur,
  total_ltv_revenue_eur,
  roi_pct
FROM voltalake.gold.kpi_campaign_roi_sensitivity
WHERE marketing_spend_eur = 100000
ORDER BY conversion_rate;

-- Query 6: Data Quality Expectation Pass Rate Audit
SELECT 
  dataset_name,
  expectation_rule,
  total_rows_evaluated,
  passing_rows,
  quarantined_rows,
  pass_rate_pct,
  status
FROM voltalake.gold.data_quality_scorecard
ORDER BY pass_rate_pct ASC;

-- Query 7: Dataset Freshness and Regulatory SLA Compliance
SELECT 
  source_system,
  jurisdiction,
  update_frequency,
  sla_days,
  sla_status,
  latency_hours
FROM voltalake.gold.freshness_tracking
ORDER BY latency_hours ASC;
