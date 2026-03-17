# General Rules

## Key Rules

- Every model must have a primary key. Use `{{ dbt_utils.generate_surrogate_key([...]) }}` when no natural key exists.
- Staging is the only layer where renaming and casting of raw fields is allowed.
- All columns on different tables relating to the same concept must have the same name.
- Do not define `materialization` or `tags` in the model file unless the value differs from the project default (`dbt_project.yml`).
- Every .sql model file must have a corresponding .yml file with the same name.

## Partitioning & Clustering in BigQuery

| Table Size | Strategy |
|------------|----------|
| **< 1 GB** | Do nothing. BigQuery is fast enough out of the box. |
| **1–30 GB** | Cluster on heavily filtered columns, such as the main date. |
| **> 30 GB** (with >1–10 GB per time unit) | Partition by time, and cluster by most-used filter columns. Consider [incremental materialization](incremental-models.md). |

When creating or editing an incremental model, read [Incremental Models](incremental-models.md) for strategy selection (`insert_overwrite` vs `merge`), partition key mismatch risks, and `is_incremental()` patterns.

## Testing

### Principles

- Every model must have its PK tested for `unique` + `not_null`
- Test strategically — don't overtest pass-through columns validated upstream
- Use `severity: warn` for non-critical tests
- Test extensively on datamart models (exposed to end users)

### Tests by Column Pattern

| Column Pattern | Detected As | Tests |
|----------------|-------------|-------|
| `<entity>_id` (first column, matches model name) | Primary key | `unique`, `not_null` |
| `<other_entity>_id` (not PK) | Foreign key | `not_null`; `relationships` (datamart only) |
| `is_*` / `has_*` / `can_*` / `was_*` / `should_*` | Boolean | `not_null` |
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

### Unit Tests

Models with very complex logic must be unit tested. Simple select/rename models do not need to be unit tested. Run in dev/CI only, not production.

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

### Model Contracts

Enforce on public/exposed models (`dim_*`, `fct_*`) that downstream consumers depend on. Contracts validate column names and data types at build time.

```yaml
models:
  - name: dim_customers
    config:
      contract:
        enforced: true
    columns:
      - name: customer_id
        data_type: string
      - name: customer_name
        data_type: string
```
