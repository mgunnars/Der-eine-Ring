"""
Detailkarten-System für Dörfer und Gebäude
Automatischer Wechsel zwischen Übersichtskarte und Detail-Maps
"""
import os
import json

class DetailMapSystem:
    """Verwaltet Detail-Maps für spezielle Orte (Dörfer, Gebäude, etc.)"""
    
    def __init__(self, base_map_data):
        self.base_map = base_map_data  # Haupt-Übersichtskarte
        self.current_map = base_map_data  # Aktuell angezeigte Karte
        self.detail_maps = {}  # Dict: (x, y) -> detail_map_data
        self.current_detail_position = None  # Aktuelle Detail-Position
        self.detail_maps_folder = "detail_maps"
        
        # Erstelle Ordner falls nicht vorhanden
        os.makedirs(self.detail_maps_folder, exist_ok=True)
        
        # Trigger-Tiles (welche Terrain-Typen lösen Detail-Maps aus)
        self.detail_triggers = ["village", "building", "castle", "dungeon"]
    
    def register_detail_map(self, base_x, base_y, detail_map_data, auto_save=True):
        """
        Registriert eine Detail-Map für eine Position auf der Basis-Karte
        
        Args:
            base_x, base_y: Position auf der Haupt-Karte
            detail_map_data: Map-Daten für die Detail-Ansicht
            auto_save: Automatisch speichern
        """
        key = (base_x, base_y)
        self.detail_maps[key] = detail_map_data
        
        if auto_save:
            self.save_detail_map(base_x, base_y, detail_map_data)
    
    def get_detail_map(self, base_x, base_y):
        """Lädt Detail-Map für Position"""
        key = (base_x, base_y)
        
        # Aus Cache
        if key in self.detail_maps:
            return self.detail_maps[key]
        
        # Von Disk laden
        detail_map = self.load_detail_map(base_x, base_y)
        if detail_map:
            self.detail_maps[key] = detail_map
            return detail_map
        
        # Keine Detail-Map vorhanden
        return None
    
    def has_detail_map(self, base_x, base_y):
        """Prüft ob eine Detail-Map für Position existiert"""
        key = (base_x, base_y)
        
        # Cache prüfen
        if key in self.detail_maps:
            return True
        
        # Disk prüfen
        filename = self._get_detail_map_filename(base_x, base_y)
        return os.path.exists(filename)
    
    def switch_to_detail(self, base_x, base_y):
        """Wechselt zur Detail-Ansicht einer Position"""
        detail_map = self.get_detail_map(base_x, base_y)
        
        if detail_map:
            self.current_map = detail_map
            self.current_detail_position = (base_x, base_y)
            return True
        
        return False
    
    def switch_to_base(self):
        """Wechselt zurück zur Basis-Karte"""
        self.current_map = self.base_map
        self.current_detail_position = None
    
    def is_in_detail_view(self):
        """Prüft ob aktuell Detail-Ansicht aktiv ist"""
        return self.current_detail_position is not None
    
    def get_current_map(self):
        """Gibt aktuell angezeigte Karte zurück"""
        return self.current_map
    
    def update_base_map(self, map_data):
        """Aktualisiert Basis-Karte"""
        self.base_map = map_data
        if not self.is_in_detail_view():
            self.current_map = map_data
    
    def should_trigger_detail(self, x, y):
        """
        Prüft ob an Position ein Detail-Trigger ist
        (z.B. Dorf, Gebäude)
        """
        tiles = self.base_map.get("tiles", [])
        if y < len(tiles) and x < len(tiles[y]):
            terrain = tiles[y][x]
            return terrain in self.detail_triggers
        return False
    
    def auto_switch_on_position(self, x, y):
        """
        Automatischer Wechsel basierend auf Position
        Ruft beim Betreten eines Detail-Triggers die Detail-Map auf
        """
        if self.is_in_detail_view():
            # Bereits in Detail-Ansicht
            return False
        
        if self.should_trigger_detail(x, y) and self.has_detail_map(x, y):
            return self.switch_to_detail(x, y)
        
        return False
    
    def create_default_village_map(self, name="Dorf"):
        """Erstellt Standard-Dorfkarte mit Häusern"""
        return {
            "name": name,
            "width": 20,
            "height": 20,
            "tiles": [
                ["grass" if (i + j) % 3 != 0 else "dirt" 
                 for i in range(20)]
                for j in range(20)
            ],
            "metadata": {
                "type": "village",
                "description": f"Detailansicht von {name}"
            }
        }
    
    def create_default_building_map(self, name="Gebäude"):
        """Erstellt Standard-Gebäude-Innenkarte"""
        tiles = [["stone" for _ in range(15)] for _ in range(15)]
        
        # Boden (Holz/Dirt)
        for y in range(2, 13):
            for x in range(2, 13):
                tiles[y][x] = "dirt"
        
        # Paar Details
        tiles[7][7] = "village"  # Tisch/Objekt
        
        return {
            "name": name,
            "width": 15,
            "height": 15,
            "tiles": tiles,
            "metadata": {
                "type": "building",
                "description": f"Innenansicht von {name}"
            }
        }
    
    def save_detail_map(self, base_x, base_y, detail_map_data):
        """Speichert Detail-Map auf Disk"""
        filename = self._get_detail_map_filename(base_x, base_y)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(detail_map_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern der Detail-Map: {e}")
            return False
    
    def load_detail_map(self, base_x, base_y):
        """Lädt Detail-Map von Disk"""
        filename = self._get_detail_map_filename(base_x, base_y)
        
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Detail-Map: {e}")
            return None
    
    def _get_detail_map_filename(self, base_x, base_y):
        """Generiert Dateinamen für Detail-Map"""
        return os.path.join(self.detail_maps_folder, f"detail_{base_x}_{base_y}.json")
    
    def list_detail_maps(self):
        """Listet alle Detail-Maps auf"""
        detail_maps = []
        
        if not os.path.exists(self.detail_maps_folder):
            return detail_maps
        
        for filename in os.listdir(self.detail_maps_folder):
            if filename.startswith("detail_") and filename.endswith(".json"):
                # Parse Position aus Dateinamen
                parts = filename.replace("detail_", "").replace(".json", "").split("_")
                if len(parts) == 2:
                    try:
                        x, y = int(parts[0]), int(parts[1])
                        detail_maps.append((x, y, filename))
                    except ValueError:
                        continue
        
        return detail_maps
    
    def delete_detail_map(self, base_x, base_y):
        """Löscht Detail-Map"""
        key = (base_x, base_y)
        
        # Aus Cache entfernen
        if key in self.detail_maps:
            del self.detail_maps[key]
        
        # Von Disk löschen
        filename = self._get_detail_map_filename(base_x, base_y)
        if os.path.exists(filename):
            try:
                os.remove(filename)
                return True
            except Exception as e:
                print(f"Fehler beim Löschen: {e}")
                return False
        
        return False
