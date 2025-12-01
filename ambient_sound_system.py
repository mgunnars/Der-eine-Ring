"""
Ambient Sound System - FoundryVTT-ähnliches Umgebungsklang-System
Ermöglicht das Platzieren von Soundquellen auf der Karte
"""

import tkinter as tk
from tkinter import ttk, filedialog
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum
import json
import math
import uuid
import os
import threading

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

# Audio-Bibliothek versuchen zu importieren
try:
    import pygame
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warnung: pygame nicht installiert. Audio-Wiedergabe nicht verfügbar.")


class SoundType(Enum):
    """Verschiedene Sound-Typen"""
    AMBIENT = "ambient"       # Dauerhafter Umgebungsklang
    TRIGGERED = "triggered"   # Wird bei Betreten ausgelöst
    MUSIC = "music"          # Hintergrundmusik
    EFFECT = "effect"        # Einmaliger Effekt


@dataclass
class AmbientSound:
    """Ein Ambient Sound auf der Karte"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Neuer Sound"
    x: float = 0.0
    y: float = 0.0
    radius: float = 200.0         # Hörradius in Pixeln
    max_radius: float = 400.0     # Maximaler Radius (wo Sound komplett ausblendet)
    volume: float = 0.8           # Basis-Lautstärke 0-1
    sound_type: SoundType = SoundType.AMBIENT
    file_path: str = ""           # Pfad zur Audio-Datei
    loop: bool = True             # Wiederholung
    is_playing: bool = False
    gm_only: bool = False         # Nur für GM hörbar
    walls_block: bool = True      # Wird durch Wände blockiert
    
    # Easing für Lautstärke
    easing: str = "linear"        # linear, quadratic, exponential
    
    def get_volume_at_distance(self, distance: float) -> float:
        """Berechnet Lautstärke basierend auf Distanz"""
        if distance <= self.radius:
            return self.volume
        
        if distance >= self.max_radius:
            return 0.0
        
        # Normalisierte Distanz zwischen radius und max_radius
        t = (distance - self.radius) / (self.max_radius - self.radius)
        
        # Easing anwenden
        if self.easing == "linear":
            factor = 1.0 - t
        elif self.easing == "quadratic":
            factor = 1.0 - (t * t)
        elif self.easing == "exponential":
            factor = math.exp(-3 * t)
        else:
            factor = 1.0 - t
        
        return self.volume * factor
    
    def distance_to(self, x: float, y: float) -> float:
        """Distanz zu einem Punkt"""
        return math.sqrt((self.x - x)**2 + (self.y - y)**2)
    
    def point_in_range(self, x: float, y: float) -> bool:
        """Prüft ob Punkt im Hörbereich liegt"""
        return self.distance_to(x, y) <= self.max_radius
    
    def to_dict(self) -> dict:
        """Sound als Dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'radius': self.radius,
            'max_radius': self.max_radius,
            'volume': self.volume,
            'sound_type': self.sound_type.value,
            'file_path': self.file_path,
            'loop': self.loop,
            'gm_only': self.gm_only,
            'walls_block': self.walls_block,
            'easing': self.easing
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AmbientSound':
        """Sound aus Dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Sound'),
            x=data.get('x', 0),
            y=data.get('y', 0),
            radius=data.get('radius', 200),
            max_radius=data.get('max_radius', 400),
            volume=data.get('volume', 0.8),
            sound_type=SoundType(data.get('sound_type', 'ambient')),
            file_path=data.get('file_path', ''),
            loop=data.get('loop', True),
            gm_only=data.get('gm_only', False),
            walls_block=data.get('walls_block', True),
            easing=data.get('easing', 'linear')
        )


class SoundManager:
    """Verwaltet alle Sounds einer Szene"""
    
    def __init__(self):
        self.sounds: List[AmbientSound] = []
        self.active_channels: Dict[str, any] = {}  # sound_id -> pygame.Channel
        self.loaded_sounds: Dict[str, any] = {}    # file_path -> pygame.Sound
        
        # Listener-Position (Token/Kamera des Spielers)
        self.listener_x = 0.0
        self.listener_y = 0.0
        
        # Master-Lautstärke
        self.master_volume = 1.0
        
        # Update-Thread
        self._update_thread = None
        self._running = False
    
    def add_sound(self, sound: AmbientSound):
        """Sound hinzufügen"""
        self.sounds.append(sound)
    
    def create_sound(self, x: float, y: float, **kwargs) -> AmbientSound:
        """Neuen Sound erstellen"""
        sound = AmbientSound(x=x, y=y, **kwargs)
        self.sounds.append(sound)
        return sound
    
    def delete_sound(self, sound_id: str) -> bool:
        """Sound löschen"""
        for i, sound in enumerate(self.sounds):
            if sound.id == sound_id:
                self.stop_sound(sound_id)
                del self.sounds[i]
                return True
        return False
    
    def get_sound(self, sound_id: str) -> Optional[AmbientSound]:
        """Sound nach ID"""
        for sound in self.sounds:
            if sound.id == sound_id:
                return sound
        return None
    
    def get_sound_at(self, x: float, y: float, threshold: float = 20) -> Optional[AmbientSound]:
        """Sound an Position finden"""
        for sound in reversed(self.sounds):
            dist = sound.distance_to(x, y)
            if dist <= threshold:
                return sound
        return None
    
    def update_listener_position(self, x: float, y: float):
        """Listener-Position aktualisieren"""
        self.listener_x = x
        self.listener_y = y
        self._update_volumes()
    
    def _update_volumes(self):
        """Lautstärken aller aktiven Sounds aktualisieren"""
        if not AUDIO_AVAILABLE:
            return
        
        for sound in self.sounds:
            if sound.is_playing and sound.id in self.active_channels:
                distance = sound.distance_to(self.listener_x, self.listener_y)
                volume = sound.get_volume_at_distance(distance) * self.master_volume
                
                channel = self.active_channels.get(sound.id)
                if channel and channel.get_busy():
                    channel.set_volume(volume)
    
    def play_sound(self, sound: AmbientSound):
        """Sound abspielen"""
        if not AUDIO_AVAILABLE:
            sound.is_playing = True
            return
        
        if not sound.file_path or not os.path.exists(sound.file_path):
            print(f"Warnung: Sound-Datei nicht gefunden: {sound.file_path}")
            return
        
        try:
            # Sound laden wenn noch nicht geschehen
            if sound.file_path not in self.loaded_sounds:
                self.loaded_sounds[sound.file_path] = pygame.mixer.Sound(sound.file_path)
            
            pygame_sound = self.loaded_sounds[sound.file_path]
            
            # Kanal für diesen Sound finden oder erstellen
            channel = pygame.mixer.find_channel()
            if channel:
                loops = -1 if sound.loop else 0
                channel.play(pygame_sound, loops=loops)
                
                # Anfangslautstärke setzen
                distance = sound.distance_to(self.listener_x, self.listener_y)
                volume = sound.get_volume_at_distance(distance) * self.master_volume
                channel.set_volume(volume)
                
                self.active_channels[sound.id] = channel
                sound.is_playing = True
        
        except Exception as e:
            print(f"Fehler beim Abspielen: {e}")
    
    def stop_sound(self, sound_id: str):
        """Sound stoppen"""
        sound = self.get_sound(sound_id)
        if sound:
            sound.is_playing = False
        
        if sound_id in self.active_channels:
            channel = self.active_channels[sound_id]
            if channel:
                channel.stop()
            del self.active_channels[sound_id]
    
    def play_all(self):
        """Alle Ambient-Sounds starten"""
        for sound in self.sounds:
            if sound.sound_type == SoundType.AMBIENT and not sound.is_playing:
                self.play_sound(sound)
    
    def stop_all(self):
        """Alle Sounds stoppen"""
        for sound in self.sounds:
            if sound.is_playing:
                self.stop_sound(sound.id)
    
    def set_master_volume(self, volume: float):
        """Master-Lautstärke setzen (0-1)"""
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
    
    def to_dict(self) -> dict:
        """Alle Sounds als Dictionary"""
        return {
            'sounds': [s.to_dict() for s in self.sounds],
            'master_volume': self.master_volume
        }
    
    def from_dict(self, data: dict):
        """Sounds aus Dictionary laden"""
        self.stop_all()
        self.sounds.clear()
        
        for sound_data in data.get('sounds', []):
            sound = AmbientSound.from_dict(sound_data)
            self.sounds.append(sound)
        
        self.master_volume = data.get('master_volume', 1.0)
    
    def save_to_file(self, filepath: str):
        """Sounds in Datei speichern"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Sounds aus Datei laden"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_dict(data)


