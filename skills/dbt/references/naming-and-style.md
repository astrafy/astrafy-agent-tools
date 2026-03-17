# Naming Conventions & Style Guide

## Column Naming Conventions

| Type | Pattern | Examples | Notes |
|------|---------|----------|-------|
| Boolean | `is_*` / `has_*` / `can_*` / `was_*` / `should_*` | `is_active`, `has_purchased`, `can_edit` | Always verb prefix; avoid negatives (`is_active` not `is_not_active`) |
| Date | `*_date` | `order_date`, `signup_date` | `DATE` type (YYYY-MM-DD) |
| Timestamp | `*_at` | `created_at`, `loaded_at` | Use `TIMESTAMP` (UTC default). Non-UTC: suffix with tz (`created_at_pt`). Events: past-tense verb (`created_at`, `deleted_at`) |
| ID / Key | `*_id` | `customer_id`, `order_id` | PKs named `<entity>_id`. String data type unless performance requires otherwise |
| Surrogate Key | `*_sk_id` | `customer_sk_id`, `order_sk_id` | Distinguishes surrogate keys from natural `*_id` keys |
| Amount / Metric | `*_amount` / `*_total` / `*_price` | `revenue_amount`, `total_tax` | Numeric currency/totals |
| Quantity | `*_qty` | `order_qty` | Quantities of items |
| Total | `total_*` | `total_tax` | Sum of multiple columns together |
| Count | `*_count` | `login_count`, `order_count` | Integer counts |
| Percentage / Ratio | `*_pct` / `*_rate` / `*_ratio` (0-1); `*_pct_100` / `*_rate_100` / `*_ratio_100` (0-100) | `conversion_rate`, `subscribed_pct_100` | Append `_100` for 0-100 scale |
| Categorical | `*_type` / `*_category` / `*_status` / `*_group` | `customer_type`, `order_status` | String fields for grouping/segmenting |
| Array | `*_list` | `tag_list`, `item_list` | BigQuery `REPEATED` fields |
| Struct | `[entity]_details` | `customer_details`, `shipping_details` | BigQuery `STRUCT` fields |
| System / Audit | `_*` (leading underscore) | `_loaded_at`, `_dbt_updated_at` | Metadata, ELT sync timestamps, dbt audit columns |

### Units of Measure

When a column represents a unit, the unit **must** be a suffix: `duration_s`, `duration_ms`, `amount_usd`, `price_eur`, `weight_kg`, `size_bytes`.

### General Rules

- Models are **pluralized**: `dim_customers`, `fct_orders`
- Every model has a **primary key**
- All names in **snake_case**
- Use **consistent field names** across models: FK must match PK name (e.g., `customer_id` everywhere, not `user_id` or `cust_id`)
- Multiple FKs to same dim: prefix contextually (`sender_customer_id`, `receiver_customer_id`)
- **No abbreviations**: `customer` not `cust`, `orders` not `o`
- **No SQL reserved words** standalone: `order_date` not `date`
- Model versions: `_v1`, `_v2` suffix
- **Column ordering**: system/audit, ids, dates, timestamps, booleans, strings, arrays, structs, numerics

## SQL Style

- **Linter**: SQLFluff
- **Indentation**: 4 spaces
- **Max line length**: 180 characters
- **Commas**: Leading
- **Keywords**: Lowercase (`select`, `from`, `where`)
- **Aliases**: Always use `as`
- **No `SELECT *`**: Explicitly list columns in all models. `SELECT *` is only permitted in the final CTE (`select * from <final_cte>`).
- **Comments**: Only to explain business edge-cases, not technical SQL. Use Jinja comments (`{# ... #}`) when comments should not compile into SQL
- **Aliases**: Table aliases must be explicit without abbreviations (e.g., `customers` not `c`)

### Fields & Aggregation

- Fields before aggregates and window functions in select
- Aggregate as early as possible (smallest dataset) before joining
- Prefer `group by all` over listing column names

### Joins

- Prefer `union all by name` over `union` (unless you explicitly need dedup)
- Prefix columns with table name when joining 2+ tables
- Be explicit: `inner join`, `left join` (never implicit)
- Avoid `right join` — switch table order instead

### Import CTEs

- All `{{ ref() }}` and `{{ source() }}` calls go in CTEs at the top of the file
- Name import CTEs after the table they reference
- Select only columns used and filter early
- *Reason:* This pattern allows instant debugging — you can query any CTE in the chain independently

### Functional CTEs

- Each CTE does one logical unit of work
- Name CTEs descriptively
- Repeated logic across models should become intermediate models
- End model with `select * from <final_cte>`

### Model Configuration

- Model-specific attributes (sort/dist keys, etc.) go in the model file
- Directory-wide configuration goes in `dbt_project.yml`

## YAML Style

- **Indentation**: 2 spaces
- **Max line length**: 80 characters
- Indent list items
- Prefer explicit lists over single-string values
- Blank line between list items that are dictionaries (when it improves readability)
- **One YAML per model**: Create a `.yml` file per model with the same name as the `.sql` file (e.g., `fct_orders.sql` → `fct_orders.yml`).
- **Descriptions**: Always add a `description` in the YAML for every model and its columns.
- **`doc()` blocks**: If a `doc` block exists for a column, reference it (`description: '{{ doc("product_category") }}'`). When a field is repeated across multiple models, add a `doc` block in the model that owns the field.
- **`data_tests` (not `tests`)**: Use the current `data_tests` key instead of the deprecated `tests` field. Use the `config` block inside `data_tests` for `meta`, `severity`, etc.
- Use the following syntax for `data_tests`:
```yaml
data_tests:
  - <test_name>:
      arguments:
        <argument_name>: <argument_value>
      config:
        <test_config>: <config-value>
```

## Jinja Style

- Spaces inside delimiters: `{{ this }}` not `{{this}}`
- Newlines to separate logical Jinja blocks
- 4-space indent inside Jinja blocks
- Prioritize readability over whitespace control

```sql
{%- if this %}

    {{- that }}

{%- else %}

    {{- the_other_thing }}

{%- endif %}
```
