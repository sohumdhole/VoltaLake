import pandas as pd
import numpy as np

# Load our merged dataframe logic
from test_26_county_merge import merged

df = merged.copy()

def min_max(s):
    return (s - s.min()) / (s.max() - s.min())

df['norm_inefficiency'] = min_max(df['pct_d_or_worse'])
df['norm_oil'] = min_max(df['pct_oil_dependent'])
df['norm_consumption'] = min_max(df['residential_kwh_per_dwelling'])
df['norm_bev'] = min_max(df['bev_share_new_cars_pct'])

# Weights: 35% thermal deficiency, 35% oil dependence, 15% consumption per dwelling, 15% BEV share
df['retrofit_propensity_score'] = (
    0.35 * df['norm_inefficiency'] +
    0.35 * df['norm_oil'] +
    0.15 * df['norm_consumption'] +
    0.15 * df['norm_bev']
) * 100

# Assign 4 tiers based on score quartiles
df['propensity_tier'] = pd.qcut(
    df['retrofit_propensity_score'], 
    q=4, 
    labels=['Low', 'Moderate', 'High', 'Prime Target']
)

df = df.sort_values('retrofit_propensity_score', ascending=False).reset_index(drop=True)
print("=== 26 COUNTIES RETROFIT PROPENSITY RANKING ===")
print(df[['county', 'retrofit_propensity_score', 'propensity_tier', 'pct_d_or_worse', 'pct_oil_dependent', 'residential_kwh_per_dwelling', 'bev_share_new_cars_pct']].to_string())
