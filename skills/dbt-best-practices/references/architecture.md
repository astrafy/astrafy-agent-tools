# Architecture & Model Organization

## Architecture & Layers

| Layer | Model | Prefix / Suffix | Materialization | Naming | Description |
|-------|-------|-----------------|-----------------|--------|-------------|
| **Raw** | Seed | `seed_` | Table | `seed_<context>__<entity>` | dbt seeds |
| **Raw** | Raw Table | `raw_` | Table (managed) | `raw_<source>__<entity>` | Ingested tables |
| **Staging** | Staging | `stg_` | View | `stg_<source>__<entity>` | 1:1 cast + rename only |
| **Staging** | Staging SCD2 | `stg_` + `_scd2` | Snapshot definition | `stg_<source>__<entity>_scd2` | SCD2 history tracking via dbt snapshot |
| **Intermediate** | Intermediate (prep) | `int_` | View (default) | `int_<source>__<entity>_<suffix>` | Source-specific prep (01_prep only) |
| **Intermediate** | Intermediate (post-prep) | `int_` | View (default) | `int_<entity>_<suffix>` | Cross-source or transformed (02_unioned and beyond) |
| **Datamart / 01_core** | Dimension | `dim_` | Table | `dim_<entity>` | Dimension presentation |
| **Datamart / 01_core** | Dimension SCD2 | `dim_` + `_scd2` | Table / Incremental | `dim_<entity>_scd2` | SCD2 dimension built from an `int_` model that consumes an upstream `stg_*_scd2` snapshot |
| **Datamart / 01_core** | Fact | `fct_` | Incremental / Table | `fct_<entity>` | Fact tables |
| **Datamart / 01_core** | Bridge | `brg_` | Table | `brg_<entity1>_<entity2>` | N:M relationship PKs |
| **Datamart / 01_core** | Utility | `util_` | Table | `util_<purpose>` | Date spines, calendars |
| **Datamart / 02_enriched** | Aggregate | `agg_` | Incremental / Table | `agg_<grain>_<entity>` | Re-grained facts |
| **Datamart / 02_enriched** | Wide | `wide_` | Table | `wide_<entity>` | Dimensions enriched with fact computations |
| **Datamart / 03_consumption** | Report | `rpt_` | Table / Incremental | `rpt_<dashboard>` | Dashboard-specific tables |
| **Datamart / 03_consumption** | Rev ETL | `retl_` | Table / Incremental | `retl_<destination>_<purpose>` | Dumps data into external systems |
| **Datamart / 03_consumption** | AI / ML | `ai_` | Table | `ai_<entity>` | Feature stores and ML-ready tables |
| **Datamart / 03_consumption** | Compliance | `comp_` | Table | `comp_<entity>` | Audit and compliance tables |
| **Datamart / 03_consumption** | Reconciliation | `rec_` | Table | `rec_<entity>` | Cross-source reconciliation checks |

## Model Flow Rules

**Reference rules** (what each model type can query):

- `stg_` refs: `raw_`, `seed_`
- `int_` refs: `stg_`, or `int_`
- `dim_`, `dim_*_scd2`, `fct_`, `brg_` ref: `int_` only (01_core — intermediate layer is mandatory)
- `wide_`, `agg_` ref: `dim_`, `fct_`, `brg_` (02_enriched — downstream models can skip this layer)
- `rpt_`, `retl_`, `ai_`, `comp_`, `rec_` ref: `wide_`, `agg_`, `dim_`, `fct_`, `brg_` (03_consumption)
- `util_` can be joined by any `int_` or datamart model

**Why `int_` only for 01_core?** FK surrogate keys are deterministic hashes of `record_source + natural_key` generated via `null_safe_surrogate_key` in the intermediate layer. Because the same natural key always produces the same sk_id, facts already carry correct dimension FK sk_ids without ever joining to the dimension. Integrity is verified by the `relationships` tests on the datamart FKs, not by joins. Do not "fix" a fact by joining to a `dim_` to pick up an sk_id — the sk_id is already there from intermediate.

## Department

A `<department>` is a **business department** — a logical grouping of related entities (e.g., `finance`, `human_resources`, `project_management`). Departments organize datamart folders so that related models live together. Choose department names based on business ownership, not source systems. Department subfolders are optional — models can live directly at the sub-layer root.

## Source Folders in Intermediate

`01_prep` models are organized by source system because they are source-specific by design. Later intermediate stages are source-agnostic and can live directly under the stage folder.

## Folder Structure

```
seeds/seed_<context>__<entity>.csv
models/sources/<source_system>.yml                                          # one YAML per source system
models/staging/<source_system>/stg_<source>__<entity>.{sql,yml}
snapshots/staging/<source_system>/stg_<source>__<entity>_scd2.sql           # SCD2 snapshot definition
snapshots/staging/<source_system>/stg_<source>__<entity>_scd2.yml           # optional snapshot properties/docs
models/intermediate/01_prep/<source>/int_<source>__<entity>_prep.{sql,yml}
models/intermediate/02_unioned/int_<entity>_unioned.{sql,yml}
models/intermediate/03_transformed/int_<entity>_<suffix>.{sql,yml}
models/intermediate/04_enriched/int_<entity>_enriched.{sql,yml}
models/datamart/01_core/<department>/{dim,fct,brg}_<entity>.{sql,yml}       # department subfolder optional
models/datamart/01_core/<department>/dim_<entity>_scd2.{sql,yml}            # SCD2 dimension
models/datamart/01_core/<department>/util_<purpose>.{sql,yml}
models/datamart/02_enriched/<department>/{agg_<grain>_<entity>,wide_<entity>}.{sql,yml}  # department subfolder optional
models/datamart/03_consumption/reporting/rpt_<dashboard>.{sql,yml}                           # purpose subfolder optional
models/datamart/03_consumption/reverse_etl/retl_<dest>_<purpose>.{sql,yml}
models/datamart/03_consumption/artificial_intelligence/ai_<entity>.{sql,yml}
models/datamart/03_consumption/compliance/comp_<entity>.{sql,yml}
models/datamart/03_consumption/data_reconciliation/rec_<entity>.{sql,yml}
tests/generic/<test_name>.sql
```

### 03_consumption suggested subfolders

These subfolders group consumption models by purpose. They are optional — models can also live at the `03_consumption/` root. These is a non-exhaustive list of recommended groups.

- `reporting/` — dashboard and BI report tables (`rpt_`)
- `reverse_etl/` — tables pushed to external systems (`retl_`)
- `artificial_intelligence/` — feature stores and ML-ready tables (`ai_`)
- `compliance/` — audit and compliance tables (`comp_`)
- `data_reconciliation/` — cross-source reconciliation checks (`rec_`)
