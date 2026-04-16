# Raw Layer

See [Architecture](../architecture.md) for materialization and naming conventions (`seed_`, `raw_`).

## Seeds vs. Raw Tables

- **Seeds** (`seed_`): Small, version-controlled CSV files (lookup tables, mapping tables). Managed by dbt. Not for large datasets.
- **Raw tables** (`raw_`): Ingested from external systems by ELT tools (Fivetran, Airbyte, etc.). dbt does not manage the ingestion — only reads from them via `{{ source() }}`.

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
