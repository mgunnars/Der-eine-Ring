@echo off
title Der Eine Ring - Tabletop Projektor
echo.
echo ===================================
echo   Der Eine Ring - Kartenprojektor
echo ===================================
echo.
echo Starte Anwendung...
echo.

py enhanced_main.py

if errorlevel 1 (
    echo.
    echo Fehler beim Starten!
    echo Stelle sicher dass Python installiert ist.
    echo.
    pause
)
