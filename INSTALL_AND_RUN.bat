@echo off
title Der Eine Ring - Legacy Installer
cls
echo ========================================
echo    Der Eine Ring - VTT System
echo    Legacy Installer (veraltet)
echo ========================================
echo.
echo ⚠️  HINWEIS: Dieser Installer ist veraltet!
echo.
echo Bitte nutze stattdessen:
echo   START.bat
echo.
echo START.bat bietet:
echo   ✅ Automatische Dependency-Installation
echo   ✅ Cairo-Setup-Assistent
echo   ✅ System-Check und Diagnostik
echo   ✅ Bessere Fehlermeldungen
echo.
echo Moechtest du trotzdem fortfahren? ^(J/N^)
set /p continue="Eingabe: "
if /i not "%continue%"=="J" (
    echo.
    echo Starte START.bat...
    call START.bat
    exit /b 0
)

echo.
echo [Legacy Installation wird ausgefuehrt...]
echo.

REM Prüfe ob Python installiert ist
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo FEHLER: Python ist nicht installiert!
        echo Bitte Python 3.10 oder neuer installieren.
        echo Download: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

echo [1/3] Python gefunden!
%PYTHON_CMD% --version

echo.
echo [2/3] Installiere Abhaengigkeiten...
%PYTHON_CMD% -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo WARNUNG: Einige Pakete konnten nicht installiert werden.
    echo Das System funktioniert moeglicherweise trotzdem.
    echo.
)

echo.
echo [3/3] Starte Anwendung...
echo.
%PYTHON_CMD% enhanced_main.py

if errorlevel 1 (
    echo.
    echo FEHLER: Anwendung konnte nicht gestartet werden!
    echo.
    pause
)
