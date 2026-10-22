import duckdb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score

con = duckdb.connect()

print("==========================================================")
print("PART 1: DIFFERENCE-IN-DIFFERENCES TARIFF EVALUATION")
print("==========================================================")

# 1. Fetch household-level peak consumption in 2012 (pre) and 2013 (post)
did_df = con.execute("""
    WITH hh_yearly_peak AS (
        SELECT 
            household_id,
            tariff_group,
            EXTRACT(YEAR FROM reading_timestamp) as yr,
            AVG(consumption_kwh_hh) as mean_peak_kwh,
            COUNT(*) as peak_readings
        FROM 'data/processed/london_smart_meter_readings.parquet'
        WHERE is_peak_window = TRUE
          AND EXTRACT(YEAR FROM reading_timestamp) IN (2012, 2013)
        GROUP BY household_id, tariff_group, EXTRACT(YEAR FROM reading_timestamp)
    ),
    pivoted AS (
        SELECT 
            household_id,
            tariff_group,
            MAX(CASE WHEN yr = 2012 THEN mean_peak_kwh END) as peak_2012,
            MAX(CASE WHEN yr = 2013 THEN mean_peak_kwh END) as peak_2013
        FROM hh_yearly_peak
        GROUP BY household_id, tariff_group
        HAVING MAX(CASE WHEN yr = 2012 THEN mean_peak_kwh END) IS NOT NULL
           AND MAX(CASE WHEN yr = 2013 THEN mean_peak_kwh END) IS NOT NULL
    )
    SELECT 
        household_id,
        tariff_group,
        peak_2012,
        peak_2013,
        (peak_2013 - peak_2012) as delta_peak_kwh
    FROM pivoted
""").fetchdf()

print(f"Total households with both 2012 and 2013 observations: {len(did_df)}")
print(did_df.groupby('tariff_group').size().rename("count").to_string())

tou_deltas = did_df[did_df['tariff_group'] == 'ToU']['delta_peak_kwh']
std_deltas = did_df[did_df['tariff_group'] == 'Std']['delta_peak_kwh']

tou_pre = did_df[did_df['tariff_group'] == 'ToU']['peak_2012'].mean()
tou_post = did_df[did_df['tariff_group'] == 'ToU']['peak_2013'].mean()
tou_diff = tou_deltas.mean()

std_pre = did_df[did_df['tariff_group'] == 'Std']['peak_2012'].mean()
std_post = did_df[did_df['tariff_group'] == 'Std']['peak_2013'].mean()
std_diff = std_deltas.mean()

did_effect = tou_diff - std_diff

# Two-sample t-test on deltas
t_stat, p_val = stats.ttest_ind(tou_deltas, std_deltas, equal_var=False)

# Pooled standard deviation for Cohen's d
n1, n2 = len(tou_deltas), len(std_deltas)
s1, s2 = tou_deltas.std(ddof=1), std_deltas.std(ddof=1)
s_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
cohens_d = did_effect / s_pooled

# 95% Confidence Interval for DiD effect (Welch's approximation)
se_diff = np.sqrt(s1**2 / n1 + s2**2 / n2)
df_welch = (s1**2 / n1 + s2**2 / n2)**2 / ((s1**2 / n1)**2 / (n1 - 1) + (s2**2 / n2)**2 / (n2 - 1))
ci_crit = stats.t.ppf(0.975, df=df_welch)
ci_lower = did_effect - ci_crit * se_diff
ci_upper = did_effect + ci_crit * se_diff

print("\n--- DiD Empirical Findings ---")
print(f"Control (Std): Pre (2012) = {std_pre:.4f} kWh/hh | Post (2013) = {std_post:.4f} kWh/hh | Delta = {std_diff:+.4f} kWh/hh (n={n2})")
print(f"Treatment (ToU): Pre (2012) = {tou_pre:.4f} kWh/hh | Post (2013) = {tou_post:.4f} kWh/hh | Delta = {tou_diff:+.4f} kWh/hh (n={n1})")
print(f"DiD Effect (Delta_ToU - Delta_Std) = {did_effect:+.4f} kWh/hh per half-hour")
print(f"t-statistic = {t_stat:.4f}, p-value = {p_val:.4f}")
print(f"Degrees of Freedom = {df_welch:.2f}")
print(f"Cohen's d = {cohens_d:+.4f}")
print(f"95% Confidence Interval: [{ci_lower:+.4f}, {ci_upper:+.4f}]")

