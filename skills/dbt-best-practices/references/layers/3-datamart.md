# Datamart Layer

See [Architecture](../architecture.md) for materialization, naming conventions, and reference rules.

The datamart is organized into three ordered sub-layers. Each sub-layer can contain department or purpose subfolders, or models can live directly at the sub-layer root.

## 01_core — Kimball Models

Prefixes: `dim_`, `fct_`, `brg_`, `util_`

Core dimensional models following Kimball star-schema design. These are the foundational building blocks of the datamart.

Facts and dimensions never join to other `dim_` tables to pick up FK sk_ids — see "Why `int_` only for 01_core" in [Architecture](../architecture.md).

- `dim_employees` — conformed dimension with attributes from one or more intermediate sources.
- `dim_employees_scd2` — SCD2 dimension preserving historical changes to employee attributes. Built from an intermediate model that consumes an upstream `stg_*_scd2` snapshot. Each row represents a version of the entity, with `dbt_valid_from` and `dbt_valid_to` tracking the validity period.
- `fct_timesheets` — fact table at the timesheet-entry grain, referencing dimension keys.
- `brg_employee_projects` — bridge table resolving N:M relationships between employees and projects.
- `util_date_spine` — date spine or calendar utility table joinable by any datamart model.

### SCD2 Dimensions

SCD2 dimensions (`dim_<entity>_scd2`) present historical attribute changes tracked by an upstream dbt snapshot. The snapshot (`stg_*_scd2`) handles all change-detection; the dimension reshapes, enriches, and adds surrogate keys.

- **Naming**: `dim_<entity>_scd2`
- **Materialization**: `table` (or `incremental` for large tables). The SCD2 tracking is done by the upstream snapshot — the dimension is a regular model consuming the snapshot output.
- **SCD2 columns from upstream**: The model selects `dbt_valid_from` and `dbt_valid_to` from the snapshot and may derive `is_current` as `dbt_valid_to is null`. See [Naming & Style](../naming-and-style.md) for column conventions.
- **Source**: Always built from an `int_` model that consumes a `stg_*_scd2` snapshot. The dimension does not implement change-detection logic itself.
- **Testing**: `unique_combination_of_columns` on surrogate key + `dbt_valid_from`; `not_null` on `dbt_valid_from`; at most one current row per entity (`dbt_valid_to is null`)

**Refs:** `int_` only.

### Folder structure

```
models/datamart/01_core/<department>/{dim,fct,brg}_<entity>.{sql,yml}
models/datamart/01_core/<department>/dim_<entity>_scd2.{sql,yml}
models/datamart/01_core/<department>/util_<purpose>.{sql,yml}
```

`<department>` is optional (e.g., `finance/`, `human_resources/`, `project_management/`).

## 02_enriched — Aggregated & Wide Models

Prefixes: `agg_`, `wide_`

Models that enrich or re-grain core models. `wide_` replaces the legacy `mart_` prefix.

- `wide_customers` — `dim_customers` enriched with lifetime order metrics from `fct_orders` (e.g. lifetime revenue, order count).
- `agg_monthly_orders` — `fct_orders` re-grained from per-order to per-customer-month (e.g. monthly revenue, order count).

**Refs:** `dim_`, `fct_`, `brg_` (this layer is optional — consumption models can query 01_core directly).

### Folder structure

```
models/datamart/02_enriched/<department>/{agg_<grain>_<entity>,wide_<entity>}.{sql,yml}
```

`<department>` is optional.

## 03_consumption — Reports, Reverse ETL & Output Models

Prefixes: `rpt_`, `retl_`, `ai_`, `comp_`, `rec_`

Consumer-facing models built for specific tools, dashboards, or external systems.

- `rpt_sales_dashboard` — pre-joined and pre-aggregated table for a specific dashboard. Naming by purpose (`rpt_monthly_sales`) is more stable than naming by dashboard tool (`rpt_looker_sales`).
- `retl_hubspot_contacts` — table shaped for reverse ETL into an external system.
- `ai_customer_churn_features` — feature table prepared for ML model training or inference.
- `comp_gdpr_data_inventory` — audit or compliance table tracking regulated data.
- `rec_deals_wo_avaza_project` — reconciliation table checking consistency across source systems.

**Refs:** `wide_`, `agg_`, `dim_`, `fct_`, `brg_`.

### Folder structure

```
models/datamart/03_consumption/reporting/rpt_<dashboard>.{sql,yml}
models/datamart/03_consumption/reverse_etl/retl_<destination>_<purpose>.{sql,yml}
models/datamart/03_consumption/artificial_intelligence/ai_<entity>.{sql,yml}
models/datamart/03_consumption/compliance/comp_<entity>.{sql,yml}
models/datamart/03_consumption/data_reconciliation/rec_<entity>.{sql,yml}
```

