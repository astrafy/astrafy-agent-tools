# Architecture & Model Organization

## Architecture & Layers

| Layer | Model | Prefix | Materialization | Naming | Description |
|-------|-------|--------|-----------------|--------|-------------|
| **Raw** | Seed | `seed_` | Table | `seed_<context>__<entity>` | dbt seeds |
| **Raw** | Raw Table | `raw_` | Table (managed) | `raw_<source>__<entity>` | Ingested tables |
| **Staging** | Snapshot | `snp_` | Snapshot (SCD2) | `snp_<entity>` | SCD2 history tracking (optional) |
| **Staging** | Staging | `stg_` | View | `stg_<source>__<entity>` | 1:1 cast + rename only |
| **Intermediate** | Intermediate | `int_` | View (default) | `int_<domain>__<entity>` | Optional transformation layer |
| **Datamart** | Dimension | `dim_` | Table | `dim_<entity>` | Dimension presentation |
| **Datamart** | Fact | `fct_` | Incremental / Table | `fct_<entity>` | Fact tables |
| **Datamart** | Bridge | `brg_` | Table | `brg_<entity1>_<entity2>` | N:M relationship PKs |
| **Datamart** | Mart | `mart_` | Table | `mart_<entity>` | Dims requiring fct computations (optional) |
| **Datamart** | Aggregate | `agg_` | Incremental / Table | `agg_<grain>_<entity>` | Re-grained facts (optional) |
| **Datamart** | Report | `rpt_` | Table / Incremental | `rpt_<dashboard>` | Dashboard-specific tables |
| **Datamart** | Rev ETL | `retl_` | Table / Incremental | `retl_<destination>_<purpose>` | Dumps data into external systems |
| **Datamart** | Utility | `util_` | Table | `util_<purpose>` | Date spines, calendars |

## Model Flow Rules

**Reference rules** (what each model type can query):

- `snp_` refs: `raw_`, `seed_` (optional layer - `stg_` can read `raw_`/`seed_` directly)
- `stg_` refs: `snp_`, or `raw_`/`seed_` directly if no snapshot exists
- `int_` refs: `stg_` (optional layer - datamart models can read `stg_` directly)
- `dim_`, `fct_`, `brg_` ref: `int_` or `stg_` directly
- `mart_`, `agg_` ref: `dim_`, `fct_`, `brg_` (both are optional - downstream models can skip them)
- `rpt_` refs: `mart_`, `agg_`, or `dim_`/`fct_`/`brg_` directly when no mart/agg is needed
- `retl_` refs: `mart_`, `agg_`
- `util_` can be joined by any `int_` or datamart model

## Folder Structure

```
seeds/seed_<context>__<entity>.csv
snapshots/<source_system>/snp_<entity>.sql
models/sources/<source_system>.yml # one YAML per source system
models/staging/<source_system>/stg_<source>__<entity>.{sql,yml}
models/intermediate/<source_system>/int_<source>__<entity>_prep.{sql,yml}
models/intermediate/<domain>/int_<domain>__<entity>.{sql,yml}
models/datamart/<domain>/{dim,fct}_<entity>.{sql,yml}
models/datamart/<domain>/brg_<entity1>_<entity2>.sql
models/datamart/<domain>/{mart_<entity>,agg_<grain>_<entity>,rpt_<dashboard>}.sql
models/datamart/<destination>/retl_<destination>_<purpose>.sql
models/utilities/util_<purpose>.{sql,yml}
tests/generic/<test_name>.sql
```
