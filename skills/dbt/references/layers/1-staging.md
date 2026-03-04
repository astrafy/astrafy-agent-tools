# Staging Layer

## Models

| Model | Prefix | Materialization | Naming | Description |
|-------|--------|-----------------|--------|-------------|
| Snapshot | `snp_` | Snapshot (SCD2) | `snp_<entity>` | SCD2 history tracking (optional) |
| Staging | `stg_` | View | `stg_<source>__<entity>` | 1:1 cast + rename only |

## Refs

- `snp_` refs: `raw_`, `seed_` (optional layer — `stg_` can read `raw_`/`seed_` directly)
- `stg_` refs: `snp_`, or `raw_`/`seed_` directly if no snapshot exists
- Uses `{{ source('<source_name>', '<table_name>') }}` to reference raw tables

## Key Behavior

- Only casting + renaming is allowed. No joins.
- MUST cast all fields, even if the type remains the same.

## Materialization

- Default: **View**.
- Use `table` if the model is used in multiple places.
- Use `incremental` if the source is expensive to process (e.g., single JSON column).

## Testing

- Required: `unique` + `not_null` on PK
- Recommended: `not_null` on critical business columns; `accepted_values` for status/type fields
