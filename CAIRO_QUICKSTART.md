# 🚀 Cairo Installation - SCHNELLANLEITUNG

## Problem
```
OSError: no library called "cairo-2" was found
```

CairoSVG ist installiert ✅, aber Cairo-DLLs fehlen ❌

---

## ✅ Lösung (5 Minuten)

### 1. GTK3 Runtime herunterladen

**Download:** https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

**Datei:** `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe` (ca. 50 MB)

### 2. Installieren

- Als **Administrator** ausführen
- Standard-Installation (C:\Program Files\GTK3-Runtime Win64)
- Alle Optionen beibehalten

### 3. System neu starten

**WICHTIG:** Windows muss neu gestartet werden damit die DLLs gefunden werden!

### 4. Testen

```bash
py -c "import cairosvg; print('✅ CairoSVG funktioniert!')"
```

**Erwartete Ausgabe:**
```
✅ CairoSVG funktioniert!
```

---

## 🎮 Dann starten:

```bash
py .\enhanced_main.py
```

**Terminal zeigt:**
```
✅ CairoSVG verfügbar - nutze High-Quality SVG-Rendering
```

🎉 **Vektorkarten werden jetzt in FARBE gerendert!**

---

## ⚠️ Troubleshooting

**Problem:** Immer noch Fehler nach Installation

**Lösungen:**
1. System NEU STARTEN (sehr wichtig!)
2. Prüfe Installation: `C:\Program Files\GTK3-Runtime Win64\bin\` sollte existieren
3. PATH-Variable prüfen (sollte automatisch gesetzt werden)

**Problem:** Download funktioniert nicht

**Alternative:** 
- https://github.com/preshing/cairo-windows/releases
- Lade einzelne DLLs herunter und kopiere nach `C:\Windows\System32\`

---

## 💡 Oder: Nutze PIL-Fallback (OHNE Cairo)

Falls GTK-Installation nicht klappt, funktioniert die App auch ohne Cairo:

**Nachteile:**
- Vektoren werden grau/schwarz gerendert
- Nur eingebettete PNG-Bilder sichtbar

**Vorteil:**
- Funktioniert ohne Installation
- Keine zusätzlichen DLLs nötig

Die App erkennt automatisch ob Cairo verfügbar ist und nutzt den besten verfügbaren Renderer.

---

**Empfohlen:** GTK3 installieren für beste Qualität! 🎨
