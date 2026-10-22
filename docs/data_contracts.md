# VoltaLake: Data Contracts & Upstream Ingestion SLAs

## 1. Principles of Data Contracts in VoltaLake
In an enterprise multi-jurisdictional lakehouse serving commercial propositions, regulatory compliance, and executive dashboards, upstream changes cannot be allowed to silently corrupt downstream metrics. Data contracts define:
1. **Schema Assertions:** Exact column names, data types, and permitted value ranges.
2. **Freshness SLAs:** Tolerable publication and ingestion latency per regulatory cadence.
3. **Quarantine Routing Protocol:** How violating records are isolated without breaking batch or streaming pipelines.
4. **Breaking Change Lifecycle:** Deprecation policies and automated alert escalations.

---

## 2. Upstream Source System Specifications & SLAs

| Source System | Jurisdiction | Cadence | SLA Freshness | Transport / Format | Upstream Publisher | Breaking Change Risk |
|---|---|---|---|---|---|---|
| **CSO Table MEC03** | Ireland (`IE`) | Annual (July) | 180 Days | REST API (JSON-stat / CSV) | Central Statistics Office (CSO) | Low (Stable PxStat API) |
| **CSO Table TEM27** | Ireland (`IE`) | Monthly | 45 Days | REST API (CSV / JSON-stat) | Central Statistics Office (CSO) | Low |
| **SEAI BER Research Tool** | Ireland (`IE`) | Quarterly | 90 Days | Parquet (Hugging Face mirror of SEAI data) | Sustainable Energy Authority of Ireland / Open Data | Medium (Bulk Parquet schema updates) |
| **CRU Retail Market Reports** | Ireland (`IE`) | Quarterly / Annual | 90 Days | PDF / Tables on divio-media | Commission for Regulation of Utilities | High (Layout variations in published PDFs) |
| **DESNZ LA Electricity** | GB (`GB`) | Annual (December) | 180 Days | Stacked CSV via GOV.UK | Dept for Energy Security & Net Zero | Low (Standard stacked CSV structure) |
| **DESNZ Table 2.7.1** | GB (`GB`) | Quarterly | 60 Days | Formatted XLSX via GOV.UK | Dept for Energy Security & Net Zero (DESNZ) | Medium (Header row shifts in spreadsheet releases) |
| **Low Carbon London Smart Meters** | GB (`GB`) | Benchmark Archive | Standing | Partitioned CSV / TsFile | UK Power Networks / London Datastore | Minimal (Static historical benchmark) |

---

## 3. Schema Expectations & Quarantine Routing Matrix

All data arriving in the `bronze` landing zone is evaluated against explicit expectation rules during the Lakeflow Declarative Pipeline execution. Violations are routed to dedicated quarantine tables (`silver.quarantine_*`).

### Contract 1: SEAI Building Energy Ratings (`bronze.raw_seai_ber_certificates`)
- **Rule 1.1 (`valid_energy_rating`):** `energyrating RLIKE '^[A-G][0-9]?$'`
  - *Violation Action:* Route to `silver.quarantine_seai_ber`. Reason: Null or unrecognised certificate rating prevents thermal segmentation.
- **Rule 1.2 (`valid_floor_area`):** `groundfloorarea > 10.0 AND groundfloorarea < 1500.0`
  - *Violation Action:* Route to quarantine. Reason: Floor areas $\le 10\,m^2$ or $\ge 1,500\,m^2$ represent data-entry errors or non-domestic structures.
- **Rule 1.3 (`valid_numeric_ber`):** `berrating > 0.0 AND berrating < 2000.0`
  - *Violation Action:* Route to quarantine. Reason: Numeric energy values $\le 0$ violate thermodynamic laws; values $> 2,000\,kWh/m^2/yr$ represent erroneous meter readings.
- **Rule 1.4 (`valid_construction_year`):** `year_of_construction >= 1800 AND year_of_construction <= 2026`
  - *Violation Action:* Route to quarantine. Reason: Erroneous default years (e.g. `1900` or `9999`).

### Contract 2: Metered Consumption (`bronze.raw_cso_metered_electricity`)
- **Rule 2.1 (`non_negative_consumption`):** `VALUE >= 0.0`
  - *Violation Action:* Route to `silver.quarantine_cso`. Reason: Metered electricity consumption cannot be negative.
- **Rule 2.2 (`reasonable_county_volume`):** `VALUE < 50000.0` (in GWh)
  - *Violation Action:* Route to quarantine. Reason: Any single county exceeding 50,000 GWh represents an upstream unit multiplier error (e.g., reporting in MWh or kWh instead of GWh).

### Contract 3: Smart Meter Load Profiles (`bronze.raw_london_smart_meters`)
- **Rule 3.1 (`valid_half_hour_consumption`):** `consumption_kwh_hh >= 0.0 AND consumption_kwh_hh < 15.0`
  - *Violation Action:* Route to `silver.quarantine_smart_meters`. Reason: A domestic single-phase smart meter exceeding $15\,kWh$ in a single 30-minute window ($>30\,kW$ continuous demand) indicates a CT meter multiplier error or short-circuit anomaly.
- **Rule 3.2 (`valid_interval_range`):** `half_hour_interval BETWEEN 0 AND 47`
  - *Violation Action:* Route to quarantine. Reason: Timestamps mapping outside standard 48 half-hour daily intervals indicate corrupted timezone conversions.

---

## 4. Breaking Change Protocol & Schema Evolution
1. **Schema Evolution Mode (`addNewColumns`):**
   - Auto Loader is configured with `.option("cloudFiles.schemaEvolutionMode", "addNewColumns")`.
   - New non-breaking attributes arriving from upstream open datasets are automatically appended to the bronze table schema.
2. **Breaking Schema Changes (Dropped Columns / Renamed Keys):**
   - If a primary key (`LCLid`, `countyname`, `Year`) is omitted, Auto Loader triggers a pipeline alert and halts downstream silver updates.
   - The alert routes immediately to the Data Engineering team via PagerDuty / Webhook (`data-alerts@example.com`).
3. **Quarantine Error Budget & Circuit Breaker:**
   - If the quarantine failure rate for any dataset exceeds **5.0%** of total batch volume, Lakeflow halts promotion to Gold and triggers an automated circuit breaker.
