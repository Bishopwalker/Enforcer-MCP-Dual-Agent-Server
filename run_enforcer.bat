@echo off
setlocal
if not exist .venv (py -3 -m venv .venv)
call .\.venv\Scripts\activate
python codex_mcp_server.py
