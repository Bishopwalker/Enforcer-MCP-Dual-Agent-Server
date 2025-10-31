# Enforcer Coding AI Assistant

See WHAT_WE_DO.md for workflow and tools.

Download
- Git clone: `git clone -b gang-gang https://gitlab.com/bishop8-group/enforcer-coding-ai-assistant.git`
- CI artifact: after a successful pipeline, download `dist/enforcer-coding-ai-assistant.zip` from the latest job artifacts.

Run (Windows)
- `run_enforcer.bat` (creates `.venv` if missing and starts the MCP server)

Run (CLI quick check)
- `python -c "import sys; sys.path.insert(0,'.'); from codex_mcp_server import CodexEnforcer; E=CodexEnforcer(); print(E.config.get('rules_dir'))"`

CI Status
- Branch: `gang-gang` pipeline runs parallel analysis and build.
- Pipeline badge:
  - ![pipeline status](https://gitlab.com/bishop8-group/enforcer-coding-ai-assistant/badges/gang-gang/pipeline.svg)

