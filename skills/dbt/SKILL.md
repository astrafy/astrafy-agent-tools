---
name: dbt
description: >
  Data modeling and dbt style guide for Data Warehouses (BigQuery, Snowflake, etc.).
  Use this skill whenever the user asks to create, review, edit, or debug dbt models.
---

# dbt Data Modeling & Style Guide

Approach: **Kimball / dimensional modeling (star schema)**.

---

## 1. Architecture & Layers

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
| **Datamart** | Utility | `util_` | Table | `util_<purpose>` | Date spines, calendars |

## 2. Model Flow Rules

**Reference rules** (what each model type can query):

- `snp_` refs: `raw_`, `seed_` (optional layer - `stg_` can read `raw_`/`seed_` directly)
- `stg_` refs: `snp_`, or `raw_`/`seed_` directly if no snapshot exists
- `int_` refs: `stg_` (optional layer - datamart models can read `stg_` directly)
- `dim_`, `fct_`, `brg_` ref: `int_` or `stg_` directly
- `mart_`, `agg_` ref: `dim_`, `fct_`, `brg_` (both are optional - downstream models can skip them)
- `rpt_` refs: `mart_`, `agg_`, or `dim_`/`fct_`/`brg_` directly when no mart/agg is needed
- `util_` can be joined by any `int_` or datamart model

**Macro rules**:

- **Staging models** reference raw tables using `{{ source('<source_name>', '<table_name>') }}`. This is required for source freshness tracking and lineage.
- **All other models** reference upstream dbt models using `{{ ref('<model_name>') }}`.

**Key rules**:

- Use `{{ dbt_utils.generate_surrogate_key([...]) }}` when no natural key exists. Field ordering is part of the key contract — changing the order produces a different hash and breaks downstream joins.
- Staging is the **only** layer where renaming and casting of raw fields is allowed.
- When the intermediate layer is skipped, any source-specific fix logic that goes beyond renaming/casting belongs in the `dim_`/`fct_` model, not in staging.

**Config rules**:

- Do not define `materialization` or `tags` in the model file unless the value differs from the project default (`dbt_project.yml`).

## 3. Intermediate Layer Patterns

The intermediate layer is **optional**. Keep things simple — skip it when `stg_` feeds cleanly into datamart.

### Simple (most cases)

| Suffix | Purpose | Materialization |
|--------|---------|-----------------|
| `_prep` | Source-specific fixes (join, calc, filter) to conform one source before combining | View / Table / Incremental |
| `_unioned` | Stack prepared tables from different sources vertically | View |

**Rule**: `_prep` applies source-specific logic only. Cross-source business rules belong in `dim_`/`fct_` models.

### Advanced (use only when needed)

| Suffix | Purpose | Typical Destination | Materialization |
|--------|---------|---------------------|-----------------|
| `_prep` | Technical fixes: timezone, currency, unit conversion | Fact | View |
| `_enriched` | Adding columns/attributes to a main entity | Dimension | View / Table |
| `_joined` | Bringing concepts together (e.g., order lines + headers) | Fact | View / Table |
| `_pivoted` | Transposing rows to columns | Dimension | View / Table |
| `_unioned` | Stacking identical tables from different sources | Fact | View |
| `_agg` | Pre-aggregating to fix fan-outs before a join | Fact | Incremental / Table |
| `_double_entry` | Duplicating rows for debit/credit pairs (GL logic) | Fact | View |
| `_spine` | Joining to a date spine to fill missing days/gaps | Fact | View |

## 4. Materializations

**Rule: Storage is cheap, compute is expensive.**

| Layer | Default | When to Deviate |
|-------|---------|-----------------|
| **Staging** | View | Use `table`/`incremental` if source is expensive to process (e.g., single JSON column) |
| **Intermediate** | View | Use `table` when reused in multiple places; use `incremental` when downstream is incremental and window functions/grouping/complex joins block predicate pushdown |
| **Datamart** | Table | Use `incremental` for large `fct_` tables expensive to reprocess. |


## 5. BigQuery Optimization (Cost & Performance)

- **Partitioning:** For tables larger than 1 GB, always configure `partition_by` (usually by a date/timestamp column).
- **Clustering:** Always configure `cluster_by` on high-cardinality filter/join columns (e.g., `user_id`, `customer_id`).

## 6. Column Naming Conventions

