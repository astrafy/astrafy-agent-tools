# Datamart Layer

## Models

| Model | Prefix | Materialization | Naming | Description |
|-------|--------|-----------------|--------|-------------|
| Dimension | `dim_` | Table | `dim_<entity>` | Dimension presentation |
| Fact | `fct_` | Incremental / Table | `fct_<entity>` | Fact tables |
| Bridge | `brg_` | Table | `brg_<entity1>_<entity2>` | N:M relationship PKs |
| Mart | `mart_` | Table | `mart_<entity>` | Dims requiring fct computations (optional) |
| Aggregate | `agg_` | Incremental / Table | `agg_<grain>_<entity>` | Re-grained facts (optional) |
| Report | `rpt_` | Table / Incremental | `rpt_<dashboard>` | Dashboard-specific tables |
| Utility | `util_` | Table | `util_<purpose>` | Date spines, calendars |

## Examples

- `mart_customers` — `dim_customers` enriched with lifetime order metrics from `fct_orders` (e.g. lifetime revenue, order count).
- `agg_monthly_orders` — `fct_orders` re-grained from per-order to per-customer-month (e.g. monthly revenue, order count).

## Refs

- `dim_`, `fct_`, `brg_` ref: `int_` or `stg_` directly
- `mart_`, `agg_` ref: `dim_`, `fct_`, `brg_`
- `rpt_` refs: `mart_`, `agg_`, `dim_`/`fct_`/`brg_`
- `util_` can be joined by any `int_` or datamart model

## Materialization

- Default: **Table**.
- Use `incremental` for large tables expensive to reprocess.

## Testing

- Required: `unique` + `not_null` on PK; `relationships` on FKs; `accepted_values` on business-critical fields
- Recommended: `not_null` on business fields; `unit tests` for complex logic
