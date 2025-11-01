"""
Map System für "Der Eine Ring"
Verwaltet Speichern und Laden von Karten
"""
import json
import os
from datetime import datetime

class MapSystem:
    """Verwaltet Karten-Speicherung und -Laden"""
    
    def __init__(self, maps_folder="maps"):
        self.maps_folder = maps_folder
        self.ensure_maps_folder()
    
    def ensure_maps_folder(self):
        """Stellt sicher, dass der Maps-Ordner existiert"""
        if not os.path.exists(self.maps_folder):
            os.makedirs(self.maps_folder)
    
    def save_map(self, map_data, filename=None):
        """
        Speichert eine Karte als JSON
        
        Args:
            map_data: Dict mit width, height, tiles
            filename: Optionaler Dateiname (sonst Zeitstempel)
        
        Returns:
            Pfad zur gespeicherten Datei
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"map_{timestamp}.json"
        
        # .json Extension sicherstellen
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(self.maps_folder, filename)
        
        # Metadaten hinzufügen
        save_data = {
            "version": "1.1",  # Version erhöht für river_directions
            "created": datetime.now().isoformat(),
            "width": map_data.get("width", 50),
            "height": map_data.get("height", 50),
            "tiles": map_data.get("tiles", []),
            "river_directions": map_data.get("river_directions", {})  # Neue Eigenschaft
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_map(self, filename):
        """
        Lädt eine Karte aus einer JSON-Datei
        
        Args:
            filename: Name oder Pfad der Datei
        
        Returns:
            Dict mit Kartendaten oder None bei Fehler
        """
        # Wenn nur Filename, dann in maps_folder suchen
        if not os.path.isabs(filename):
            filepath = os.path.join(self.maps_folder, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            print(f"Karte nicht gefunden: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validierung
            if not all(key in data for key in ["width", "height", "tiles"]):
                print(f"Ungültige Kartendaten in {filepath}")
                return None
            
            # Rückwärtskompatibilität: river_directions hinzufügen wenn nicht vorhanden
            if "river_directions" not in data:
                data["river_directions"] = {}
            
            return data
        
        except json.JSONDecodeError as e:
            print(f"Fehler beim Laden der Karte: {e}")
            return None
    
    def list_maps(self):
        """
        Listet alle verfügbaren Karten auf
        
        Returns:
            Liste von Tupeln (filename, created_date)
        """
        maps = []
        
        if not os.path.exists(self.maps_folder):
            return maps
        
        for filename in os.listdir(self.maps_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(self.maps_folder, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    created = data.get('created', 'Unbekannt')
                    size = f"{data.get('width', '?')}x{data.get('height', '?')}"
                    maps.append((filename, created, size))
                
                except:
                    maps.append((filename, 'Fehler beim Laden', '?'))
        
        return sorted(maps, key=lambda x: x[1], reverse=True)
    
    def delete_map(self, filename):
        """
        Löscht eine Karte
        
        Args:
            filename: Name der zu löschenden Datei
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        filepath = os.path.join(self.maps_folder, filename)
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Löschen: {e}")
            return False
    
    def export_map(self, map_data, export_path):
        """
        Exportiert eine Karte an einen beliebigen Ort
        
        Args:
            map_data: Kartendaten
            export_path: Ziel-Pfad
        """
        save_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "width": map_data.get("width", 50),
            "height": map_data.get("height", 50),
            "tiles": map_data.get("tiles", [])
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return export_path
    
    def create_default_map(self, width=50, height=50):
        """
        Erstellt eine Standard-Karte mit verschiedenen Terrains
        
        Returns:
            Dict mit Kartendaten
        """
        import random
        
        tiles = []
        
        for y in range(height):
            row = []
            for x in range(width):
                # Einfaches Terrain-Pattern
                if y < height * 0.2:
                    terrain = "mountain"
                elif y < height * 0.4:
                    terrain = random.choice(["grass", "grass", "forest"])
                elif y < height * 0.6:
                    terrain = "grass"
                elif y < height * 0.8:
                    terrain = random.choice(["grass", "water", "grass", "grass"])
                else:
                    terrain = "water"
                
                row.append(terrain)
            tiles.append(row)
        
        return {
            "width": width,
            "height": height,
            "tiles": tiles
        }
