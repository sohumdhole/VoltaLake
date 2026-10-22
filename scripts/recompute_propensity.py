import duckdb
import pandas as pd
import numpy as np

con = duckdb.connect()

# 1. BER Summary conformed to 26 counties
ber_raw = con.execute("""
    SELECT county, energyrating, cert_count, avg_ber_rating_kwh_m2_yr, avg_floor_area_sqm,
           avg_construction_year, heating_oil_count, mains_gas_count, heatpump_or_elec_count, solid_fuel_count
    FROM 'data/processed/seai_ber_county_summary.parquet'
""").fetchdf()

def map_ber_county(c):
    c_str = str(c).strip().upper()
    if 'DUBLIN' in c_str:
        return 'Dublin'
    if 'CORK' in c_str:
        return 'Cork'
    if 'GALWAY' in c_str:
        return 'Galway'
    if 'LIMERICK' in c_str:
        return 'Limerick'
    if 'WATERFORD' in c_str:
        return 'Waterford'
    return c_str.replace('CO. ', '').strip().capitalize()

ber_raw['county_26'] = ber_raw['county'].apply(map_ber_county)

ber_agg = ber_raw.groupby('county_26').apply(lambda g: pd.Series({
    'total_ber_certs': g['cert_count'].sum(),
    'poor_ber_certs': g[g['energyrating'].isin(['D','D1','D2','E','E1','E2','F','G'])]['cert_count'].sum(),
    'good_ber_certs': g[g['energyrating'].isin(['A','A0','A1','A2','A3','B','B1','B2','B3'])]['cert_count'].sum(),
    'total_oil_heating': g['heating_oil_count'].sum(),
    'total_gas_heating': g['mains_gas_count'].sum(),
    'total_heatpump_elec': g['heatpump_or_elec_count'].sum(),
    'avg_floor_area_sqm': round((g['avg_floor_area_sqm'] * g['cert_count']).sum() / g['cert_count'].sum(), 2),
    'avg_ber_rating': round((g['avg_ber_rating_kwh_m2_yr'] * g['cert_count']).sum() / g['cert_count'].sum(), 2),
})).reset_index().rename(columns={'county_26': 'county'})

ber_agg['pct_d_or_worse'] = (ber_agg['poor_ber_certs'] / ber_agg['total_ber_certs']) * 100
ber_agg['pct_oil_dependent'] = (ber_agg['total_oil_heating'] / ber_agg['total_ber_certs']) * 100

# 2. CSO MEC03 2024 Residential Consumption
mec = pd.read_csv('data/raw/cso_mec03_raw.csv')
mec_res = mec[(mec['Sector'] == '10 Residential') & (mec['Year'] == 2024)].copy()

def map_mec_county(name):
    name_str = str(name).strip()
    if 'Dublin' in name_str:
        return 'Dublin'
    if name_str.startswith('Co. '):
        return name_str.replace('Co. ', '').strip().capitalize()
    return name_str.capitalize()

mec_res = mec_res[~mec_res['Counties & Dublin Postal Districts'].isin(['All Counties and Dublin Postal Districts', 'Not coded'])]
mec_res['county_26'] = mec_res['Counties & Dublin Postal Districts'].apply(map_mec_county)
mec_agg = mec_res.groupby('county_26')['VALUE'].sum().reset_index().rename(columns={'county_26': 'county', 'VALUE': 'residential_gwh'})

# 3. CSO TEM27 2025 BEV Share of New Car Registrations
tem = pd.read_csv('data/raw/cso_tem27_raw.csv')
tem_new = tem[
    (tem['Statistic Label'] == 'New Private Cars') & 
    (tem['Licensing Authority'] != 'All licensing authorities') &
    (tem['Month'].str.contains('2025'))
]
bev = tem_new[tem_new['Type of Fuel'] == 'Electric'].groupby('Licensing Authority')['VALUE'].sum().rename('bev_count')
all_fuel = tem_new[tem_new['Type of Fuel'] == 'All fuel types'].groupby('Licensing Authority')['VALUE'].sum().rename('total_new_cars')
tem_agg = pd.concat([bev, all_fuel], axis=1).reset_index().rename(columns={'Licensing Authority': 'county'})
tem_agg['county'] = tem_agg['county'].str.strip().str.capitalize()
tem_agg['bev_share_new_cars_pct'] = (tem_agg['bev_count'] / tem_agg['total_new_cars']) * 100

