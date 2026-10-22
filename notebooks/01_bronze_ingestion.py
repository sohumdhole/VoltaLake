# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # VoltaLake: 01 - Bronze Ingestion Layer
# MAGIC **Catalog:** `voltalake` | **Schema:** `bronze`
# MAGIC 
# MAGIC ### Purpose & Production Design
# MAGIC Sourcing raw, multi-jurisdiction public energy data for Ireland (`IE`) and Great Britain (`GB`).
# MAGIC - Ingestion mechanism: Auto Loader (`cloudFiles`) and `COPY INTO` from Unity Catalog Volumes (`/Volumes/voltalake/bronze/landing_zone/`).
# MAGIC - Raw immutability: Raw files are stored verbatim in their native formats without lossy conversion.
# MAGIC - Standard Audit Metadata: Every record receives `_source_file`, `_ingested_at`, `_source_system`, and `_jurisdiction`.
# MAGIC 
# MAGIC ### Interview Defense: Architectural Decisions
# MAGIC 1. **Why Auto Loader over standard batch streaming?** Auto Loader provides schema inference, schema evolution (`addNewColumns`), and file notification mode on cloud storage volumes without maintaining directory state manifests manually.
# MAGIC 2. **Why UC Volumes instead of raw DBFS/S3 mount points?** DBFS mounts are deprecated in modern Databricks. UC Volumes enforce unified governance, IAM federation, and audit logging under Unity Catalog.

# COMMAND ----------
# Databricks Widgets / Parameterization
dbutils.widgets.text("environment", "prod", "Environment")
dbutils.widgets.text("catalog_name", "voltalake", "Unity Catalog Name")

CATALOG = dbutils.widgets.get("catalog_name")
SPARK = spark

# Ensure catalog and bronze schema exist
SPARK.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
SPARK.sql(f"USE CATALOG {CATALOG}")
SPARK.sql("CREATE SCHEMA IF NOT EXISTS bronze COMMENT 'Raw, immutable ingested data with audit metadata'")
SPARK.sql("CREATE VOLUME IF NOT EXISTS bronze.landing_zone COMMENT 'Landing volume for raw source files'")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Ingestion: Ireland CSO Table MEC03 (Metered Electricity Consumption)

# COMMAND ----------
from pyspark.sql.functions import current_timestamp, input_file_name, lit, col

cso_mec03_path = f"/Volumes/{CATALOG}/bronze/landing_zone/cso_mec03/"

# Auto Loader ingestion pattern
cso_mec03_stream = (
    SPARK.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", f"/Volumes/{CATALOG}/bronze/landing_zone/_checkpoints/cso_mec03_schema")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("header", "true")
    .load(cso_mec03_path)
    .withColumn("_source_file", input_file_name())
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_system", lit("CSO_PxStat_MEC03"))
    .withColumn("_jurisdiction", lit("IE"))
)

# In batch mode for serverless execution:
(
    cso_mec03_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"/Volumes/{CATALOG}/bronze/landing_zone/_checkpoints/cso_mec03_delta")
    .trigger(availableNow=True)
    .toTable("bronze.raw_cso_metered_electricity")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Ingestion: Ireland CSO Table TEM27 (Vehicle Licensing / EVs by County)

# COMMAND ----------
cso_tem27_path = f"/Volumes/{CATALOG}/bronze/landing_zone/cso_tem27/"

cso_tem27_stream = (
    SPARK.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", f"/Volumes/{CATALOG}/bronze/landing_zone/_checkpoints/cso_tem27_schema")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("header", "true")
    .load(cso_tem27_path)
    .withColumn("_source_file", input_file_name())
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_system", lit("CSO_PxStat_TEM27"))
    .withColumn("_jurisdiction", lit("IE"))
)

(
    cso_tem27_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"/Volumes/{CATALOG}/bronze/landing_zone/_checkpoints/cso_tem27_delta")
    .trigger(availableNow=True)
    .toTable("bronze.raw_cso_vehicle_licensing")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Ingestion: Ireland SEAI BER Research Tool (Building Energy Ratings)

# COMMAND ----------
seai_ber_path = f"/Volumes/{CATALOG}/bronze/landing_zone/seai_ber/"

# SEAI Parquet Ingestion (1.45M certificate records)
(
    SPARK.read
    .format("parquet")
    .load(seai_ber_path)
    .withColumn("_source_file", input_file_name())
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_system", lit("SEAI_National_BER_Research_Tool"))
    .withColumn("_jurisdiction", lit("IE"))
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("bronze.raw_seai_ber_certificates")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Ingestion: GB DESNZ Sub-national Local Authority Electricity

# COMMAND ----------
desnz_la_path = f"/Volumes/{CATALOG}/bronze/landing_zone/desnz_la_elec/"

(
    SPARK.read
    .format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .option("encoding", "latin1")
    .load(desnz_la_path)
    .withColumn("_source_file", input_file_name())
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_system", lit("DESNZ_Subnational_Electricity"))
    .withColumn("_jurisdiction", lit("GB"))
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("bronze.raw_desnz_la_electricity")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Ingestion: GB Ofgem / DESNZ Switching Statistics (Table 2.7.1)

# COMMAND ----------
ofgem_switching_path = f"/Volumes/{CATALOG}/bronze/landing_zone/ofgem_table_271/"

(
    SPARK.read
    .format("parquet")
    .load(ofgem_switching_path)
    .withColumn("_source_file", input_file_name())
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_system", lit("Ofgem_DESNZ_Table_271"))
    .withColumn("_jurisdiction", lit("GB"))
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("bronze.raw_ofgem_switching_quarterly")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Ingestion: London Smart Meter Trial (Low Carbon London)

# COMMAND ----------
lcl_smart_meters_path = f"/Volumes/{CATALOG}/bronze/landing_zone/london_smart_meters/"

# Multi-partition half-hourly ingestion with partition discovery
(
    SPARK.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", f"/Volumes/{CATALOG}/bronze/landing_zone/_checkpoints/lcl_schema")
    .option("header", "true")
    .load(lcl_smart_meters_path)
    .withColumn("_source_file", input_file_name())
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_system", lit("UK_Power_Networks_Low_Carbon_London"))
    .withColumn("_jurisdiction", lit("GB"))
    .writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"/Volumes/{CATALOG}/bronze/landing_zone/_checkpoints/lcl_delta")
    .trigger(availableNow=True)
    .toTable("bronze.raw_london_smart_meters")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ### Verification & Bronze Health Audit

# COMMAND ----------
tables = SPARK.sql("SHOW TABLES IN bronze").collect()
for t in tables:
    count = SPARK.table(f"bronze.{t.tableName}").count()
    print(f"Bronze Table: bronze.{t.tableName} | Record Count: {count:,}")
