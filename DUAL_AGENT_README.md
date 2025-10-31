Dual‑Agent MCP Setup — Codex (Enforcer) + Claude (Builder)

Overview
- Codex MCP server enforces pristine code quality; Claude builds features.
- Artifacts are written under `.codex/` for shared visibility between tools.

Install
- Point Claude Desktop’s MCP to `codex_mcp_server.py` or run `install_codex.bat`.
- Ensure Python is available and `codex_config.json` exists alongside the server.

Safety Boundaries
- Codex only operates within `allowed_roots` from `codex_config.json`.
- Update at runtime: `codex_set_allowed_roots(roots=["<ABSOLUTE_PATH>", ...])`.

Key Tools
- `codex_snapshot(paths=[...])` — Capture content+hash snapshot; persists to `.codex/snapshots/`.
- `codex_enforce(paths=[...], dry_run=true|false)` — Clean up code; dry‑run previews changes without writing.
- `codex_validate(paths=[...])` — Score and issues only; no writes.
- `codex_restore(paths=[...], snapshot_id=optional)` — Restore files from latest/specified snapshot.
- `codex_version()` — Show version and active configuration.
- `codex_activity(limit=50)` — Show recent actions from `.codex/activity.log`.
- `codex_context_index(root=..., max_depth=3)` — Build universal context index to `.codex/context_index.json`.

Dry‑Run Enforce (what it is)
- A “dry run” enforcement analyzes and stages potential changes but does not write files.
- It produces a report with:
  - `issues` found (e.g., line‑length, debug statements)
  - `fixes_applied` summary (what would change)
  - `files_modified` list (what would be touched)
  - `diffs` per file in the persisted report JSON under `.codex/reports/`
- Use this to safely preview and review diffs before applying real changes.

Recommended Workflow
- Set `allowed_roots` to your AI workspace and target project directories.
- Run `codex_context_index(root=...)` to generate a shared context.
- For each change:
  1) `codex_snapshot(paths=[...])`
  2) Build/test with Claude
  3) `codex_enforce(paths=[...], dry_run=true)` and review the report
  4) `codex_enforce(paths=[...])` to apply
  5) `codex_validate(paths=[...])` to confirm ≥9.0

Config Highlights (codex_config.json)
- `max_file_lines`: default 800; adjust as needed
- `remove_prints`: true (keeps in tests if `ignore_tests_for_prints=true`)
- `remove_todos`: false (keep TODO/DEBUG comments by default)
- `preserve_docblocks`: true (e.g., `/** ... */`)
- `extensions`: file types included in scans (Python, JS/TS, Go, Rust, etc.)
- `exclude`: skip large or generated directories (node_modules, venv, build)

Notes
- Use inline marker `codex: keep` to preserve a specific print/console line.
- Reports/snapshots are designed to be readable by both Claude and ChatGPT sessions.
