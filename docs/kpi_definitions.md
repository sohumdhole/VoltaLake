# VoltaLake: Verified KPI Definitions & Mathematical Formulations
### Unified Metrics Dictionary for Ireland & Great Britain Energy Intelligence
*(Audited & Verified Implementation — Zero-Fabrication Standard)*

Every mathematical definition, formula, unit of measure, and data source in this document reflects executed code from real public records or cited regulatory reports.

---

## 1. Regulatory Switching & Churn Proxy Metrics

### A. Annual Customer Switching Rate (%)
* **Definition:** Percentage of active electricity meter points transferring between licensed energy suppliers over a calendar year.
* **Operational Formula:**
  $$\text{Switching Rate} = \left( \frac{\sum \text{Completed Electricity Meter Switches}}{\text{Average Customer Base}} \right) \times 100$$
* **Data Sources & Citations:**
  * **Ireland:** Commission for Regulation of Utilities (CRU) Annual Energy Monitoring Reports.
    * **2021:** **16.68%** (358,267 switches / ~2,147,884 customer base) [*CRU Energy Monitoring Report for 2022 (CRU202389), p.15, p.16*].
    * **2022 (Like-for-like):** **16.57%** (418,597 switches / ~2,526,234 customer base) [*CRU Energy Monitoring Report for 2023 (CRU2024132), p.15*].
      * *Report Method Comparison:* In the previous 2022 report (*CRU202389, p.16*), the figure published was **19.51%** (418,595 switches / ~2,145,541 base) under that report's earlier method. The 2022 Executive Summary (p.3, p.15) also cited **16.85%**, which Footnote 1 defined as "calculated by dividing the total amount of customers by the total amount of completed switches" (defining the calculation method, not a domestic subset). In VoltaLake's conformed gold table (`fact_market_switching`), we use the like-for-like pair from CRU2024132 p.15 (16.57% in 2022 → 11.67% in 2023) for consistent trend analysis, while explicitly labeling 19.51% as the 2022 report's own figure.
    * **2023:** **11.67%** (294,669 switches / ~2,525,013 customer base) [*CRU Energy Monitoring Report for 2023 (CRU2024132), p.15*].
      * *Rounding Note:* Executive Summary p.3 and p.14 round this figure to **12%**. The unrounded calculation based on total completed switches reported on p.15 is **11.67%**. Switching volume fell 29% from 2022 (418,597) to 2023 (294,669).
    * *Historical Note on 2018–2020:* Annual rows for 2018, 2019, and 2020 have been removed under VoltaLake's zero-fabrication standard, as exact full-year switching numbers and customer counts for those years are not published in verified tabular form in CRU202389 or CRU2024132.
  * **Great Britain:** UK Department for Energy Security and Net Zero (DESNZ) Table 2.7.1 (Quarterly Energy Prices, Electricity Transfers).
    * 2018: 19.06% (5,402,000 switches / 28,335,500 base)
    * 2019: 20.82% (5,946,000 switches / 28,556,000 base)
    * 2020: 20.22% (5,812,000 switches / 28,748,750 base)
    * 2021: 15.57% (4,502,000 switches / 28,916,250 base)
    * 2022: 3.06% (893,000 switches / 29,224,250 base) [Energy crisis collapse under Energy Price Guarantee]
    * 2023: 6.33% (1,867,000 switches / 29,486,750 base)
    * 2024: 9.03% (2,681,000 switches / 29,695,000 base)
* **Limitation:** Regulated switching rates measure total inter-supplier mobility across the market, serving as an external churn velocity benchmark rather than an internal cohort survival curve.

### B. In-Contract Renegotiation Rate (%)
* **Definition:** Percentage of customers negotiating a new contract term, discounted tariff, or fixed loyalty package with their incumbent supplier without transferring to an external competitor.
* **Scope Clarification:** The **21% renegotiation figure covers ALL electricity customers (both domestic and non-domestic)**, not just domestic [*CRU202389, p.3, p.15; CRU2024132, p.3, p.14*].
* **Empirical Values (CRU Official Reports):**
  * **2022:** **21%** of all electricity customers (and 21% of gas customers) renegotiated with their current supplier [*CRU202389, p.3, p.15*].
  * **2023:** **21%** of all electricity customers (and 26% of gas customers) renegotiated with their current supplier [*CRU2024132, p.3, p.14*].
* **Combined Customer Engagement:** In 2023, **33% of all electricity customers** actively looked for a better plan through either switching supplier (11.67%, rounded to 12% in executive summary) or renegotiating with their current supplier (21%) [*CRU2024132, p.3, p.14, p.18*].

---

## 2. Clean Energy & Retrofit Propensity Index (Ireland)

### A. Geographical Coverage
Conformed across **exactly the 26 administrative counties of Ireland** (merging Dublin City, Dún Laoghaire-Rathdown, Fingal, and South Dublin into Dublin; merging city and county local authorities for Cork, Galway, Limerick, and Waterford). Zero imputation applied.

### B. Index Formula & Weights
The index combines thermal need, fossil fuel displacement opportunity, baseline electricity demand, and clean technology adoption:

