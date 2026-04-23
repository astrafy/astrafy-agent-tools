# Intermediate Layer

See [Architecture](../architecture.md) for materialization, naming conventions, and reference rules (`int_`).

## When to Use

The intermediate layer is **mandatory** for every entity that reaches the datamart. Even if no transformation is needed, the intermediate layer creates the surrogate key and preserves the natural key. This ensures every datamart model consumes entities with a consistent key structure.

## Naming

- **`01_prep`**: Source-specific → `int_<source>__<entity>_prep.sql`
- **`02_unioned` and beyond**: Common entities, no source → `int_<entity>_<suffix>.sql`

If two sources produce an entity with the same name, disambiguate by adding context to the entity name (e.g., `int_financial_transactions_unioned`, `int_api_transactions_unioned`). Do **not** keep the source prefix — the entity name itself must be unambiguous project-wide.

## Folder Structure

Intermediate models are organized into numbered subdirectories that reflect the data flow:

```
models/intermediate/
├── 01_prep/
│   └── <source>/
│       ├── int_<source>__<entity>_prep.{sql,yml}
│       ├── int_<source>__<entity>_mapping.{sql,yml}    (optional, accompanies _deduped)
│       └── int_<source>__<entity>_deduped.{sql,yml}    (optional, when dedup needed)
├── 02_unioned/
│   ├── int_<entity>_unioned.{sql,yml}
│   ├── int_<entity>_mapping.{sql,yml}              (optional, accompanies _deduped)
│   └── int_<entity>_deduped.{sql,yml}              (optional, when dedup needed)
├── 03_transformed/
│   ├── int_<entity>_remapped.{sql,yml}             (example — FK canonicalization)
│   ├── int_<entity>_pivoted.{sql,yml}              (example)
│   ├── int_<entity>_agg.{sql,yml}                  (example)
│   └── int_<entity>_double_entry.{sql,yml}         (example)
└── 04_enriched/
    └── int_<entity>_enriched.{sql,yml}
```

## Keys

### Surrogate Keys

Every intermediate model must have a surrogate key (`<entity>_sk_id`) as its primary key, generated with `null_safe_surrogate_key`. The surrogate key is built by concatenating `record_source` (from staging) with the natural key.

**Never generate a surrogate key when the natural key is NULL.** `dbt_utils.generate_surrogate_key` is deterministic — passing `null` produces a fixed hash, which creates a "ghost" sk_id that points to nothing in the parent dimension and silently breaks downstream `relationships` tests.

Use the project macro `null_safe_surrogate_key` (in `macros/null_safe_surrogate_key.sql`) for **every** sk_id and FK sk_id. Before using, verify the macro exists at that path — if missing, create it. It wraps `dbt_utils.generate_surrogate_key` in a NULL guard:

```sql
{% macro null_safe_surrogate_key(natural_key, record_source='record_source') %}
case
    when {{ natural_key }} is null then null
    else {{ dbt_utils.generate_surrogate_key([record_source, natural_key]) }}
end
{% endmacro %}
```

Examples:

```sql
, {{ null_safe_surrogate_key('customer_id', 'record_source') }} as customer_sk_id

-- with a qualified record_source column:
, {{ null_safe_surrogate_key('invoices.company_id_fk', 'invoices.record_source') }} as company_sk_id

-- with an expression as the natural key:
, {{ null_safe_surrogate_key("json_extract_scalar(line_item, '$.ProjectIDFK')") }} as project_sk_id
```

This ensures uniqueness across sources when records from different systems are combined.

**Exceptions:** Utility models (date spines, calendars) do not require surrogate keys.

### Natural Keys

Every intermediate model must also preserve the original natural key as `<entity>_nk_id`. This keeps the source system's identifier available for debugging, auditing, and cross-referencing.

```sql
customer_id as customer_nk_id
```

### When to Create Keys

Surrogate keys and natural keys must be created on the **first intermediate model** built for each entity. This could be `_prep`, `_unioned`, `_enriched`, or whichever model is the entity's entry point into the intermediate layer.

For foreign keys referencing other entities, generate the FK surrogate key in the same model using the same pattern: `null_safe_surrogate_key('<fk_natural_key>', '<record_source_column>')`. This applies to both the entity's own PK and any FK references.


**Never generate a surrogate key when the natural key is NULL.** `dbt_utils.generate_surrogate_key` is deterministic — passing `null` produces a fixed hash, which creates a "ghost" sk_id that points to nothing in the parent dimension and silently breaks downstream `relationships` tests.