| Type | Pattern | Examples | Notes |
|------|---------|----------|-------|
| Boolean | `is_*` / `has_*` / `can_*` | `is_active`, `has_purchased`, `can_edit` | Always verb prefix; avoid negatives (`is_active` not `is_not_active`) |
| Date | `*_date` | `order_date`, `signup_date` | `DATE` type (YYYY-MM-DD) |
| Timestamp | `*_at` | `created_at`, `loaded_at` | Use `TIMESTAMP` (UTC default). Non-UTC: suffix with tz (`created_at_pt`). Events: past-tense verb (`created_at`, `deleted_at`) |
| ID / Key | `*_id` | `customer_id`, `order_id` | PKs named `<entity>_id`. String data type unless performance requires otherwise |
| Amount / Metric | `*_amount` / `*_total` / `*_price` | `revenue_amount`, `total_tax` | Numeric currency/totals |
| Count | `*_count` | `login_count`, `order_count` | Integer counts |
| Categorical | `*_type` / `*_category` / `*_status` / `*_group` | `customer_type`, `order_status` | String fields for grouping/segmenting |
| Array | `[plural_noun]` | `tags`, `items` | BigQuery `REPEATED` fields |
| Struct | `*_details` / `*_record` | `customer_details`, `shipping_record` | BigQuery `STRUCT` fields |
| System / Audit | `_*` (leading underscore) | `_loaded_at`, `_dbt_updated_at` | Metadata, ELT sync timestamps, dbt audit columns |

### Units of Measure

When a column represents a unit, the unit **must** be a suffix: `duration_s`, `duration_ms`, `amount_usd`, `price_eur`, `weight_kg`, `size_bytes`.

### General Rules

- Models are **pluralized**: `dim_customers`, `fct_orders`
- Every model has a **primary key**
- All names in **snake_case**
- Use **consistent field names** across models: FK must match PK name (e.g., `customer_id` everywhere, not `user_id` or `cust_id`)
- Multiple FKs to same dim: prefix contextually (`sender_customer_id`, `receiver_customer_id`)
- **No abbreviations**: `customer` not `cust`, `orders` not `o`
- **No SQL reserved words** standalone: `order_date` not `date`
- Model versions: `_v1`, `_v2` suffix
- **Column ordering**: system/audit, ids, dates, timestamps, booleans, strings, arrays, structs, numerics
- **Multi-package dependencies**: Always include the package name. Use `{{ ref('my_package', 'my_model') }}` over `{{ ref('my_model') }}`.

## 7. Testing

### Principles

- Every model **must** have its PK tested for `unique` + `not_null`
- Test strategically — don't overtest pass-through columns validated upstream
- Use `severity: warn` for non-critical tests
- Test **extensively** on datamart models (exposed to end users)

### Tests by Layer

| Layer | Required | Recommended |
|-------|----------|-------------|
| **Sources** | Source freshness (`loaded_at` field) | `not_null` on primary identifier |
| **Staging** | `unique` + `not_null` on PK | `not_null` on critical business columns; `accepted_values` for status/type fields |
| **Intermediate** | `unique` + `not_null` on PK (especially when re-graining) | `accepted_values` on derived fields |
| **Datamart** | `unique` + `not_null` on PK; `relationships` on FKs; `accepted_values` on business-critical fields | `not_null` on business fields; `unit tests` for complex logic |

### Tests by Column Pattern

| Column Pattern | Detected As | Tests |
|----------------|-------------|-------|
| `<entity>_id` (first column, matches model name) | Primary key | `unique`, `not_null` |
| `<other_entity>_id` (not PK) | Foreign key | `not_null`; `relationships` (datamart only) |
| `is_*` / `has_*` / `can_*` | Boolean | `not_null` |
| `*_date` | Date | `not_null` (if in incremental logic) |
| `*_at` | Timestamp | `not_null` (if in incremental logic) |
| `*_amount` / `*_total` / `*_price` | Monetary | `dbt_utils.accepted_range` (use `min_value: 0` for revenue; omit for refunds/credits/adjustments); `not_null` |
| `*_count` | Count | `dbt_utils.accepted_range: {min_value: 0}`; `not_null` |
| `*_type` / `*_category` / `*_status` / `*_group` | Categorical | `accepted_values` with explicit list |

### Test Severity