class SoundLayer:
    """Canvas-Layer für Sound-Visualisierung"""
    
    def __init__(self, canvas: tk.Canvas, sound_manager: SoundManager):
        self.canvas = canvas
        self.sound_manager = sound_manager
        
        # Platzierungsmodus
        self.placement_mode = False
        
        # Auswahl
        self.selected_sound: Optional[AmbientSound] = None
        
        # Canvas-IDs
        self.sound_canvas_ids: Dict[str, List[int]] = {}
        
        # Callbacks
        self.on_sound_selected: Optional[Callable[[AmbientSound], None]] = None
        
        # Anzeige-Optionen
        self.show_ranges = True
        self.show_icons = True
    
    def enable_placement(self):
        """Platzierungsmodus aktivieren"""
        self.placement_mode = True
        self.canvas.config(cursor="crosshair")
        self.canvas.bind("<Button-1>", self._on_place)
    
    def disable_placement(self):
        """Platzierungsmodus deaktivieren"""
        self.placement_mode = False
        self.canvas.config(cursor="")
        self.canvas.unbind("<Button-1>")
    
    def enable_selection(self):
        """Auswahlmodus aktivieren"""
        self.placement_mode = False
        self.canvas.config(cursor="hand2")
        self.canvas.bind("<Button-1>", self._on_select)
    
    def _on_place(self, event):
        """Sound platzieren"""
        sound = self.sound_manager.create_sound(event.x, event.y)
        self._draw_sound(sound)
        
        # Dialog zur Konfiguration öffnen
        if hasattr(self.canvas, 'winfo_toplevel'):
            SoundConfigDialog(
                self.canvas.winfo_toplevel(),
                sound,
                self._on_sound_configured
            )
    
    def _on_select(self, event):
        """Sound auswählen"""
        sound = self.sound_manager.get_sound_at(event.x, event.y)
        
        # Vorherige Auswahl aufheben
        if self.selected_sound:
            self._draw_sound(self.selected_sound)
        
        self.selected_sound = sound
        
        if sound:
            self._draw_sound(sound, selected=True)
            if self.on_sound_selected:
                self.on_sound_selected(sound)
    
    def _on_sound_configured(self, sound: AmbientSound):
        """Callback wenn Sound konfiguriert wurde"""
        if sound:
            self._draw_sound(sound)
    
    def _draw_sound(self, sound: AmbientSound, selected: bool = False):
        """Sound auf Canvas zeichnen"""
        # Alte Zeichnung löschen
        if sound.id in self.sound_canvas_ids:
            for canvas_id in self.sound_canvas_ids[sound.id]:
                self.canvas.delete(canvas_id)
        
        ids = []
        
        if self.show_ranges:
            # Maximaler Radius (äußerer Kreis)
            outer_id = self.canvas.create_oval(
                sound.x - sound.max_radius,
                sound.y - sound.max_radius,
                sound.x + sound.max_radius,
                sound.y + sound.max_radius,
                outline="#4488ff" if sound.is_playing else "#445588",
                width=1,
                dash=(4, 4),
                tags=("sound", f"sound_{sound.id}")
            )
            ids.append(outer_id)
            
            # Innerer Radius (volle Lautstärke)
            inner_id = self.canvas.create_oval(
                sound.x - sound.radius,
                sound.y - sound.radius,
                sound.x + sound.radius,
                sound.y + sound.radius,
                outline="#44ff88" if sound.is_playing else "#448855",
                fill="" if not sound.is_playing else "#44ff8820",
                width=2,
                tags=("sound", f"sound_{sound.id}")
            )
            ids.append(inner_id)
        
        if self.show_icons:
            # Icon in der Mitte
            icon_color = UIColors.SUCCESS if sound.is_playing else UIColors.TEXT_DIM
            
            # Icon basierend auf Typ
            if sound.sound_type == SoundType.AMBIENT:
                icon = "🔊"
            elif sound.sound_type == SoundType.MUSIC:
                icon = "🎵"
            elif sound.sound_type == SoundType.TRIGGERED:
                icon = "🔔"
            else:
                icon = "📢"
            
            # Hintergrund-Kreis
            bg_color = UIColors.ACCENT if selected else UIColors.BG_MEDIUM
            bg_id = self.canvas.create_oval(
                sound.x - 15, sound.y - 15,
                sound.x + 15, sound.y + 15,
                fill=bg_color,
                outline="white" if selected else UIColors.BORDER,
                width=2 if selected else 1,
                tags=("sound", f"sound_{sound.id}")
            )
            ids.append(bg_id)
            
            # Icon
            icon_id = self.canvas.create_text(
                sound.x, sound.y,
                text=icon,
                font=("Segoe UI Emoji", 12),
                fill="white",
                tags=("sound", f"sound_{sound.id}")
            )
            ids.append(icon_id)
            
            # Name
            if sound.name:
                name_id = self.canvas.create_text(
                    sound.x, sound.y + 25,
                    text=sound.name,
                    font=("Segoe UI", 9),
                    fill=UIColors.TEXT,
                    tags=("sound", f"sound_{sound.id}")
                )
                ids.append(name_id)
        
        self.sound_canvas_ids[sound.id] = ids
    
    def redraw_all(self):
        """Alle Sounds neu zeichnen"""
        self.canvas.delete("sound")
        self.sound_canvas_ids.clear()
        
        for sound in self.sound_manager.sounds:
            is_selected = self.selected_sound and self.selected_sound.id == sound.id
            self._draw_sound(sound, selected=is_selected)
    
    def delete_selected(self):
        """Ausgewählten Sound löschen"""
        if self.selected_sound:
            self.sound_manager.delete_sound(self.selected_sound.id)
            self.redraw_all()
            self.selected_sound = None


