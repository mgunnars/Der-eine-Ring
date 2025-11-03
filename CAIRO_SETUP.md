# 🎨 CairoSVG Setup für Windows

## Warum CairoSVG?

CairoSVG rendert **echte SVG-Vektoren** in voller Qualität, während PIL nur eingebettete PNG-Bilder anzeigen kann.

**Mit CairoSVG:**
- ✅ Perfekte Vektorgrafiken
- ✅ Verlustfreies Zooming
- ✅ Schnelles Rendering
- ✅ Kleine Dateien (echte Vektoren)

**Ohne CairoSVG (PIL-Fallback):**
- ⚠️ Nur Base64-PNG-Bilder werden gerendert
- ⚠️ Vektoren erscheinen grau/schwarz
- ⚠️ Größere Dateien

---

## 🚀 Installation (Windows)

### Methode 1: Automatisches Setup (EMPFOHLEN)

```bash
# Führe das Installations-Script aus:
INSTALL_CAIRO.bat
```

### Methode 2: Manuelle Installation

#### Schritt 1: Python-Paket installieren

```bash
py -m pip install cairosvg
```

#### Schritt 2: GTK3 Runtime installieren

Die GTK3 Runtime enthält alle benötigten Cairo-DLLs.

**Download:**
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

**Installiere:**
- `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe` (oder neuer)
- Standardinstallation durchführen
- System neu starten (falls nötig)

#### Schritt 3: Testen

```bash
py -c "import cairosvg; print('✅ CairoSVG funktioniert!')"
```

---

## 🔍 Troubleshooting

### Problem: "OSError: no library called 'cairo-2' was found"

**Lösung:** GTK3 Runtime wurde nicht korrekt installiert.

1. Deinstalliere alte GTK-Versionen
2. Installiere neueste GTK3 Runtime
3. Starte System neu
4. Teste erneut

### Problem: "ImportError: No module named 'cairosvg'"

**Lösung:** Python-Paket fehlt:

```bash
py -m pip install cairosvg
```

### Problem: SVG zeigt nur graue/schwarze Flächen

**Ursache:** CairoSVG ist nicht verfügbar, PIL rendert nur Base64-Bilder.

**Lösung:** 
1. Prüfe ob CairoSVG installiert ist
2. Prüfe ob GTK3 Runtime installiert ist
3. Schaue ins Terminal - dort steht der Status

---

## 🎯 Alternative: Base64-Modus (ohne Cairo)

Falls CairoSVG nicht installiert werden kann, nutze den Base64-Modus:

**Vorteile:**
- ✅ Funktioniert ohne zusätzliche Installation
- ✅ PIL kann PNG-Bilder anzeigen
- ✅ Farbig und vollständig

**Nachteile:**
- ❌ Größere Dateien (Base64-encoded PNGs)
- ❌ Keine echten Vektoren
- ❌ Langsamer beim Export

Der Base64-Fallback wird automatisch genutzt wenn CairoSVG fehlt.

---

## 📊 Status prüfen

Beim Start der Anwendung siehst du im Terminal:

**✅ CairoSVG verfügbar:**
```
✅ CairoSVG verfügbar - nutze High-Quality SVG-Rendering
```

**⚠️ CairoSVG fehlt:**
```
⚠️ CairoSVG nicht installiert - nutze PIL-Fallback
   📦 Installiere mit: py -m pip install cairosvg
   🔧 Unter Windows zusätzlich benötigt: GTK3 Runtime
```

**⚠️ DLLs fehlen:**
```
⚠️ CairoSVG installiert, aber Cairo-DLLs fehlen!
   🔧 Unter Windows benötigt: GTK3 Runtime für Cairo-DLLs
```

---

## 🌐 Links

- **CairoSVG Dokumentation:** https://cairosvg.org/
- **GTK3 Runtime (Windows):** https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
- **Cairo Bibliothek:** https://cairographics.org/
- **Alternative Downloads:** https://github.com/preshing/cairo-windows/releases

---

## 💡 Hinweise

- **Linux/Mac:** CairoSVG funktioniert meist "out of the box"
- **Windows:** Benötigt GTK3 Runtime für die Cairo-DLLs
- **Performance:** Cairo ist 5-10x schneller als PIL-Fallback
- **Qualität:** Cairo rendert Vektoren perfekt, PIL approximiert nur

---

**Nach erfolgreicher Installation:**
```bash
# Starte Anwendung neu
py .\enhanced_main.py

# Terminal zeigt:
# ✅ CairoSVG verfügbar - nutze High-Quality SVG-Rendering
```

🎉 Vektorexporte erscheinen jetzt in voller Farbpracht!
