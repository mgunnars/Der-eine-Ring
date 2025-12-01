"""
Token System für "Der Eine Ring" VTT
=====================================

Implementiert Token-Funktionalität ähnlich FoundryVTT:
- Token-Platzierung auf der Karte
- Drag & Drop
- HP/Status-Tracking
- Token-Attribute (Name, Initiative, etc.)
- Verschiedene Token-Typen (PC, NPC, Monster)

Inspiriert von FoundryVTT's Token Layer System.
"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Callable
from enum import Enum
import json
import os
import math
import uuid

# UI-Framework importieren
try:
    from ui_framework import (
        UIColors, UISizes, UIIcons, 
        BaseDialog, VTTButton, VTTLabel, VTTEntry,
        show_info, show_warning, show_error, ask_confirm, ask_input
    )
    UI_FRAMEWORK_AVAILABLE = True
except ImportError:
    UI_FRAMEWORK_AVAILABLE = False


class TokenType(Enum):
    """Token-Typen für verschiedene Entitäten"""
    PC = "player_character"      # Spielercharakter
    NPC = "non_player_character" # Nicht-Spieler-Charakter
    MONSTER = "monster"          # Monster/Gegner
    CREATURE = "creature"        # Kreatur/Tier
    OBJECT = "object"            # Objekt (Falle, Schatz, etc.)
    MARKER = "marker"            # Einfacher Marker


class TokenCondition(Enum):
    """Status-Effekte für Tokens"""
    NONE = ""
    DEAD = "💀"
    UNCONSCIOUS = "😵"
    STUNNED = "⭐"
    POISONED = "☠️"
    BURNING = "🔥"
    FROZEN = "❄️"
    BLESSED = "✨"
    CURSED = "👁️"
    HIDDEN = "👤"
    PRONE = "🛏️"
    RESTRAINED = "⛓️"
    FRIGHTENED = "😱"
    CHARMED = "💕"
    INVISIBLE = "👻"


@dataclass
class Token:
    """
    Repräsentiert einen Token auf der Karte.
    
    Ein Token kann ein Spielercharakter, NPC, Monster oder Objekt sein.
    """
    # Identifikation
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Unbenannt"
    
    # Position (in Tile-Koordinaten)
    x: float = 0.0
    y: float = 0.0
    
    # Größe (in Tiles)
    width: int = 1
    height: int = 1
    
    # Typ
    token_type: TokenType = TokenType.PC
    
    # Darstellung
    image_path: Optional[str] = None
    color: str = "#4a90d9"  # Fallback-Farbe wenn kein Bild
    border_color: str = "#ffffff"
    show_name: bool = True
    
    # Attribute
    hp_current: int = 10
    hp_max: int = 10
    initiative: int = 0
    ac: int = 10  # Armor Class / Rüstungsklasse
    
    # Status
    conditions: List[TokenCondition] = field(default_factory=list)
    is_hidden: bool = False  # Nur für GM sichtbar
    
    # Rotation (in Grad)
    rotation: float = 0.0
    
    # Notizen
    notes: str = ""
    
    # Sichtbarkeit
    vision_range: int = 0  # 0 = nutzt globale Einstellung
    emits_light: bool = False
    light_radius: int = 2
    
    def to_dict(self) -> dict:
        """Serialisiert Token zu Dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "token_type": self.token_type.value,
            "image_path": self.image_path,
            "color": self.color,
            "border_color": self.border_color,
            "show_name": self.show_name,
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "initiative": self.initiative,
            "ac": self.ac,
            "conditions": [c.name for c in self.conditions],
            "is_hidden": self.is_hidden,
            "rotation": self.rotation,
            "notes": self.notes,
            "vision_range": self.vision_range,
            "emits_light": self.emits_light,
            "light_radius": self.light_radius
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Token':
        """Deserialisiert Token aus Dictionary"""
        token = cls()
        token.id = data.get("id", str(uuid.uuid4())[:8])
        token.name = data.get("name", "Unbenannt")
        token.x = data.get("x", 0.0)
        token.y = data.get("y", 0.0)
        token.width = data.get("width", 1)
        token.height = data.get("height", 1)
        token.token_type = TokenType(data.get("token_type", "player_character"))
        token.image_path = data.get("image_path")
        token.color = data.get("color", "#4a90d9")
        token.border_color = data.get("border_color", "#ffffff")
        token.show_name = data.get("show_name", True)
        token.hp_current = data.get("hp_current", 10)
        token.hp_max = data.get("hp_max", 10)
        token.initiative = data.get("initiative", 0)
        token.ac = data.get("ac", 10)
        token.conditions = [TokenCondition[c] for c in data.get("conditions", [])]
        token.is_hidden = data.get("is_hidden", False)
        token.rotation = data.get("rotation", 0.0)
        token.notes = data.get("notes", "")
        token.vision_range = data.get("vision_range", 0)
        token.emits_light = data.get("emits_light", False)
        token.light_radius = data.get("light_radius", 2)
        return token
    
    def get_hp_percentage(self) -> float:
        """Gibt HP als Prozentsatz zurück"""
        if self.hp_max <= 0:
            return 0.0
        return max(0.0, min(1.0, self.hp_current / self.hp_max))
    
    def get_hp_color(self) -> str:
        """Gibt Farbe basierend auf HP-Prozentsatz zurück"""
        pct = self.get_hp_percentage()
        if pct > 0.5:
            return "#44ff44"  # Grün
        elif pct > 0.25:
            return "#ffaa00"  # Orange
        elif pct > 0:
            return "#ff4444"  # Rot
        else:
            return "#888888"  # Grau (tot)
    
    def add_condition(self, condition: TokenCondition):
        """Fügt Status-Effekt hinzu"""
        if condition not in self.conditions:
            self.conditions.append(condition)
    
    def remove_condition(self, condition: TokenCondition):
        """Entfernt Status-Effekt"""
        if condition in self.conditions:
            self.conditions.remove(condition)
    
    def toggle_condition(self, condition: TokenCondition):
        """Toggled Status-Effekt"""
        if condition in self.conditions:
            self.conditions.remove(condition)
        else:
            self.conditions.append(condition)


