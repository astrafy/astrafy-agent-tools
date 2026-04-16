# Incremental Models

Use incremental materialization when the target table is **>= 30 GB**.

Incremental models process only new/changed rows instead of rebuilding the full table.

## Strategy Selection

| Strategy | Use When | Trade-off |
|----------|----------|-----------|
| `insert_overwrite` | Source and target share the **same partition key** (or 1:1 mapping) | Fast (bulk partition replace), but risks data loss on key mismatch |
| `merge` | Partition keys differ, or rows can change partition values | Safer (row-level upsert), but slower on large tables due to full scan |

**Default to `insert_overwrite`** unless the conditions require `merge`.

## `insert_overwrite`

Replaces entire partitions. dbt runs the filtered query, identifies touched partitions, **deletes those partitions**, then inserts new rows.

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='insert_overwrite',
        partition_by={
            "field": "event_date",
            "data_type": "date",
            "granularity": "day"
        }
    )
}}

select
    event_id,
    user_id,
    event_type,
    event_date,
    created_at
from {{ source('raw', 'events') }}

{% if is_incremental() %}
    where event_date >= date_sub(current_date(), interval 3 day)
{% endif %}
```

### Partition Key Mismatch Risk

When source filter key != target partition key, `insert_overwrite` can **silently delete unrelated rows**.

Example: source filtered by `order_date`, target partitioned by `ship_date`. Query returns rows with `ship_date = 2025-12-31`, so dbt deletes the entire `2025-12-31` partition, including old rows from prior runs that had nothing to do with today's `order_date` filter.

**Rule: only use `insert_overwrite` when source filter key and target partition key are the same or have a guaranteed 1:1 mapping.**

## `merge`

Row-level `MERGE` (upsert) using a `unique_key`. Matches incoming rows against existing rows — no partition-level deletion, so no orphaned/lost rows.

Less efficient: BigQuery must scan and compare every row in the target.

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='event_id',
        partition_by={
            "field": "event_date",
            "data_type": "date",
            "granularity": "day"
        }
    )
}}

select
    event_id,
    user_id,
    event_type,
    event_date,
    created_at
from {{ source('raw', 'events') }}

{% if is_incremental() %}
    where created_at >= timestamp_sub(current_timestamp(), interval 3 day)
{% endif %}
```

## BigQuery Optimizations

- **`require_partition_filter: true`**: Add to large incremental tables to prevent accidental full-table scans by downstream queries. Forces consumers to include the partition column in their `WHERE` clause.
- **`copy_partitions: true`**: Use with `insert_overwrite` to copy partitions via metadata operations instead of re-inserting rows. Significantly faster for large partitions.

```sql
config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by={"field": "event_date", "data_type": "date", "granularity": "day"},
    require_partition_filter=true,
    copy_partitions=true
)
```

## `is_incremental()` Patterns

The `{% if is_incremental() %}` block filters data on incremental runs. On first run or `--full-refresh`, it evaluates to `false` (full load).

```sql
-- Filter on max existing value
{% if is_incremental() %}
    where viewed_at > (select max(viewed_at) from {{ this }})
{% endif %}

-- Fixed lookback window (guards against late-arriving data)
{% if is_incremental() %}
    where viewed_at >= date_sub(current_date(), interval 3 day)
{% endif %}

-- Configurable lookback via var
{% set lookback_days = var('lookback_days', 3) %}
{% if is_incremental() %}
    where event_date >= date_sub(current_date(), interval {{ lookback_days }} day)
{% endif %}
```
