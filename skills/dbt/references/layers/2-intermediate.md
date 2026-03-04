# Intermediate Layer

## Model

| Prefix | Materialization | Naming | Description |
|--------|-----------------|--------|-------------|
| `int_` | View (default) | `int_<domain>__<entity>` | Optional transformation layer |

## Refs

- `int_` refs: `stg_` or `int_`

## Suffix Patterns

The intermediate layer is **optional**. Keep things simple, skip it when `stg_` feeds cleanly into datamart.

### Simple (most cases)

| Suffix | Purpose | Materialization |
|--------|---------|-----------------|
| `_prep` | Source-specific fixes (join, calc, filter) to conform one source before combining | View / Table / Incremental |
| `_unioned` | Stack prepared tables from different sources vertically | View |

**Rule**: `_prep` applies source-specific logic only. Cross-source business rules belong in `dim_`/`fct_` models.

### Advanced
Use when it is not possible to achieve the desired result with a `_prep` and `_unioned` models.

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

## Materialization

- Default: **View**.
- Use `table` if the model is used in multiple places.
- Use `incremental` when downstream is incremental and window functions/grouping/complex joins block predicate pushdown.

## Testing

| Required | Recommended |
|----------|-------------|
| `unique` + `not_null` on PK (especially when re-graining) | `accepted_values` on derived fields |
