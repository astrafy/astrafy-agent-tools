---
name: dimensional-erd
description: Rules for editing dbt models under `models/datamart/01_core/` so the auto-generated ERD (`erd/output.d2` + `.svg`) stays valid. Use this whenever you add, rename, modify, or touch any model (sql or yml) under `models/datamart/01_core/`, or when the user mentions ERD, relationships, group tags, `generate_erd.py`, or a failing `generate-erd` / `dbt-docs-generate` pre-commit hook. The script hard-fails the commit if a 01_core model is missing a group tag or has more than one — so assume this skill applies by default for any 01_core edit, even if the user doesn't mention the ERD.
---

# ERD rules for `models/datamart/01_core/`

The repo auto-generates a conceptual ERD from every model under
`models/datamart/01_core/` via `scripts/generate_erd.py`, wired into
`.pre-commit-config.yaml` as two hooks: `dbt-docs-generate` (refreshes
`target/catalog.json`) and `generate-erd` (runs the script). Outputs:
`erd/output.d2` and `erd/output.svg`.

The script reads `manifest.json` + `catalog.json`, then **discards** dbterd's
own relationship detection and redraws arrows purely from each model's
`meta.relationships`. It also groups nodes in the diagram by model tag.

Two contracts must hold for every 01_core model. Violations cause pre-commit
to fail (`sys.exit`) or silently regress the ERD.

## Rule 1 — Exactly one group tag

`scripts/generate_erd.py` defines:

```python
GROUP_TAGS = [
    "google_workspace", "finance", "human_resources",
    "project_management", "utils", "dimension",
]
```

Every model in 01_core **must** have exactly one of these tags. Zero tags or
two tags both cause a hard failure listing the offending models.

Put the tag under `config.tags` (project convention — matches
`fct_expenditures.yml`, `dim_projects.yml`, etc.). Example:

```yaml
models:
  - name: fct_new_thing
    description: ...
    config:
      tags:
        - finance
```

The tag does double duty: validation + diagram grouping (each tag becomes a
visual cluster in the SVG).

Quick local sanity check before committing:

```bash
rg -l '^\s*- (finance|human_resources|project_management|utils|dimension|google_workspace)$' models/datamart/01_core | sort -u
```

## Rule 2 — Declare FK arrows in `config.meta.relationships`

The ERD's arrows come from `config.meta.relationships` on the *source* (FK-holding)
model. This is separate from dbt's column-level `relationships` data test —
keep both: one draws the diagram, the other enforces referential integrity.

Shorthand (when FK column name is the same on both sides):

```yaml
models:
  - name: fct_employee_absences
    config:
      tags:
        - human_resources
      meta:
        relationships:
          - to: dim_employees
            column: employee_email
            type: many-to-one
```

Explicit (different column names):

```yaml
    config:
      tags:
        - project_management
      meta:
        relationships:
          - to: dim_employees
            from_column: owner_email
            to_column: employee_email
            type: many-to-one
```

Accepted `type` values: `one-to-one`, `one-to-many`, `many-to-one` (default),
`many-to-many`. Any other value causes the script to exit with an error.

For **nullable FKs**, add `optional: true` to the relationship entry. This
switches the target-side arrowhead from the "required" crow's-foot variant to
the nullable one (`cf-one-required` → `cf-one`, `cf-many-required` → `cf-many`)
so the diagram reflects that the FK can be null.

```yaml
config:
  meta:
    relationships:
      - to: dim_deals
        column: deal_sk_id
        type: many-to-one
        optional: true   # project may have no deal
```

Default is `optional: false`. Use it alongside (not instead of) dbt's
column-level `relationships` test — the test should also be marked
`severity: warn` or the column `not_null` dropped when the FK is nullable.

Working references:
- `models/datamart/01_core/human_resources/fct_employee_absences.yml` (shorthand)
- `models/datamart/01_core/project_management/dim_projects.yml` (multiple targets)

## Regenerating the ERD

After changing relationships, tags, or adding/renaming models, regenerate and
commit the outputs:

```bash
uv run pre-commit run generate-erd --all-files
```

This also runs `dbt-docs-generate` via the hook chain. Fallback if you want
to run pieces manually:

```bash
uv run dbt docs generate -s path:models/datamart/01_core/
uv run python scripts/generate_erd.py
```

Stage `erd/output.d2` and `erd/output.svg` along with the model changes.

## Troubleshooting

| Script output | Fix |
|---|---|
| `Models with none of the required group tags ...: [...]` | Add one tag from `GROUP_TAGS` under `config.tags` for each listed model. |
| `Models tagged with more than one group tag: ...` | Remove the extra group tag; keep exactly one. Non-group tags are fine. |
| `warn: ... -> unknown model \`X\` (skipped)` | Target model isn't in 01_core or was renamed. Update `to:` or remove the entry. |
| `warn: ... missing column(s) (skipped)` | Relationship entry lacks `column` or both `from_column`+`to_column`. |
| `error: unknown relationship type \`X\` on ...` | `type:` isn't one of the four accepted cardinalities — fix it. |
| `error: \`d2\` not found on PATH` | Install d2 locally, or re-run with `--no-svg` if only the `.d2` is needed. |

## Scope

This skill applies **only** to `models/datamart/01_core/`.