`<purpose>` subfolders are optional but recommended:

- `reporting/` — dashboard and BI report tables (`rpt_`)
- `reverse_etl/` — tables pushed to external systems (`retl_`)
- `artificial_intelligence/` — feature stores and ML-ready tables (`ai_`)
- `compliance/` — audit and compliance tables (`comp_`)
- `data_reconciliation/` — cross-source reconciliation checks (`rec_`)

## Examples

### Dimension — `dim_customers.sql`

```sql
with customers as (
    select * from {{ ref('int_customers_enriched') }}
)

, final as (
    select
        customer_sk_id
        , customer_nk_id
        , record_source
        , created_at
        , updated_at
        , is_active
        , customer_type
        , customer_name
        , email
        , lifetime_order_count
    from customers
)

select * from final
```

### Dimension — `dim_customers.yml`

```yaml
models:
  - name: dim_customers
    description: >
      Conformed customer dimension combining all source systems.
      One row per customer.
    columns:
      - name: customer_sk_id
        description: Surrogate key for the customer entity.
        data_tests:
          - unique
          - not_null
      - name: customer_nk_id
        description: Natural key from the source system.
        data_tests:
          - not_null
      - name: record_source
        description: Source system identifier.
      - name: created_at
        description: Timestamp when the customer was created.
      - name: updated_at
        description: Timestamp of the last update.
      - name: is_active
        description: Whether the customer is currently active.
        data_tests:
          - not_null
      - name: customer_type
        description: Customer classification.
        data_tests:
          - accepted_values:
              values: ['individual', 'business']
              config:
                severity: warn
      - name: customer_name
        description: Full name of the customer.
      - name: email
        description: Customer email address.
      - name: lifetime_order_count
        description: Total number of orders placed by the customer.
```

### Fact — `fct_orders.sql`

```sql
with orders as (
    select * from {{ ref('int_orders_enriched') }}
)

, final as (
    select
        order_sk_id
        , order_nk_id
        , customer_sk_id
        , product_sk_id
        , record_source
        , order_date
        , created_at
        , order_status
        , order_qty
        , revenue_amount
        , discount_amount
    from orders
)

select * from final
```

### Fact — `fct_orders.yml`

```yaml
models:
  - name: fct_orders
    description: >
      Order fact table at the individual order grain.
      One row per order.
    columns:
      - name: order_sk_id
        description: Surrogate key for the order entity.
        data_tests:
          - unique
          - not_null
      - name: order_nk_id
        description: Natural key from the source system.
        data_tests:
          - not_null
      - name: customer_sk_id
        description: FK to dim_customers.
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_sk_id
      - name: product_sk_id
        description: FK to dim_products.
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_products')
              field: product_sk_id
      - name: record_source
        description: Source system identifier.
      - name: order_date
        description: Date the order was placed.
        data_tests:
          - not_null
      - name: created_at
        description: Timestamp when the order was created.
      - name: order_status
        description: Current status of the order.
        data_tests:
          - accepted_values:
              values: ['pending', 'completed', 'cancelled', 'refunded']
      - name: order_qty
        description: Number of items in the order.
        data_tests:
          - dbt_utils.accepted_range:
              min_value: 0
      - name: revenue_amount
        description: Total revenue amount for the order.
        data_tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              config:
                severity: warn
      - name: discount_amount
        description: Discount applied to the order.
```

### Bridge — `brg_employee_projects.sql`

```sql
with employee_projects as (
    select * from {{ ref('int_employee_projects_enriched') }}
)

, final as (
    select
        employee_sk_id
        , project_sk_id
        , record_source
        , assigned_date
        , role_type
    from employee_projects
)

select * from final
```

### Bridge — `brg_employee_projects.yml`

```yaml
models:
  - name: brg_employee_projects
    description: >
      Bridge table resolving the N:M relationship between
      employees and projects. One row per assignment.
    columns:
      - name: employee_sk_id
        description: FK to dim_employees.
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_employees')
              field: employee_sk_id
      - name: project_sk_id
        description: FK to dim_projects.
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_projects')
              field: project_sk_id
      - name: record_source
        description: Source system identifier.
      - name: assigned_date
        description: Date the employee was assigned to the project.
      - name: role_type
        description: Role of the employee on the project.
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - employee_sk_id
            - project_sk_id
```

## Materialization

- Default: **Table**.
- Use `incremental` when the table meets the threshold in [Incremental Models](../incremental-models.md).

## Testing

- Required: `unique` + `not_null` on `<entity>_sk_id`; `relationships` on `*_sk_id` FKs; `accepted_values` on business-critical fields
- Recommended: `not_null` on business fields; `unit tests` for complex logic

## YAML

- **All columns must be listed** in the YAML file, each with a `description`.
- Use `doc()` blocks for descriptions shared across multiple models.
