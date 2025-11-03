@echo off
REM ====================================================
REM Cairo SVG Installation für Windows
REM ====================================================
echo.
echo ================================================
echo   Cairo SVG Installation - Der Eine Ring VTT
echo ================================================
echo.
echo CairoSVG ist bereits installiert, aber die Cairo-DLLs fehlen!
echo.
echo Fehler: OSError: no library called "cairo-2" was found
echo.
echo ================================================
echo   LOESUNG: GTK3 Runtime installieren
echo ================================================
echo.
echo Die GTK3 Runtime enthaelt alle benoetigten Cairo-DLLs:
echo   - libcairo-2.dll
echo   - libpng16-16.dll  
echo   - libfreetype-6.dll
echo   - zlib1.dll
echo   und weitere...
echo.
echo Download-Link:
echo https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
echo.
echo Aktuelle Version: gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe
echo.
pause

echo.
echo Oeffne Download-Seite im Browser...
start https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

echo.
echo ================================================
echo   INSTALLATION
echo ================================================
echo.
echo 1. Lade herunter: gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe
echo 2. Fuehre Installer aus (als Administrator)
echo 3. Standard-Installation waehlen
echo 4. Nach Installation: System NEU STARTEN
echo 5. Danach dieses Script nochmal ausfuehren zum Testen
echo.
pause

echo.
echo Teste ob CairoSVG jetzt funktioniert...
echo.
py -c "import cairosvg; print('✅ CairoSVG funktioniert perfekt!')"

if errorlevel 1 (
    echo.
    echo ================================================
    echo   ❌ CairoSVG funktioniert NOCH NICHT
    echo ================================================
    echo.
    echo Moegliche Probleme:
    echo   1. GTK3 Runtime noch nicht installiert
    echo   2. System muss neu gestartet werden
    echo   3. Falsche GTK-Version installiert
    echo.
    echo WICHTIG: Nach GTK-Installation System NEU STARTEN!
    echo.
    echo Alternative: Nutze die Anwendung MIT PIL-Fallback
    echo              (funktioniert, aber ohne echte Vektoren)
    echo.
) else (
    echo.
    echo ================================================
    echo   ✅ ERFOLG! CairoSVG ist einsatzbereit!
    echo ================================================
    echo.
    echo Vektorkarten werden jetzt in voller Qualitaet gerendert.
    echo Du kannst jetzt "py .\enhanced_main.py" starten.
    echo.
)

pause

