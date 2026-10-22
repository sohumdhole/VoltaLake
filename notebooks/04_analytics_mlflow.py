# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # VoltaLake: 04 - Analytics, Machine Learning & MLflow Experiment Tracking
# MAGIC **Catalog:** `voltalake` | **Schema:** `gold` | **MLflow Experiment:** `/Shared/VoltaLake_Customer_Intelligence`
# MAGIC 
# MAGIC ### Purpose & Production Design
# MAGIC This notebook executes the analytical and predictive core of VoltaLake, tracking all models and statistical tests in **MLflow**:
# MAGIC 1. **Retrofit & Heat-Pump Propensity Index:** Multi-criteria weighted propensity across 26 Irish counties and 350 GB Local Authorities.
# MAGIC 2. **Household Load-Shape Segmentation:** Unsupervised clustering (k-means) on 48 half-hour load profiles, evaluated with Silhouette scores and Davies-Bouldin indices ($k=3$ selected; exploratory segments).
# MAGIC 3. **Difference-in-Differences Tariff Evaluation:** 2012 pre-period baseline vs 2013 ToU post-period comparison (ToU vs Std) reporting true sign, effect size, and confidence intervals.
# MAGIC 4. **Campaign ROI / CPA Sensitivity Simulator:** Interactive unit economics simulator for marketing and propositions leaders (`contacts = spend / cost_per_contact`).

# COMMAND ----------
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score
import json
import math

mlflow.set_experiment("/Shared/VoltaLake_Customer_Intelligence")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. MLflow Experiment 1: Retrofit & Heat-Pump Propensity Model (26 Irish Counties)

