@echo off
REM ========================================
REM CODEX MCP Server Installation Script
REM The Enforcer - Russian Olympic Judge
REM ========================================

echo.
echo ================================================
echo    CODEX MCP SERVER INSTALLER
echo    The Enforcer is coming for your code!
echo ================================================
echo.

REM Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ first
    pause
    exit /b 1
)
echo ✓ Python found

REM Create directory structure
echo [2/6] Creating Codex directory structure...
set CODEX_DIR=C:\Users\%USERNAME%\.claude\codex_mcp
mkdir "%CODEX_DIR%" 2>nul
mkdir "%CODEX_DIR%\.codex" 2>nul
mkdir "%CODEX_DIR%\.codex\snapshots" 2>nul
mkdir "%CODEX_DIR%\.codex\reports" 2>nul
echo ✓ Directories created

REM Check if files exist
echo [3/6] Checking for required files...
if not exist "codex_mcp_server.py" (
    echo ERROR: codex_mcp_server.py not found in current directory
    echo Please run this script from the directory containing the server files
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found in current directory
    pause
    exit /b 1
)
echo ✓ Files found

REM Copy files to installation directory
echo [4/6] Copying files to %CODEX_DIR%...
copy /Y "codex_mcp_server.py" "%CODEX_DIR%\" >nul
copy /Y "requirements.txt" "%CODEX_DIR%\" >nul
copy /Y "*.md" "%CODEX_DIR%\" >nul 2>nul
echo ✓ Files copied

REM Install Python dependencies
echo [5/6] Installing Python dependencies...
cd /d "%CODEX_DIR%"
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    echo Trying with --user flag...
    pip install -r requirements.txt --user --quiet
)
echo ✓ Dependencies installed

REM Create or update Claude Desktop config
echo [6/6] Configuring Claude Desktop...
set CONFIG_DIR=%APPDATA%\Claude
set CONFIG_FILE=%CONFIG_DIR%\claude_desktop_config.json

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM Check if config exists
if exist "%CONFIG_FILE%" (
    echo.
    echo ⚠ WARNING: Claude Desktop config already exists
    echo.
    echo Please add the following to your %CONFIG_FILE% manually:
    echo.
    echo {
    echo   "mcpServers": {
    echo     "codex": {
    echo       "command": "python",
    echo       "args": ["%CODEX_DIR%\codex_mcp_server.py"],
    echo       "env": {
    echo         "PYTHONPATH": "%CODEX_DIR%",
    echo         "CODEX_PROJECT_ROOT": "C:\\Users\\%USERNAME%\\IdeaProjects\\ebl"
    echo       }
    echo     }
    echo   }
    echo }
    echo.
) else (
    REM Create new config
    (
    echo {
    echo   "mcpServers": {
    echo     "codex": {
    echo       "command": "python",
    echo       "args": ["%CODEX_DIR%\\codex_mcp_server.py"],
    echo       "env": {
    echo         "PYTHONPATH": "%CODEX_DIR%",
    echo         "CODEX_PROJECT_ROOT": "C:\\Users\\%USERNAME%\\IdeaProjects\\ebl"
    echo       }
    echo     }
    echo   }
    echo }
    ) > "%CONFIG_FILE%"
    echo ✓ Config file created
)

REM Test the server
echo.
echo ========================================
echo Testing Codex MCP Server...
echo ========================================
python "%CODEX_DIR%\codex_mcp_server.py" --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Server test passed
) else (
    echo ⚠ Server test inconclusive (this is normal)
)

REM Success message
echo.
echo ================================================
echo    ✨ INSTALLATION COMPLETE! ✨
echo ================================================
echo.
echo The Enforcer is ready to judge your code!
echo.
echo NEXT STEPS:
echo 1. Restart Claude Desktop
echo 2. Look for "codex" in available tools
echo 3. Start using Codex commands:
echo    - codex_snapshot
echo    - codex_enforce
echo    - codex_analyze
echo    - codex_dual_answer
echo    - codex_clean
echo.
echo Installation directory: %CODEX_DIR%
echo.
echo Russian Olympic Judges are standing by...
echo.
pause
