# General Rules

## Key Rules

- All columns on different tables relating to the same concept must have the same name.
- Do not define `materialization` or `tags` in the model file unless the value differs from the project default (`dbt_project.yml`).
- Every model `.sql` file must have a corresponding `.yml` file with the same name. This does not apply to sources (one shared YAML per source system) or seeds (one shared YAML for all seeds).
- Never use `SELECT *` — explicitly list columns in all CTEs. `SELECT *` is only permitted in **import CTEs** (the initial `ref()`/`source()` wrappers at the top of the file) and in the **final CTE** (`select * from <final_cte>`).

## Partitioning & Clustering in BigQuery

| Table Size | Strategy |
|------------|----------|
| **< 1 GB** | Do nothing. BigQuery is fast enough out of the box. |
| **1–30 GB** | Cluster on heavily filtered columns, such as the main date. |
| **≥ 30 GB** (with >1–10 GB per time unit) | Partition by time, and cluster by most-used filter columns. See [Incremental Models](incremental-models.md) for when and how to use incremental. |

When creating or editing an incremental model, read [Incremental Models](incremental-models.md) for strategy selection (`insert_overwrite` vs `merge`), partition key mismatch risks, and `is_incremental()` patterns.

## Testing

### Principles

- Every model must have its PK tested for `unique` + `not_null`
- On intermediate and datamart models, the PK is expected to be `<entity>_sk_id`
- Test strategically — don't overtest pass-through columns validated upstream
- Use `severity: warn` for non-critical tests
- Test extensively on datamart models (exposed to end users)

### Tests by Column Pattern

| Column Pattern | Detected As | Tests |
|----------------|-------------|-------|
| `<entity>_sk_id` (first key column on intermediate/datamart) | Primary key | `unique`, `not_null` |
| `<other_entity>_sk_id` (not PK) | Foreign key | `not_null`; `relationships` (datamart only) |
| `<entity>_id` (staging/raw primary identifier) | Source or natural key | `unique`, `not_null` when it is the layer PK |
| `is_*` / `has_*` / `can_*` / `was_*` / `should_*` | Boolean | `not_null` |
| `*_date` | Date | `not_null` (if in incremental logic) |
| `*_at` | Timestamp | `not_null` (if in incremental logic) |
| `*_amount` / `*_total` / `*_price` | Monetary | `dbt_utils.accepted_range` (use `min_value: 0` for revenue; omit for refunds/credits/adjustments); `not_null` |
| `*_count` | Count | `dbt_utils.accepted_range: {min_value: 0}`; `not_null` |
| `*_qty` | Quantity | `dbt_utils.accepted_range: {min_value: 0}`; `not_null` |
| `*_pct` / `*_rate` / `*_ratio` | Percentage / Ratio (0-1) | `dbt_utils.accepted_range: {min_value: 0, max_value: 1}` |
| `*_pct_100` / `*_rate_100` / `*_ratio_100` | Percentage / Ratio (0-100) | `dbt_utils.accepted_range: {min_value: 0, max_value: 100}` |
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

## Macros

### Conventions

- **Naming**: `snake_case`, descriptive verb-noun pattern (e.g., `null_safe_surrogate_key`, `cents_to_dollars`)
- **File organization**: One macro per file in `macros/`, file name matches macro name
- **When to create**: Extract logic into a macro when the same SQL pattern is used in 3+ models, or when the logic is complex enough to benefit from centralized maintenance
- **Existence check**: Before calling a project macro (e.g., `null_safe_surrogate_key`), verify it exists at the expected path. If missing, create it before using it.
