# Der Eine Ring - Interaktiver Tabletop-Kartenprojektor

Ein interaktives Kartenprojektionssystem für Herr-der-Ringe-Tabletop-Spiele mit handgezeichneten Aquarell-Texturen.

## Features

- 🎨 Handgezeichnete Aquarell-Texturen
- 🌊 Animierte Gewässer mit Fließeffekten
- 🏰 Automatischer Wechsel zwischen Weltkarte und Innenräumen
- 🎭 Split-View für geteilte Gruppen
- 📹 Webcam-Integration für Bewegungserkennung
- 🗺️ Vorgefertigte Mittelerde-Karte

## Installation

```bash
# Repository klonen
git clone https://github.com/mgunnars/Der-eine-Ring.git
cd Der-eine-Ring

# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python enhanced_main.py
```

## Systemanforderungen

- Python 3.8+
- Webcam (optional, für Bewegungserkennung)
- Beamer/zweiter Bildschirm (empfohlen für Projektion)

## Verwendung

1. **Karteneditor**: Erstelle deine eigene Mittelerde-Karte
2. **Projektionsmodus**: Projiziere die Karte auf den Spieltisch
3. **Orte betreten**: Spielfiguren wechseln automatisch zu Innenansichten
4. **Nebel des Krieges**: Verstecke Bereiche vor Spielern

## Lizenz

Für persönliche und nicht-kommerzielle Nutzung
