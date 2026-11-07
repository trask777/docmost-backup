@echo off
:: Docmost Backup Launcher - Direct API with secure credential storage
:: Double-click to run. Uses Windows Credential Manager for passwords.

set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%docmost_backup.py

:: Try to find Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON=python3
    ) else (
        echo Python not found in PATH.
        echo Please install Python from https://python.org or Microsoft Store.
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
)

:: Check if script exists
if not exist "%PYTHON_SCRIPT%" (
    echo Backup script not found: %PYTHON_SCRIPT%
    pause
    exit /b 1
)

:: Check for required packages
%PYTHON% -c "import requests" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing required Python packages...
    %PYTHON% -m pip install requests --quiet
    if %errorlevel% neq 0 (
        echo Failed to install 'requests' package.
        echo Run manually: pip install requests
        pause
        exit /b 1
    )
)

%PYTHON% -c "import keyring" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing keyring for secure credential storage...
    %PYTHON% -m pip install keyring --quiet
    if %errorlevel% neq 0 (
        echo Failed to install 'keyring' package.
        echo Run manually: pip install keyring
        echo Password will be prompted each run instead of stored securely.
    )
)

:: Run the backup script (pass through any arguments)
echo Starting Docmost Backup (Direct API, secure credentials)...
echo.
"%PYTHON%" "%PYTHON_SCRIPT%" %*

:: Always pause at the end so you can see the output
echo.
echo ============================================================
echo Script finished. Press any key to close this window...
pause >nul