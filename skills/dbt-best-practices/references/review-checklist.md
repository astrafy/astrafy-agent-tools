# Review Checklist

Walk through each item below when auditing a model. Report any violations found.

## Structure & Naming

- [ ] Model file has a matching `.yml` file with the same name
- [ ] Model name follows the correct prefix for its layer (`stg_`, `int_`, `dim_`, `fct_`, etc.)
- [ ] Model lives in the correct folder per the architecture
- [ ] All column names follow naming conventions (snake_case, correct suffixes)
- [ ] No abbreviations in column or alias names
- [ ] Models are pluralized (`dim_customers`, not `dim_customer`)

## SQL Quality

- [ ] No `SELECT *` except in import CTEs and the final `select * from <final_cte>`
- [ ] All `ref()` and `source()` calls are in import CTEs at the top
- [ ] Import CTEs are named after the model they reference
- [ ] Functional CTEs have descriptive verb-based names
- [ ] Joins are explicit (`inner join`, `left join` — no implicit joins or `right join`)
- [ ] Columns are prefixed with table name when joining 2+ tables
- [ ] `group by all` used instead of listing column numbers
- [ ] Keywords are lowercase
- [ ] Leading commas
- [ ] Table aliases are explicit without abbreviations

## Layer-Specific

- [ ] **Staging**: All fields are cast (even if type is unchanged); `record_source` is first column; no joins
- [ ] **Intermediate**: Has surrogate key (`<entity>_sk_id`) via `null_safe_surrogate_key`; natural key preserved as `<entity>_nk_id`
- [ ] **Datamart**: Refs only `int_` models (01_core); all columns listed in YAML with descriptions

## Refs & Flow

- [ ] Model only references allowed upstream layers (see architecture flow rules)
- [ ] No circular dependencies
- [ ] `materialization` and `tags` are only set when they differ from `dbt_project.yml` defaults

## Testing

- [ ] PK has `unique` + `not_null` tests
- [ ] FK `*_sk_id` columns have `not_null`; datamart FKs also have `relationships` tests
- [ ] Boolean columns have `not_null`
- [ ] Categorical columns (`*_type`, `*_status`) have `accepted_values`
- [ ] Monetary columns have `dbt_utils.accepted_range`
- [ ] Uses `data_tests` key (not deprecated `tests`)

## YAML

- [ ] Model has a `description`
- [ ] Pre-datamart: only columns with tests are listed
- [ ] Datamart: all columns are listed with descriptions
- [ ] Multiline descriptions use folded block scalars (`>`)
