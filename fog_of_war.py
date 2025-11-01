"""
Fog-of-War System für den Projektor
Verwaltet sichtbare/verborgene Bereiche der Karte
"""
import numpy as np

class FogOfWar:
    """Verwaltet Nebel des Krieges (Fog-of-War) für die Karte"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # Fog-Status: False = Nebel, True = sichtbar
        self.revealed = np.zeros((height, width), dtype=bool)
        
        # Sichtweite (in Tiles)
        self.sight_range = 3
        
    def reveal_at_position(self, x, y, range_override=None):
        """
        Lichtet Nebel um eine Position herum
        """
        sight_range = range_override if range_override is not None else self.sight_range
        
        # Kreisförmigen Bereich aufdecken
        for dy in range(-sight_range, sight_range + 1):
            for dx in range(-sight_range, sight_range + 1):
                # Distanz prüfen (kreisförmig)
                if dx*dx + dy*dy <= sight_range*sight_range:
                    nx, ny = x + dx, y + dy
                    
                    # Grenzen prüfen
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        self.revealed[ny][nx] = True
    
    def reveal_area(self, x1, y1, x2, y2):
        """Deckt einen rechteckigen Bereich auf"""
        x1 = max(0, min(x1, self.width - 1))
        x2 = max(0, min(x2, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        y2 = max(0, min(y2, self.height - 1))
        
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        self.revealed[y1:y2+1, x1:x2+1] = True
    
    def hide_area(self, x1, y1, x2, y2):
        """Verbirgt einen rechteckigen Bereich wieder"""
        x1 = max(0, min(x1, self.width - 1))
        x2 = max(0, min(x2, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        y2 = max(0, min(y2, self.height - 1))
        
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        self.revealed[y1:y2+1, x1:x2+1] = False
    
    def is_revealed(self, x, y):
        """Prüft ob ein Tile sichtbar ist"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.revealed[y][x]
        return False
    
    def reveal_all(self):
        """Deckt die gesamte Karte auf"""
        self.revealed.fill(True)
    
    def hide_all(self):
        """Verbirgt die gesamte Karte"""
        self.revealed.fill(False)
    
    def get_revealed_tiles(self):
        """Gibt Liste aller aufgedeckten Tiles zurück"""
        tiles = []
        for y in range(self.height):
            for x in range(self.width):
                if self.revealed[y][x]:
                    tiles.append((x, y))
        return tiles
    
    def save_state(self):
        """Speichert aktuellen Fog-Status"""
        return self.revealed.copy()
    
    def load_state(self, state):
        """Lädt gespeicherten Fog-Status"""
        if state.shape == self.revealed.shape:
            self.revealed = state.copy()
