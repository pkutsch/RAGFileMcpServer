@echo off
setlocal

set "VENV_DIR=.venv"

echo ========================================
echo     RAG File MCP Server (Windows)
echo ========================================

:: Check if venv exists
if not exist "%VENV_DIR%" (
    echo Creating virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo Error: Failed to create virtual environment. Is Python installed?
        pause
        exit /b 1
    )
    echo Virtual environment created.
)

:: Activate venv
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install requirements - prefer local RAGMcpServerCore if available
echo Checking dependencies...
if exist "..\RAGMcpServerCore" (
    echo Using local RAGMcpServerCore...
    pip install -e "..\RAGMcpServerCore[chroma,qdrant]"
    if errorlevel 1 (
        echo Error: Failed to install local RAGMcpServerCore.
        pause
        exit /b 1
    )
    pip install -e ".[dev]"
    if errorlevel 1 (
        echo Error: Failed to install project dependencies.
        pause
        exit /b 1
    )
) else (
    echo Using Git RAGMcpServerCore...
    pip install -e ".[dev]"
    if errorlevel 1 (
        echo Error: Failed to install requirements.
        pause
        exit /b 1
    )
)

:: Create data directories
if not exist "data\uploads" mkdir data\uploads
if not exist "data\chroma" mkdir data\chroma

:: Default ports
if not defined STREAMLIT_PORT set STREAMLIT_PORT=8501

echo.
echo Starting services...
echo.

:: Start MCP server in background (new window)
echo Starting MCP Server...
start "RAG File MCP Server" cmd /c "python -m src.server"

:: Give MCP server a moment to start
timeout /t 3 /nobreak >nul

:: Start Streamlit UI in this window
echo Starting Streamlit UI on http://localhost:%STREAMLIT_PORT%
streamlit run src/streamlit_app.py --server.port=%STREAMLIT_PORT% --server.address=0.0.0.0 --browser.gatherUsageStats=false

:end
if exist "%VENV_DIR%\Scripts\deactivate.bat" call "%VENV_DIR%\Scripts\deactivate.bat"
echo.
echo Application stopped.
pause