$$\text{Score} = \left( 0.35 \times \tilde{I}_{\text{thermal}} + 0.35 \times \tilde{O}_{\text{oil}} + 0.15 \times \tilde{C}_{\text{dwelling}} + 0.15 \times \tilde{E}_{\text{bev}} \right) \times 100$$

Where each component is Min-Max normalized across the 26 counties:
$$\tilde{X} = \frac{X - X_{\min}}{X_{\max} - X_{\min}}$$

1. **Thermal Inefficiency Share ($\tilde{I}_{\text{thermal}}$):**  
   $$\text{pct\_d\_or\_worse} = \frac{\text{D1, D2, E1, E2, F, G Certificates}}{\text{Total Registered Certificates}} \times 100$$  
   *Source:* Hugging Face mirror of SEAI National BER Research Tool (1.45M certs conformed to 26 counties). Range: 19.72% (Meath) to 41.76% (Leitrim).
2. **Oil Heating Dependence Share ($\tilde{O}_{\text{oil}}$):**  
   $$\text{pct\_oil\_dependent} = \frac{\text{Heating Oil / Kerosene Primary Systems}}{\text{Total Registered Certificates}} \times 100$$  
   *Source:* Hugging Face mirror of SEAI National BER Research Tool. Range: 5.55% (Dublin) to 70.01% (Donegal).
3. **Residential Consumption per Dwelling ($\tilde{C}_{\text{dwelling}}$):**  
   $$\text{residential\_kwh\_per\_dwelling} = \frac{\text{CSO MEC03 Sector 10 Residential GWh} \times 1,000,000}{\text{CSO Census 2022 Private Households (PxStat Table FY004B)}}$$  
   *Source:* CSO Table MEC03 (2024, Sector '10 Residential') divided by CSO Census 2022 Private Households from Table FY004B (State total: 1,841,152 households). Range: 4,074 kWh/dwelling (Roscommon) to 5,603 kWh/dwelling (Westmeath).
4. **2025 BEV Share of New Car Registrations ($\tilde{E}_{\text{bev}}$):**  
   $$\text{bev\_share\_new\_cars\_pct} = \frac{\text{Electric (BEV) New Private Cars}}{\text{All Fuel Types New Private Cars}} \times 100$$  
   *Source:* CSO Table TEM27 (Calendar Year 2025, Statistic Label 'New Private Cars', excluding 'All licensing authorities'). Range: 5.04% (Roscommon) to 27.72% (Wicklow).

### C. 26-County Propensity Quartile Tiers (Recomputed with Census 2022 Denominator)
* **Prime Target (7 counties, Scores 72.7–84.8):** Tipperary (84.75), Mayo (79.84), Kerry (77.91), Donegal (76.87), Leitrim (76.68), Westmeath (73.94), Monaghan (72.68).
* **High (6 counties, Scores 68.5–72.6):** Wexford (72.61), Sligo (71.36), Longford (71.25), Clare (68.56), Cavan (68.52), Offaly (68.51).
* **Moderate (6 counties, Scores 53.7–66.7):** Galway (66.67), Roscommon (66.16), Carlow (60.61), Limerick (57.77), Kilkenny (57.21), Waterford (53.67).
* **Low (7 counties, Scores 29.4–52.7):** Wicklow (52.68), Cork (48.77), Laois (48.30), Louth (40.96), Kildare (39.01), Meath (37.11), Dublin (29.39).

---

## 3. Customer Load Segmentation & Difference-in-Differences Experiment

### A. Outlier-Aware Normalised Load-Shape Clustering (London Smart Meters)
* **Dataset:** UK Power Networks Low Carbon London trial (2.05M half-hourly records across 63 households).
* **Normalization:** 48 half-hour interval consumption values divided by total daily consumption $\sum_{t=1}^{48} x_{it} = 1.0$ (isolating shape from volume).
* **Data Hygiene & Outlier Quarantine:** 5 anomalous meters (`MAC000991`, `MAC000032`, `MAC000034`, `MAC000003`, `MAC000025`, representing 7.9% of sample) exhibiting unphysical single-interval spikes or extreme midnight anomalies were routed to the Lakehouse quarantine table, leaving 58 valid households for segmentation.
* **Cluster Validation on Valid Sample ($n=58$):**
  * $k=2$: Silhouette = 0.1756, Davies-Bouldin = 1.8895 (counts: 35, 23)
  * **$k=3$ (Selected): Silhouette = 0.1773, Davies-Bouldin = 1.5744**
    * *Structure Note:* The silhouette score of 0.18 indicates weak cluster structure, so segments are exploratory. $k=3$ was selected to provide balanced exploratory personas without sub-5% singletons:
    * **Cluster 1 (Dual-Peak Residential Consumer):** 32 households (**55.17%**). Evening peak load of 0.261 kWh/hh vs 0.162 kWh/hh off-peak (peak-to-offpeak ratio 1.61). Exploratory Target: Dynamic Time-of-Use Tariff & Smart Appliance Automation.
    * **Cluster 0 (High-Baseload Continuous Consumer):** 19 households (**32.76%**). Mean load 0.309 kWh/hh, elevated night baseline 0.254 kWh/hh (day-to-night ratio 1.29). Exploratory Target: Baseload Efficiency Audit & Home Battery Storage.
    * **Cluster 2 (Daytime-Active Household):** 7 households (**12.07%**). Daytime consumption 0.237 kWh/hh vs night 0.082 kWh/hh (day-to-night ratio 2.89). Exploratory Target: Solar PV & Daytime Clean Self-Consumption Export.
  * $k=4$: Silhouette = 0.1662, Davies-Bouldin = 1.4678 (counts: 25, 15, 11, 7)
