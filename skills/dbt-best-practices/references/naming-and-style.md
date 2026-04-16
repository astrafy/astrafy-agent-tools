# Naming Conventions & Style Guide

## Column Naming Conventions

| Type | Pattern | Examples | Notes |
|------|---------|----------|-------|
| Boolean | `is_*` / `has_*` / `can_*` / `was_*` / `should_*` | `is_active`, `has_purchased`, `can_edit` | Always verb prefix; avoid negatives (`is_active` not `is_not_active`) |
| Date | `*_date` | `order_date`, `signup_date` | `DATE` type (YYYY-MM-DD) |
| Timestamp | `*_at` | `created_at`, `loaded_at` | Use `TIMESTAMP` (UTC default). Non-UTC: suffix with tz (`created_at_pt`). Events: past-tense verb (`created_at`, `deleted_at`) |
| Surrogate Key | `*_sk_id` | `customer_sk_id`, `order_sk_id` | Surrogate key — generated hash combining `record_source` + natural key |
| Natural Key | `*_nk_id` | `customer_nk_id`, `order_nk_id` | Preserved natural key from the source system, kept alongside the surrogate key |
| Amount / Metric | `*_amount` / `*_total` / `*_price` | `revenue_amount`, `total_tax` | Numeric currency/totals |
| Quantity | `*_qty` | `order_qty` | Quantities of items |
| Total | `total_*` | `total_tax` | Sum of multiple columns together |
| Count | `*_count` | `login_count`, `order_count` | Integer counts |
| Percentage / Ratio | `*_pct` / `*_rate` / `*_ratio` (0-1); `*_pct_100` / `*_rate_100` / `*_ratio_100` (0-100) | `conversion_rate`, `subscribed_pct_100` | Append `_100` for 0-100 scale |
| Categorical | `*_type` / `*_category` / `*_status` / `*_group` | `customer_type`, `order_status` | String fields for grouping/segmenting |
| Array | `*_list` | `tag_list`, `item_list` | BigQuery `REPEATED` fields |
| Struct | `[entity]_details` | `customer_details`, `shipping_details` | BigQuery `STRUCT` fields |
| SCD2 Validity | `dbt_valid_from`, `dbt_valid_to` | `dbt_valid_from`, `dbt_valid_to` | `TIMESTAMP` columns managed automatically by dbt snapshots. `dbt_valid_from` is the start of the validity period; `dbt_valid_to` is the end (`NULL` for the current record). Do not select these in the snapshot query — dbt adds them. |
| SCD2 Derived | `is_current` | `is_current` | `BOOLEAN` derived downstream as `dbt_valid_to is null`. Not present on the snapshot itself — add it in the dimension or intermediate model that consumes the snapshot. |
| System / Audit | `_*` (leading underscore) | `_loaded_at`, `_dbt_updated_at` | Metadata, ELT sync timestamps, dbt audit columns |

### Units of Measure

When a column represents a unit, the unit **must** be a suffix: `duration_s`, `duration_ms`, `amount_usd`, `price_eur`, `weight_kg`, `size_bytes`.

### General Rules

- Models are **pluralized**: `dim_customers`, `fct_orders`, `int_customers_unioned`
- Every model should have a **primary key** except aggregate models.
- All names in **snake_case**
- Use **consistent field names** across models: FK must match PK name (e.g., `customer_sk_id` everywhere, not `user_sk_id` or `cust_sk_id`)
- Multiple FKs to same dim: prefix contextually (`sender_customer_sk_id`, `receiver_customer_sk_id`)
- **No abbreviations**: `customer` not `cust`, `orders` not `o`
- **No SQL reserved words** standalone: `order_date` not `date`
- Model versions: `_v1`, `_v2` suffix
- **SCD2 models**: Append `_scd2` suffix to the model name (e.g., `stg_shop__customers_scd2`, `dim_employees_scd2`). The `_scd2` suffix replaces the old `snp_` prefix convention. SCD2 models live in the same folder as their non-SCD2 counterparts.
- **Column ordering**: system/audit, ids, dates, timestamps, booleans, categoricals (type/status/category/group), strings, arrays, structs, numerics. For models consuming a snapshot, place `dbt_valid_from`, `dbt_valid_to`, and `is_current` (derived) after all entity columns and before system/audit columns.

## SQL Style

- **Linter**: SQLFluff
- **Indentation**: 4 spaces
- **Max line length**: 180 characters
- **Commas**: Leading
- **Keywords**: Lowercase (`select`, `from`, `where`)
- **Aliases**: Always use `as`
- **Comments**: Only to explain business edge-cases, not technical SQL. Use Jinja comments (`{# ... #}`) when comments should not compile into SQL
- **Aliases**: Table aliases must be explicit without abbreviations (e.g., `customers` not `c`)

### Fields & Aggregation

- Fields before aggregates and window functions in select
- Aggregate as early as possible (smallest dataset) before joining
- Prefer `group by all` over listing column names (BigQuery syntax)

### Joins

- Prefix columns with table name when joining 2+ tables
- Be explicit: `inner join`, `left join` (never implicit)
- Avoid `right join` — switch table order instead

### Unions

- Use `union all` with explicit column lists

### Import CTEs

- All `{{ ref() }}` and `{{ source() }}` calls go in CTEs at the top of the file
- Name import CTEs after the source model they reference (e.g., `stg_shop__orders`, `int_customers_enriched`)
- Select only columns used and filter early
- *Reason:* This pattern allows instant debugging — you can query any CTE in the chain independently

### Functional CTEs

- Each CTE does one logical unit of work
- Name CTEs with verb-based descriptive names (e.g., `filtered_active`, `aggregated_by_month`, `joined_with_customers`, `final`)
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
- **One YAML per model**: Create a `.yml` file per model with the same name as the `.sql` file (e.g., `fct_orders.sql` → `fct_orders.yml`). This is not applied for sources or seeds.
- **Descriptions**: Always add a `description` in the YAML for every model. Before datamart only columns with tests should have a description.
- **Multiline descriptions**: When a description exceeds 80 characters, use YAML folded block scalars (`>`) to wrap across lines:
  ```yaml
  description: >
    Total revenue amount in USD, calculated as the sum of
    all line item amounts after discounts and before tax.
  ```
- **`doc()` blocks**: If a `doc` block exists for a column, reference it (`description: '{{ doc("product_category") }}'`). When a field is repeated across multiple models, add a `doc` block in the model that owns the field. Place `doc` blocks in a `_docs.md` file inside the same folder as the model that owns the field.
- **`data_tests` (not `tests`)**: Use the current `data_tests` key instead of the deprecated `tests` field. Use the `config` block inside `data_tests` for `meta`, `severity`, etc.
- Use the following syntax for `data_tests`:
```yaml
data_tests:
  - <test_name>:
      <argument_name>: <argument_value>
      config:
        <test_config>: <config-value>
```

**Example:**
```yaml
columns:
  - name: customer_sk_id
    data_tests:
      - unique
      - not_null
  - name: revenue_amount
    data_tests:
      - not_null
      - dbt_utils.accepted_range:
          min_value: 0
          config:
            severity: warn
  - name: order_status
    data_tests:
      - accepted_values:
          values: ['pending', 'completed', 'cancelled']
          config:
            severity: warn
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
