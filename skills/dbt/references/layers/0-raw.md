# Raw Layer

## Models

| Model | Prefix | Materialization | Naming | Description |
|-------|--------|-----------------|--------|-------------|
| Seed | `seed_` | Table | `seed_<context>__<entity>` | dbt seeds |
| Raw Table | `raw_` | Table (managed) | `raw_<source>__<entity>` | Ingested tables |

## Testing

- Required: Source freshness (`loaded_at` field)
- Recommended: `not_null` on primary identifier
