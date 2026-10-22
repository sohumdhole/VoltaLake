# VoltaLake: Enterprise GDPR Compliance & Data Protection Framework

## 1. Regulatory Context & Legal Basis
As a multi-jurisdictional analytics lakehouse handling smart metering profiles and household energy data across **Ireland (under GDPR / Data Protection Act 2018)** and **Great Britain (under UK GDPR / Data Protection Act 2018)**, VoltaLake operates under a strict **Data Protection by Design and by Default** mandate (GDPR Article 25).

While the data utilised in VoltaLake is derived from open public releases and anonymised smart-meter trials, the pipeline applies **personal-data safeguards (pseudonymisation, masking and access controls)** of the kind used in production customer data systems.

---

## 2. Technical Safeguards & Cryptographic Controls

### 2.1 Salted Cryptographic Pseudonymisation (GDPR Article 4(5) & Recital 26)
Under European Data Protection Board (EDPB) guidance, simple unsalted hashing (such as standard MD5 or SHA-1) does not constitute robust pseudonymisation because rainbow-table and frequency-analysis attacks can re-identify original account identifiers or MPRN/MPAN meter points.

**VoltaLake Implementation:**
- All raw household identifiers (`LCLid`, MPRN references) are transformed in the Silver layer using **SHA-256 combined with a high-entropy enterprise salt**:
  $$\text{Masked ID} = \text{SHA256}(\text{Raw Identifier} \parallel \text{Secret Enterprise Salt})[0:16]$$
- **Salt Management:** The salt is managed via Databricks Secrets (`dbutils.secrets.get(scope="gdpr", key="salt")`) and Azure Key Vault / AWS Secrets Manager in production, completely isolated from analyst query logs.
- **Irreversibility:** Downstream analysts, BI dashboards, and MLflow models only ever interact with `household_id_masked`. The raw mapping table is stored in a restricted, audited Unity Catalog schema accessible solely by the designated Data Protection Officer (DPO).

---

### 2.2 Unity Catalog Dynamic Column Masking
Instead of duplicating data into redacting views, Unity Catalog enforces column-level redaction natively at SQL query compilation time based on the active user's identity and group membership:

```sql
-- Dynamic Column Masking Policy
CREATE OR REPLACE FUNCTION voltalake.silver.mask_household_id(id_val STRING)
RETURN CASE 
  -- DPO / Admin sees complete pseudonym
  WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_dpo_admin') THEN id_val
  -- Analytics team sees truncated token
  WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_analytics_team') THEN CONCAT('PSEUDO-', SUBSTR(id_val, 1, 8))
  -- All other non-technical stakeholders see REDACTED
  ELSE 'REDACTED-GDPR'
END;

ALTER TABLE voltalake.silver.silver_london_smart_meters 
ALTER COLUMN household_id_masked SET MASK voltalake.silver.mask_household_id;
```

---

### 2.3 Unity Catalog Row-Level Security (RLS) & Jurisdiction Isolation
To enforce jurisdictional governance and prevent cross-border data leakage between Irish retail operations and GB teams, Row Filters are applied at the storage engine level:

```sql
-- Jurisdiction Row Filter
CREATE OR REPLACE FUNCTION voltalake.silver.filter_jurisdiction_access(jurisdiction STRING)
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_exec_global') THEN TRUE
  WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_ireland_specialist') AND jurisdiction = 'IE' THEN TRUE
  WHEN IS_ACCOUNT_GROUP_MEMBER('voltalake_gb_analyst') AND jurisdiction = 'GB' THEN TRUE
  ELSE FALSE
END;

ALTER TABLE voltalake.silver.silver_cso_metered_consumption 
SET ROW FILTER voltalake.silver.filter_jurisdiction_access ON (_jurisdiction);
```

---

## 3. Data Subject Rights & Operational Procedures

### 3.1 Right to Erasure / "Right to be Forgotten" (RTBF - GDPR Article 17)
In traditional data lakes, honoring a deletion request requires expensive full-table rewrites or leaves tombstoned records in parquet files. 
In VoltaLake:
1. **Delta Lake Change Data Feed (CDF):** Enabled on all Silver and Gold tables (`ALTER TABLE ... SET TBLPROPERTIES (delta.enableChangeDataFeed = true)`).
2. **Targeted Partition Deletion:** When a valid deletion request is verified by the DPO, a script executes:
   ```sql
   DELETE FROM voltalake.gold.fact_household_load 
   WHERE household_id_masked = :pseudonym_hash;
   ```
3. **Vacuuming Physical Parquet Files:** `VACUUM voltalake.gold.fact_household_load RETAIN 0 HOURS` permanently purges physical parquet files from cloud storage, satisfying cryptographic erasure audits.

### 3.2 Audit Logging & Access Traceability
Every access, query, and column mask evaluation is logged automatically by **Unity Catalog System Tables** (`system.access.audit`). The audit logs record:
- User email and client IP address
- Timestamp and execution duration
- Exact SQL text and catalog/table/column access vectors
- Access decision (`ALLOWED` / `DENIED`)
