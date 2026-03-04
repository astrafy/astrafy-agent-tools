---
name: dbt-best-practices
description: dbt data modeling best practices following Kimball/dimensional modeling. Use when writing or reviewing dbt models, adding tests, choosing materializations, or following SQL/YAML/Jinja style conventions. Covers architecture layers, naming conventions, testing strategy, SQL style, and BigQuery optimization.
---

# dbt Best Practices

Approach: **Kimball / dimensional modeling (star schema)**.

## Creating New Models

### Step 1: Decide what to build

Read [Architecture](references/architecture.md) to determine:
- Which models to create (layer, prefix, naming convention)
- What each model queries (flow rules)
- Where to place files (folder structure)

### Step 2: Write the `.sql` and `.yml` files

Read these three references, then create the files:

1. [General Rules](references/general-rules.md) — key rules, BigQuery optimization, testing by column pattern, severity, useful packages
2. [Naming & Style](references/naming-and-style.md) — column naming conventions, SQL/YAML/Jinja style
3. The corresponding layer file:

| Model prefix | Layer file |
|-------------|------------|
| `seed_`, `raw_` | [Raw](references/layers/0-raw.md) |
| `snp_`, `stg_` | [Staging](references/layers/1-staging.md) |
| `int_` | [Intermediate](references/layers/2-intermediate.md) |
| `dim_`, `fct_`, `brg_`, `mart_`, `agg_`, `rpt_`, `util_` | [Datamart](references/layers/3-datamart.md) |

## Editing Existing Models

Identify the layer from the model's prefix, then read:

1. [General Rules](references/general-rules.md)
2. [Naming & Style](references/naming-and-style.md)
3. The corresponding layer file (see table above)
