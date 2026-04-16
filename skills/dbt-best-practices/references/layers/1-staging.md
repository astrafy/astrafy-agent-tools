# Staging Layer

See [Architecture](../architecture.md) for materialization, naming conventions, and reference rules (`stg_`).

Staging models use `{{ source('<source_name>', '<table_name>') }}` to reference raw tables.

## Key Behavior

- Must cast all fields, even if the type remains the same. Do not cast uncasteable fields such as `REPEATED` or `STRUCT` fields.
- Must rename all fields, even if the name remains the same.
- No joins.

- **All ID columns must be cast to `STRING`** — regardless of the source data type. This ensures consistency across sources and compatibility with surrogate key generation downstream.
- **Every staging model must include a `record_source` column** that identifies where the record originates. This is a hardcoded string literal, not derived from the data. Examples: `'avaza_es'`, `'hubspot'`, `'salesforce'`. As a system/audit column, it goes **first** in the select list (see column ordering in [Naming & Style](../naming-and-style.md)):
  ```sql
  'hubspot' as record_source
  ```

## Materialization

- Default: **View**.
- Use `table` if the model is used in multiple places.
- Use `incremental` if the source is expensive to process (e.g., single JSON column). See [Incremental Models](../incremental-models.md).

## Testing

- Required: `unique` + `not_null` on PK
- Recommended: `not_null` on critical business columns; `accepted_values` for status/type fields

## YAML

- Only include columns that have tests. Do not list columns without tests — keep the YAML lean.
- Always add a `description` for the model itself.

## Example

### `stg_shop__customers.sql`

```sql
with source as (
    select * from {{ source('shop', 'customers') }}
)

select
    'shop' as record_source
    , cast(id as string) as customer_id
    , cast(created_at as timestamp) as created_at
    , cast(updated_at as timestamp) as updated_at
    , cast(is_active as boolean) as is_active
    , cast(status as string) as customer_status
    , cast(full_name as string) as customer_name
    , cast(email as string) as email
from source
```

### `stg_shop__customers.yml`

```yaml
models:
  - name: stg_shop__customers
    description: Staged customers from the shop source system.
    columns:
      - name: customer_id
        data_tests:
          - unique
          - not_null
```

## Event-Sourced Sources (Latest State)

Some sources are append-only: every change to an entity lands as a new row in the raw table (e.g. a `user` stream where each update produces a new record with an `updated_at`). When downstream only cares about the **current value** per entity, this is still a regular staging model — name it `stg_<source>__<entity>` with no special suffix — but you need to collapse the event stream down to one row per business key.

Use `qualify row_number()` to keep only the most recent row per key. Prefer an `incremental` materialization with `incremental_strategy='merge'` and `unique_key=<business_key>`: merging on the key means each run only processes new events and upserts the latest row per entity in place, rather than rebuilding the dedupe over the full event stream every run.

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='user_id'
) }}

with source as (
    select * from {{ source('shop', 'user_events') }}
    {% if is_incremental() %}
        where updated_at > (select max(updated_at) from {{ this }})
    {% endif %}
)

select
    'shop' as record_source
    , cast(id as string) as user_id
    , cast(updated_at as timestamp) as updated_at
    , cast(email as string) as email
    , cast(status as string) as user_status
from source
qualify row_number() over (partition by id order by updated_at desc) = 1
```

> The `qualify` is still required under `merge`. A single incremental batch can contain several new events for the same `user_id`, and BigQuery's `merge` errors out when more than one source row matches the same target key (*"UPDATE/MERGE must match at most one source row for each target row"*). `qualify` collapses each batch to one row per key so the merge is well-defined.

Same cast + rename rules, same `record_source` first, same PK tests (`unique` + `not_null` on `user_id`). If downstream needs the **full history** rather than just latest state, see [SCD2 from Event-Sourced Sources](#scd2-from-event-sourced-sources) below — that is a different model, built as SCD2 in SQL.

## SCD2 Staging Models (Snapshots)

SCD2 staging models use **dbt snapshots** to automatically track history for a source entity. They are snapshot definitions, not regular models, and follow the naming pattern `stg_<source>__<entity>_scd2`.

dbt handles all change-detection, row-closing, and row-opening logic automatically. There is no need to write custom incremental merge logic.

### Key Differences from Regular Staging

- **Naming**: `stg_<source>__<entity>_scd2`
- **Artifact**: snapshot SQL definition using a `{% snapshot %}` block
- **Location**: `snapshots/staging/<source_system>/stg_<source>__<entity>_scd2.sql`
- **Strategy**: `check` (compares tracked columns) or `timestamp` (compares an `updated_at` column). Prefer `check` when the source has no reliable `updated_at`; prefer `timestamp` when one exists — it is more performant on large tables.
- **dbt-managed SCD2 columns** (added automatically — do not select them in the query):
  - `dbt_scd_id` — unique identifier for each version row
  - `dbt_updated_at` — when dbt detected the change
  - `dbt_valid_from` — start of the validity period
  - `dbt_valid_to` — end of the validity period (`NULL` for the current record)
- Same cast + rename rules apply to all entity columns.
- Same `record_source` column requirement applies.
- The `select` body is written like a regular staging model inside the snapshot block — dbt wraps it with snapshot logic.

## SCD2 from Event-Sourced Sources

When the source is append-only (one row per change, as described in [Event-Sourced Sources (Latest State)](#event-sourced-sources-latest-state)) **and** downstream needs point-in-time history, build the SCD2 model directly in SQL rather than using a `{% snapshot %}` block. The history is already in the data — snapshotting would re-detect change at dbt run time against a live source, losing intra-run changes and adding unnecessary state on top of history you already have.

Name the model `stg_<source>__<entity>_scd2`. Derive `valid_from` from the event timestamp and `valid_to` via `lead()` over the same timestamp — the current row gets `null` for `valid_to`, matching the convention used by the snapshot-based SCD2 section above.

```sql
with source as (
    select * from {{ source('shop', 'user_events') }}
)

, casted as (
    select
        'shop' as record_source
        , cast(id as string) as user_id
        , cast(updated_at as timestamp) as updated_at
        , cast(email as string) as email
        , cast(status as string) as user_status
    from source
)

select
    record_source
    , user_id
    , email
    , user_status
    , updated_at as valid_from
    , lead(updated_at) over (partition by user_id order by updated_at) as valid_to
    , lead(updated_at) over (partition by user_id order by updated_at) is null as is_current
from casted
```

**Rules that still apply**:
- Same cast + rename rules for all entity columns.
- `record_source` first in the select list.
- Primary key is the composite (`user_id`, `valid_from`). Add `not_null` on `valid_from` and a composite uniqueness test (e.g. `dbt_utils.unique_combination_of_columns`) on (`user_id`, `valid_from`).
- `is_current` is a convenience flag so downstream can filter the open record without a `valid_to is null` check.

**Materialization**: `view` by default. Switch to `table` if it is used in multiple places, or `incremental` on `updated_at` if the event stream is large enough that recomputing the window every run is expensive — see [Incremental Models](../incremental-models.md).