class TokenLayer:
    """
    Verwaltet alle Tokens auf einer Karte.
    
    Ähnlich dem Token Layer in FoundryVTT.
    """
    
    def __init__(self):
        self.tokens: Dict[str, Token] = {}
        self.selected_token_id: Optional[str] = None
        self.on_token_changed: Optional[Callable[[Token], None]] = None
        self.on_selection_changed: Optional[Callable[[Optional[Token]], None]] = None
        
        # Cached Token-Images
        self._image_cache: Dict[str, ImageTk.PhotoImage] = {}
    
    def add_token(self, token: Token) -> str:
        """Fügt Token hinzu und gibt ID zurück"""
        self.tokens[token.id] = token
        if self.on_token_changed:
            self.on_token_changed(token)
        return token.id
    
    def remove_token(self, token_id: str) -> bool:
        """Entfernt Token"""
        if token_id in self.tokens:
            del self.tokens[token_id]
            if self.selected_token_id == token_id:
                self.selected_token_id = None
                if self.on_selection_changed:
                    self.on_selection_changed(None)
            return True
        return False
    
    def get_token(self, token_id: str) -> Optional[Token]:
        """Holt Token nach ID"""
        return self.tokens.get(token_id)
    
    def get_all_tokens(self) -> List[Token]:
        """Gibt alle Tokens zurück"""
        return list(self.tokens.values())
    
    def get_visible_tokens(self, is_gm: bool = False) -> List[Token]:
        """Gibt sichtbare Tokens zurück (GM sieht versteckte)"""
        if is_gm:
            return self.get_all_tokens()
        return [t for t in self.tokens.values() if not t.is_hidden]
    
    def get_token_at(self, x: float, y: float) -> Optional[Token]:
        """Findet Token an Position (Tile-Koordinaten)"""
        for token in reversed(list(self.tokens.values())):
            if (token.x <= x < token.x + token.width and
                token.y <= y < token.y + token.height):
                return token
        return None
    
    def select_token(self, token_id: Optional[str]):
        """Wählt Token aus"""
        self.selected_token_id = token_id
        if self.on_selection_changed:
            token = self.tokens.get(token_id) if token_id else None
            self.on_selection_changed(token)
    
    def get_selected_token(self) -> Optional[Token]:
        """Gibt ausgewählten Token zurück"""
        if self.selected_token_id:
            return self.tokens.get(self.selected_token_id)
        return None
    
    def move_token(self, token_id: str, x: float, y: float):
        """Bewegt Token zu neuer Position"""
        token = self.tokens.get(token_id)
        if token:
            token.x = x
            token.y = y
            if self.on_token_changed:
                self.on_token_changed(token)
    
    def duplicate_token(self, token_id: str) -> Optional[str]:
        """Dupliziert Token und gibt neue ID zurück"""
        original = self.tokens.get(token_id)
        if original:
            data = original.to_dict()
            data["id"] = str(uuid.uuid4())[:8]
            data["x"] = original.x + 1  # Leicht versetzt
            data["y"] = original.y + 1
            new_token = Token.from_dict(data)
            return self.add_token(new_token)
        return None
    
    def to_dict(self) -> dict:
        """Serialisiert Layer"""
        return {
            "tokens": [t.to_dict() for t in self.tokens.values()]
        }
    
    def from_dict(self, data: dict):
        """Lädt Layer aus Dictionary"""
        self.tokens.clear()
        for token_data in data.get("tokens", []):
            token = Token.from_dict(token_data)
            self.tokens[token.id] = token
    
    def get_token_image(self, token: Token, size: int = 64) -> Image.Image:
        """
        Erstellt Token-Bild für Rendering.
        
        Args:
            token: Der Token
            size: Größe in Pixeln (pro Tile)
        
        Returns:
            PIL Image des Tokens
        """
        total_size = size * max(token.width, token.height)
        
        # Versuche Bild zu laden
        if token.image_path and os.path.exists(token.image_path):
            try:
                img = Image.open(token.image_path)
                img = img.resize((total_size, total_size), Image.Resampling.LANCZOS)
                
                # Kreisförmig maskieren
                mask = Image.new('L', (total_size, total_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse([2, 2, total_size-2, total_size-2], fill=255)
                
                # RGBA-Modus sicherstellen
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Maske anwenden
                output = Image.new('RGBA', (total_size, total_size), (0, 0, 0, 0))
                output.paste(img, (0, 0), mask)
                
                return output
            except Exception as e:
                print(f"⚠️ Fehler beim Laden des Token-Bildes: {e}")
        
        # Fallback: Farbiger Kreis
        img = Image.new('RGBA', (total_size, total_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Hintergrundkreis
        r, g, b = self._hex_to_rgb(token.color)
        draw.ellipse([2, 2, total_size-2, total_size-2], 
                    fill=(r, g, b, 255))
        
        # Rand
        br, bg, bb = self._hex_to_rgb(token.border_color)
        draw.ellipse([2, 2, total_size-2, total_size-2], 
                    outline=(br, bg, bb, 255), width=3)
        
        # Initiale des Namens in der Mitte
        if token.name:
            initial = token.name[0].upper()
            try:
                font = ImageFont.truetype("arial.ttf", total_size // 2)
            except:
                font = ImageFont.load_default()
            
            # Text-Bounding-Box für Zentrierung
            bbox = draw.textbbox((0, 0), initial, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (total_size - text_width) // 2
            y = (total_size - text_height) // 2 - bbox[1]
            
            draw.text((x, y), initial, fill=(255, 255, 255, 255), font=font)
        
        return img
    
    def render_token(self, token: Token, tile_size: int = 64) -> Image.Image:
        """
        Rendert kompletten Token mit HP-Bar und Status-Icons.
        """
        base_img = self.get_token_image(token, tile_size)
        total_size = tile_size * max(token.width, token.height)
        
        # Neues Bild mit Platz für Zusatz-Elemente
        output = Image.new('RGBA', (total_size, total_size + 20), (0, 0, 0, 0))
        output.paste(base_img, (0, 0), base_img)
        
        draw = ImageDraw.Draw(output)
        
        # HP-Bar (unten)
        if token.hp_max > 0:
            bar_y = total_size + 2
            bar_height = 8
            bar_width = total_size - 10
            bar_x = 5
            
            # Hintergrund
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                          fill=(40, 40, 40, 200))
            
            # HP-Fill
            hp_pct = token.get_hp_percentage()
            fill_width = int(bar_width * hp_pct)
            if fill_width > 0:
                hp_color = token.get_hp_color()
                r, g, b = self._hex_to_rgb(hp_color)
                draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height],
                              fill=(r, g, b, 230))
            
            # Rahmen
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                          outline=(100, 100, 100, 255))
        
        # Status-Icons (oben links)
        if token.conditions:
            condition_str = "".join([c.value for c in token.conditions[:3]])
            if condition_str:
                try:
                    small_font = ImageFont.truetype("arial.ttf", 12)
                except:
                    small_font = ImageFont.load_default()
                draw.text((3, 3), condition_str, fill=(255, 255, 255, 255), font=small_font)
        
        # Versteckt-Indikator (für GM)
        if token.is_hidden:
            draw.text((total_size - 20, 3), "👁️", fill=(255, 200, 0, 200))
        
        return output
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Konvertiert Hex-Farbe zu RGB-Tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class TokenPropertiesDialog(BaseDialog if UI_FRAMEWORK_AVAILABLE else tk.Toplevel):
    """
    Dialog zum Bearbeiten von Token-Eigenschaften.
    """
    
    def __init__(self, parent, token: Token, on_save: Callable[[Token], None] = None):
        self.token = token
        self.on_save = on_save
        
        if UI_FRAMEWORK_AVAILABLE:
            super().__init__(parent, f"Token: {token.name}", width=600, height=700)
        else:
            super().__init__(parent)
            self.title(f"Token: {token.name}")
            self.geometry("600x700")
            self.configure(bg="#1a1a1a")
            self.transient(parent)
            self.grab_set()
            
            # Content-Frame manuell erstellen
            self.content_frame = tk.Frame(self, bg="#1a1a1a")
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            self.button_frame = tk.Frame(self, bg="#1a1a1a")
            self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Erstellt die Dialog-UI"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
        fg = UIColors.TEXT_PRIMARY if UI_FRAMEWORK_AVAILABLE else "#ffffff"
        input_bg = UIColors.BG_INPUT if UI_FRAMEWORK_AVAILABLE else "#3a3a3a"
        
        # Notebook für Tabs
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Basis
        base_frame = tk.Frame(notebook, bg=bg)
        notebook.add(base_frame, text="  📋 Basis  ")
        self._setup_base_tab(base_frame, bg, fg, input_bg)
        
        # Tab 2: Attribute
        attr_frame = tk.Frame(notebook, bg=bg)
        notebook.add(attr_frame, text="  ⚔️ Attribute  ")
        self._setup_attributes_tab(attr_frame, bg, fg, input_bg)
        
        # Tab 3: Status
        status_frame = tk.Frame(notebook, bg=bg)
        notebook.add(status_frame, text="  🏷️ Status  ")
        self._setup_status_tab(status_frame, bg, fg, input_bg)
        
        # Tab 4: Darstellung
        visual_frame = tk.Frame(notebook, bg=bg)
        notebook.add(visual_frame, text="  🎨 Darstellung  ")
        self._setup_visual_tab(visual_frame, bg, fg, input_bg)
        
        # Buttons
        self._add_buttons()
    
    def _setup_base_tab(self, parent, bg, fg, input_bg):
        """Basis-Eigenschaften Tab"""
        # Name
        tk.Label(parent, text="Name:", bg=bg, fg=fg, font=("Arial", 11)).pack(anchor=tk.W, pady=(10, 2))
        self.name_var = tk.StringVar(value=self.token.name)
        tk.Entry(parent, textvariable=self.name_var, bg=input_bg, fg=fg,
                font=("Arial", 11), insertbackground=fg).pack(fill=tk.X, pady=(0, 10))
        
        # Typ
        tk.Label(parent, text="Typ:", bg=bg, fg=fg, font=("Arial", 11)).pack(anchor=tk.W, pady=(10, 2))
        self.type_var = tk.StringVar(value=self.token.token_type.value)
        type_frame = tk.Frame(parent, bg=bg)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        types = [
            ("🧙 Spieler", TokenType.PC.value),
            ("👤 NPC", TokenType.NPC.value),
            ("👹 Monster", TokenType.MONSTER.value),
            ("🦊 Kreatur", TokenType.CREATURE.value),
            ("📦 Objekt", TokenType.OBJECT.value),
            ("📍 Marker", TokenType.MARKER.value),
        ]
        
        for text, value in types:
            tk.Radiobutton(type_frame, text=text, variable=self.type_var, value=value,
                          bg=bg, fg=fg, selectcolor=input_bg, activebackground=bg,
                          font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        # Größe
        tk.Label(parent, text="Größe (in Tiles):", bg=bg, fg=fg, font=("Arial", 11)).pack(anchor=tk.W, pady=(10, 2))
        size_frame = tk.Frame(parent, bg=bg)
        size_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(size_frame, text="Breite:", bg=bg, fg=fg).pack(side=tk.LEFT)
        self.width_var = tk.IntVar(value=self.token.width)
        tk.Spinbox(size_frame, from_=1, to=10, textvariable=self.width_var, width=5).pack(side=tk.LEFT, padx=5)
        
        tk.Label(size_frame, text="Höhe:", bg=bg, fg=fg).pack(side=tk.LEFT, padx=(20, 0))
        self.height_var = tk.IntVar(value=self.token.height)
        tk.Spinbox(size_frame, from_=1, to=10, textvariable=self.height_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # Notizen
        tk.Label(parent, text="Notizen:", bg=bg, fg=fg, font=("Arial", 11)).pack(anchor=tk.W, pady=(10, 2))
        self.notes_text = tk.Text(parent, height=6, bg=input_bg, fg=fg, font=("Arial", 10),
                                 insertbackground=fg)
        self.notes_text.pack(fill=tk.X, pady=(0, 10))
        self.notes_text.insert("1.0", self.token.notes)
    
    def _setup_attributes_tab(self, parent, bg, fg, input_bg):
        """Attribute Tab"""
        # HP
        hp_frame = tk.LabelFrame(parent, text="Lebenspunkte (HP)", bg=bg, fg=fg, font=("Arial", 11, "bold"))
        hp_frame.pack(fill=tk.X, padx=10, pady=10)
        
        hp_inner = tk.Frame(hp_frame, bg=bg)
        hp_inner.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(hp_inner, text="Aktuell:", bg=bg, fg=fg).pack(side=tk.LEFT)
        self.hp_current_var = tk.IntVar(value=self.token.hp_current)
        tk.Spinbox(hp_inner, from_=0, to=999, textvariable=self.hp_current_var, width=5).pack(side=tk.LEFT, padx=5)
        
        tk.Label(hp_inner, text="/ Maximum:", bg=bg, fg=fg).pack(side=tk.LEFT, padx=(10, 0))
        self.hp_max_var = tk.IntVar(value=self.token.hp_max)
        tk.Spinbox(hp_inner, from_=1, to=999, textvariable=self.hp_max_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # Quick-Buttons
        quick_frame = tk.Frame(hp_frame, bg=bg)
        quick_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        for label, change in [("-5", -5), ("-1", -1), ("+1", 1), ("+5", 5), ("Voll", "full")]:
            def make_hp_change(c):
                return lambda: self._change_hp(c)
            
            color = "#2a7d2a" if change in [1, 5, "full"] else "#7d2a2a"
            tk.Button(quick_frame, text=label, bg=color, fg="white", font=("Arial", 9),
                     padx=8, command=make_hp_change(change)).pack(side=tk.LEFT, padx=2)
        
        # Initiative
        init_frame = tk.LabelFrame(parent, text="Kampf", bg=bg, fg=fg, font=("Arial", 11, "bold"))
        init_frame.pack(fill=tk.X, padx=10, pady=10)
        
        init_inner = tk.Frame(init_frame, bg=bg)
        init_inner.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(init_inner, text="Initiative:", bg=bg, fg=fg).pack(side=tk.LEFT)
        self.initiative_var = tk.IntVar(value=self.token.initiative)
        tk.Spinbox(init_inner, from_=0, to=99, textvariable=self.initiative_var, width=5).pack(side=tk.LEFT, padx=5)
        
        tk.Label(init_inner, text="Rüstungsklasse:", bg=bg, fg=fg).pack(side=tk.LEFT, padx=(20, 0))
        self.ac_var = tk.IntVar(value=self.token.ac)
        tk.Spinbox(init_inner, from_=0, to=99, textvariable=self.ac_var, width=5).pack(side=tk.LEFT, padx=5)
    
    def _setup_status_tab(self, parent, bg, fg, input_bg):
        """Status-Effekte Tab"""
        tk.Label(parent, text="Aktive Status-Effekte:", bg=bg, fg=fg, 
                font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Condition Checkbuttons
        conditions_frame = tk.Frame(parent, bg=bg)
        conditions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.condition_vars = {}
        
        for i, condition in enumerate(TokenCondition):
            if condition == TokenCondition.NONE:
                continue
            
            var = tk.BooleanVar(value=condition in self.token.conditions)
            self.condition_vars[condition] = var
            
            row = i // 3
            col = i % 3
            
            text = f"{condition.value} {condition.name.replace('_', ' ').title()}"
            tk.Checkbutton(conditions_frame, text=text, variable=var,
                          bg=bg, fg=fg, selectcolor=input_bg, activebackground=bg,
                          font=("Arial", 10)).grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
        
        # Versteckt
        tk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=15)
        
        self.hidden_var = tk.BooleanVar(value=self.token.is_hidden)
        tk.Checkbutton(parent, text="👁️ Token ist versteckt (nur für GM sichtbar)",
                      variable=self.hidden_var, bg=bg, fg=fg, selectcolor=input_bg,
                      font=("Arial", 11)).pack(anchor=tk.W, padx=10)
    
    def _setup_visual_tab(self, parent, bg, fg, input_bg):
        """Darstellungs-Tab"""
        # Bild
        tk.Label(parent, text="Token-Bild:", bg=bg, fg=fg, font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        img_frame = tk.Frame(parent, bg=bg)
        img_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.image_path_var = tk.StringVar(value=self.token.image_path or "")
        tk.Entry(img_frame, textvariable=self.image_path_var, bg=input_bg, fg=fg,
                font=("Arial", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(img_frame, text="📂", bg=input_bg, fg=fg,
                 command=self._browse_image).pack(side=tk.LEFT, padx=5)
        
        # Farben
        color_frame = tk.Frame(parent, bg=bg)
        color_frame.pack(fill=tk.X, padx=10, pady=15)
        
        tk.Label(color_frame, text="Hintergrundfarbe:", bg=bg, fg=fg).pack(side=tk.LEFT)
        self.color_btn = tk.Button(color_frame, text="   ", bg=self.token.color,
                                  command=self._pick_color, width=4)
        self.color_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Label(color_frame, text="Randfarbe:", bg=bg, fg=fg).pack(side=tk.LEFT, padx=(20, 0))
        self.border_btn = tk.Button(color_frame, text="   ", bg=self.token.border_color,
                                   command=self._pick_border_color, width=4)
        self.border_btn.pack(side=tk.LEFT, padx=5)
        
        # Name anzeigen
        self.show_name_var = tk.BooleanVar(value=self.token.show_name)
        tk.Checkbutton(parent, text="Name anzeigen", variable=self.show_name_var,
                      bg=bg, fg=fg, selectcolor=input_bg, font=("Arial", 11)).pack(anchor=tk.W, padx=10, pady=10)
        
        # Licht
        light_frame = tk.LabelFrame(parent, text="Lichtquelle", bg=bg, fg=fg, font=("Arial", 11, "bold"))
        light_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.emits_light_var = tk.BooleanVar(value=self.token.emits_light)
        tk.Checkbutton(light_frame, text="Token emittiert Licht", variable=self.emits_light_var,
                      bg=bg, fg=fg, selectcolor=input_bg).pack(anchor=tk.W, padx=10, pady=5)
        
        light_radius_frame = tk.Frame(light_frame, bg=bg)
        light_radius_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(light_radius_frame, text="Lichtradius (Tiles):", bg=bg, fg=fg).pack(side=tk.LEFT)
        self.light_radius_var = tk.IntVar(value=self.token.light_radius)
        tk.Spinbox(light_radius_frame, from_=1, to=20, textvariable=self.light_radius_var, width=5).pack(side=tk.LEFT, padx=5)
    
    def _add_buttons(self):
        """Fügt Speichern/Abbrechen Buttons hinzu"""
        btn_bg = UIColors.ACCENT_GREEN if UI_FRAMEWORK_AVAILABLE else "#2a7d2a"
        cancel_bg = UIColors.ACCENT_RED if UI_FRAMEWORK_AVAILABLE else "#7d2a2a"
        
        tk.Button(self.button_frame, text="✅ Speichern", bg=btn_bg, fg="white",
                 font=("Arial", 11, "bold"), padx=20, pady=8,
                 command=self._on_save).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(self.button_frame, text="❌ Abbrechen", bg=cancel_bg, fg="white",
                 font=("Arial", 11, "bold"), padx=20, pady=8,
                 command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _change_hp(self, change):
        """Ändert HP"""
        if change == "full":
            self.hp_current_var.set(self.hp_max_var.get())
        else:
            new_val = max(0, self.hp_current_var.get() + change)
            self.hp_current_var.set(new_val)
    
    def _browse_image(self):
        """Öffnet Datei-Dialog für Token-Bild"""
        path = filedialog.askopenfilename(
            title="Token-Bild auswählen",
            filetypes=[
                ("Bilder", "*.png;*.jpg;*.jpeg;*.gif;*.webp"),
                ("Alle Dateien", "*.*")
            ]
        )
        if path:
            self.image_path_var.set(path)
    
    def _pick_color(self):
        """Öffnet Farbwähler"""
        color = colorchooser.askcolor(self.color_btn.cget("bg"), title="Hintergrundfarbe wählen")
        if color[1]:
            self.color_btn.config(bg=color[1])
    
    def _pick_border_color(self):
        """Öffnet Farbwähler für Rand"""
        color = colorchooser.askcolor(self.border_btn.cget("bg"), title="Randfarbe wählen")
        if color[1]:
            self.border_btn.config(bg=color[1])
    
    def _on_save(self):
        """Speichert Änderungen"""
        # Werte übernehmen
        self.token.name = self.name_var.get()
        self.token.token_type = TokenType(self.type_var.get())
        self.token.width = self.width_var.get()
        self.token.height = self.height_var.get()
        self.token.notes = self.notes_text.get("1.0", tk.END).strip()
        
        self.token.hp_current = self.hp_current_var.get()
        self.token.hp_max = self.hp_max_var.get()
        self.token.initiative = self.initiative_var.get()
        self.token.ac = self.ac_var.get()
        
        # Conditions
        self.token.conditions = [c for c, var in self.condition_vars.items() if var.get()]
        self.token.is_hidden = self.hidden_var.get()
        
        # Visual
        img_path = self.image_path_var.get().strip()
        self.token.image_path = img_path if img_path else None
        self.token.color = self.color_btn.cget("bg")
        self.token.border_color = self.border_btn.cget("bg")
        self.token.show_name = self.show_name_var.get()
        self.token.emits_light = self.emits_light_var.get()
        self.token.light_radius = self.light_radius_var.get()
        
        if self.on_save:
            self.on_save(self.token)
        
        self.destroy()


class TokenToolbar(tk.Frame):
    """
    Toolbar für Token-Operationen.
    Wird im Editor oder GM-Panel angezeigt.
    """
    
    def __init__(self, parent, token_layer: TokenLayer, on_token_action: Callable = None):
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        super().__init__(parent, bg=bg)
        
        self.token_layer = token_layer
        self.on_token_action = on_token_action
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Erstellt Toolbar-UI"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        fg = UIColors.TEXT_PRIMARY if UI_FRAMEWORK_AVAILABLE else "#ffffff"
        
        # Titel
        tk.Label(self, text="🎭 Tokens", bg=bg, fg=fg,
                font=("Arial", 12, "bold")).pack(pady=(10, 5))
        
        # Buttons
        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        buttons = [
            ("➕ Neu", self._add_token, "#2a7d2a"),
            ("📋 Duplizieren", self._duplicate_token, "#2a5d8d"),
            ("🗑️ Löschen", self._delete_token, "#7d2a2a"),
        ]
        
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, bg=color, fg="white",
                     font=("Arial", 9), padx=8, pady=4,
                     command=cmd).pack(side=tk.LEFT, padx=2)
        
        # Token-Liste
        tk.Label(self, text="Auf der Karte:", bg=bg, fg=fg,
                font=("Arial", 10)).pack(anchor=tk.W, padx=5, pady=(10, 2))
        
        list_frame = tk.Frame(self, bg=bg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.token_listbox = tk.Listbox(list_frame, bg="#2a2a2a", fg=fg,
                                       font=("Arial", 10), selectmode=tk.SINGLE,
                                       yscrollcommand=scrollbar.set)
        self.token_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.token_listbox.yview)
        
        self.token_listbox.bind("<<ListboxSelect>>", self._on_select)
        self.token_listbox.bind("<Double-Button-1>", self._on_double_click)
        
        # Initial befüllen
        self.refresh_list()
    
    def refresh_list(self):
        """Aktualisiert Token-Liste"""
        self.token_listbox.delete(0, tk.END)
        
        for token in self.token_layer.get_all_tokens():
            # Format: Icon + Name + HP
            icon = "👁️" if token.is_hidden else ""
            type_icons = {
                TokenType.PC: "🧙",
                TokenType.NPC: "👤",
                TokenType.MONSTER: "👹",
                TokenType.CREATURE: "🦊",
                TokenType.OBJECT: "📦",
                TokenType.MARKER: "📍",
            }
            type_icon = type_icons.get(token.token_type, "🎭")
            hp_text = f"({token.hp_current}/{token.hp_max})"
            
            text = f"{icon}{type_icon} {token.name} {hp_text}"
            self.token_listbox.insert(tk.END, text)
    
    def _add_token(self):
        """Fügt neuen Token hinzu"""
        token = Token(name="Neuer Token", x=5, y=5)
        self.token_layer.add_token(token)
        self.refresh_list()
        
        if self.on_token_action:
            self.on_token_action("add", token)
    
    def _duplicate_token(self):
        """Dupliziert ausgewählten Token"""
        token = self.token_layer.get_selected_token()
        if token:
            new_id = self.token_layer.duplicate_token(token.id)
            if new_id:
                self.refresh_list()
                if self.on_token_action:
                    self.on_token_action("duplicate", self.token_layer.get_token(new_id))
    
    def _delete_token(self):
        """Löscht ausgewählten Token"""
        token = self.token_layer.get_selected_token()
        if token:
            self.token_layer.remove_token(token.id)
            self.refresh_list()
            if self.on_token_action:
                self.on_token_action("delete", token)
    
    def _on_select(self, event):
        """Bei Auswahl in Liste"""
        selection = self.token_listbox.curselection()
        if selection:
            tokens = self.token_layer.get_all_tokens()
            if selection[0] < len(tokens):
                token = tokens[selection[0]]
                self.token_layer.select_token(token.id)
    
    def _on_double_click(self, event):
        """Bei Doppelklick - Properties öffnen"""
        token = self.token_layer.get_selected_token()
        if token:
            def on_save(t):
                self.refresh_list()
                if self.on_token_action:
                    self.on_token_action("update", t)
            
            TokenPropertiesDialog(self, token, on_save)


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Token System Test")
    root.geometry("800x600")
    root.configure(bg="#1a1a1a")
    
    # Token Layer erstellen
    layer = TokenLayer()
    
    # Test-Tokens
    t1 = Token(name="Aragorn", token_type=TokenType.PC, x=5, y=5, hp_current=50, hp_max=50)
    t2 = Token(name="Orc Krieger", token_type=TokenType.MONSTER, x=10, y=5, 
               hp_current=15, hp_max=20, color="#8b0000")
    t3 = Token(name="Gandalf", token_type=TokenType.NPC, x=7, y=8,
               hp_current=100, hp_max=100, emits_light=True, light_radius=5)
    
    layer.add_token(t1)
    layer.add_token(t2)
    layer.add_token(t3)
    
    # Toolbar
    toolbar = TokenToolbar(root, layer)
    toolbar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    
    # Preview-Canvas
    canvas = tk.Canvas(root, bg="#2a2a2a", width=400, height=400)
    canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Tokens rendern
    tile_size = 64
    for token in layer.get_all_tokens():
        img = layer.render_token(token, tile_size)
        photo = ImageTk.PhotoImage(img)
        
        x = int(token.x * tile_size)
        y = int(token.y * tile_size)
        
        canvas.create_image(x, y, image=photo, anchor=tk.NW, tags=token.id)
        canvas.image = photo  # Referenz behalten
    
    root.mainloop()
