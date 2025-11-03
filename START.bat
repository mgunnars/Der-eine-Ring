@echo off
title Der Eine Ring - Tabletop Projektor PRO
cls

REM ========================================
REM   AUTO-SETUP & DEPENDENCY CHECKER
REM ========================================

REM Prüfe ob Python installiert ist
py --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ================================================
    echo   FEHLER: Python nicht gefunden!
    echo ================================================
    echo.
    echo Bitte installiere Python 3.10 oder neuer:
    echo https://www.python.org/downloads/
    echo.
    echo WICHTIG: Waehle bei Installation "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

REM Erstelle .setup_complete Flag-Datei falls nicht vorhanden
if not exist .setup_complete (
    call :first_time_setup
) else (
    REM Quick-Check: Prüfe ob wichtige Pakete fehlen
    py -c "import PIL, numpy, cv2" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ⚠️  Dependencies fehlen - fuehre Reparatur durch...
        echo.
        call :install_dependencies
    )
)

REM Starte Anwendung
cls
echo.
echo ================================================
echo   Der Eine Ring - PRO Edition
echo   Virtual Tabletop mit SVG-Vektor-Support
echo ================================================
echo.
echo 🚀 Starte Anwendung...
echo.

py enhanced_main.py

if errorlevel 1 (
    echo.
    echo ================================================
    echo   FEHLER beim Starten!
    echo ================================================
    echo.
    echo Moegliche Probleme:
    echo   - Dependencies nicht installiert
    echo   - Python-Version zu alt (min. 3.10)
    echo   - Datei enhanced_main.py fehlt
    echo.
    echo Versuche: START.bat nochmal ausfuehren
    echo.
    pause
)
exit /b 0

REM ========================================
REM   FIRST-TIME SETUP
REM ========================================
:first_time_setup
cls
echo.
echo ================================================
echo   🎉 WILLKOMMEN bei Der Eine Ring VTT!
echo ================================================
echo.
echo Dies ist der erste Start. Wir richten alles ein:
echo.
echo   [1/3] Python-Dependencies installieren
echo   [2/3] Cairo SVG-Renderer pruefen (optional)
echo   [3/3] System-Check durchfuehren
echo.
echo Dies dauert ca. 1-2 Minuten...
echo.
pause

call :install_dependencies

REM Prüfe Cairo
echo.
echo ================================================
echo   [2/3] Cairo SVG-Renderer
echo ================================================
echo.
py -c "import cairosvg; print('✅ Cairo verfuegbar')" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  CairoSVG installiert, aber Cairo-DLLs fehlen
    echo.
    echo Cairo ermoeglicht HOCHQUALITATIVES SVG-Rendering:
    echo   ✅ Vektorkarten in voller Farbpracht
    echo   ✅ Verlustfreies Zooming
    echo   ✅ 5x schneller als Fallback
    echo.
    echo OPTIONAL: GTK3 Runtime installieren fuer Cairo
    echo   Download: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
    echo   Datei: gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe
    echo.
    echo Ohne Cairo: App funktioniert trotzdem ^(mit PIL-Fallback^)
    echo.
    echo Moechtest du Cairo JETZT installieren? ^(J/N^)
    set /p install_cairo="Eingabe: "
    if /i "%install_cairo%"=="J" (
        echo.
        echo Oeffne Download-Seite...
        start https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
        echo.
        echo SCHRITTE:
        echo   1. Lade gtk3-runtime-xxx.exe herunter
        echo   2. Als Administrator ausfuehren
        echo   3. System NEU STARTEN
        echo   4. Dann START.bat nochmal ausfuehren
        echo.
        pause
        exit /b 0
    ) else (
        echo.
        echo ℹ️  Ueberspringe Cairo - nutze PIL-Fallback
        echo    ^(Du kannst Cairo spaeter mit INSTALL_CAIRO.bat nachinstallieren^)
    )
) else (
    echo ✅ Cairo verfuegbar - High-Quality Rendering aktiv!
)

REM System-Check
echo.
echo ================================================
echo   [3/3] System-Check
echo ================================================
echo.
py -c "import sys; print(f'Python {sys.version.split()[0]}')"
py -c "import PIL; print(f'Pillow {PIL.__version__}')"
py -c "import numpy; print(f'NumPy {numpy.__version__}')"
py -c "import cv2; print(f'OpenCV {cv2.__version__}')"
echo.

REM Erstelle Flag-Datei
echo Setup completed on %date% %time% > .setup_complete

echo.
echo ================================================
echo   ✅ SETUP ABGESCHLOSSEN!
echo ================================================
echo.
echo Die Anwendung startet jetzt...
echo.
timeout /t 3 >nul
goto :eof

REM ========================================
REM   INSTALL DEPENDENCIES
REM ========================================
:install_dependencies
echo.
echo ================================================
echo   [1/3] Installiere Python-Pakete
echo ================================================
echo.
echo 📦 Dies kann beim ersten Mal etwas dauern...
echo.

REM Upgrade pip first
echo [1/10] Aktualisiere pip...
py -m pip install --upgrade pip --quiet

REM Core dependencies
echo [2/10] Installiere Pillow ^(Bildverarbeitung^)...
py -m pip install Pillow>=10.0.0 --quiet

echo [3/10] Installiere NumPy ^(Mathematik^)...
py -m pip install numpy>=1.24.0 --quiet

echo [4/10] Installiere OpenCV ^(Webcam-Tracking^)...
py -m pip install opencv-python>=4.8.0 --quiet

REM Optional dependencies
echo [5/10] Installiere PyGame ^(Sound - optional^)...
py -m pip install pygame>=2.5.0 --quiet 2>nul

echo [6/10] Installiere Noise ^(Texturen - optional^)...
py -m pip install noise>=1.2.2 --quiet 2>nul

echo [7/10] Installiere ImageIO ^(GIF-Export - optional^)...
py -m pip install imageio>=2.31.0 --quiet 2>nul

echo [8/10] Installiere SciPy ^(Mathematik - optional^)...
py -m pip install scipy>=1.11.0 --quiet 2>nul

REM SVG-Rendering
echo [9/10] Installiere CairoSVG ^(SVG-Rendering^)...
py -m pip install cairosvg>=2.7.0 --quiet 2>nul

echo [10/10] Verifiziere Installation...
py -c "import PIL, numpy, cv2; print('✅ Kern-Pakete installiert')"

if errorlevel 1 (
    echo.
    echo ❌ Fehler bei der Installation!
    echo.
    echo Versuche manuelle Installation:
    echo   py -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Alle Dependencies installiert!
goto :eof
