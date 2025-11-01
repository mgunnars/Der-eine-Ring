@echo off
echo ========================================
echo    Der Eine Ring - VTT System
echo    Installation und Start
echo ========================================
echo.

REM Prüfe ob Python installiert ist
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo FEHLER: Python ist nicht installiert!
    echo Bitte Python 3.8 oder neuer installieren.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Python gefunden!
python --version

echo.
echo [2/3] Installiere Abhängigkeiten...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo WARNUNG: Einige Pakete konnten nicht installiert werden.
    echo Das System funktioniert möglicherweise trotzdem.
    echo.
)

echo.
echo [3/3] Starte Anwendung...
echo.
python enhanced_main.py

if %errorlevel% neq 0 (
    echo.
    echo FEHLER: Anwendung konnte nicht gestartet werden!
    echo.
    pause
)