# 4. CSO Census 2022 Private Households
cso_hh = pd.read_csv('data/raw/cso_census2022_households_raw.csv')

# Merge all 4
ie_prop = ber_agg.merge(mec_agg, on='county', how='inner')
ie_prop = ie_prop.merge(tem_agg[['county', 'bev_count', 'total_new_cars', 'bev_share_new_cars_pct']], on='county', how='inner')
ie_prop = ie_prop.merge(cso_hh, on='county', how='inner')

# Recompute kWh per dwelling using Census 2022 private households
ie_prop['residential_kwh_per_dwelling'] = (ie_prop['residential_gwh'] * 1_000_000) / ie_prop['cso_private_households']

# Min-max normalization
def min_max(s):
    return (s - s.min()) / (s.max() - s.min())

ie_prop['norm_inefficiency'] = min_max(ie_prop['pct_d_or_worse'])
ie_prop['norm_oil'] = min_max(ie_prop['pct_oil_dependent'])
ie_prop['norm_consumption'] = min_max(ie_prop['residential_kwh_per_dwelling'])
ie_prop['norm_bev'] = min_max(ie_prop['bev_share_new_cars_pct'])

# Score: 35% thermal inefficiency, 35% oil dependence, 15% grid load intensity, 15% EV transition momentum
ie_prop['retrofit_propensity_score'] = (
    0.35 * ie_prop['norm_inefficiency'] +
    0.35 * ie_prop['norm_oil'] +
    0.15 * ie_prop['norm_consumption'] +
    0.15 * ie_prop['norm_bev']
) * 100

# 4 balanced tiers
ie_prop['propensity_tier'] = pd.qcut(
    ie_prop['retrofit_propensity_score'], 
    q=4, 
    labels=['Low', 'Moderate', 'High', 'Prime Target']
)

ie_prop = ie_prop.sort_values('retrofit_propensity_score', ascending=False).reset_index(drop=True)

print("=== RECOMPUTED 26-COUNTY RETROFIT PROPENSITY TABLE ===")
cols_to_print = ['county', 'cso_private_households', 'residential_gwh', 'residential_kwh_per_dwelling', 'pct_d_or_worse', 'pct_oil_dependent', 'bev_share_new_cars_pct', 'retrofit_propensity_score', 'propensity_tier']
print(ie_prop[cols_to_print].to_string())

print("\n--- Summary by Tier ---")
print(ie_prop.groupby('propensity_tier').agg({
    'county': 'count',
    'retrofit_propensity_score': ['min', 'max', 'mean'],
    'residential_kwh_per_dwelling': 'mean',
    'pct_oil_dependent': 'mean'
}))

print("\nTop 5 Counties:")
for i, r in ie_prop.head(5).iterrows():
    print(f"  {r['county']}: Score = {r['retrofit_propensity_score']:.2f}, Tier = {r['propensity_tier']}, kWh/dwelling = {r['residential_kwh_per_dwelling']:.0f}, Oil% = {r['pct_oil_dependent']:.1f}%, D+ = {r['pct_d_or_worse']:.1f}%")

print("\nBottom 5 Counties:")
for i, r in ie_prop.tail(5).iterrows():
    print(f"  {r['county']}: Score = {r['retrofit_propensity_score']:.2f}, Tier = {r['propensity_tier']}, kWh/dwelling = {r['residential_kwh_per_dwelling']:.0f}, Oil% = {r['pct_oil_dependent']:.1f}%, D+ = {r['pct_d_or_worse']:.1f}%")
