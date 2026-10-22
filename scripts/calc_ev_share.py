import pandas as pd

df = pd.read_csv('data/raw/cso_tem27_raw.csv')

# Check 2025 months
m_2025 = [m for m in df['Month'].unique() if '2025' in str(m)]
print("2025 months (count = {}): {}".format(len(m_2025), sorted(m_2025)))

# Check 2024 months
m_2024 = [m for m in df['Month'].unique() if '2024' in str(m)]
print("2024 months (count = {}): {}".format(len(m_2024), sorted(m_2024)))

# Filter for:
# Statistic Label == 'New Private Cars'
# Denominator: Type of Fuel == 'All fuel types'
# Numerator: Type of Fuel == 'Electric' (BEV)
# Exclude Licensing Authority == 'All licensing authorities'
# Year 2025

df_new = df[
    (df['Statistic Label'] == 'New Private Cars') & 
    (df['Licensing Authority'] != 'All licensing authorities') &
    (df['Month'].str.contains('2025'))
]

# Aggregate across the 12 months of 2025
bev = df_new[df_new['Type of Fuel'] == 'Electric'].groupby('Licensing Authority')['VALUE'].sum().rename('bev_count')
all_fuel = df_new[df_new['Type of Fuel'] == 'All fuel types'].groupby('Licensing Authority')['VALUE'].sum().rename('total_new_cars')

res = pd.concat([bev, all_fuel], axis=1)
res['bev_share_new_cars_pct'] = (res['bev_count'] / res['total_new_cars']) * 100

print("\n--- 2025 BEV SHARE OF NEW CAR REGISTRATIONS BY LICENSING AUTHORITY ---")
print(res.sort_values('bev_share_new_cars_pct', ascending=False).to_string())
print(f"\nTotal licensing authorities: {len(res)}")
