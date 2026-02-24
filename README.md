# astrafy-agent-tools

A central hub for Astrafy's AI agent tools: skills, MCPs, commands, hooks, and more. Includes a CLI to download any skill directly into your project.

## Available skills

| Skill | Path | Description |
|-------|------|-------------|
| dbt | `skills/dbt` | SQL style guide, BigQuery optimization, naming conventions, YAML standards |
## Install a skill

Run a single command to download a skill into your project — no clone required:

```bash
# For Claude
uvx --from git+https://github.com/astrafy/astrafy-agent-tools.git astrafy-agent-tools skills/dbt --dest .claude/

# For Cursor
uvx --from git+https://github.com/astrafy/astrafy-agent-tools.git astrafy-agent-tools skills/dbt --dest .cursor/

# For other agents (not all included are compatible)
uvx --from git+https://github.com/astrafy/astrafy-agent-tools.git astrafy-agent-tools skills/dbt --dest .agents/
```

This fetches the `skills/dbt` folder from the repository and writes it to `./<agent>/<skill>/` in your current directory.

You can replace `skills/dbt` with any path in the repo, and `--dest` with wherever you want the files to land (defaults to `./<agent>/`).

By default the CLI **refuses to overwrite** existing local files. If any target file already exists, it lists the conflicts and exits. To allow overwriting, pass `--overwrite`:

```bash
uvx --from git+https://github.com/astrafy/astrafy-agent-tools.git astrafy-agent-tools skills/dbt --dest .claude/ --overwrite
```

## System-wide install

If you use the CLI frequently, install it globally so you can call `astrafy-agent-tools` directly without `uvx`:

```bash
uv tool install git+https://github.com/astrafy/astrafy-agent-tools.git
```

Then use it anywhere:

```bash
astrafy-agent-tools skills/dbt --dest .claude/
```

## Developer setup

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Getting started

```bash
git clone https://github.com/astrafy/astrafy-agent-tools.git
cd astrafy-agent-tools

uv sync

uv run pre-commit install
```

### Run the CLI locally

```bash
uv run astrafy-agent-tools skills/dbt --dest /tmp/test
```
