@echo off
title Der Eine Ring - Tabletop Projektor PRO
echo.
echo ===================================
echo   Der Eine Ring - PRO Edition
echo   JSON + SVG Support
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
