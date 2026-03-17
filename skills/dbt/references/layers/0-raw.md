# Raw Layer

## Models

| Model | Prefix | Materialization | Naming | Description |
|-------|--------|-----------------|--------|-------------|
| Seed | `seed_` | Table | `seed_<context>__<entity>` | dbt seeds |
| Raw Table | `raw_` | Table (managed) | `raw_<source>__<entity>` | Ingested tables |

## Testing

- Required: Source freshness (`loaded_at` field)
- Recommended: `not_null` on primary identifier

### Source Freshness

Define freshness on critical sources in your source YAML files:

```yaml
sources:
  - name: stripe
    loaded_at_field: _fivetran_synced
    freshness:
      warn_after: {count: 24, period: hour}
      error_after: {count: 36, period: hour}
    tables:
      - name: charges
```
