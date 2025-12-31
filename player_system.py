"""
Player System für "Der Eine Ring" VTT
======================================

Verwaltet Spieler und Teams auf Hexagon-Karten:
- Spieler-Definitionen (Name, Team, Farbe, Bild)
- Team-Gruppierung mit Teamfarben
- Zufällige Verteilung auf Spawn-Hexagone
- Position-Tracking und Sichtbarkeits-System
- Webcam-basiertes Figuren-Tracking

Autor: VTT Development Team
Version: 1.0.0
"""

import json
import os
import random
import uuid
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk


# Vordefinierte Team-Farben
TEAM_COLORS = {
    "Rot": "#FF4444",
    "Blau": "#4488FF",
    "Grün": "#44FF44",
    "Gelb": "#FFFF44",
    "Lila": "#AA44FF",
    "Orange": "#FF8844",
    "Cyan": "#44FFFF",
    "Pink": "#FF44AA",
    "Weiß": "#FFFFFF",
    "Grau": "#888888"
}


@dataclass
class PlayerDefinition:
    """Definition eines Spielers"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Spieler"
    
    # Team-Zugehörigkeit (None = Einzelspieler)
    team_id: Optional[str] = None
    team_name: str = ""
    
    # Visuelle Einstellungen
    color: str = "#4488FF"  # Spieler-/Team-Farbe
    image_path: Optional[str] = None  # Optionales Spieler-Bild
    token_size: int = 40  # Größe des Tokens auf der Karte
    
    # Position auf der Karte
    hex_q: int = 0  # Aktuelle Hexagon-Koordinate q
    hex_r: int = 0  # Aktuelle Hexagon-Koordinate r
    
    # Spieler-Eigenschaften
    is_active: bool = True  # Spieler aktiv im Spiel?
    notes: str = ""
    
    # Bounty-System: Spieler mit Bounty sind für alle Teams sichtbar
    has_bounty: bool = False  # Hat dieser Spieler ein Bounty?
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "color": self.color,
            "image_path": self.image_path,
            "token_size": self.token_size,
            "hex_q": self.hex_q,
            "hex_r": self.hex_r,
            "is_active": self.is_active,
            "notes": self.notes,
            "has_bounty": self.has_bounty
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlayerDefinition':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Spieler"),
            team_id=data.get("team_id"),
            team_name=data.get("team_name", ""),
            color=data.get("color", "#4488FF"),
            image_path=data.get("image_path"),
            token_size=data.get("token_size", 40),
            hex_q=data.get("hex_q", 0),
            hex_r=data.get("hex_r", 0),
            is_active=data.get("is_active", True),
            notes=data.get("notes", ""),
            has_bounty=data.get("has_bounty", False)
        )


@dataclass
class TeamDefinition:
    """Definition eines Teams/Gruppe"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Team"
    color: str = "#4488FF"  # Team-Farbe
    
    # Mitglieder-IDs (Spieler)
    member_ids: List[str] = field(default_factory=list)
    
    # Aktuelle Position des Teams (alle Mitglieder am gleichen Ort)
    hex_q: int = 0
    hex_r: int = 0
    
    # Team-Optionen
    shared_vision: bool = True  # Teammitglieder teilen Sichtfeld
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "member_ids": self.member_ids,
            "hex_q": self.hex_q,
            "hex_r": self.hex_r,
            "shared_vision": self.shared_vision
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TeamDefinition':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Team"),
            color=data.get("color", "#4488FF"),
            member_ids=data.get("member_ids", []),
            hex_q=data.get("hex_q", 0),
            hex_r=data.get("hex_r", 0),
            shared_vision=data.get("shared_vision", True)
        )


@dataclass
class PlayerPlacement:
    """Platzierung eines Spielers auf der Karte"""
    player_id: str  # Referenz zur PlayerDefinition
    hex_q: int      # Hexagon-Koordinate q
    hex_r: int      # Hexagon-Koordinate r
    visible_to_teams: List[str] = field(default_factory=list)  # Welche Teams können diesen Spieler sehen
    
    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "hex_q": self.hex_q,
            "hex_r": self.hex_r,
            "visible_to_teams": self.visible_to_teams
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlayerPlacement':
        return cls(
            player_id=data.get("player_id", ""),
            hex_q=data.get("hex_q", 0),
            hex_r=data.get("hex_r", 0),
            visible_to_teams=data.get("visible_to_teams", [])
        )


