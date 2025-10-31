@echo off
REM Minimal installer for Codex MCP (no emojis, plain ASCII)

setlocal enabledelayedexpansion

echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo ERROR: Python not found in PATH. Install Python 3.8+ and retry.
  exit /b 1
)

echo [2/4] Preparing directories...
set "CODEX_DIR=%USERPROFILE%\.claude\codex_mcp"
if not exist "%CODEX_DIR%" mkdir "%CODEX_DIR%" 2>nul

echo [3/4] Copying files...
if not exist "codex_mcp_server.py" (
  echo ERROR: codex_mcp_server.py not found in current directory.
  exit /b 1
)
copy /Y "codex_mcp_server.py" "%CODEX_DIR%\" >nul
if exist "requirements.txt" copy /Y "requirements.txt" "%CODEX_DIR%\" >nul
if exist "codex_config.json" copy /Y "codex_config.json" "%CODEX_DIR%\" >nul

echo [4/4] Installing Python dependencies...
pushd "%CODEX_DIR%" >nul
if exist requirements.txt (
  pip install -r requirements.txt --quiet || pip install -r requirements.txt --user --quiet
) else (
  echo NOTE: requirements.txt not found. Skipping pip install.
)
popd >nul

echo.
echo Done. Add this to Claude Desktop config (claude_desktop_config.json):
echo {
echo   "mcpServers": {
echo     "codex-enforcer": {
echo       "command": "python",
echo       "args": ["%CODEX_DIR%\\codex_mcp_server.py"],
echo       "env": { "PYTHONUNBUFFERED": "1" }
echo     }
echo   }
echo }
echo.
echo Then restart Claude Desktop.
exit /b 0