* *Persona Threshold Rule:* Every segmented cluster represents at least 12.07% of valid households, strictly satisfying the requirement that no cluster smaller than ~5% is designated as a commercial persona.

### B. Difference-in-Differences (DiD) Econometric Evaluation
* **Hypothesis:** Did enrollment in the Low Carbon London voluntary Time-of-Use (ToU) dynamic tariff cause a statistically significant reduction in 4 PM – 8 PM peak demand compared to flat Standard (Std) tariffs between 2012 (pre-intervention) and 2013 (post-intervention)?
* **Model Formulation:**
  $$\Delta \text{Peak}_{i} = \text{Peak}_{i, 2013} - \text{Peak}_{i, 2012}$$
  $$\text{DiD} = \overline{\Delta \text{Peak}}_{\text{ToU}} - \overline{\Delta \text{Peak}}_{\text{Std}}$$
* **Empirical Execution Results ($n=61$ paired households):**
  * **Control Group (Std, $n=29$):** Pre (2012) = 0.2759 kWh/hh, Post (2013) = 0.2580 kWh/hh, Delta = -0.0179 kWh/hh.
  * **Treatment Group (ToU, $n=32$):** Pre (2012) = 0.2784 kWh/hh, Post (2013) = 0.2773 kWh/hh, Delta = -0.0010 kWh/hh.
  * **DiD Effect:** $+0.0169\text{ kWh/hh}$ per half-hour.
  * **Welch Two-Sample t-Test:** $t = 1.4170$, $p = 0.1623$, Degrees of Freedom = 53.06, Cohen's $d = +0.3676$.
  * **95% Confidence Interval:** $[-0.0070, +0.0407]\text{ kWh/hh}$.
  * **Finding:** Found no statistically significant peak reduction in this 61-household sample ($p = 0.1623$; 95% CI $[-0.0070, +0.0407]$ includes small reductions).
  * **Commercial Hypothesis to Test:** Voluntary behavioral price signals alone may fail to produce peak demand clipping; future trials could test the hypothesis that achieving peak shifting requires automated hardware (smart EV chargers, automated heat pump thermostats, home battery storage).

---

## 4. Commercial Campaign Economics & CAC/LTV Model

### A. Reach Formula
$$\text{Contacts Reached} = \left\lfloor \frac{\text{Marketing Spend (€)}}{\text{Cost per Targeted Contact (€)}} \right\rfloor$$
* At €100,000 spend and €5.50 cost per contact:
  $$\text{Contacts Reached} = \left\lfloor \frac{100,000}{5.50} \right\rfloor = 18,181\text{ contacts}$$

### B. Acquisition & CPA Formula
$$\text{Customers Acquired} = \lfloor \text{Contacts Reached} \times \text{Conversion Rate} \rfloor$$
$$\text{CPA} = \frac{\text{Marketing Spend (€)}}{\text{Customers Acquired}}$$
* At baseline 3.5% conversion rate:
  * Customers Acquired = $\lfloor 18,181 \times 0.035 \rfloor = 636\text{ customers}$
  * Cost per Acquisition (CPA) = $\frac{€100,000}{636} = €157.23$

### C. Composite Customer Lifetime Value (LTV) Formula
$$\text{Composite LTV} = \text{Base Electricity LTV} + (\text{Dual-Fuel Share} \times \text{Dual-Fuel Uplift}) - \text{Annual Service Cost} + \text{Green Margin}$$
* Parameter Values:
  * Base electricity gross margin (3-year horizon): €525.00
  * Dual-fuel uptake (70% probability $\times$ €400 gas margin uplift): €280.00
  * Customer service and billing overhead: -€40.00
  * Green premium tariff margin: +€70.50
  * **Composite LTV:** €835.50

### D. Net Campaign ROI & Break-Even Conversion Rate
$$\text{Total Gross LTV Revenue} = 636 \times €835.50 = €531,378.00$$
$$\text{Net Profit} = €531,378.00 - €100,000.00 = €431,378.00$$
$$\text{Net Campaign ROI} = \left( \frac{€431,378.00}{€100,000.00} \right) \times 100 = 431.4\%$$
$$\text{Break-Even Conversion Rate} = \frac{\text{Marketing Spend}}{\text{Contacts Reached} \times \text{Composite LTV}} = \frac{€100,000}{18,181 \times €835.50} = 0.658\%$$
