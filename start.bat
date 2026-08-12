@echo off
REM Start the Oracle MCP Server from the repository root.
REM Ensure Python 3.10+ is installed and available on PATH.

SETLOCAL

REM Optional: activate a virtual environment if one is used.
REM Uncomment and update the next line if you have a venv in the project.
REM call .\venv\Scripts\activate

echo Starting Oracle MCP Server...
python -m oracle_mcp

ENDLOCAL
