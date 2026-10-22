import urllib.request
import json
import itertools
import pandas as pd

url = 'https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/FY004B/JSON-stat/2.0/en'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

dims = data['id']
size = data['size']
dim_categories = {}
for d in dims:
    cat = data['dimension'][d]['category']
    lbl = cat['label']
    if isinstance(lbl, dict):
        dim_categories[d] = list(lbl.values())
    else:
        dim_categories[d] = list(lbl)

records = list(itertools.product(*[dim_categories[d] for d in dims]))
cso_df = pd.DataFrame(records, columns=dims)
cso_df['value'] = data['value']

c2022 = cso_df[(cso_df['TLIST(A1)'] == '2022') & (cso_df['STATISTIC'] == 'Private households')].copy()
c2022 = c2022[c2022['C04104V04868'] != 'State'].copy()

def map_cso_county(geo):
    g = str(geo).strip()
    if any(x in g.lower() for x in ['dublin', 'fingal', 'laoghaire']):
        return 'Dublin'
    if 'galway' in g.lower():
        return 'Galway'
    if 'cork' in g.lower():
        return 'Cork'
    if 'limerick' in g.lower():
        return 'Limerick'
    if 'waterford' in g.lower():
        return 'Waterford'
    return g

c2022['county'] = c2022['C04104V04868'].apply(map_cso_county)
county_hh = c2022.groupby('county')['value'].sum().reset_index().rename(columns={'value': 'cso_private_households'})
county_hh['cso_private_households'] = county_hh['cso_private_households'].astype(int)
print(f"Total counties: {len(county_hh)}, Total households: {county_hh['cso_private_households'].sum():,}")
print(county_hh.to_string())

county_hh.to_csv('data/raw/cso_census2022_households_raw.csv', index=False)