| Severity | When |
|----------|------|
| `error` (default) | PK tests, critical business logic |
| `warn` | Accepted values on low-impact fields, optional relationship tests |
| `warn` + `error_if` | Volume anomalies (e.g., `error_if: ">1000"`) |

### Useful Packages

- **dbt core**: `unique`, `not_null`, `accepted_values`, `relationships`
- **dbt_utils**: `generate_surrogate_key`, `expression_is_true`, `recency`, `at_least_one`, `unique_combination_of_columns`, `accepted_range`, `equal_rowcount`, `not_null_proportion`
- **dbt_expectations**: `expect_column_values_to_be_between`, `expect_table_row_count_to_be_between`
- **elementary**: `volume_anomalies`

### Unit Tests (dbt Core 1.8+)

Use only for complex business logic (pricing, conditional categorization, incremental logic). Do not unit test simple select/rename. Run in dev/CI only, not production.

```yaml
unit_tests:
  - name: test_order_status_logic
    model: fct_orders
    given:
      - input: ref('stg_shop__orders')
        rows:
          - {order_id: "1", status: "P", amount: 100}
    expect:
      rows:
        - {order_id: "1", status: "pending", amount_usd: 100.00}
```

## 8. Folder Structure

```
models/
  sources/                    # one YAML per source system
    <source_system>.yml
  staging/
    <source_system>/
      stg_*.sql
      stg_*.yml              # tests for staging models
  intermediate/
    <domain>/
      int_*.sql
      int_*.yml
  datamart/
    <domain>/
      dim_*.sql
      dim_*.yml
      fct_*.sql
      fct_*.yml
      agg_*.sql
      agg_*.yml
      ...
```

## 9. SQL Style

- **Linter**: SQLFluff
- **Indentation**: 4 spaces
- **Max line length**: 180 characters
- **Commas**: Leading
- **Keywords**: Lowercase (`select`, `from`, `where`)
- **Aliases**: Always use `as`. Always include table and column aliases when there is more than one table. Aliases must be explicit without abbreviations.
- **No `SELECT *`**: Explicitly list columns in all models. `SELECT *` is only permitted in the final CTE (`select * from <final_cte>`).
- **Comments**: Add comments if necessary to explain edge-cases in term of business requirements. Comments must not be used to explain technical aspects of the SQL.

### Fields & Aggregation

- Fields before aggregates and window functions in select
- Aggregate as early as possible (smallest dataset) before joining
- Prefer `group by all` over listing column names

### Joins

- Prefer `union all by name` over `union` (unless you explicitly need dedup)
- Prefix columns with table name when joining 2+ tables
- Be explicit: `inner join`, `left join` (never implicit)
- Avoid `right join` — switch table order instead

### Import CTEs

- All `{{ ref() }}` and `{{ source() }}` calls go in CTEs at the top of the file
- Name import CTEs after the table they reference
- Select only columns used and filter early
- *Reason:* This pattern allows instant debugging — you can query any CTE in the chain independently

### Functional CTEs

- Each CTE does one logical unit of work
- Name CTEs descriptively
- Repeated logic across models should become intermediate models
- End model with `select * from <final_cte>`

## 10. YAML Style

- **Indentation**: 2 spaces
- **Max line length**: 80 characters
- Indent list items
- Prefer explicit lists over single-string values
- Blank line between list items that are dictionaries (when it improves readability)
- **One YAML per model**: Create a `.yml` file per model with the same name as the `.sql` file (e.g., `fct_orders.sql` → `fct_orders.yml`).
- **Descriptions**: Always add a `description` in the YAML for every model and its columns.
- **`doc()` blocks**: If a `doc` block exists for a column, reference it (`description: '{{ doc("product_category") }}'`). When a field is repeated across multiple models, add a `doc` block in the model that owns the field.
- **`data_tests` (not `tests`)**: Use the current `data_tests` key instead of the deprecated `tests` field. Use the `config` block inside `data_tests` for `meta`, `severity`, etc.

## 11. Jinja Style

- Spaces inside delimiters: `{{ this }}` not `{{this}}`
- Newlines to separate logical Jinja blocks
- 4-space indent inside Jinja blocks
- Prioritize readability over whitespace control

```sql
{%- if this %}

    {{- that }}

{%- else %}

    {{- the_other_thing }}

{%- endif %}
```
