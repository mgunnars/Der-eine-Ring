# Cloud-Referenzbild Speichern

## Anleitung

Das System sucht automatisch nach einem Cloud-Referenzbild an folgenden Orten:

1. `cloud_reference.png` (im Hauptverzeichnis)
2. `cloud_reference.jpg` (im Hauptverzeichnis)
3. `maps/cloud_reference.png`
4. `maps/cloud_reference.jpg`
5. `textures/cloud_reference.png`

## Schritte

**Option 1: Manuell speichern**
1. Rechtsklick auf das Cloud-Bild das du gesendet hast
2. "Bild speichern als..." wählen
3. Als `cloud_reference.png` im Hauptverzeichnis speichern
   - Pfad: `c:\Users\PC\Desktop\Programmieren\Der-eine-Ring-main\Der-eine-Ring-main\cloud_reference.png`

**Option 2: In maps/ Ordner**
1. Bild als `cloud_reference.png` speichern
2. In den `maps/` Unterordner legen

**Option 3: In textures/ Ordner**
1. Falls noch nicht vorhanden, `textures/` Ordner erstellen
2. Bild als `cloud_reference.png` dort speichern

## Was passiert dann?

- Beim Start von `main.py` oder `projector_window.py` wird das Bild automatisch erkannt
- Die Fog-Textur verwendet dann dein echtes Cloud-Bild als Basis
- Die Konsole zeigt: `✓ Cloud-Referenzbild geladen: [pfad]`
- Fog wird EXAKT wie dein Bild aussehen, nur skaliert und mit Alpha=255 für volle Deckkraft

## Testen

Nach dem Speichern kannst du testen:
```
python test_fog_water_fixes.py
```

Oder einfach die Anwendung starten und den Projector öffnen!