class SoundConfigDialog:
    """Dialog zur Sound-Konfiguration"""
    
    def __init__(self, parent: tk.Tk, sound: AmbientSound, 
                 on_save: Callable[[AmbientSound], None]):
        self.sound = sound
        self.on_save = on_save
        
        # Dialog erstellen
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sound konfigurieren")
        self.dialog.geometry("450x550")
        self.dialog.configure(bg=UIColors.BG_DARK)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        
        # Zentrieren
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 550) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """UI aufbauen"""
        main_frame = tk.Frame(self.dialog, bg=UIColors.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Titel
        tk.Label(
            main_frame,
            text="🔊 Sound-Eigenschaften",
            font=("Segoe UI", 14, "bold"),
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Name
        name_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        name_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            name_frame,
            text="Name:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=12,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.name_var = tk.StringVar(value=self.sound.name)
        tk.Entry(
            name_frame,
            textvariable=self.name_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Sound-Typ
        type_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        type_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            type_frame,
            text="Typ:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=12,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.type_var = tk.StringVar(value=self.sound.sound_type.value)
        type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.type_var,
            values=[t.value for t in SoundType],
            state="readonly"
        )
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Datei
        file_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        file_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            file_frame,
            text="Datei:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=12,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.file_var = tk.StringVar(value=self.sound.file_path)
        file_entry = tk.Entry(
            file_frame,
            textvariable=self.file_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT
        )
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(
            file_frame,
            text="...",
            command=self._browse_file,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=3
        ).pack(side=tk.LEFT, padx=5)
        
        # Lautstärke
        vol_frame = tk.LabelFrame(
            main_frame,
            text="Lautstärke",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        )
        vol_frame.pack(fill=tk.X, pady=10)
        
        self.volume_var = tk.DoubleVar(value=self.sound.volume)
        
        vol_inner = tk.Frame(vol_frame, bg=UIColors.BG_DARK)
        vol_inner.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            vol_inner,
            text="Lautstärke:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        self.vol_label = tk.Label(
            vol_inner,
            text=f"{int(self.sound.volume * 100)}%",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=5
        )
        self.vol_label.pack(side=tk.RIGHT)
        
        vol_scale = tk.Scale(
            vol_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self._update_vol_label,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            troughcolor=UIColors.BG_MEDIUM,
            highlightthickness=0
        )
        vol_scale.set(int(self.sound.volume * 100))
        vol_scale.pack(fill=tk.X, padx=10, pady=5)
        
        # Radius
        radius_frame = tk.LabelFrame(
            main_frame,
            text="Reichweite",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        )
        radius_frame.pack(fill=tk.X, pady=10)
        
        # Innerer Radius
        inner_frame = tk.Frame(radius_frame, bg=UIColors.BG_DARK)
        inner_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            inner_frame,
            text="Volle Lautstärke (px):",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=20,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.radius_var = tk.IntVar(value=int(self.sound.radius))
        tk.Spinbox(
            inner_frame,
            from_=10, to=1000,
            textvariable=self.radius_var,
            width=8,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        # Äußerer Radius
        outer_frame = tk.Frame(radius_frame, bg=UIColors.BG_DARK)
        outer_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            outer_frame,
            text="Max. Reichweite (px):",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=20,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.max_radius_var = tk.IntVar(value=int(self.sound.max_radius))
        tk.Spinbox(
            outer_frame,
            from_=10, to=2000,
            textvariable=self.max_radius_var,
            width=8,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        # Easing
        ease_frame = tk.Frame(radius_frame, bg=UIColors.BG_DARK)
        ease_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            ease_frame,
            text="Ausblenden:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=20,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.easing_var = tk.StringVar(value=self.sound.easing)
        ttk.Combobox(
            ease_frame,
            textvariable=self.easing_var,
            values=["linear", "quadratic", "exponential"],
            state="readonly",
            width=12
        ).pack(side=tk.LEFT)
        
        # Optionen
        opt_frame = tk.LabelFrame(
            main_frame,
            text="Optionen",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        )
        opt_frame.pack(fill=tk.X, pady=10)
        
        self.loop_var = tk.BooleanVar(value=self.sound.loop)
        tk.Checkbutton(
            opt_frame,
            text="Wiederholen (Loop)",
            variable=self.loop_var,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        self.gm_only_var = tk.BooleanVar(value=self.sound.gm_only)
        tk.Checkbutton(
            opt_frame,
            text="Nur für GM hörbar",
            variable=self.gm_only_var,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        self.walls_var = tk.BooleanVar(value=self.sound.walls_block)
        tk.Checkbutton(
            opt_frame,
            text="Durch Wände blockiert",
            variable=self.walls_var,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        btn_frame.pack(fill=tk.X, pady=15)
        
        tk.Button(
            btn_frame,
            text="▶ Test",
            command=self._test_sound,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="■ Stop",
            command=self._stop_sound,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="Speichern",
            command=self._save,
            bg=UIColors.SUCCESS,
            fg="white",
            width=10
        ).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(
            btn_frame,
            text="Abbrechen",
            command=self.dialog.destroy,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=10
        ).pack(side=tk.RIGHT, padx=2)
    
    def _update_vol_label(self, value):
        """Lautstärke-Label aktualisieren"""
        self.vol_label.config(text=f"{int(float(value))}%")
    
    def _browse_file(self):
        """Audio-Datei auswählen"""
        filetypes = [
            ("Audio-Dateien", "*.mp3 *.wav *.ogg *.flac"),
            ("MP3", "*.mp3"),
            ("WAV", "*.wav"),
            ("OGG", "*.ogg"),
            ("Alle Dateien", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Audio-Datei wählen",
            filetypes=filetypes
        )
        
        if filepath:
            self.file_var.set(filepath)
    
    def _test_sound(self):
        """Sound testen"""
        if not AUDIO_AVAILABLE:
            return
        
        filepath = self.file_var.get()
        if filepath and os.path.exists(filepath):
            try:
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.set_volume(self.volume_var.get() / 100)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Fehler beim Testen: {e}")
    
    def _stop_sound(self):
        """Test-Sound stoppen"""
        if AUDIO_AVAILABLE:
            pygame.mixer.music.stop()
    
    def _save(self):
        """Änderungen speichern"""
        self.sound.name = self.name_var.get()
        self.sound.sound_type = SoundType(self.type_var.get())
        self.sound.file_path = self.file_var.get()
        self.sound.volume = self.volume_var.get() / 100
        self.sound.radius = self.radius_var.get()
        self.sound.max_radius = self.max_radius_var.get()
        self.sound.easing = self.easing_var.get()
        self.sound.loop = self.loop_var.get()
        self.sound.gm_only = self.gm_only_var.get()
        self.sound.walls_block = self.walls_var.get()
        
        self._stop_sound()
        self.on_save(self.sound)
        self.dialog.destroy()


class SoundToolbar(tk.Frame):
    """Toolbar für Sound-Werkzeuge"""
    
    def __init__(self, parent: tk.Widget, sound_layer: SoundLayer, sound_manager: SoundManager):
        super().__init__(parent, bg=UIColors.BG_MEDIUM)
        self.sound_layer = sound_layer
        self.sound_manager = sound_manager
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Toolbar-Buttons erstellen"""
        # Titel
        tk.Label(
            self,
            text="🔊 Ambient Sounds",
            font=("Segoe UI", 11, "bold"),
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Auswahl-Tool
        tk.Button(
            self,
            text="🔍 Auswahl",
            command=self._enable_select,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=2)
        
        # Platzieren-Tool
        tk.Button(
            self,
            text="➕ Platzieren",
            command=self._enable_place,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=2)
        
        # Löschen
        tk.Button(
            self,
            text="🗑️ Löschen",
            command=self.sound_layer.delete_selected,
            bg=UIColors.DANGER,
            fg="white"
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Alle abspielen/stoppen
        tk.Button(
            self,
            text="▶ Alle starten",
            command=self.sound_manager.play_all,
            bg=UIColors.SUCCESS,
            fg="white"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            self,
            text="■ Alle stoppen",
            command=self.sound_manager.stop_all,
            bg=UIColors.WARNING,
            fg="black"
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Master-Lautstärke
        tk.Label(
            self,
            text="Master:",
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=5)
        
        self.master_vol = tk.Scale(
            self,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            length=100,
            command=self._set_master_volume,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            troughcolor=UIColors.BG_DARK,
            highlightthickness=0
        )
        self.master_vol.set(100)
        self.master_vol.pack(side=tk.LEFT)
        
        # Anzeige-Optionen
        self.show_ranges_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self,
            text="Reichweite anzeigen",
            variable=self.show_ranges_var,
            command=self._toggle_ranges,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_DARK
        ).pack(side=tk.RIGHT, padx=10)
    
    def _enable_select(self):
        """Auswahlmodus"""
        self.sound_layer.disable_placement()
        self.sound_layer.enable_selection()
    
    def _enable_place(self):
        """Platzierungsmodus"""
        self.sound_layer.enable_placement()
    
    def _set_master_volume(self, value):
        """Master-Lautstärke setzen"""
        self.sound_manager.set_master_volume(float(value) / 100)
    
    def _toggle_ranges(self):
        """Reichweite-Anzeige umschalten"""
        self.sound_layer.show_ranges = self.show_ranges_var.get()
        self.sound_layer.redraw_all()


# Testfunktion
def test_sound_system():
    """Testet das Sound-System"""
    root = tk.Tk()
    root.title("Ambient Sound System Test")
    root.geometry("1000x700")
    root.configure(bg=UIColors.BG_DARK)
    
    # Manager erstellen
    sound_manager = SoundManager()
    
    # Canvas
    canvas = tk.Canvas(
        root,
        bg="#2a2a4a",
        highlightthickness=0
    )
    
    # Grid zeichnen
    for x in range(0, 1000, 50):
        canvas.create_line(x, 0, x, 700, fill="#3a3a5a", dash=(2, 4))
    for y in range(0, 700, 50):
        canvas.create_line(0, y, 1000, y, fill="#3a3a5a", dash=(2, 4))
    
    # Sound Layer
    sound_layer = SoundLayer(canvas, sound_manager)
    
    # Toolbar
    toolbar = SoundToolbar(root, sound_layer, sound_manager)
    toolbar.pack(fill=tk.X)
    
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Info-Label
    info_label = tk.Label(
        root,
        text=f"Audio verfügbar: {AUDIO_AVAILABLE} | Klicken um Sound zu platzieren",
        bg=UIColors.BG_DARK,
        fg=UIColors.TEXT_DIM
    )
    info_label.pack(pady=5)
    
    # Test-Sounds erstellen
    test_sound1 = sound_manager.create_sound(200, 200, name="Wasserfall", radius=100, max_radius=250)
    sound_layer._draw_sound(test_sound1)
    
    test_sound2 = sound_manager.create_sound(500, 300, name="Lagerfeuer", sound_type=SoundType.AMBIENT)
    sound_layer._draw_sound(test_sound2)
    
    root.mainloop()


if __name__ == "__main__":
    test_sound_system()
