"""
Kamera-Controller für dynamischen Zoom und Fokus
Verfolgt Spieler-Positionen und passt Ansicht automatisch an
"""
import math

class CameraController:
    """Steuert Kamera-Position und Zoom basierend auf Spieler-Aktivität"""
    
    def __init__(self, map_width, map_height):
        self.map_width = map_width
        self.map_height = map_height
        
        # Kamera-Status
        self.target_zoom = 1.0
        self.current_zoom = 1.0
        self.target_center_x = map_width / 2
        self.target_center_y = map_height / 2
        self.current_center_x = map_width / 2
        self.current_center_y = map_height / 2
        
        # Auto-Zoom Einstellungen
        self.auto_zoom_enabled = False
        self.zoom_padding = 3  # Zusätzliche Tiles um Spieler-Bereich
        self.zoom_speed = 0.1  # Geschwindigkeit der Zoom-Transition (0-1)
        self.pan_speed = 0.15  # Geschwindigkeit der Kamera-Bewegung
        
        # Spieler-Positionen tracking
        self.player_positions = []  # Liste von (x, y) Positionen
        self.active_area_center = None
        self.active_area_size = None
        
        # Zoom-Grenzen
        self.min_zoom = 0.5
        self.max_zoom = 3.0
    
    def add_player_position(self, x, y):
        """Fügt eine Spieler-Position hinzu"""
        if (x, y) not in self.player_positions:
            self.player_positions.append((x, y))
    
    def remove_player_position(self, x, y):
        """Entfernt eine Spieler-Position"""
        if (x, y) in self.player_positions:
            self.player_positions.remove((x, y))
    
    def clear_player_positions(self):
        """Löscht alle Spieler-Positionen"""
        self.player_positions.clear()
    
    def update_from_revealed_tiles(self, revealed_tiles):
        """Aktualisiert Spieler-Positionen basierend auf aufgedeckten Tiles"""
        # Nimm die zuletzt aufgedeckten Tiles als Spieler-Positionen
        if revealed_tiles:
            # Begrenze auf letzte 10 Positionen für bessere Performance
            self.player_positions = revealed_tiles[-10:]
    
    def calculate_bounding_box(self):
        """Berechnet Bounding Box um alle Spieler-Positionen"""
        if not self.player_positions:
            return None
        
        min_x = min(pos[0] for pos in self.player_positions)
        max_x = max(pos[0] for pos in self.player_positions)
        min_y = min(pos[1] for pos in self.player_positions)
        max_y = max(pos[1] for pos in self.player_positions)
        
        # Padding hinzufügen
        min_x = max(0, min_x - self.zoom_padding)
        max_x = min(self.map_width - 1, max_x + self.zoom_padding)
        min_y = max(0, min_y - self.zoom_padding)
        max_y = min(self.map_height - 1, max_y + self.zoom_padding)
        
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        return {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'width': width,
            'height': height,
            'center_x': center_x,
            'center_y': center_y
        }
    
    def calculate_optimal_zoom(self, bbox, screen_width, screen_height):
        """Berechnet optimalen Zoom-Level für Bounding Box"""
        if not bbox:
            return 1.0
        
        # Berechne wie viel Zoom nötig ist, um den Bereich zu zeigen
        # Mehr Tiles = weniger Zoom
        tiles_width = bbox['width']
        tiles_height = bbox['height']
        
        # Berechne Zoom basierend auf Bildschirmgröße
        # Je kleiner der Bereich, desto mehr können wir zoomen
        zoom_x = (screen_width / 64) / tiles_width  # 64 = durchschnittliche Tile-Größe
        zoom_y = (screen_height / 64) / tiles_height
        
        # Nimm den kleineren Zoom-Wert, damit alles passt
        optimal_zoom = min(zoom_x, zoom_y)
        
        # Begrenze auf erlaubte Werte
        optimal_zoom = max(self.min_zoom, min(self.max_zoom, optimal_zoom))
        
        return optimal_zoom
    
    def update(self, screen_width=1920, screen_height=1080):
        """Aktualisiert Kamera basierend auf Auto-Zoom-Einstellungen"""
        if not self.auto_zoom_enabled or not self.player_positions:
            # Sanft zurück zur Standardansicht
            self.target_zoom = 1.0
            self.target_center_x = self.map_width / 2
            self.target_center_y = self.map_height / 2
        else:
            # Berechne Bounding Box
            bbox = self.calculate_bounding_box()
            
            if bbox:
                # Setze Ziel-Zoom und Ziel-Center
                self.target_zoom = self.calculate_optimal_zoom(bbox, screen_width, screen_height)
                self.target_center_x = bbox['center_x']
                self.target_center_y = bbox['center_y']
                
                self.active_area_center = (bbox['center_x'], bbox['center_y'])
                self.active_area_size = (bbox['width'], bbox['height'])
        
        # Sanfte Transition zu Ziel-Werten
        self.current_zoom += (self.target_zoom - self.current_zoom) * self.zoom_speed
        self.current_center_x += (self.target_center_x - self.current_center_x) * self.pan_speed
        self.current_center_y += (self.target_center_y - self.current_center_y) * self.pan_speed
    
    def get_zoom(self):
        """Gibt aktuellen Zoom-Level zurück"""
        return self.current_zoom
    
    def get_center(self):
        """Gibt aktuelle Kamera-Center-Position zurück"""
        return (self.current_center_x, self.current_center_y)
    
    def set_zoom(self, zoom):
        """Setzt Zoom manuell"""
        self.target_zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        self.current_zoom = self.target_zoom
    
    def set_center(self, x, y):
        """Setzt Kamera-Center manuell"""
        self.target_center_x = x
        self.target_center_y = y
        self.current_center_x = x
        self.current_center_y = y
    
    def enable_auto_zoom(self, enabled=True):
        """Aktiviert/Deaktiviert Auto-Zoom"""
        self.auto_zoom_enabled = enabled
    
    def is_auto_zoom_enabled(self):
        """Prüft ob Auto-Zoom aktiv ist"""
        return self.auto_zoom_enabled
    
    def reset(self):
        """Setzt Kamera auf Standardwerte zurück"""
        self.target_zoom = 1.0
        self.current_zoom = 1.0
        self.target_center_x = self.map_width / 2
        self.target_center_y = self.map_height / 2
        self.current_center_x = self.map_width / 2
        self.current_center_y = self.map_height / 2
        self.player_positions.clear()