Use the project macro `null_safe_surrogate_key` (in `macros/null_safe_surrogate_key.sql`) for **every** sk_id and FK sk_id in the intermediate layer. It wraps `dbt_utils.generate_surrogate_key` in a NULL guard:

```sql
, {{ null_safe_surrogate_key('<natural_key_col>', '<record_source_column>') }} as <entity>_sk_id

-- with a qualified record_source column:
, {{ null_safe_surrogate_key('invoices.company_id_fk', 'invoices.record_source') }} as company_sk_id

-- with an expression as the natural key:
, {{ null_safe_surrogate_key("json_extract_scalar(line_item, '$.ProjectIDFK')") }} as project_sk_id
```

Do not call `dbt_utils.generate_surrogate_key` directly in intermediate models. The same rule applies to PK generation when the natural key can legitimately be null (rare — usually a sign the row should be filtered out instead).

## Stage Details

### 01_prep

The prep layer takes one staging source and produces a conformed entity ready to be unioned with other sources. The goal is to create the **conformed dimension** — the entity with the columns, types, and grain needed downstream. Responsibilities:

1. **Deduplicate** the source data (if needed)
2. **Create ALL surrogate keys and natural keys** — PK (`<entity>_sk_id`, `<entity>_nk_id`) and FKs (`<related_entity>_sk_id`) using `null_safe_surrogate_key('<natural_key>', '<record_source_column>')`
3. **Apply source-specific transformations** needed to conform the entity (field mappings, status normalization, unit conversion, etc.)
4. **Change grain** when the source grain doesn't match the target entity grain (e.g., aggregate correction entries, collapse detail rows to the target grain). Document the grain change in the model description and test `unique` on the new grain.
5. **Flatten arrays/JSON** when a staging model contains nested structures (JSON columns, repeated fields). Unnest them into one row per element. This changes the grain from the parent entity to the child entity — name the model after the child entity, not the parent.
6. **Join to other entities within the same source** when needed for enrichment (e.g., joining timesheets to tasks for classification tags, joining invoices to credit notes for allocation). Cross-source joins are not allowed — each prep model handles a single source system.
7. **No cross-source logic** — each `_prep` model handles a single source system.

**Minimal prep model:** If the entity requires no transformation beyond key creation, the prep model still exists — it creates the surrogate key, preserves the natural key, and selects the columns needed downstream.

### 02_unioned

The unioned layer stacks prepared entities from different sources into a single consolidated entity:

1. **Union** the `_prep` models using `union all` with explicit column lists
2. **Create surrogate keys** for the combined result if not already created in `_prep`

For deduplication, mapping, and remapped patterns, see [Intermediate Dedup Patterns](2a-intermediate-dedup.md).

### Filtered Pattern

The `_filtered` suffix is used when a model subsets data by business criteria (e.g., active records only, valid status only, exclude test data).

`_filtered` can be applied at **any stage** — prep, unioned, or transformed — wherever the filtering is needed. Place it in the folder of the stage where it logically belongs:

- In `01_prep/`: `int_<source>__<entity>_filtered` — filter a single source before unioning
- In `02_unioned/`: `int_<entity>_filtered` — filter after union or dedup
- In `03_transformed/`: `int_<entity>_filtered` — filter as part of a transformation chain

### 03_transformed

Any additional transformation that doesn't fit prep or unioned. Common patterns:

| Suffix | Purpose |
|--------|---------|
| `_pivoted` | Transposing rows to columns |
| `_agg` | Pre-aggregating to fix fan-outs before a join |
| `_double_entry` | Duplicating rows for debit/credit pairs (GL logic) |
| `_spine` | Joining to a date spine to fill missing days/gaps |
| `_filtered` | Subsetting rows by business criteria |
| `_remapped` | Resolving FKs to canonical sk_ids via a `_mapping` table (when the source carries non-canonical duplicates) |

### 04_enriched

Adding columns/attributes to a main entity from other entities (e.g., enriching a customer with their latest contract info). Typically feeds dimensions.

**When to use:** Use 04_enriched when the enrichment is consumed by **2+ downstream models**. If only one datamart model needs the enrichment, do the join there.

## Materialization

- Default: **View**.
- Use `table` if the model is used in multiple places.
- Use `incremental` when downstream is incremental and window functions/grouping/complex joins block predicate pushdown.

## Testing

| Required | Recommended |
|----------|-------------|
| `unique` + `not_null` on `<entity>_sk_id` (especially when re-graining) | `accepted_values` on derived fields; `not_null` on critical `*_sk_id` FKs |

## YAML

- Only include columns that have tests. Do not list columns without tests — keep the YAML lean.
- Always add a `description` for the model itself.
