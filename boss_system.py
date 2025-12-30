"""
Boss System für "Der Eine Ring" VTT
====================================

Verwaltet Boss-Gegner auf Hexagon-Karten:
- Boss-Definitionen (Name, Bild, HP)
- Zufällige Verteilung auf Boss-Hexagone
- Enthüllung durch Fog-of-War
- Health-Tracking mit visueller Anzeige

Autor: VTT Development Team
Version: 1.0.0
"""

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk


@dataclass
class BossDefinition:
    """Definition eines Boss-Gegners"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Unbekannter Boss"
    max_health: int = 100
    current_health: int = 100
    image_path: Optional[str] = None  # Pfad zu SVG/PNG/JPG
    description: str = ""
    
    # Visuelle Einstellungen
    name_color: str = "#ff4444"  # Rot für Boss-Namen
    health_bar_color: str = "#00ff00"  # Grün für volle HP
    health_bar_damage_color: str = "#ff0000"  # Rot für Schaden
    
    # Spezielle Eigenschaften
    abilities: List[str] = field(default_factory=list)
    loot: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "max_health": self.max_health,
            "current_health": self.current_health,
            "image_path": self.image_path,
            "description": self.description,
            "name_color": self.name_color,
            "health_bar_color": self.health_bar_color,
            "health_bar_damage_color": self.health_bar_damage_color,
            "abilities": self.abilities,
            "loot": self.loot
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BossDefinition':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Unbekannter Boss"),
            max_health=data.get("max_health", 100),
            current_health=data.get("current_health", data.get("max_health", 100)),
            image_path=data.get("image_path"),
            description=data.get("description", ""),
            name_color=data.get("name_color", "#ff4444"),
            health_bar_color=data.get("health_bar_color", "#00ff00"),
            health_bar_damage_color=data.get("health_bar_damage_color", "#ff0000"),
            abilities=data.get("abilities", []),
            loot=data.get("loot", [])
        )
    
    def take_damage(self, amount: int) -> int:
        """Boss nimmt Schaden. Gibt verbleibende HP zurück."""
        self.current_health = max(0, self.current_health - amount)
        return self.current_health
    
    def heal(self, amount: int) -> int:
        """Boss heilt. Gibt aktuelle HP zurück."""
        self.current_health = min(self.max_health, self.current_health + amount)
        return self.current_health
    
    def reset_health(self):
        """Setzt HP auf Maximum zurück."""
        self.current_health = self.max_health
    
    @property
    def health_percentage(self) -> float:
        """Gibt HP als Prozentsatz zurück (0.0 - 1.0)."""
        if self.max_health <= 0:
            return 0.0
        return self.current_health / self.max_health
    
    @property
    def is_defeated(self) -> bool:
        """Prüft ob Boss besiegt ist."""
        return self.current_health <= 0


@dataclass
class BossPlacement:
    """Platzierung eines Bosses auf der Karte"""
    boss_id: str  # Referenz zur BossDefinition
    hex_q: int    # Hexagon-Koordinate q
    hex_r: int    # Hexagon-Koordinate r
    revealed: bool = False  # Wurde vom GM enthüllt?
    
    def to_dict(self) -> Dict:
        return {
            "boss_id": self.boss_id,
            "hex_q": self.hex_q,
            "hex_r": self.hex_r,
            "revealed": self.revealed
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BossPlacement':
        return cls(
            boss_id=data.get("boss_id", ""),
            hex_q=data.get("hex_q", 0),
            hex_r=data.get("hex_r", 0),
            revealed=data.get("revealed", False)
        )


class BossManager:
    """Verwaltet alle Bosse einer Karte/Session"""
    
    def __init__(self):
        self.boss_definitions: Dict[str, BossDefinition] = {}  # id -> Boss
        self.placements: List[BossPlacement] = []  # Aktive Platzierungen
        self.boss_images: Dict[str, Image.Image] = {}  # id -> geladenes Bild
        self.boss_photo_cache: Dict[str, ImageTk.PhotoImage] = {}  # Cache für Tk
        
    def add_boss(self, boss: BossDefinition):
        """Fügt eine Boss-Definition hinzu."""
        self.boss_definitions[boss.id] = boss
        
    def remove_boss(self, boss_id: str):
        """Entfernt eine Boss-Definition."""
        if boss_id in self.boss_definitions:
            del self.boss_definitions[boss_id]
        # Entferne auch zugehörige Platzierungen
        self.placements = [p for p in self.placements if p.boss_id != boss_id]
        
    def get_boss(self, boss_id: str) -> Optional[BossDefinition]:
        """Gibt Boss-Definition zurück."""
        return self.boss_definitions.get(boss_id)
    
    def distribute_bosses_randomly(self, boss_hexagons: List[Tuple[int, int]]):
        """
        Verteilt alle definierten Bosse zufällig auf Boss-Hexagone.
        Wird aufgerufen wenn der Projektor-Modus neu geöffnet wird.
        
        Args:
            boss_hexagons: Liste von (q, r) Koordinaten die als Boss-Hexagon markiert sind
        """
        # Alle Bosse zurücksetzen
        for boss in self.boss_definitions.values():
            boss.reset_health()
        
        # Alte Platzierungen löschen
        self.placements.clear()
        
        if not boss_hexagons or not self.boss_definitions:
            if not self.boss_definitions:
                print(f"⚠️ Keine Bosse im Story Editor definiert! ({len(boss_hexagons)} Boss-Hexagone auf Karte)")
                print("   → Öffne Story Editor → 🐉 Bosse Tab → Neuer Boss hinzufügen")
            elif not boss_hexagons:
                print("⚠️ Keine Boss-Hexagone auf der Karte markiert!")
            return
        
        # Kopie der Hexagone für Shuffle
        available_hexes = boss_hexagons.copy()
        random.shuffle(available_hexes)
        
        # Bosse auf Hexagone verteilen
        boss_list = list(self.boss_definitions.values())
        
        for i, boss in enumerate(boss_list):
            if i < len(available_hexes):
                hex_q, hex_r = available_hexes[i]
                placement = BossPlacement(
                    boss_id=boss.id,
                    hex_q=hex_q,
                    hex_r=hex_r,
                    revealed=False
                )
                self.placements.append(placement)
                print(f"🎲 Boss '{boss.name}' platziert auf Hex ({hex_q}, {hex_r})")
            else:
                print(f"⚠️ Nicht genug Boss-Hexagone für Boss '{boss.name}'")
        
        print(f"✅ {len(self.placements)} Bosse verteilt auf {len(boss_hexagons)} Boss-Hexagone")
    
    def get_placement_at_hex(self, q: int, r: int) -> Optional[BossPlacement]:
        """Gibt Platzierung an einem Hexagon zurück, falls vorhanden."""
        for placement in self.placements:
            if placement.hex_q == q and placement.hex_r == r:
                return placement
        return None
    
    def reveal_boss_at_hex(self, q: int, r: int) -> Optional[BossDefinition]:
        """
        Enthüllt den Boss an einem Hexagon.
        Gibt die Boss-Definition zurück falls ein Boss dort platziert ist.
        """
        placement = self.get_placement_at_hex(q, r)
        if placement and not placement.revealed:
            placement.revealed = True
            boss = self.get_boss(placement.boss_id)
            if boss:
                print(f"👁️ Boss enthüllt: {boss.name} bei ({q}, {r})")
                return boss
        return None
    
    def damage_boss_at_hex(self, q: int, r: int, damage: int) -> Optional[Tuple[BossDefinition, int]]:
        """
        Fügt dem Boss an einem Hexagon Schaden zu.
        Gibt (Boss, verbleibende HP) zurück.
        """
        placement = self.get_placement_at_hex(q, r)
        if placement and placement.revealed:
            boss = self.get_boss(placement.boss_id)
            if boss:
                remaining_hp = boss.take_damage(damage)
                print(f"⚔️ Boss '{boss.name}' nimmt {damage} Schaden! HP: {remaining_hp}/{boss.max_health}")
                return (boss, remaining_hp)
        return None
    
    def load_boss_image(self, boss_id: str, target_size: int = 150) -> Optional[Image.Image]:
        """Lädt und cached das Boss-Bild."""
        if boss_id in self.boss_images:
            return self.boss_images[boss_id]
        
        boss = self.get_boss(boss_id)
        if not boss or not boss.image_path:
            return None
        
        try:
            if not os.path.exists(boss.image_path):
                print(f"⚠️ Boss-Bild nicht gefunden: {boss.image_path}")
                return None
            
            # SVG oder Bitmap?
            ext = os.path.splitext(boss.image_path)[1].lower()
            
            if ext == '.svg':
                # SVG mit CairoSVG rendern
                try:
                    import cairosvg
                    from io import BytesIO
                    png_data = cairosvg.svg2png(
                        url=boss.image_path,
                        output_width=target_size,
                        output_height=target_size
                    )
                    img = Image.open(BytesIO(png_data))
                except ImportError:
                    print("⚠️ CairoSVG nicht installiert, kann SVG nicht laden")
                    return None
            else:
                # PNG/JPG direkt laden
                img = Image.open(boss.image_path)
                
                # Auf Zielgröße skalieren (Aspect Ratio beibehalten)
                img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
            
            # In RGBA konvertieren falls nötig
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            self.boss_images[boss_id] = img
            print(f"✅ Boss-Bild geladen: {boss.name}")
            return img
            
        except Exception as e:
            print(f"❌ Fehler beim Laden des Boss-Bildes: {e}")
            return None
    
    def render_boss_overlay(self, boss: BossDefinition, 
                           width: int = 200, height: int = 280,
                           show_image: bool = True) -> Image.Image:
        """
        Rendert ein Boss-Overlay mit Bild, Name und Lebensleiste.
        
        Returns:
            PIL Image mit dem kompletten Boss-Overlay
        """
        # Erstelle transparentes Bild
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Hintergrund (halbtransparent dunkel)
        bg_rect = (0, 0, width, height)
        draw.rounded_rectangle(bg_rect, radius=10, fill=(20, 20, 30, 200))
        
        # Rand (Boss-Farbe)
        draw.rounded_rectangle(bg_rect, radius=10, outline=boss.name_color, width=3)
        
        y_offset = 10
        
        # Boss-Bild zeichnen (falls vorhanden und gewünscht)
        if show_image and boss.image_path:
            boss_img = self.load_boss_image(boss.id, target_size=min(width - 20, 150))
            if boss_img:
                # Zentrieren
                img_x = (width - boss_img.width) // 2
                overlay.paste(boss_img, (img_x, y_offset), boss_img)
                y_offset += boss_img.height + 10
        
        # Name zeichnen
        try:
            # Versuche eine bessere Schrift
            font_name = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            font_name = ImageFont.load_default()
            font_small = font_name
        
        # Name zentriert
        name_bbox = draw.textbbox((0, 0), boss.name, font=font_name)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = (width - name_width) // 2
        draw.text((name_x, y_offset), boss.name, fill=boss.name_color, font=font_name)
        y_offset += 25
        
        # HP-Text
        hp_text = f"{boss.current_health} / {boss.max_health} HP"
        hp_bbox = draw.textbbox((0, 0), hp_text, font=font_small)
        hp_width = hp_bbox[2] - hp_bbox[0]
        hp_x = (width - hp_width) // 2
        draw.text((hp_x, y_offset), hp_text, fill="#ffffff", font=font_small)
        y_offset += 20
        
        # Lebensleiste
        bar_margin = 15
        bar_height = 20
        bar_x1 = bar_margin
        bar_x2 = width - bar_margin
        bar_width = bar_x2 - bar_x1
        
        # Hintergrund der Leiste (dunkelgrau)
        draw.rounded_rectangle(
            (bar_x1, y_offset, bar_x2, y_offset + bar_height),
            radius=5, fill=(40, 40, 40, 255)
        )
        
        # HP-Anteil
        hp_percent = boss.health_percentage
        hp_bar_width = int(bar_width * hp_percent)
        
        if hp_bar_width > 0:
            # Farbe basierend auf HP-Prozent (Grün -> Gelb -> Orange -> Rot)
            if hp_percent > 0.6:
                bar_color = (0, 200, 0, 255)  # Grün
            elif hp_percent > 0.3:
                bar_color = (255, 165, 0, 255)  # Orange
            else:
                bar_color = (255, 50, 50, 255)  # Rot
            
            draw.rounded_rectangle(
                (bar_x1, y_offset, bar_x1 + hp_bar_width, y_offset + bar_height),
                radius=5, fill=bar_color
            )
        
        # Rand der Leiste
        draw.rounded_rectangle(
            (bar_x1, y_offset, bar_x2, y_offset + bar_height),
            radius=5, outline=(100, 100, 100, 255), width=2
        )
        
        return overlay
    
    def to_dict(self) -> Dict:
        """Exportiert den BossManager als Dictionary."""
        return {
            "boss_definitions": [b.to_dict() for b in self.boss_definitions.values()],
            "placements": [p.to_dict() for p in self.placements]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BossManager':
        """Erstellt einen BossManager aus Dictionary-Daten."""
        manager = cls()
        
        for boss_data in data.get("boss_definitions", []):
            boss = BossDefinition.from_dict(boss_data)
            manager.boss_definitions[boss.id] = boss
        
        for placement_data in data.get("placements", []):
            placement = BossPlacement.from_dict(placement_data)
            manager.placements.append(placement)
        
        return manager
    
    def save(self, filepath: str):
        """Speichert den BossManager als JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"💾 Boss-Daten gespeichert: {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'BossManager':
        """Lädt einen BossManager aus einer JSON-Datei."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class BossEditorDialog(tk.Toplevel):
    """Dialog zum Bearbeiten einer Boss-Definition"""
    
    def __init__(self, parent, boss: Optional[BossDefinition] = None):
        super().__init__(parent)
        self.result: Optional[BossDefinition] = None
        self.boss = boss or BossDefinition()
        self.image_preview = None
        
        self.title("🐉 Boss bearbeiten" if boss else "🐉 Neuer Boss")
        self.configure(bg="#1a1a2e")
        self.geometry("450x650")
        self.minsize(450, 650)
        self.resizable(True, True)
        
        self._center_on_parent(parent)
        self._create_widgets()
        
        self.transient(parent)
        self.grab_set()
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        # === BUTTONS am unteren Rand (zuerst packen für Priorität) ===
        btn_frame = tk.Frame(self, bg="#16213e", padx=15, pady=15)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Button(btn_frame, text="✓ Speichern", command=self._save,
                 bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                 width=15, height=2).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self.destroy,
                 bg="#dc3545", fg="white", font=("Arial", 12, "bold"),
                 width=15, height=2).pack(side=tk.RIGHT, padx=10)
        
        # Scrollbarer Hauptbereich
        main = tk.Frame(self, bg="#1a1a2e", padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # === NAME ===
        tk.Label(main, text="🐉 BOSS-NAME", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(0, 5))
        
        name_frame = tk.Frame(main, bg="#16213e", padx=10, pady=10)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.name_var = tk.StringVar(value=self.boss.name)
        tk.Entry(name_frame, textvariable=self.name_var, width=40,
                font=("Arial", 12), bg="#0f3460", fg="white",
                insertbackground="white").pack(fill=tk.X)
        
        # === HEALTH ===
        tk.Label(main, text="❤️ LEBENSPUNKTE", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(10, 5))
        
        health_frame = tk.Frame(main, bg="#16213e", padx=10, pady=10)
        health_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(health_frame, text="Max HP:", bg="#16213e", fg="white").grid(row=0, column=0, sticky=tk.W)
        self.health_var = tk.IntVar(value=self.boss.max_health)
        tk.Spinbox(health_frame, from_=1, to=10000, textvariable=self.health_var,
                  width=10, bg="#0f3460", fg="white").grid(row=0, column=1, padx=10)
        
        # === BILD ===
        tk.Label(main, text="🖼️ BOSS-BILD (optional)", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(10, 5))
        
        image_frame = tk.Frame(main, bg="#16213e", padx=10, pady=10)
        image_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.image_path_var = tk.StringVar(value=self.boss.image_path or "")
        path_entry = tk.Entry(image_frame, textvariable=self.image_path_var, width=30,
                             bg="#0f3460", fg="white", insertbackground="white")
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(image_frame, text="📂", command=self._browse_image,
                 bg="#0f3460", fg="white", width=3).pack(side=tk.LEFT, padx=5)
        
        # Bild-Vorschau
        self.preview_label = tk.Label(main, bg="#1a1a2e", width=150, height=150)
        self.preview_label.pack(pady=10)
        self._update_preview()
        
        # === BESCHREIBUNG ===
        tk.Label(main, text="📝 BESCHREIBUNG", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(10, 5))
        
        self.desc_text = tk.Text(main, height=4, bg="#0f3460", fg="white",
                                insertbackground="white", wrap=tk.WORD)
        self.desc_text.pack(fill=tk.X, pady=(0, 10))
        self.desc_text.insert("1.0", self.boss.description)
    
    def _browse_image(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Boss-Bild auswählen",
            filetypes=[
                ("Bilder", "*.png;*.jpg;*.jpeg;*.svg"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("SVG", "*.svg"),
                ("Alle", "*.*")
            ]
        )
        if path:
            self.image_path_var.set(path)
            self._update_preview()
    
    def _update_preview(self):
        """Aktualisiert die Bildvorschau."""
        path = self.image_path_var.get()
        if path and os.path.exists(path):
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext == '.svg':
                    try:
                        import cairosvg
                        from io import BytesIO
                        png_data = cairosvg.svg2png(url=path, output_width=100, output_height=100)
                        img = Image.open(BytesIO(png_data))
                    except:
                        return
                else:
                    img = Image.open(path)
                    img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                
                self.image_preview = ImageTk.PhotoImage(img)
                self.preview_label.config(image=self.image_preview)
            except Exception as e:
                print(f"Vorschau-Fehler: {e}")
    
    def _save(self):
        """Speichert den Boss und schließt den Dialog."""
        name = self.name_var.get().strip()
        if not name:
            from tkinter import messagebox
            messagebox.showwarning("Name erforderlich", "Bitte gib einen Namen für den Boss ein.")
            return
        
        self.boss.name = name
        self.boss.max_health = self.health_var.get()
        self.boss.current_health = self.boss.max_health
        self.boss.image_path = self.image_path_var.get() or None
        self.boss.description = self.desc_text.get("1.0", tk.END).strip()
        
        self.result = self.boss
        print(f"🐉 Boss gespeichert: {self.boss.name} (HP: {self.boss.max_health})")
        self.destroy()


class BossControlPanel(tk.Frame):
    """Panel zur Kontrolle aktiver Bosse (für GM)"""
    
    def __init__(self, parent, boss_manager: BossManager, 
                 on_damage_callback=None, on_reveal_callback=None):
        super().__init__(parent, bg="#1a1a2e")
        self.boss_manager = boss_manager
        self.on_damage_callback = on_damage_callback
        self.on_reveal_callback = on_reveal_callback
        
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        # Header
        header = tk.Frame(self, bg="#16213e")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header, text="🐉 AKTIVE BOSSE", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(side=tk.LEFT, padx=10, pady=5)
        
        tk.Button(header, text="🔄", command=self.refresh,
                 bg="#0f3460", fg="white", width=3).pack(side=tk.RIGHT, padx=5)
        
        # Boss-Liste
        self.boss_frame = tk.Frame(self, bg="#1a1a2e")
        self.boss_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        self.canvas = tk.Canvas(self.boss_frame, bg="#1a1a2e", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.boss_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1a1a2e")
        
        self.scrollable_frame.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def refresh(self):
        """Aktualisiert die Boss-Liste."""
        # Alte Widgets entfernen
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Für jeden platzierten Boss ein Panel erstellen
        for placement in self.boss_manager.placements:
            boss = self.boss_manager.get_boss(placement.boss_id)
            if boss:
                self._create_boss_panel(boss, placement)
    
    def _create_boss_panel(self, boss: BossDefinition, placement: BossPlacement):
        """Erstellt ein Panel für einen einzelnen Boss."""
        frame = tk.Frame(self.scrollable_frame, bg="#16213e", relief=tk.RAISED, bd=2)
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Header mit Name und Status
        header = tk.Frame(frame, bg="#16213e")
        header.pack(fill=tk.X, padx=10, pady=5)
        
        status_icon = "👁️" if placement.revealed else "❓"
        status_color = "#00ff00" if placement.revealed else "#888888"
        
        tk.Label(header, text=f"{status_icon} {boss.name}", 
                font=("Arial", 11, "bold"),
                bg="#16213e", fg=status_color).pack(side=tk.LEFT)
        
        tk.Label(header, text=f"({placement.hex_q}, {placement.hex_r})",
                font=("Arial", 9), bg="#16213e", fg="#666666").pack(side=tk.RIGHT)
        
        if placement.revealed:
            # HP-Anzeige
            hp_frame = tk.Frame(frame, bg="#16213e")
            hp_frame.pack(fill=tk.X, padx=10, pady=2)
            
            hp_percent = boss.health_percentage
            hp_color = "#00ff00" if hp_percent > 0.6 else ("#ffaa00" if hp_percent > 0.3 else "#ff4444")
            
            tk.Label(hp_frame, text=f"❤️ {boss.current_health}/{boss.max_health}",
                    font=("Arial", 10), bg="#16213e", fg=hp_color).pack(side=tk.LEFT)
            
            # Damage-Input
            dmg_frame = tk.Frame(frame, bg="#16213e")
            dmg_frame.pack(fill=tk.X, padx=10, pady=5)
            
            dmg_var = tk.IntVar(value=10)
            tk.Spinbox(dmg_frame, from_=1, to=1000, textvariable=dmg_var,
                      width=6, bg="#0f3460", fg="white").pack(side=tk.LEFT)
            
            tk.Button(dmg_frame, text="⚔️ Schaden", 
                     command=lambda: self._apply_damage(boss, placement, dmg_var.get()),
                     bg="#dc3545", fg="white").pack(side=tk.LEFT, padx=5)
            
            tk.Button(dmg_frame, text="💚 Heilen",
                     command=lambda: self._apply_heal(boss, placement, dmg_var.get()),
                     bg="#28a745", fg="white").pack(side=tk.LEFT, padx=2)
        else:
            # Reveal-Button
            tk.Button(frame, text="👁️ Enthüllen",
                     command=lambda: self._reveal_boss(placement),
                     bg="#0f3460", fg="white").pack(padx=10, pady=5)
    
    def _apply_damage(self, boss: BossDefinition, placement: BossPlacement, damage: int):
        """Wendet Schaden an und aktualisiert die Anzeige."""
        boss.take_damage(damage)
        self.refresh()
        if self.on_damage_callback:
            self.on_damage_callback(boss, placement)
    
    def _apply_heal(self, boss: BossDefinition, placement: BossPlacement, amount: int):
        """Heilt den Boss und aktualisiert die Anzeige."""
        boss.heal(amount)
        self.refresh()
        if self.on_damage_callback:
            self.on_damage_callback(boss, placement)
    
    def _reveal_boss(self, placement: BossPlacement):
        """Enthüllt einen Boss."""
        boss = self.boss_manager.reveal_boss_at_hex(placement.hex_q, placement.hex_r)
        self.refresh()
        if boss and self.on_reveal_callback:
            self.on_reveal_callback(boss, placement)


# Test
if __name__ == "__main__":
    # Test Boss-System
    manager = BossManager()
    
    # Bosse erstellen
    boss1 = BossDefinition(name="Saurons Schatten", max_health=500)
    boss2 = BossDefinition(name="Balrog von Moria", max_health=800, description="Ein uralter Dämon")
    boss3 = BossDefinition(name="Nazgûl-König", max_health=300)
    
    manager.add_boss(boss1)
    manager.add_boss(boss2)
    manager.add_boss(boss3)
    
    # Boss-Hexagone (normalerweise aus der Map)
    boss_hexes = [(0, 0), (5, 3), (10, 7), (2, 8)]
    
    # Verteilen
    manager.distribute_bosses_randomly(boss_hexes)
    
    # Test: Reveal und Damage
    revealed = manager.reveal_boss_at_hex(manager.placements[0].hex_q, manager.placements[0].hex_r)
    if revealed:
        print(f"Revealed: {revealed.name}")
        manager.damage_boss_at_hex(manager.placements[0].hex_q, manager.placements[0].hex_r, 100)
    
    # Speichern/Laden Test
    manager.save("test_bosses.json")
    loaded = BossManager.load("test_bosses.json")
    print(f"Geladen: {len(loaded.boss_definitions)} Bosse, {len(loaded.placements)} Platzierungen")
