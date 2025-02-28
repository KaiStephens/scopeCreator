@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    Scope Creator Setup Script (Windows)
echo ========================================
echo.

:: Check if Python is installed
echo Checking for Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed. Please install Python 3.6+ and try again.
    goto :end
)

:: Check Python version
for /f "tokens=*" %%a in ('python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"') do set PYTHON_VERSION=%%a
echo Found Python %PYTHON_VERSION%

:: Check if pip is installed
echo Checking for pip...
where pip >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: pip is not installed. Please install pip and try again.
    goto :end
)
echo Found pip

:: Check if venv module is available
echo Checking for venv module...
python -c "import venv" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: venv module not found. Please install it and try again.
    goto :end
)
echo Found venv module

:: Check if virtual environment already exists
if exist ".venv" (
    echo Virtual environment already exists. Do you want to recreate it? (y/n)
    set /p recreate=
    if /i "!recreate!"=="y" (
        echo Removing existing virtual environment...
        rmdir /s /q .venv
    ) else (
        echo Using existing virtual environment.
    )
)

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to create virtual environment.
        goto :end
    )
    echo Virtual environment created.
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate virtual environment.
    goto :end
)
echo Virtual environment activated.

:: Install requirements
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install dependencies.
    goto :end
)
echo Dependencies installed successfully.

:: Check if .env file exists and handle API key
if exist ".env" (
    echo Found existing .env file. Do you want to update your OpenRouter API key? (y/n)
    set /p update_key=
    if /i "!update_key!"=="y" (
        echo Please enter your OpenRouter API key:
        set /p api_key=
        
        :: Create a temporary file with the updated content
        set "tempfile=.env.tmp"
        set "found=0"
        for /f "usebackq tokens=*" %%a in (".env") do (
            set "line=%%a"
            if "!line:~0,16!"=="OPENROUTER_API_KEY" (
                echo OPENROUTER_API_KEY=!api_key!>>!tempfile!
                set "found=1"
            ) else (
                echo !line!>>!tempfile!
            )
        )
        
        :: If key wasn't found, append it
        if "!found!"=="0" (
            echo OPENROUTER_API_KEY=!api_key!>>!tempfile!
        )
        
        :: Replace original file with updated one
        move /y !tempfile! .env
        echo API key updated in .env file.
    )
) else (
    :: Create new .env file
    echo Please enter your OpenRouter API key:
    set /p api_key=
    echo OPENROUTER_API_KEY=!api_key!>.env
    echo .env file created with API key.
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To run the Scope Creator application:
echo 1. Activate the virtual environment (if not already activated):
echo    .venv\Scripts\activate.bat
echo 2. Start the application:
echo    python app.py
echo.
echo You can access the application in your web browser at:
echo http://localhost:5006
echo.

:: Ask if user wants to run the application now
echo Do you want to run the application now? (y/n)
set /p run_now=
if /i "!run_now!"=="y" (
    echo Starting the application...
    python app.py
)

:end
endlocal 