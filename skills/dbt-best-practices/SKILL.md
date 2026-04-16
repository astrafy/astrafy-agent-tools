---
name: dbt-best-practices
description: Kimball/dimensional dbt best practices for this repo. Use whenever creating, editing, reviewing, or testing any dbt model, snapshot, seed, macro, or test. Also use when answering questions about data modeling patterns, surrogate keys, SCD2, incremental strategies, or layer architecture in this project.
---

# dbt Best Practices

Approach: **Kimball / dimensional modeling (star schema)**.

## Creating New Models

### Step 1: Decide what to build

Read [Architecture](references/architecture.md) to determine:
- Which models to create (layer, prefix, naming convention)
- What each model queries (flow rules)
- Where to place files (folder structure)

### Step 2: Write the model or snapshot files

Read these three references, then create the required files:

1. [General Rules](references/general-rules.md) — key rules, BigQuery optimization, testing by column pattern, severity, useful packages
2. [Naming & Style](references/naming-and-style.md) — column naming conventions, SQL/YAML/Jinja style
3. The corresponding layer file:

| Model prefix | Sub-layer | Layer file |
|-------------|-----------|------------|
| `seed_`, `raw_` | | [Raw](references/layers/0-raw.md) |
| `stg_` (incl. `stg_*_scd2` snapshots) | | [Staging](references/layers/1-staging.md) |
| `int_` | | [Intermediate](references/layers/2-intermediate.md) |
| `dim_`, `dim_*_scd2`, `fct_`, `brg_`, `util_` | 01_core | [Datamart](references/layers/3-datamart.md) |
| `agg_`, `wide_` | 02_enriched | [Datamart](references/layers/3-datamart.md) |
| `rpt_`, `retl_`, `ai_`, `comp_`, `rec_` | 03_consumption | [Datamart](references/layers/3-datamart.md) |

For regular models, create matching `.sql` and `.yml` files. For `stg_*_scd2`, create a dbt snapshot SQL definition and follow the snapshot-specific guidance in the staging reference.

## SCD2 Work

When creating or editing any `*_scd2` artifact, read all of:

1. [General Rules](references/general-rules.md)
2. [Naming & Style](references/naming-and-style.md)
3. [Staging](references/layers/1-staging.md) — for the `stg_*_scd2` snapshot definition
4. [Intermediate](references/layers/2-intermediate.md) — for the `int_` model that consumes the snapshot
5. [Datamart](references/layers/3-datamart.md) — for the `dim_*_scd2`

A `dim_*_scd2` **must** be built from an `int_` model that consumes a `stg_*_scd2` snapshot. Before building the dimension, verify the upstream snapshot and intermediate model exist — if missing, create them first.

## Editing Existing Models

Identify the layer from the model's prefix, then read:

1. [General Rules](references/general-rules.md)
2. [Naming & Style](references/naming-and-style.md)
3. The corresponding layer file (see table above)

## Reviewing / Auditing Models

Read [General Rules](references/general-rules.md), [Naming & Style](references/naming-and-style.md), the corresponding layer file, and the [Review Checklist](references/review-checklist.md).
Walk through each checklist item and report violations. If the layer is unclear, infer it from the model prefix; if there is no prefix, ask the user.

## Macros

Read [General Rules](references/general-rules.md).

## Adding or Fixing Tests Only

Read [General Rules](references/general-rules.md) (testing section) and the corresponding layer file for layer-specific testing requirements.

## Performance / Incremental Work

Read [General Rules](references/general-rules.md) (partitioning & clustering) and [Incremental Models](references/incremental-models.md).

## Deduplication / Mapping Patterns

When working with dedup, mapping, or remapped models in the intermediate layer, read [Intermediate Dedup Patterns](references/layers/2a-intermediate-dedup.md) in addition to the intermediate layer file.

## Before Finishing

After creating or editing any model, build it with `uv run dbt build --select <model>` (append `+` for downstream if relevant). Use the `bq` CLI against the dev project/datasets for data checks. Do not consider the task complete until the model builds and its tests pass.

## When to Ask the User

Always ask the user before making assumptions on:

- **Business logic decisions**: dedup strategy, grain definition, accepted values lists, SCD type
- **Ambiguous entity naming**: when multiple sources produce entities with the same name
- **Model placement**: whether to create a new intermediate model vs. inline logic in the datamart
- **Grain changes**: when a transformation changes the grain of the data