print("\n==========================================================")
print("PART 2: CLUSTERING & METRIC EVALUATION")
print("==========================================================")

# Fetch normalized 48 half-hour profiles per household
profiles = con.execute("""
    WITH hh_interval_avg AS (
        SELECT 
            household_id,
            half_hour_interval,
            AVG(consumption_kwh_hh) as avg_consumption
        FROM 'data/processed/london_smart_meter_readings.parquet'
        GROUP BY household_id, half_hour_interval
    ),
    hh_total AS (
        SELECT 
            household_id,
            SUM(avg_consumption) as daily_total
        FROM hh_interval_avg
        GROUP BY household_id
        HAVING SUM(avg_consumption) > 0
    )
    SELECT 
        a.household_id,
        a.half_hour_interval,
        a.avg_consumption / t.daily_total as norm_val
    FROM hh_interval_avg a
    JOIN hh_total t ON a.household_id = t.household_id
    ORDER BY a.household_id, a.half_hour_interval
""").fetchdf()

# Pivot to household x 48 matrix
X = profiles.pivot(index='household_id', columns='half_hour_interval', values='norm_val').fillna(0)
print(f"Profiles matrix shape: {X.shape}")

# Evaluate k=2 to k=6
cluster_results = []
for k in range(2, 7):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    sil = silhouette_score(X, labels)
    db = davies_bouldin_score(X, labels)
    cluster_results.append({'k': k, 'silhouette': sil, 'davies_bouldin': db})

cluster_metrics_df = pd.DataFrame(cluster_results)
print("\n--- Cluster Evaluation Metrics ---")
print(cluster_metrics_df.to_string(index=False))

# Best k based on silhouette:
best_k = cluster_metrics_df.loc[cluster_metrics_df['silhouette'].idxmax(), 'k']
print(f"\nBest k by Silhouette: k = {best_k}")

# Fit best_k model
km_best = KMeans(n_clusters=int(best_k), random_state=42, n_init=10)
labels_best = km_best.fit_predict(X)

# Analyze clusters
clustered_hh = pd.DataFrame({'household_id': X.index, 'cluster': labels_best})

# Join with total consumption and peak stats
hh_stats = con.execute("""
    SELECT 
        household_id,
        tariff_group,
        SUM(consumption_kwh_hh) as total_kwh,
        AVG(consumption_kwh_hh) as avg_hh_kwh,
        AVG(CASE WHEN is_peak_window THEN consumption_kwh_hh END) as peak_kwh,
        AVG(CASE WHEN NOT is_peak_window THEN consumption_kwh_hh END) as offpeak_kwh,
        AVG(CASE WHEN hour BETWEEN 0 AND 6 THEN consumption_kwh_hh END) as night_kwh,
        AVG(CASE WHEN hour BETWEEN 10 AND 16 THEN consumption_kwh_hh END) as daytime_kwh
    FROM 'data/processed/london_smart_meter_readings.parquet'
    GROUP BY household_id, tariff_group
""").fetchdf()

merged_clusters = clustered_hh.merge(hh_stats, on='household_id')

summary = merged_clusters.groupby('cluster').agg({
    'household_id': 'count',
    'avg_hh_kwh': 'mean',
    'peak_kwh': 'mean',
    'offpeak_kwh': 'mean',
    'night_kwh': 'mean',
    'daytime_kwh': 'mean'
}).rename(columns={'household_id': 'hh_count'}).reset_index()

summary['peak_to_offpeak_ratio'] = summary['peak_kwh'] / summary['offpeak_kwh']
summary['night_to_day_ratio'] = summary['night_kwh'] / summary['daytime_kwh']

print("\n--- Cluster Profile Summary ---")
print(summary.to_string(index=False))
