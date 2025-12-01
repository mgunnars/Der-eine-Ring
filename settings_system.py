"""
Settings System - Umfassendes Einstellungssystem für das VTT
Verwaltet alle Konfigurationen zentral
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import json
import os
from pathlib import Path

# UI Framework importieren
try:
    from ui_framework import UIColors, UISizes, WindowManager, BaseDialog
except ImportError:
    class UIColors:
        BG_DARK = "#1a1a2e"
        BG_MEDIUM = "#16213e"
        BG_LIGHT = "#0f3460"
        ACCENT = "#e94560"
        TEXT = "#eaeaea"
        TEXT_DIM = "#888888"
        SUCCESS = "#4ecca3"
        WARNING = "#ffc107"
        DANGER = "#ff6b6b"
        BORDER = "#333355"


class SettingType(Enum):
    """Typen von Einstellungen"""
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    COLOR = "color"
    PATH = "path"
    CHOICE = "choice"
    KEYBIND = "keybind"
    RANGE = "range"


@dataclass
class Setting:
    """Eine einzelne Einstellung"""
    key: str
    name: str
    description: str = ""
    setting_type: SettingType = SettingType.STRING
    default_value: Any = None
    current_value: Any = None
    
    # Für CHOICE
    choices: List[Any] = field(default_factory=list)
    
    # Für RANGE/INTEGER/FLOAT
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    
    # Für PATH
    path_type: str = "file"  # "file" oder "directory"
    file_types: List[tuple] = field(default_factory=list)
    
    # Kategorie
    category: str = "Allgemein"
    
    # Callback bei Änderung
    on_change: Optional[Callable[[Any], None]] = None
    
    # Nur für erfahrene Benutzer
    advanced: bool = False
    
    # Neustart erforderlich
    requires_restart: bool = False
    
    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value
    
    def reset(self):
        """Auf Standardwert zurücksetzen"""
        self.current_value = self.default_value
        if self.on_change:
            self.on_change(self.current_value)
    
    def set_value(self, value: Any):
        """Wert setzen"""
        old_value = self.current_value
        self.current_value = value
        
        if self.on_change and old_value != value:
            self.on_change(value)
    
    def to_dict(self) -> dict:
        """Als Dictionary für JSON"""
        return {
            'key': self.key,
            'value': self.current_value
        }


class SettingsManager:
    """Verwaltet alle Einstellungen"""
    
    def __init__(self, config_dir: str = None):
        self.settings: Dict[str, Setting] = {}
        self.categories: List[str] = []
        
        # Konfigurationspfad
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".vtt_settings")
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "settings.json")
        
        # Callbacks
        self.on_settings_changed: Optional[Callable[[], None]] = None
        
        # Standard-Einstellungen registrieren
        self._register_default_settings()
    
    def _register_default_settings(self):
        """Standard-Einstellungen registrieren"""
        
        # === ANZEIGE ===
        self.register(Setting(
            key="display.theme",
            name="Farbschema",
            description="Das Farbschema der Benutzeroberfläche",
            setting_type=SettingType.CHOICE,
            default_value="dark",
            choices=["dark", "light", "midnight", "forest"],
            category="Anzeige"
        ))
        
        self.register(Setting(
            key="display.font_size",
            name="Schriftgröße",
            description="Basis-Schriftgröße der UI",
            setting_type=SettingType.RANGE,
            default_value=12,
            min_value=8,
            max_value=24,
            step=1,
            category="Anzeige"
        ))
        
        self.register(Setting(
            key="display.animations",
            name="Animationen",
            description="UI-Animationen aktivieren",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="Anzeige"
        ))
        
        self.register(Setting(
            key="display.show_fps",
            name="FPS anzeigen",
            description="Zeigt die Bildrate an",
            setting_type=SettingType.BOOLEAN,
            default_value=False,
            category="Anzeige",
            advanced=True
        ))
        
        # === KARTE ===
        self.register(Setting(
            key="map.grid_size",
            name="Rastergröße",
            description="Größe eines Rasterfeldes in Pixeln",
            setting_type=SettingType.INTEGER,
            default_value=50,
            min_value=10,
            max_value=200,
            category="Karte"
        ))
        
        self.register(Setting(
            key="map.grid_color",
            name="Rasterfarbe",
            description="Farbe des Kartenrasters",
            setting_type=SettingType.COLOR,
            default_value="#444466",
            category="Karte"
        ))
        
        self.register(Setting(
            key="map.grid_opacity",
            name="Raster-Deckkraft",
            description="Transparenz des Rasters (0-100%)",
            setting_type=SettingType.RANGE,
            default_value=50,
            min_value=0,
            max_value=100,
            category="Karte"
        ))
        
        self.register(Setting(
            key="map.snap_to_grid",
            name="Am Raster ausrichten",
            description="Token automatisch am Raster ausrichten",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="Karte"
        ))
        
        self.register(Setting(
            key="map.default_zoom",
            name="Standard-Zoom",
            description="Zoom-Stufe beim Laden einer Karte",
            setting_type=SettingType.RANGE,
            default_value=100,
            min_value=25,
            max_value=400,
            step=25,
            category="Karte"
        ))
        
        # === TOKEN ===
        self.register(Setting(
            key="token.default_size",
            name="Standard Token-Größe",
            description="Größe neuer Token in Rasterfeldern",
            setting_type=SettingType.CHOICE,
            default_value=1,
            choices=[0.5, 1, 2, 3, 4],
            category="Token"
        ))
        
        self.register(Setting(
            key="token.show_hp_bar",
            name="HP-Balken anzeigen",
            description="Lebensbalken über Token anzeigen",
            setting_type=SettingType.CHOICE,
            default_value="always",
            choices=["always", "hover", "owner", "never"],
            category="Token"
        ))
        
        self.register(Setting(
            key="token.show_names",
            name="Namen anzeigen",
            description="Token-Namen anzeigen",
            setting_type=SettingType.CHOICE,
            default_value="hover",
            choices=["always", "hover", "owner", "never"],
            category="Token"
        ))
        
        self.register(Setting(
            key="token.default_vision",
            name="Standard-Sichtweite",
            description="Sichtweite für neue Token (in Feldern)",
            setting_type=SettingType.INTEGER,
            default_value=12,
            min_value=0,
            max_value=50,
            category="Token"
        ))
        
        # === BELEUCHTUNG ===
        self.register(Setting(
            key="lighting.global_illumination",
            name="Globale Beleuchtung",
            description="Grundbeleuchtung der Szene",
            setting_type=SettingType.RANGE,
            default_value=50,
            min_value=0,
            max_value=100,
            category="Beleuchtung"
        ))
        
        self.register(Setting(
            key="lighting.darkness_color",
            name="Dunkelheitsfarbe",
            description="Farbe unbeleuchteter Bereiche",
            setting_type=SettingType.COLOR,
            default_value="#000000",
            category="Beleuchtung"
        ))
        
        self.register(Setting(
            key="lighting.soft_shadows",
            name="Weiche Schatten",
            description="Weiche Schattenränder aktivieren",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="Beleuchtung"
        ))
        
        self.register(Setting(
            key="lighting.fog_exploration",
            name="Nebel des Krieges",
            description="Unerforschte Bereiche verbergen",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="Beleuchtung"
        ))
        
        # === AUDIO ===
        self.register(Setting(
            key="audio.master_volume",
            name="Master-Lautstärke",
            description="Gesamtlautstärke aller Sounds",
            setting_type=SettingType.RANGE,
            default_value=80,
            min_value=0,
            max_value=100,
            category="Audio"
        ))
        
        self.register(Setting(
            key="audio.ambient_volume",
            name="Ambient-Lautstärke",
            description="Lautstärke von Umgebungsgeräuschen",
            setting_type=SettingType.RANGE,
            default_value=70,
            min_value=0,
            max_value=100,
            category="Audio"
        ))
        
        self.register(Setting(
            key="audio.music_volume",
            name="Musik-Lautstärke",
            description="Lautstärke der Hintergrundmusik",
            setting_type=SettingType.RANGE,
            default_value=60,
            min_value=0,
            max_value=100,
            category="Audio"
        ))
        
        self.register(Setting(
            key="audio.sound_library",
            name="Sound-Bibliothek",
            description="Pfad zur Sound-Bibliothek",
            setting_type=SettingType.PATH,
            default_value="",
            path_type="directory",
            category="Audio"
        ))
        
        # === TASTENKÜRZEL ===
        self.register(Setting(
            key="keybind.toggle_gm_panel",
            name="GM-Panel öffnen",
            description="Tastenkürzel für das GM-Panel",
            setting_type=SettingType.KEYBIND,
            default_value="F1",
            category="Tastenkürzel"
        ))
        
        self.register(Setting(
            key="keybind.toggle_combat",
            name="Combat Tracker",
            description="Tastenkürzel für den Combat Tracker",
            setting_type=SettingType.KEYBIND,
            default_value="F2",
            category="Tastenkürzel"
        ))
        
        self.register(Setting(
            key="keybind.toggle_journal",
            name="Journal",
            description="Tastenkürzel für das Journal",
            setting_type=SettingType.KEYBIND,
            default_value="F3",
            category="Tastenkürzel"
        ))
        
        self.register(Setting(
            key="keybind.pause_game",
            name="Spiel pausieren",
            description="Tastenkürzel zum Pausieren",
            setting_type=SettingType.KEYBIND,
            default_value="space",
            category="Tastenkürzel"
        ))
        
        self.register(Setting(
            key="keybind.select_tool",
            name="Auswahl-Werkzeug",
            description="Zum Auswahl-Werkzeug wechseln",
            setting_type=SettingType.KEYBIND,
            default_value="v",
            category="Tastenkürzel"
        ))
        
        # === PERFORMANCE ===
        self.register(Setting(
            key="performance.max_fps",
            name="Max. FPS",
            description="Maximale Bildrate",
            setting_type=SettingType.CHOICE,
            default_value=60,
            choices=[30, 60, 120, 0],  # 0 = unbegrenzt
            category="Performance",
            advanced=True
        ))
        
        self.register(Setting(
            key="performance.hardware_acceleration",
            name="Hardware-Beschleunigung",
            description="GPU für Rendering verwenden",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="Performance",
            requires_restart=True
        ))
        
        self.register(Setting(
            key="performance.texture_quality",
            name="Textur-Qualität",
            description="Qualität der Texturen",
            setting_type=SettingType.CHOICE,
            default_value="high",
            choices=["low", "medium", "high", "ultra"],
            category="Performance"
        ))
        
        self.register(Setting(
            key="performance.cache_size",
            name="Cache-Größe (MB)",
            description="Maximale Größe des Bild-Caches",
            setting_type=SettingType.INTEGER,
            default_value=512,
            min_value=128,
            max_value=4096,
            category="Performance",
            advanced=True
        ))
        
        # === PFADE ===
        self.register(Setting(
            key="paths.maps",
            name="Karten-Ordner",
            description="Standard-Ordner für Karten",
            setting_type=SettingType.PATH,
            default_value="",
            path_type="directory",
            category="Pfade"
        ))
        
        self.register(Setting(
            key="paths.tokens",
            name="Token-Ordner",
            description="Standard-Ordner für Token-Bilder",
            setting_type=SettingType.PATH,
            default_value="",
            path_type="directory",
            category="Pfade"
        ))
        
        self.register(Setting(
            key="paths.scenes",
            name="Szenen-Ordner",
            description="Standard-Ordner für Szenen",
            setting_type=SettingType.PATH,
            default_value="",
            path_type="directory",
            category="Pfade"
        ))
        
        self.register(Setting(
            key="paths.exports",
            name="Export-Ordner",
            description="Standard-Ordner für Exporte",
            setting_type=SettingType.PATH,
            default_value="",
            path_type="directory",
            category="Pfade"
        ))
    
    def register(self, setting: Setting):
        """Einstellung registrieren"""
        self.settings[setting.key] = setting
        
        if setting.category not in self.categories:
            self.categories.append(setting.category)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Einstellungswert abrufen"""
        setting = self.settings.get(key)
        if setting:
            return setting.current_value
        return default
    
    def set(self, key: str, value: Any):
        """Einstellungswert setzen"""
        setting = self.settings.get(key)
        if setting:
            setting.set_value(value)
            
            if self.on_settings_changed:
                self.on_settings_changed()
    
    def reset_all(self):
        """Alle Einstellungen zurücksetzen"""
        for setting in self.settings.values():
            setting.reset()
        
        if self.on_settings_changed:
            self.on_settings_changed()
    
    def reset_category(self, category: str):
        """Kategorie zurücksetzen"""
        for setting in self.settings.values():
            if setting.category == category:
                setting.reset()
        
        if self.on_settings_changed:
            self.on_settings_changed()
    
    def get_settings_by_category(self, category: str, 
                                  include_advanced: bool = False) -> List[Setting]:
        """Einstellungen einer Kategorie"""
        return [
            s for s in self.settings.values()
            if s.category == category and (include_advanced or not s.advanced)
        ]
    
    def save(self):
        """Einstellungen speichern"""
        # Verzeichnis erstellen
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Daten sammeln
        data = {}
        for key, setting in self.settings.items():
            data[key] = setting.current_value
        
        # Speichern
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        """Einstellungen laden"""
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, value in data.items():
                if key in self.settings:
                    self.settings[key].current_value = value
        
        except Exception as e:
            print(f"Fehler beim Laden der Einstellungen: {e}")
    
    def export_to_file(self, filepath: str):
        """Einstellungen exportieren"""
        data = {}
        for key, setting in self.settings.items():
            data[key] = setting.current_value
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def import_from_file(self, filepath: str):
        """Einstellungen importieren"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, value in data.items():
            if key in self.settings:
                self.settings[key].current_value = value
        
        if self.on_settings_changed:
            self.on_settings_changed()


class SettingWidget:
    """Widget für eine einzelne Einstellung"""
    
    @staticmethod
    def create(parent: tk.Frame, setting: Setting, 
               on_change: Callable[[Any], None]) -> tk.Widget:
        """Passendes Widget für Einstellungstyp erstellen"""
        
        if setting.setting_type == SettingType.BOOLEAN:
            return SettingWidget._create_boolean(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.INTEGER:
            return SettingWidget._create_integer(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.FLOAT:
            return SettingWidget._create_float(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.STRING:
            return SettingWidget._create_string(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.COLOR:
            return SettingWidget._create_color(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.PATH:
            return SettingWidget._create_path(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.CHOICE:
            return SettingWidget._create_choice(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.KEYBIND:
            return SettingWidget._create_keybind(parent, setting, on_change)
        
        elif setting.setting_type == SettingType.RANGE:
            return SettingWidget._create_range(parent, setting, on_change)
        
        return tk.Label(parent, text="?", bg=UIColors.BG_DARK)
    
    @staticmethod
    def _create_boolean(parent, setting, on_change):
        var = tk.BooleanVar(value=setting.current_value)
        
        def changed():
            on_change(var.get())
        
        cb = tk.Checkbutton(
            parent,
            variable=var,
            command=changed,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM,
            activebackground=UIColors.BG_DARK
        )
        return cb
    
    @staticmethod
    def _create_integer(parent, setting, on_change):
        var = tk.IntVar(value=setting.current_value)
        
        def changed(*args):
            try:
                on_change(var.get())
            except:
                pass
        
        spinbox = tk.Spinbox(
            parent,
            from_=setting.min_value,
            to=setting.max_value,
            textvariable=var,
            command=changed,
            width=10,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        )
        spinbox.bind("<Return>", changed)
        return spinbox
    
    @staticmethod
    def _create_float(parent, setting, on_change):
        var = tk.DoubleVar(value=setting.current_value)
        
        def changed(*args):
            try:
                on_change(var.get())
            except:
                pass
        
        spinbox = tk.Spinbox(
            parent,
            from_=setting.min_value,
            to=setting.max_value,
            increment=setting.step,
            textvariable=var,
            command=changed,
            width=10,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        )
        return spinbox
    
    @staticmethod
    def _create_string(parent, setting, on_change):
        var = tk.StringVar(value=setting.current_value or "")
        
        def changed(*args):
            on_change(var.get())
        
        entry = tk.Entry(
            parent,
            textvariable=var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT,
            width=30
        )
        entry.bind("<FocusOut>", changed)
        entry.bind("<Return>", changed)
        return entry
    
    @staticmethod
    def _create_color(parent, setting, on_change):
        frame = tk.Frame(parent, bg=UIColors.BG_DARK)
        
        color_label = tk.Label(
            frame,
            text="  ",
            bg=setting.current_value or "#000000",
            width=4,
            relief=tk.RAISED
        )
        color_label.pack(side=tk.LEFT, padx=5)
        
        def choose_color():
            color = colorchooser.askcolor(
                initialcolor=setting.current_value,
                title="Farbe wählen"
            )
            if color[1]:
                color_label.config(bg=color[1])
                on_change(color[1])
        
        tk.Button(
            frame,
            text="Wählen...",
            command=choose_color,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        return frame
    
    @staticmethod
    def _create_path(parent, setting, on_change):
        frame = tk.Frame(parent, bg=UIColors.BG_DARK)
        
        var = tk.StringVar(value=setting.current_value or "")
        
        entry = tk.Entry(
            frame,
            textvariable=var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            width=30
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse():
            if setting.path_type == "directory":
                path = filedialog.askdirectory()
            else:
                path = filedialog.askopenfilename(filetypes=setting.file_types)
            
            if path:
                var.set(path)
                on_change(path)
        
        tk.Button(
            frame,
            text="...",
            command=browse,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=3
        ).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    @staticmethod
    def _create_choice(parent, setting, on_change):
        var = tk.StringVar(value=str(setting.current_value))
        
        def changed(event=None):
            value = var.get()
            # Typ konvertieren wenn nötig
            for choice in setting.choices:
                if str(choice) == value:
                    on_change(choice)
                    break
        
        combo = ttk.Combobox(
            parent,
            textvariable=var,
            values=[str(c) for c in setting.choices],
            state="readonly",
            width=15
        )
        combo.bind("<<ComboboxSelected>>", changed)
        return combo
    
    @staticmethod
    def _create_keybind(parent, setting, on_change):
        frame = tk.Frame(parent, bg=UIColors.BG_DARK)
        
        var = tk.StringVar(value=setting.current_value or "")
        
        entry = tk.Entry(
            frame,
            textvariable=var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            width=15,
            state="readonly"
        )
        entry.pack(side=tk.LEFT)
        
        def capture_key():
            dialog = tk.Toplevel(parent)
            dialog.title("Taste drücken...")
            dialog.geometry("200x100")
            dialog.configure(bg=UIColors.BG_DARK)
            dialog.transient(parent.winfo_toplevel())
            dialog.grab_set()
            
            tk.Label(
                dialog,
                text="Drücke eine Taste...",
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT
            ).pack(expand=True)
            
            def on_key(event):
                key = event.keysym
                var.set(key)
                on_change(key)
                dialog.destroy()
            
            dialog.bind("<Key>", on_key)
            dialog.focus_set()
        
        tk.Button(
            frame,
            text="Ändern",
            command=capture_key,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    @staticmethod
    def _create_range(parent, setting, on_change):
        frame = tk.Frame(parent, bg=UIColors.BG_DARK)
        
        var = tk.DoubleVar(value=setting.current_value)
        
        def changed(value):
            val = float(value)
            if setting.step >= 1:
                val = int(val)
            label.config(text=str(val))
            on_change(val)
        
        scale = tk.Scale(
            frame,
            from_=setting.min_value,
            to=setting.max_value,
            resolution=setting.step,
            orient=tk.HORIZONTAL,
            variable=var,
            command=changed,
            length=150,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            troughcolor=UIColors.BG_MEDIUM,
            highlightthickness=0,
            showvalue=False
        )
        scale.pack(side=tk.LEFT)
        
        label = tk.Label(
            frame,
            text=str(setting.current_value),
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=5
        )
        label.pack(side=tk.LEFT, padx=5)
        
        return frame


class SettingsWindow(tk.Toplevel):
    """Einstellungs-Fenster"""
    
    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        
        self.title("⚙️ Einstellungen")
        self.configure(bg=UIColors.BG_DARK)
        
        # Fenster zentriert auf Bildschirm platzieren
        self._center_on_screen(800, 600)
        self.minsize(700, 500)
    
    def _center_on_screen(self, width: int, height: int):
        """Zentriert Fenster und passt an Bildschirmgröße an"""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(width, screen_w - 100)
        height = min(height, screen_h - 100)
        x = max(50, (screen_w - width) // 2)
        y = max(30, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.show_advanced = False
        self.pending_restart = False
        
        self._create_widgets()
        self._load_category(self.settings_manager.categories[0])
    
    def _create_widgets(self):
        """UI aufbauen"""
        # Linke Seite: Kategorien
        left_frame = tk.Frame(self, bg=UIColors.BG_MEDIUM, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        tk.Label(
            left_frame,
            text="Kategorien",
            font=("Segoe UI", 12, "bold"),
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        ).pack(pady=10)
        
        self.category_buttons = []
        for category in self.settings_manager.categories:
            btn = tk.Button(
                left_frame,
                text=category,
                command=lambda c=category: self._load_category(c),
                bg=UIColors.BG_LIGHT,
                fg=UIColors.TEXT,
                relief=tk.FLAT,
                anchor=tk.W,
                padx=20
            )
            btn.pack(fill=tk.X, padx=5, pady=2)
            self.category_buttons.append((category, btn))
        
        # Erweitert-Checkbox
        self.advanced_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            left_frame,
            text="Erweiterte Optionen",
            variable=self.advanced_var,
            command=self._toggle_advanced,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_DARK
        ).pack(side=tk.BOTTOM, pady=10)
        
        # Rechte Seite: Einstellungen
        right_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(right_frame, bg=UIColors.BG_DARK)
        header.pack(fill=tk.X, padx=20, pady=10)
        
        self.category_label = tk.Label(
            header,
            text="",
            font=("Segoe UI", 16, "bold"),
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        )
        self.category_label.pack(side=tk.LEFT)
        
        tk.Button(
            header,
            text="Kategorie zurücksetzen",
            command=self._reset_category,
            bg=UIColors.WARNING,
            fg="black"
        ).pack(side=tk.RIGHT)
        
        # Scrollbarer Bereich
        canvas_frame = tk.Frame(right_frame, bg=UIColors.BG_DARK)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg=UIColors.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.settings_frame = tk.Frame(self.canvas, bg=UIColors.BG_DARK)
        
        self.canvas.create_window((0, 0), window=self.settings_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.settings_frame.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Mausrad-Binding
        self.canvas.bind_all("<MouseWheel>", 
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Footer
        footer = tk.Frame(right_frame, bg=UIColors.BG_MEDIUM)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(
            footer,
            text="Alle zurücksetzen",
            command=self._reset_all,
            bg=UIColors.DANGER,
            fg="white"
        ).pack(side=tk.LEFT, padx=10, pady=10)
        
        tk.Button(
            footer,
            text="Exportieren",
            command=self._export,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            footer,
            text="Importieren",
            command=self._import,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            footer,
            text="Speichern & Schließen",
            command=self._save_and_close,
            bg=UIColors.SUCCESS,
            fg="white"
        ).pack(side=tk.RIGHT, padx=10, pady=10)
    
    def _load_category(self, category: str):
        """Kategorie laden"""
        self.current_category = category
        self.category_label.config(text=category)
        
        # Buttons aktualisieren
        for cat, btn in self.category_buttons:
            if cat == category:
                btn.config(bg=UIColors.ACCENT)
            else:
                btn.config(bg=UIColors.BG_LIGHT)
        
        # Alte Widgets löschen
        for widget in self.settings_frame.winfo_children():
            widget.destroy()
        
        # Einstellungen laden
        settings = self.settings_manager.get_settings_by_category(
            category, include_advanced=self.show_advanced
        )
        
        for setting in settings:
            self._create_setting_row(setting)
    
    def _create_setting_row(self, setting: Setting):
        """Zeile für eine Einstellung erstellen"""
        row = tk.Frame(self.settings_frame, bg=UIColors.BG_DARK)
        row.pack(fill=tk.X, pady=5, padx=10)
        
        # Labels
        label_frame = tk.Frame(row, bg=UIColors.BG_DARK)
        label_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        name_text = setting.name
        if setting.advanced:
            name_text = f"⚙️ {name_text}"
        if setting.requires_restart:
            name_text = f"{name_text} 🔄"
        
        tk.Label(
            label_frame,
            text=name_text,
            font=("Segoe UI", 10, "bold"),
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            anchor=tk.W
        ).pack(anchor=tk.W)
        
        if setting.description:
            tk.Label(
                label_frame,
                text=setting.description,
                font=("Segoe UI", 9),
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT_DIM,
                anchor=tk.W
            ).pack(anchor=tk.W)
        
        # Widget
        widget_frame = tk.Frame(row, bg=UIColors.BG_DARK)
        widget_frame.pack(side=tk.RIGHT)
        
        def on_change(value):
            setting.set_value(value)
            if setting.requires_restart:
                self.pending_restart = True
        
        widget = SettingWidget.create(widget_frame, setting, on_change)
        widget.pack()
        
        # Trennlinie
        ttk.Separator(self.settings_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)
    
    def _toggle_advanced(self):
        """Erweiterte Optionen umschalten"""
        self.show_advanced = self.advanced_var.get()
        self._load_category(self.current_category)
    
    def _reset_category(self):
        """Aktuelle Kategorie zurücksetzen"""
        if messagebox.askyesno("Zurücksetzen", 
            f"Alle Einstellungen in '{self.current_category}' zurücksetzen?"):
            self.settings_manager.reset_category(self.current_category)
            self._load_category(self.current_category)
    
    def _reset_all(self):
        """Alle Einstellungen zurücksetzen"""
        if messagebox.askyesno("Zurücksetzen",
            "ALLE Einstellungen auf Standardwerte zurücksetzen?"):
            self.settings_manager.reset_all()
            self._load_category(self.current_category)
    
    def _export(self):
        """Einstellungen exportieren"""
        filepath = filedialog.asksaveasfilename(
            title="Einstellungen exportieren",
            filetypes=[("JSON", "*.json")],
            defaultextension=".json"
        )
        
        if filepath:
            try:
                self.settings_manager.export_to_file(filepath)
                messagebox.showinfo("Erfolg", "Einstellungen exportiert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
    
    def _import(self):
        """Einstellungen importieren"""
        filepath = filedialog.askopenfilename(
            title="Einstellungen importieren",
            filetypes=[("JSON", "*.json")]
        )
        
        if filepath:
            try:
                self.settings_manager.import_from_file(filepath)
                self._load_category(self.current_category)
                messagebox.showinfo("Erfolg", "Einstellungen importiert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Import fehlgeschlagen:\n{e}")
    
    def _save_and_close(self):
        """Speichern und Schließen"""
        self.settings_manager.save()
        
        if self.pending_restart:
            messagebox.showinfo("Neustart erforderlich",
                "Einige Änderungen erfordern einen Neustart der Anwendung.")
        
        self.destroy()


# Singleton für globalen Zugriff
_settings_manager: Optional[SettingsManager] = None

def get_settings_manager() -> SettingsManager:
    """Globalen SettingsManager abrufen"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        _settings_manager.load()
    return _settings_manager


# Testfunktion
def test_settings_system():
    """Testet das Settings-System"""
    root = tk.Tk()
    root.withdraw()
    
    settings = get_settings_manager()
    
    window = SettingsWindow(root, settings)
    window.mainloop()


if __name__ == "__main__":
    test_settings_system()
