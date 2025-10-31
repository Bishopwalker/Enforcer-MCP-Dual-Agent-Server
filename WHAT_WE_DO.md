Dual‑Agent Quality Workflow (Claude + Codex MCP)

Overview
- Purpose: deliver fast feature development with strict, automated cleanup.
- Roles:
  - Claude (Builder): implements features, explores, uses larger context.
  - Codex MCP (Enforcer): snapshots, cleans debug/noise, validates, restores, and produces auditable reports.

What Codex Does
- Cleans debug output (print/console, debugger) with keep‑markers available.
- Removes commented‑out dead code with careful heuristics (keeps docblocks).
- Validates file length (configurable, with exemptions for generated/large files).
- Enforces only inside allowed roots (safety fence).
- Persists artifacts for both agents under `.codex/`:
  - `.codex/snapshots/` — content snapshots for later restore.
  - `.codex/reports/` — enforcement/prune reports with diffs and inputs.
  - `.codex/activity.log` — action log (JSON lines).
  - `.codex/context_index.json` — directory tree + dependency metadata.

Safety and Scope
- Allowed roots define where Codex can read/write; everything else is ignored.
- Rules are loaded from `codex_config.json` plus a centralized rules directory (e.g., your Claude folder).
- No destructive actions without backups:
  - Enforcement is reversible via snapshots.
  - Prune applies create timestamped backups under `.codex/prune_backups/`.

Setup
1) Install the MCP server files locally and register with Claude Desktop:
   - Minimal installer: run `install_codex_minimal.bat` from this folder.
   - In Claude config (`claude_desktop_config.json`), add an MCP entry pointing `args` to `codex_mcp_server.py` and restart Claude.
2) Point Codex to your centralized rules folder (e.g., `C:\Users\<you>\.claude`).
3) Set allowed roots to your active projects.

Rules Source (Claude Folder)
- Codex merges rules from JSON files in a designated folder:
  - `codex_rules.json` or `codex_config.json` in that folder.
- Precedence: environment variable `CLAUDE_RULES_DIR` (or `CODEX_RULES_DIR`) → `rules_dir` in workspace `codex_config.json` → `~/.claude` if present.

Context Initialization
- Goal: write a compact project map and dependency metadata that both agents can use.
- Run tool: `codex_context_init(root="<PROJECT_ROOT>", max_depth=3)`
- Output: `.codex/context_index.json`

Daily Workflow (Task Splitting)
1) Snapshot before changes: `codex_snapshot(paths=["<ROOT or files>"])`
2) Claude builds and tests.
3) Dry‑run cleanup: `codex_enforce(paths=["<ROOT or files>"], dry_run=true)` and review the report under `.codex/reports/`.
4) Apply cleanup: `codex_enforce(paths=["<ROOT or files>"])`.
5) Validate: `codex_validate(paths=["<ROOT or files>"])` (target score ≥ 9.0).
6) Restore if needed: `codex_restore(paths=["<files>"])`.

Tools Cheat Sheet
- `codex_snapshot` — capture file content and hashes for restore.
- `codex_enforce` — remove debug/dead code, enforce limits; supports `dry_run`.
- `codex_validate` — compute score/issues without writes.
- `codex_restore` — restore from the latest (or specified) snapshot.
- `codex_version` — current config and version.
- `codex_activity` — tail recent events from `.codex/activity.log`.
- `codex_set_allowed_roots` — update the safety fence of writable roots.
- `codex_set_rules_dir` — point to centralized rules (e.g., your Claude folder).
- `codex_context_index` / `codex_context_init` — generate `.codex/context_index.json`.
- `codex_prune_dryrun` — analyze and propose extra files/unused symbols (no writes).
- `codex_prune_apply` — apply prune (backup first), optional language targeting.
  - Requires `confirm=true`. The underlying apply will not execute without explicit confirmation (safety guard).

Triple Verification (Rule Enforcement Loop)
- Purpose: prevent agents from drifting from instructions by cross‑checking work.
- Steps per titled run (`title`, `module` recommended for logs):
  1) Builder self‑attests: `codex_attest_submit(agent="builder", rules_id, rules_hash, checklist, evidence, title, module)`
  2) Enforcer peer‑attests: `codex_attest_submit(agent="enforcer", ...)` after enforce/validate.
  3) Builder re‑checks: `codex_attest_submit(agent="builder_recheck", ...)` reviewing enforcer’s report.
  4) Finalize gate: `codex_verify_attestations(title, module)` then `codex_gate_finalize(title, module, rules_id)`.
- All attestations include the same `rules_id`/`rules_hash` from `codex_rules_contract_get`.

Central Logs Hub (Enforcer Logs)
- Location: `<rules_dir>/enforcer_logs/<YYYY-MM-DD>/<module>/<title>/` if `rules_dir` is configured; otherwise `.codex/enforcer_logs/...`.
- Contents per run:
  - `summary.md` — quick human summary (kind, score, counts).
  - `enforce_*.json`, `prune_dryrun_*.json`, `prune_apply_*.json`, `context_*.json` — detailed artifacts.
  - Graphs and context: Mermaid `.mmd` and readable `.md` files when using `codex_rag_context`.
- Suggested naming:
  - Module examples: `frontend_src`, `backend_python`, `infra`, etc.
  - Title examples: `startup_issue_fix`, `compact_prune_src`, `dead_code_cleanup`.

Dry‑Run vs Apply
- Dry‑run: computes issues, planned changes, diffs, and writes a report only.
- Apply: writes cleaned content; reports include diffs and inputs.
- Use dry‑run first to review changes; then apply with confidence.

Prune Analysis and Caveats
- Purpose: identify extra files not reachable from entry points and top‑level symbols never referenced.
- Heuristics: static import graph for Python + JS/TS; naive stem‑to‑file mapping for bare imports.
- Limitations: dynamic imports, reflection, file‑based routing, framework loaders may not be detected.
- Best practice: provide explicit `entry_points` for accuracy and review the report before applying.

Recovery Paths
- Snapshots: revert file content to an earlier state via `codex_restore`.
- Prune backups: every delete/edit during prune apply is backed up under `.codex/prune_backups/<timestamp>/`.

Configuration Keys (codex_config.json)
- `mode` — strict|lenient (how aggressively to remove debug lines).
- `max_file_lines` — max allowed lines per file.
- `length_exempt_patterns` — globs exempt from line‑length checks (e.g., generated/JSON/MD).
- `remove_prints` — remove print/console (tests can be exempted).
- `ignore_tests_for_prints` — keep debug prints in tests.
- `remove_todos` — remove TODO/DEBUG comments (off by default).
- `preserve_docblocks` — keep structured doc comments.
- `extensions` — file extensions included in scans and indexing.
- `include`/`exclude` — path filters.
- `allowed_roots` — safety fence for read/write operations.
- `rules_dir` — external rules directory for centralized policy.

Known Behaviors and Safeguards
- Python block safety: after cleanup, Codex inserts `pass` when a block would be empty to avoid `IndentationError`.
- Keep‑marker: preserve a specific debug line by adding `codex: keep` to that line (Python: comment; JS/TS: comment).
- Large project tuning: line‑length limit and exemptions should exclude generated and non‑source files.

Troubleshooting
- MCP server not visible in Claude: verify the config entry, Python in PATH, and restart Claude Desktop.
- Excessive “extra files” in prune: pass explicit entry points and/or restrict roots to the relevant subtree.
- Unexpected cleanup changes: re‑run with `dry_run=true`, review the diff report, add keep‑markers, and re‑apply.