class PlayerManager:
    """Verwaltet alle Spieler und Teams einer Session"""
    
    def __init__(self):
        self.players: Dict[str, PlayerDefinition] = {}  # id -> Player
        self.teams: Dict[str, TeamDefinition] = {}  # id -> Team
        self.placements: List[PlayerPlacement] = []  # Aktive Platzierungen
        self.player_images: Dict[str, Image.Image] = {}  # id -> geladenes Bild
        self.player_photo_cache: Dict[str, ImageTk.PhotoImage] = {}  # Cache für Tk
        
        # Sichtbarkeits-Settings
        self.visibility_radius: int = 3  # Hexagone Sichtweite
        self.teams_can_see_each_other: bool = False  # Können Teams sich gegenseitig sehen?
        
    # =====================================================
    # SPIELER-VERWALTUNG
    # =====================================================
    
    def add_player(self, player: PlayerDefinition):
        """Fügt einen Spieler hinzu."""
        self.players[player.id] = player
        
    def remove_player(self, player_id: str):
        """Entfernt einen Spieler."""
        if player_id in self.players:
            # Aus Team entfernen falls vorhanden
            player = self.players[player_id]
            if player.team_id and player.team_id in self.teams:
                team = self.teams[player.team_id]
                if player_id in team.member_ids:
                    team.member_ids.remove(player_id)
            
            del self.players[player_id]
        
        # Entferne auch Platzierungen
        self.placements = [p for p in self.placements if p.player_id != player_id]
        
    def get_player(self, player_id: str) -> Optional[PlayerDefinition]:
        """Gibt Spieler-Definition zurück."""
        return self.players.get(player_id)
    
    def get_all_players(self) -> List[PlayerDefinition]:
        """Gibt alle Spieler zurück."""
        return list(self.players.values())
    
    # =====================================================
    # TEAM-VERWALTUNG
    # =====================================================
    
    def add_team(self, team: TeamDefinition):
        """Fügt ein Team hinzu."""
        self.teams[team.id] = team
        
    def remove_team(self, team_id: str):
        """Entfernt ein Team (Spieler werden zu Einzelspielern)."""
        if team_id in self.teams:
            team = self.teams[team_id]
            # Spieler aus Team entfernen
            for player_id in team.member_ids:
                if player_id in self.players:
                    self.players[player_id].team_id = None
                    self.players[player_id].team_name = ""
            
            del self.teams[team_id]
    
    def get_team(self, team_id: str) -> Optional[TeamDefinition]:
        """Gibt Team-Definition zurück."""
        return self.teams.get(team_id)
    
    def get_all_teams(self) -> List[TeamDefinition]:
        """Gibt alle Teams zurück."""
        return list(self.teams.values())
    
    def add_player_to_team(self, player_id: str, team_id: str):
        """Fügt einen Spieler zu einem Team hinzu."""
        if player_id not in self.players:
            return
        if team_id not in self.teams:
            return
        
        player = self.players[player_id]
        team = self.teams[team_id]
        
        # Aus altem Team entfernen
        if player.team_id and player.team_id in self.teams:
            old_team = self.teams[player.team_id]
            if player_id in old_team.member_ids:
                old_team.member_ids.remove(player_id)
        
        # Zu neuem Team hinzufügen
        player.team_id = team_id
        player.team_name = team.name
        player.color = team.color  # Team-Farbe übernehmen
        
        if player_id not in team.member_ids:
            team.member_ids.append(player_id)
    
    def remove_player_from_team(self, player_id: str):
        """Entfernt einen Spieler aus seinem Team."""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        
        if player.team_id and player.team_id in self.teams:
            team = self.teams[player.team_id]
            if player_id in team.member_ids:
                team.member_ids.remove(player_id)
        
        player.team_id = None
        player.team_name = ""
    
    def get_team_members(self, team_id: str) -> List[PlayerDefinition]:
        """Gibt alle Spieler eines Teams zurück."""
        if team_id not in self.teams:
            return []
        
        team = self.teams[team_id]
        return [self.players[pid] for pid in team.member_ids if pid in self.players]
    
    def get_player_team(self, player_id: str) -> Optional[TeamDefinition]:
        """Gibt das Team eines Spielers zurück."""
        if player_id not in self.players:
            return None
        
        player = self.players[player_id]
        if player.team_id:
            return self.teams.get(player.team_id)
        return None
    
    # =====================================================
    # SPAWN-VERTEILUNG
    # =====================================================
    
    def distribute_players_randomly(self, spawn_hexagons: List[Tuple[int, int]]):
        """
        Verteilt alle Spieler/Teams zufällig auf Spawn-Hexagone.
        Wird aufgerufen wenn der Projektor-Modus neu geöffnet wird.
        
        Args:
            spawn_hexagons: Liste von (q, r) Koordinaten die als Spawn markiert sind
        """
        # Alte Platzierungen löschen
        self.placements.clear()
        
        if not spawn_hexagons:
            print("⚠️ Keine Spawn-Hexagone auf der Karte markiert!")
            return
        
        if not self.players:
            print("⚠️ Keine Spieler definiert!")
            return
        
        # Kopie der Hexagone für Shuffle
        available_hexes = spawn_hexagons.copy()
        random.shuffle(available_hexes)
        
        # Sammle Teams und Einzelspieler
        teams_to_place: List[TeamDefinition] = []
        solo_players: List[PlayerDefinition] = []
        
        for player in self.players.values():
            if not player.is_active:
                continue
            
            if player.team_id:
                team = self.teams.get(player.team_id)
                if team and team not in teams_to_place:
                    teams_to_place.append(team)
            else:
                solo_players.append(player)
        
        hex_index = 0
        
        # Teams platzieren (alle Mitglieder am gleichen Punkt)
        for team in teams_to_place:
            if hex_index >= len(available_hexes):
                print(f"⚠️ Nicht genug Spawn-Hexagone für Team '{team.name}'")
                continue
            
            hex_q, hex_r = available_hexes[hex_index]
            hex_index += 1
            
            # Team-Position setzen
            team.hex_q = hex_q
            team.hex_r = hex_r
            
            # Alle Teammitglieder an diese Position setzen
            for player_id in team.member_ids:
                if player_id in self.players:
                    player = self.players[player_id]
                    player.hex_q = hex_q
                    player.hex_r = hex_r
                    
                    placement = PlayerPlacement(
                        player_id=player_id,
                        hex_q=hex_q,
                        hex_r=hex_r,
                        visible_to_teams=[team.id]  # Nur eigenes Team sieht
                    )
                    self.placements.append(placement)
            
            print(f"👥 Team '{team.name}' ({len(team.member_ids)} Spieler) platziert auf Hex ({hex_q}, {hex_r})")
        
        # Einzelspieler platzieren
        for player in solo_players:
            if hex_index >= len(available_hexes):
                print(f"⚠️ Nicht genug Spawn-Hexagone für Spieler '{player.name}'")
                continue
            
            hex_q, hex_r = available_hexes[hex_index]
            hex_index += 1
            
            player.hex_q = hex_q
            player.hex_r = hex_r
            
            placement = PlayerPlacement(
                player_id=player.id,
                hex_q=hex_q,
                hex_r=hex_r,
                visible_to_teams=[]  # Einzelspieler - für sich allein
            )
            self.placements.append(placement)
            
            print(f"🎮 Spieler '{player.name}' platziert auf Hex ({hex_q}, {hex_r})")
        
        print(f"✅ {len(self.placements)} Spieler verteilt auf {len(spawn_hexagons)} Spawn-Hexagone")
    
    def move_player(self, player_id: str, new_q: int, new_r: int):
        """Bewegt einen Spieler zu einer neuen Position."""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        player.hex_q = new_q
        player.hex_r = new_r
        
        # Placement aktualisieren
        for placement in self.placements:
            if placement.player_id == player_id:
                placement.hex_q = new_q
                placement.hex_r = new_r
                break
    
    def move_team(self, team_id: str, new_q: int, new_r: int):
        """Bewegt ein ganzes Team zu einer neuen Position."""
        if team_id not in self.teams:
            return
        
        team = self.teams[team_id]
        team.hex_q = new_q
        team.hex_r = new_r
        
        # Alle Teammitglieder bewegen
        for player_id in team.member_ids:
            self.move_player(player_id, new_q, new_r)
    
    # =====================================================
    # SICHTBARKEITS-BERECHNUNG
    # =====================================================
    
    def get_hex_distance(self, q1: int, r1: int, q2: int, r2: int) -> int:
        """Berechnet die Distanz zwischen zwei Hexagonen (Cube-Koordinaten)."""
        # Axial zu Cube
        x1, z1 = q1, r1
        y1 = -x1 - z1
        x2, z2 = q2, r2
        y2 = -x2 - z2
        
        return (abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)) // 2
    
    def can_team_see_position(self, team_id: str, target_q: int, target_r: int) -> bool:
        """Prüft ob ein Team eine Position sehen kann."""
        if team_id not in self.teams:
            return False
        
        team = self.teams[team_id]
        distance = self.get_hex_distance(team.hex_q, team.hex_r, target_q, target_r)
        return distance <= self.visibility_radius
    
    def can_player_see_position(self, player_id: str, target_q: int, target_r: int) -> bool:
        """Prüft ob ein Spieler eine Position sehen kann."""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        
        # Wenn Spieler in Team: Team-Position nutzen
        if player.team_id and player.team_id in self.teams:
            return self.can_team_see_position(player.team_id, target_q, target_r)
        
        # Einzelspieler
        distance = self.get_hex_distance(player.hex_q, player.hex_r, target_q, target_r)
        return distance <= self.visibility_radius
    
    def can_teams_see_each_other(self, team_a_id: str, team_b_id: str) -> bool:
        """Prüft ob zwei Teams sich gegenseitig sehen können."""
        if not self.teams_can_see_each_other:
            return False
        
        if team_a_id not in self.teams or team_b_id not in self.teams:
            return False
        
        team_a = self.teams[team_a_id]
        team_b = self.teams[team_b_id]
        
        distance = self.get_hex_distance(
            team_a.hex_q, team_a.hex_r,
            team_b.hex_q, team_b.hex_r
        )
        
        return distance <= self.visibility_radius
    
    def get_visible_players_for_team(self, team_id: str) -> List[PlayerDefinition]:
        """Gibt alle Spieler zurück, die ein Team sehen kann."""
        visible = []
        
        if team_id not in self.teams:
            return visible
        
        team = self.teams[team_id]
        
        for player in self.players.values():
            if not player.is_active:
                continue
            
            # Eigene Teammitglieder immer sichtbar
            if player.team_id == team_id:
                visible.append(player)
                continue
            
            # Prüfe ob in Sichtweite
            if self.can_team_see_position(team_id, player.hex_q, player.hex_r):
                visible.append(player)
        
        return visible
    
    def get_revealed_area_for_team(self, team_id: str) -> Set[Tuple[int, int]]:
        """Gibt alle Hexagone zurück, die ein Team sehen kann."""
        revealed = set()
        
        if team_id not in self.teams:
            return revealed
        
        team = self.teams[team_id]
        
        # Alle Hexagone im Radius
        for dq in range(-self.visibility_radius, self.visibility_radius + 1):
            for dr in range(-self.visibility_radius, self.visibility_radius + 1):
                if abs(dq + dr) <= self.visibility_radius:
                    revealed.add((team.hex_q + dq, team.hex_r + dr))
        
        return revealed
    
    # =====================================================
    # RENDERING
    # =====================================================
    
    def render_player_token(self, player: PlayerDefinition, size: int = 50) -> Image.Image:
        """Rendert ein Spieler-Token mit Name und Farbe."""
        # Token erstellen
        token = Image.new('RGBA', (size, size + 25), (0, 0, 0, 0))
        draw = ImageDraw.Draw(token)
        
        # Kreis mit Team-Farbe
        circle_margin = 5
        circle_size = size - circle_margin * 2
        
        # Parse Farbe
        try:
            color = player.color
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
            else:
                r, g, b = 68, 136, 255  # Default Blau
        except:
            r, g, b = 68, 136, 255
        
        # Äußerer Ring (dunkler)
        draw.ellipse(
            (circle_margin, circle_margin, 
             circle_margin + circle_size, circle_margin + circle_size),
            fill=(r // 2, g // 2, b // 2, 255),
            outline=(255, 255, 255, 255),
            width=2
        )
        
        # Innerer Kreis (Team-Farbe)
        inner_margin = 8
        draw.ellipse(
            (inner_margin, inner_margin,
             size - inner_margin, size - inner_margin),
            fill=(r, g, b, 220)
        )
        
        # Initialen oder Icon
        try:
            font = ImageFont.truetype("arial.ttf", int(size * 0.4))
            name_font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            name_font = font
        
        # Initiale zentriert
        initial = player.name[0].upper() if player.name else "?"
        bbox = draw.textbbox((0, 0), initial, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (size - text_width) // 2
        text_y = (size - text_height) // 2 - 3
        
        draw.text((text_x, text_y), initial, fill=(255, 255, 255, 255), font=font)
        
        # Name unter dem Token
        name_bbox = draw.textbbox((0, 0), player.name, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = (size - name_width) // 2
        
        # Hintergrund für Name
        draw.rectangle(
            (name_x - 3, size, name_x + name_width + 3, size + 18),
            fill=(0, 0, 0, 180)
        )
        draw.text((name_x, size + 2), player.name, fill=(255, 255, 255, 255), font=name_font)
        
        return token
    
    def render_team_indicator(self, team: TeamDefinition, size: int = 30) -> Image.Image:
        """Rendert einen Team-Indikator für die Minimap."""
        indicator = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(indicator)
        
        # Parse Farbe
        try:
            color = team.color
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
            else:
                r, g, b = 68, 136, 255
        except:
            r, g, b = 68, 136, 255
        
        # Diamant/Raute als Team-Symbol
        points = [
            (size // 2, 2),  # Oben
            (size - 2, size // 2),  # Rechts
            (size // 2, size - 2),  # Unten
            (2, size // 2)  # Links
        ]
        
        draw.polygon(points, fill=(r, g, b, 220), outline=(255, 255, 255, 255))
        
        return indicator
    
    # =====================================================
    # SERIALISIERUNG
    # =====================================================
    
    def to_dict(self) -> Dict:
        """Serialisiert den kompletten Spieler-Manager."""
        return {
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "teams": {tid: t.to_dict() for tid, t in self.teams.items()},
            "placements": [p.to_dict() for p in self.placements],
            "visibility_radius": self.visibility_radius,
            "teams_can_see_each_other": self.teams_can_see_each_other
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlayerManager':
        """Deserialisiert einen Spieler-Manager."""
        manager = cls()
        
        # Spieler laden
        for pid, pdata in data.get("players", {}).items():
            manager.players[pid] = PlayerDefinition.from_dict(pdata)
        
        # Teams laden
        for tid, tdata in data.get("teams", {}).items():
            manager.teams[tid] = TeamDefinition.from_dict(tdata)
        
        # Platzierungen laden
        for pdata in data.get("placements", []):
            manager.placements.append(PlayerPlacement.from_dict(pdata))
        
        manager.visibility_radius = data.get("visibility_radius", 3)
        manager.teams_can_see_each_other = data.get("teams_can_see_each_other", False)
        
        return manager
    
    def save_to_file(self, filepath: str):
        """Speichert Spieler-Daten in eine JSON-Datei."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"✅ Spieler-Daten gespeichert: {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'PlayerManager':
        """Lädt Spieler-Daten aus einer JSON-Datei."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


# =====================================================
# SPLIT-VIEW HELPER
# =====================================================

class SplitViewManager:
    """
    Verwaltet die Split-View für mehrere Teams.
    Jedes Team bekommt einen eigenen Viewport auf die Karte.
    """
    
    def __init__(self, player_manager: PlayerManager, num_screens: int = 2):
        self.player_manager = player_manager
        self.num_screens = num_screens
        self.zoom_level = 2.0  # 200% Zoom
        
        # Viewport pro Screen (team_id -> viewport_data)
        self.viewports: Dict[str, Dict] = {}
    
    def setup_viewports(self, canvas_width: int, canvas_height: int):
        """Initialisiert die Viewports für alle Teams."""
        teams = list(self.player_manager.teams.values())
        
        # Screen-Breite pro Team
        screen_width = canvas_width // self.num_screens
        
        for i, team in enumerate(teams[:self.num_screens]):
            self.viewports[team.id] = {
                "screen_index": i,
                "screen_x": i * screen_width,
                "screen_width": screen_width,
                "screen_height": canvas_height,
                "center_q": team.hex_q,
                "center_r": team.hex_r,
                "zoom": self.zoom_level
            }
    
    def get_viewport_for_team(self, team_id: str) -> Optional[Dict]:
        """Gibt die Viewport-Daten für ein Team zurück."""
        return self.viewports.get(team_id)
    
    def update_viewport_center(self, team_id: str, new_q: int, new_r: int):
        """Aktualisiert das Zentrum eines Team-Viewports."""
        if team_id in self.viewports:
            self.viewports[team_id]["center_q"] = new_q
            self.viewports[team_id]["center_r"] = new_r
    
    def get_screen_for_position(self, screen_x: int) -> Optional[str]:
        """Gibt die Team-ID für eine Screen-Position zurück."""
        for team_id, viewport in self.viewports.items():
            if viewport["screen_x"] <= screen_x < viewport["screen_x"] + viewport["screen_width"]:
                return team_id
        return None


# =====================================================
# WEBCAM FIGURE TRACKER (Basis-Klasse)
# =====================================================

class WebcamFigureTracker:
    """
    Trackt physische Figuren per Webcam und synchronisiert
    deren Position mit den digitalen Spieler-Positionen.
    """
    
    def __init__(self, player_manager: PlayerManager):
        self.player_manager = player_manager
        self.is_active = False
        self.camera = None
        self.camera_index = 0  # Standard-Kamera
        self.calibration_data = {}  # Kalibrierungsdaten für Hexagon-Erkennung
        
        # Map-Größe für Koordinaten-Konvertierung
        self.map_size = (20, 20)  # (width, height) in Hexagonen
        
        # Figuren-Tracking (color -> player_id)
        self.color_assignments: Dict[str, str] = {}
        
        # Letzte erkannte Positionen
        self.last_positions: Dict[str, Tuple[int, int]] = {}
    
    def start_tracking(self, camera_index: int = 0):
        """Startet das Webcam-Tracking."""
        try:
            import cv2
            self.camera = cv2.VideoCapture(camera_index)
            self.is_active = True
            print(f"📷 Webcam-Tracking gestartet (Kamera {camera_index})")
        except ImportError:
            print("❌ OpenCV nicht installiert - Webcam-Tracking nicht verfügbar")
        except Exception as e:
            print(f"❌ Webcam-Fehler: {e}")
    
    def stop_tracking(self):
        """Stoppt das Webcam-Tracking."""
        if self.camera:
            self.camera.release()
            self.camera = None
        self.is_active = False
        print("📷 Webcam-Tracking gestoppt")
    
    def calibrate(self, hex_corners: List[Tuple[int, int]]):
        """
        Kalibriert das Tracking mit den Ecken des Hexagon-Feldes.
        
        Args:
            hex_corners: 4 Ecken des sichtbaren Spielfelds in Pixel-Koordinaten
        """
        if len(hex_corners) != 4:
            print("❌ Kalibrierung benötigt 4 Eckpunkte")
            return
        
        self.calibration_data = {
            "corners": hex_corners,
            "calibrated": True
        }
        print("✅ Webcam-Tracking kalibriert")
    
    def assign_color_to_player(self, color_hsv: Tuple[int, int, int], player_id: str):
        """
        Weist eine Farbe einem Spieler zu.
        
        Args:
            color_hsv: HSV-Farbwert für die Figur
            player_id: ID des Spielers
        """
        color_key = f"{color_hsv[0]}_{color_hsv[1]}_{color_hsv[2]}"
        self.color_assignments[color_key] = player_id
    
    def detect_figures(self) -> Dict[str, Tuple[int, int]]:
        """
        Erkennt Figuren im aktuellen Kamerabild.
        
        Returns:
            Dict von player_id -> (hex_q, hex_r)
        """
        if not self.is_active or not self.camera:
            return {}
        
        detected = {}
        
        try:
            import cv2
            import numpy as np
            
            ret, frame = self.camera.read()
            if not ret:
                return {}
            
            # Konvertiere zu HSV für Farberkennung
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Für jede zugewiesene Farbe suchen
            for color_key, player_id in self.color_assignments.items():
                parts = color_key.split('_')
                h, s, v = int(parts[0]), int(parts[1]), int(parts[2])
                
                # Farbbereich definieren
                lower = np.array([max(0, h - 10), max(0, s - 40), max(0, v - 40)])
                upper = np.array([min(179, h + 10), min(255, s + 40), min(255, v + 40)])
                
                # Maske erstellen
                mask = cv2.inRange(hsv, lower, upper)
                
                # Konturen finden
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    # Größte Kontur finden
                    largest = max(contours, key=cv2.contourArea)
                    if cv2.contourArea(largest) > 100:  # Mindestgröße
                        M = cv2.moments(largest)
                        if M["m00"] > 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            
                            # Pixel zu Hexagon konvertieren
                            hex_q, hex_r = self._pixel_to_hex(cx, cy)
                            detected[player_id] = (hex_q, hex_r)
                            
                            # Position im Player-Manager aktualisieren
                            if player_id in self.player_manager.players:
                                old_q = self.player_manager.players[player_id].hex_q
                                old_r = self.player_manager.players[player_id].hex_r
                                
                                # Nur aktualisieren wenn sich Position geändert hat
                                if (hex_q, hex_r) != (old_q, old_r):
                                    self.player_manager.move_player(player_id, hex_q, hex_r)
                                    print(f"🎯 Spieler {player_id} bewegt: ({old_q},{old_r}) -> ({hex_q},{hex_r})")
        
        except Exception as e:
            print(f"⚠️ Figuren-Erkennung Fehler: {e}")
        
        self.last_positions = detected
        return detected
    
    def _pixel_to_hex(self, pixel_x: int, pixel_y: int) -> Tuple[int, int]:
        """Konvertiert Pixel-Koordinaten zu Hexagon-Koordinaten."""
        if not self.calibration_data.get("calibrated"):
            return (0, 0)
        
        # TODO: Perspektiv-Transformation basierend auf Kalibrierung
        # Vereinfachte Version: Lineare Skalierung
        corners = self.calibration_data["corners"]
        
        # Annahme: corners sind [top_left, top_right, bottom_right, bottom_left]
        min_x = min(c[0] for c in corners)
        max_x = max(c[0] for c in corners)
        min_y = min(c[1] for c in corners)
        max_y = max(c[1] for c in corners)
        
        # Normalisieren auf 0-1
        norm_x = (pixel_x - min_x) / (max_x - min_x) if max_x > min_x else 0
        norm_y = (pixel_y - min_y) / (max_y - min_y) if max_y > min_y else 0
        
        # Zu Hex-Koordinaten (abhängig von Kartengrößen)
        # Diese Werte müssen mit der tatsächlichen Karte abgestimmt werden
        hex_q = int(norm_x * 20)  # Beispiel: 20 Hexagone breit
        hex_r = int(norm_y * 20)
        
        return (hex_q, hex_r)


if __name__ == "__main__":
    # Test
    manager = PlayerManager()
    
    # Team erstellen
    team1 = TeamDefinition(name="Die Gefährten", color="#4488FF")
    manager.add_team(team1)
    
    # Spieler erstellen
    p1 = PlayerDefinition(name="Frodo", color="#4488FF")
    p2 = PlayerDefinition(name="Sam", color="#4488FF")
    manager.add_player(p1)
    manager.add_player(p2)
    
    # Zum Team hinzufügen
    manager.add_player_to_team(p1.id, team1.id)
    manager.add_player_to_team(p2.id, team1.id)
    
    # Zweites Team
    team2 = TeamDefinition(name="Orks", color="#FF4444")
    manager.add_team(team2)
    
    p3 = PlayerDefinition(name="Ork-Häuptling")
    manager.add_player(p3)
    manager.add_player_to_team(p3.id, team2.id)
    
    # Spawn-Test
    spawn_hexes = [(0, 0), (5, 5), (10, 10)]
    manager.distribute_players_randomly(spawn_hexes)
    
    print(f"\n📊 Spieler: {len(manager.players)}")
    print(f"📊 Teams: {len(manager.teams)}")
    print(f"📊 Platzierungen: {len(manager.placements)}")
    
    # Serialisierung testen
    data = manager.to_dict()
    print(f"\n📄 Serialisiert: {len(json.dumps(data))} Bytes")