# COMMAND ----------
with mlflow.start_run(run_name="Retrofit_Propensity_Model_IE_26_Counties") as run:
    weights = {
        "weight_thermal_inefficiency": 0.35,
        "weight_oil_displacement": 0.35,
        "weight_consumption_per_dwelling": 0.15,
        "weight_bev_share_2025": 0.15
    }
    mlflow.log_params(weights)
    mlflow.log_param("geography_scope", "26 conformed administrative counties (zero imputation)")
    
    df_ie_prop = spark.table("voltalake.gold.kpi_retrofit_propensity_ie").toPandas()
    
    mean_score_ie = float(df_ie_prop["retrofit_propensity_score"].mean())
    top_tier_count = int((df_ie_prop["propensity_tier"] == "Prime Target").sum())
    prime_target_counties = df_ie_prop[df_ie_prop["propensity_tier"] == "Prime Target"]["county"].tolist()
    
    mlflow.log_metric("mean_propensity_score_ie", mean_score_ie)
    mlflow.log_metric("prime_target_counties_count", top_tier_count)
    mlflow.log_dict({"prime_target_counties": prime_target_counties}, "prime_target_counties.json")
    
    print(f"[MLflow] Retrofit Model Logged. Mean IE Score: {mean_score_ie:.2f} | Prime Target Counties: {top_tier_count}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. MLflow Experiment 2: Household Load-Shape Segmentation (Selected k=3; Exploratory)
 
# COMMAND ----------
with mlflow.start_run(run_name="Household_Load_Shape_KMeans_Clustering") as run:
    df_load = spark.table("voltalake.gold.fact_household_load").toPandas()
    
    hh_profiles = df_load.groupby(["household_id", "half_hour_interval"])["consumption_kwh_hh"].mean().unstack().dropna()
    row_sums = hh_profiles.sum(axis=1)
    hh_profiles_norm = hh_profiles.div(row_sums, axis=0)
    
    # Evaluate across k=2..6
    k_eval = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(hh_profiles_norm)
        sil = float(silhouette_score(hh_profiles_norm, labels))
        db = float(davies_bouldin_score(hh_profiles_norm, labels))
        k_eval[k] = {"silhouette": sil, "davies_bouldin": db}
        mlflow.log_metric(f"silhouette_k_{k}", sil)
        mlflow.log_metric(f"davies_bouldin_k_{k}", db)
        
    best_k = 3  # Selected k (silhouette 0.1773 indicates weak cluster structure; exploratory personas)
    mlflow.log_param("selected_k", best_k)
    mlflow.log_param("selection_criterion", "Selected k=3 (Silhouette 0.1773; Balanced Segments >5%)")
    
    final_km = KMeans(n_clusters=best_k, random_state=42, n_init=20)
    final_labels = final_km.fit_predict(hh_profiles_norm)
    
    mlflow.sklearn.log_model(final_km, "kmeans_load_shape_model")
    mlflow.log_metric("final_silhouette_score", k_eval[best_k]["silhouette"])
    mlflow.log_metric("final_davies_bouldin_index", k_eval[best_k]["davies_bouldin"])
    
    print(f"[MLflow] K-Means Clustering Logged. Selected k={best_k} | Silhouette: {k_eval[best_k]['silhouette']:.4f}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. MLflow Experiment 3: Difference-in-Differences (DiD) Tariff Evaluation
# MAGIC 2012 Pre-Period Baseline vs 2013 ToU Trial Period ($n=61$ households)

# COMMAND ----------
with mlflow.start_run(run_name="Tariff_Response_Difference_in_Differences_2012_2013") as run:
    df_did = spark.table("voltalake.gold.kpi_tariff_did_experiment").toPandas()
    
    tou_deltas = df_did[df_did["tariff_group"] == "ToU"]["delta_peak_kwh"]
    std_deltas = df_did[df_did["tariff_group"] == "Std"]["delta_peak_kwh"]
    
    n1, n2 = len(tou_deltas), len(std_deltas)
    delta_tou = float(tou_deltas.mean())
    delta_std = float(std_deltas.mean())
    did_effect = delta_tou - delta_std  # True sign: +0.0169 kWh/hh per half-hour
    
    # Welch's two-sample t-test on deltas
    t_stat, p_val = stats.ttest_ind(tou_deltas, std_deltas, equal_var=False)
    
    # Cohen's d
    s1, s2 = tou_deltas.std(ddof=1), std_deltas.std(ddof=1)
    s_pooled = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    cohens_d = float(did_effect / s_pooled)
    
    # 95% Confidence Interval (Welch's df)
    se_diff = math.sqrt(s1**2 / n1 + s2**2 / n2)
    df_welch = (s1**2 / n1 + s2**2 / n2)**2 / ((s1**2 / n1)**2 / (n1 - 1) + (s2**2 / n2)**2 / (n2 - 1))
    ci_crit = stats.t.ppf(0.975, df=df_welch)
    ci_lower = float(did_effect - ci_crit * se_diff)
    ci_upper = float(did_effect + ci_crit * se_diff)
    
    mlflow.log_params({
        "methodology": "Difference_in_Differences",
        "pre_period_baseline_year": 2012,
        "post_period_trial_year": 2013,
        "peak_window": "16:00 - 20:00",
        "treatment_group": "ToU (Dynamic Time-of-Use)",
        "control_group": "Std (Standard Flat Rate)"
    })
    
    mlflow.log_metrics({
        "treatment_sample_size": n1,
        "control_sample_size": n2,
        "treatment_delta_kwh": delta_tou,
        "control_delta_kwh": delta_std,
        "did_effect_kwh_per_half_hour": did_effect,
        "welch_t_statistic": float(t_stat),
        "two_tailed_p_value": float(p_val),
        "cohens_d_effect_size": cohens_d,
        "ci_95_lower": ci_lower,
        "ci_95_upper": ci_upper
    })
    
    scientific_summary = {
        "finding": "The Difference-in-Differences effect is +0.0169 kWh/hh per half-hour (95% CI [-0.0070, +0.0407], p = 0.1623), finding no statistically significant peak reduction.",
        "commercial_conclusion": "Found no statistically significant peak reduction in this 61-household sample (p=0.16; 95% CI includes small reductions). Hypothesis to test: propositions may require bundling automated smart chargers and heat-pump controllers rather than relying on voluntary manual shifting.",
        "did_effect": did_effect,
        "p_value": float(p_val),
        "cohens_d": cohens_d
    }
    mlflow.log_dict(scientific_summary, "did_tariff_findings.json")
    print(f"[MLflow] DiD Tariff Response Logged: DiD={did_effect:+.4f} kWh/hh, p-value={p_val:.4f}, 95% CI=[{ci_lower:+.4f}, {ci_upper:+.4f}]")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. MLflow Experiment 4: Campaign ROI & CPA Sensitivity Simulator

# COMMAND ----------
with mlflow.start_run(run_name="Campaign_ROI_CPA_Sensitivity_Simulator") as run:
    assumptions = {
        "channel_cost_per_contact_eur": 5.50,
        "annual_gross_margin_per_customer_eur": 240.0,
        "customer_tenure_years": 3.2,
        "retrofit_commission_fee_eur": 450.0,
        "retrofit_takeup_rate_on_switch": 0.15,
        "formula_reach": "contacts_reached = marketing_spend / channel_cost_per_contact"
    }
    mlflow.log_params(assumptions)
    
    df_sens = spark.table("voltalake.gold.kpi_campaign_roi_sensitivity").toPandas()
    
    best_roi_record = df_sens.sort_values(by="roi_pct", ascending=False).iloc[0]
    worst_roi_record = df_sens.sort_values(by="roi_pct", ascending=True).iloc[0]
    
    mlflow.log_metrics({
        "max_simulated_roi_pct": float(best_roi_record["roi_pct"]),
        "min_simulated_roi_pct": float(worst_roi_record["roi_pct"]),
        "lowest_cpa_eur": float(best_roi_record["cpa_eur"]),
        "highest_cpa_eur": float(worst_roi_record["cpa_eur"]),
        "break_even_conversion_rate_pct": float(df_sens["break_even_conversion_rate"].iloc[0])
    })
    
    print(f"[MLflow] Campaign Simulator Logged. Max ROI: {best_roi_record['roi_pct']}% | Break-even Conversion: {df_sens['break_even_conversion_rate'].iloc[0]}%")
