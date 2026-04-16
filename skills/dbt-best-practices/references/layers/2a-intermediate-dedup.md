# Intermediate Dedup & Mapping Patterns

## Deduplication & Mapping Pattern

When duplicate records need to be merged (e.g., the same company appears in multiple sources), and downstream tables hold foreign keys pointing to those duplicates, use this sequential pattern:

`_unioned` → `_mapping` → `_deduped`

1. **`_unioned` stays clean**: Only unions sources and creates surrogate keys. No matching/canonical logic.

2. **Create `_mapping`** (same folder): Reads from `_unioned`. Contains the matching logic (e.g., window function to determine the canonical record). Outputs a lookup with original and canonical `sk_id`, so other entities (e.g., deals referencing companies) can resolve their foreign keys to the correct record.

3. **Create `_deduped`** (same folder): Reads from both `_unioned` and `_mapping`. Joins them to keep only canonical records.

**Important:** The deduplication logic (partition key, ordering, canonical record selection) is a business decision. It must be specified by the user — never infer or assume the dedup strategy. Always ask the user how duplicates should be resolved before implementing a `_mapping` model.

**Where to apply**: If dedup happens at the source level, `_mapping` and `_deduped` go in `01_prep/`. If dedup happens after unioning across sources, they go in `02_unioned/`.

## Consuming Dedup Models Downstream

When a downstream entity holds a FK to a deduped entity, the FK **must** be resolved through the `_mapping` table. There are two valid ways to do this:

1. **Preferred — `_remapped` intermediate** (`03_transformed/int_<entity>_remapped`): create an intermediate model that reads `int_<entity>_unioned`, joins each FK to its corresponding `_mapping`, and exposes the resolved sk_ids. All downstream facts/dims then ref the `_remapped` model. This centralizes the resolution rule and avoids every fact re-implementing the join. Use this whenever (a) more than one fact/dim consumes the entity, or (b) the source carries multiple FKs that need remapping.

   ```sql
   -- int_invoice_lineitems_remapped.sql
   with line_items as (
       select * from {{ ref('int_invoice_lineitems_unioned') }}
   ),
   projects_mapping as (
       select * from {{ ref('int_projects_mapping') }}
   )
   select
       line_items.field1
       , line_items.field2
       , coalesce(projects_mapping.canonical_project_sk_id, line_items.project_sk_id) as project_sk_id
   from line_items
   left join projects_mapping
       on line_items.project_sk_id = projects_mapping.original_project_sk_id
   ```

   Coalesce to the original sk_id so rows with no mapping entry are preserved and surface as data-quality failures via the `relationships` test, rather than being silently dropped.

2. **Fallback — inline join in the fact/dim**: for a strictly one-off consumer with a single FK to remap, the join can be done directly in the fact:

   ```sql
   left join {{ ref('int_customers_mapping') }} as customers_mapping
       on fact_table.company_sk_id = customers_mapping.original_company_sk_id
   ```

   Select `customers_mapping.canonical_company_sk_id` as the resolved FK. If a second consumer ever appears, promote the logic to a `_remapped` model.

Either way, the resolved FK **must** carry a `relationships` test to the corresponding `dim_<entity>` so the resolution is verified.
