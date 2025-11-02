@echo off
title Der Eine Ring - Tabletop Projektor
echo.
echo ===================================
echo   Der Eine Ring - Kartenprojektor
echo ===================================
echo.
echo Starte Anwendung mit SVG-Support...
echo.

py start_with_svg.py

if errorlevel 1 (
    echo.
    echo Fehler beim Starten!
    echo Stelle sicher dass Python installiert ist.
    echo.
    pause
)
