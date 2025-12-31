"""
Story Editor - Vollständige Integration
========================================

Hauptmodul das alle Story-Editor Komponenten zusammenführt.

Autor: VTT Development Team
Version: 1.0.0

Komponenten:
- story_editor_base.py: Basis-UI (Fenster, Menü, Toolbar)
- story_editor_scenes.py: Szenen-Verwaltung mit Drag & Drop
- story_editor_graph.py: Visueller Flow-Graph
- story_editor_properties.py: Trigger/Action/Overlay Editor
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable
import os

# Storyboard-System
from storyboard_system import (
    Storyboard, Chapter, Scene, Trigger, Action, Overlay,
    SceneType, TriggerType, ActionType, StoryboardEngine
)

# Editor-Komponenten
from story_editor_scenes import ScenesPanel, SceneTypeSelector, ChapterDialog
from story_editor_graph import FlowGraphPanel
from story_editor_properties import PropertiesPanel
from story_editor_bosses import BossPanel
from story_editor_players import PlayerPanel
from boss_system import BossManager
from player_system import PlayerManager


class StoryEditor(tk.Toplevel):
    """
    Vollständiger Story-Editor für das VTT
    
    Kombiniert:
    - Kapitel/Szenen-Verwaltung (links)
    - Flow-Graph Visualisierung (mitte)
    - Properties-Editor (rechts)
    """
    
    def __init__(self, parent, storyboard: Optional[Storyboard] = None,
                 on_scene_preview: Optional[Callable[[Scene], None]] = None):
        super().__init__(parent)
        
        self.title("🎬 Story Editor - Der Eine Ring VTT")
        self.configure(bg="#1a1a2e")
        
        # Fenstergröße berechnen (passt auf Bildschirm)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        # Maximalgröße: 90% des Bildschirms, aber nicht mehr als gewünscht
        w = min(1400, int(screen_w * 0.9))
        h = min(900, int(screen_h * 0.85))  # 85% für Taskleiste
        
        # Zentrieren mit Sicherheitsabstand
        x = max(50, (screen_w - w) // 2)
        y = max(30, (screen_h - h) // 2)
        
        # Sicherstellen, dass Fenster nicht abgeschnitten wird
        if y + h > screen_h - 60:  # Taskleiste berücksichtigen
            y = max(30, screen_h - h - 60)
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(900, 600)  # Reduzierte Mindestgröße
        
        # Storyboard
        self.storyboard = storyboard or Storyboard(name="Neues Abenteuer")
        self.current_chapter: Optional[Chapter] = None
        self.current_scene: Optional[Scene] = None
        
        # State
        self.has_unsaved_changes = False
        self._current_file_path: Optional[str] = None
        
        # Callbacks
        self.on_scene_preview = on_scene_preview
        
        # UI aufbauen
        self._setup_menu()
        self._setup_toolbar()
        self._setup_main_layout()
        self._setup_statusbar()
        self._setup_shortcuts()
        
        # Initial
        self._update_title()
        
        # Close Handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_menu(self):
        """Erstellt das Hauptmenü"""
        self.menubar = tk.Menu(self, bg="#2a2a4e", fg="white")
        self.config(menu=self.menubar)
        
        # Datei
        file_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="📁 Datei", menu=file_menu)
        
        file_menu.add_command(label="Neu", command=self._new_storyboard, accelerator="Ctrl+N")
        file_menu.add_command(label="Öffnen...", command=self._open_storyboard, accelerator="Ctrl+O")
        file_menu.add_command(label="Speichern", command=self._save_storyboard, accelerator="Ctrl+S")
        file_menu.add_command(label="Speichern unter...", command=self._save_storyboard_as)
        file_menu.add_separator()
        file_menu.add_command(label="Als JSON exportieren...", command=self._export_json)
        file_menu.add_separator()
        file_menu.add_command(label="Schließen", command=self._on_close)
        
        # Bearbeiten
        edit_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="✏️ Bearbeiten", menu=edit_menu)
        
        edit_menu.add_command(label="Kapitel hinzufügen", command=self._add_chapter)
        edit_menu.add_command(label="Szene hinzufügen", command=self._add_scene)
        edit_menu.add_separator()
        edit_menu.add_command(label="Ausgewähltes löschen", command=self._delete_selected, accelerator="Del")
        
        # Ansicht
        view_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="👁️ Ansicht", menu=view_menu)
        
        self.show_graph = tk.BooleanVar(value=True)
        self.show_props = tk.BooleanVar(value=True)
        
        view_menu.add_checkbutton(label="Flow-Graph", variable=self.show_graph,
                                  command=self._toggle_panels)
        view_menu.add_checkbutton(label="Eigenschaften", variable=self.show_props,
                                  command=self._toggle_panels)
        view_menu.add_separator()
        view_menu.add_command(label="Flow-Graph: Auto-Layout", command=self._auto_layout_graph)
        view_menu.add_command(label="Flow-Graph: Zentrieren", command=self._center_graph)
        
        # Hilfe
        help_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="❓ Hilfe", menu=help_menu)
        
        help_menu.add_command(label="Tastenkürzel", command=self._show_shortcuts)
        help_menu.add_command(label="Über Story Editor", command=self._show_about)
    
    def _setup_toolbar(self):
        """Erstellt die Toolbar"""
        self.toolbar = tk.Frame(self, bg="#16213e", height=50)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.toolbar.pack_propagate(False)
        
        # Links: Datei
        left = tk.Frame(self.toolbar, bg="#16213e")
        left.pack(side=tk.LEFT, padx=10, pady=5)
        
        self._toolbar_btn(left, "📄", "Neu", self._new_storyboard)
        self._toolbar_btn(left, "📂", "Öffnen", self._open_storyboard)
        self._toolbar_btn(left, "💾", "Speichern", self._save_storyboard)
        
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Mitte: Kapitel/Szenen
        mid = tk.Frame(self.toolbar, bg="#16213e")
        mid.pack(side=tk.LEFT, padx=10, pady=5)
        
        self._toolbar_btn(mid, "📖", "Kapitel hinzufügen", self._add_chapter)
        self._toolbar_btn(mid, "🎬", "Szene hinzufügen", self._add_scene)
        
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Rechts: Vorschau
        right = tk.Frame(self.toolbar, bg="#16213e")
        right.pack(side=tk.LEFT, padx=10, pady=5)
        
        self._toolbar_btn(right, "▶️", "Vorschau", self._preview_scene)
        self._toolbar_btn(right, "🎮", "Test-Modus", self._test_mode)
        self._toolbar_btn(right, "🔲", "Split-View", self._start_split_view)
        
        # Ganz rechts: Storyboard-Name
        info = tk.Frame(self.toolbar, bg="#16213e")
        info.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.name_label = tk.Label(
            info,
            text=f"📚 {self.storyboard.name}",
            bg="#16213e", fg="#e94560",
            font=("Arial", 12, "bold")
        )
        self.name_label.pack(side=tk.RIGHT)
    
    def _toolbar_btn(self, parent, icon: str, tooltip: str, cmd: Callable):
        """Erstellt einen Toolbar-Button"""
        btn = tk.Button(
            parent, text=icon,
            font=("Arial", 16),
            bg="#0f3460", fg="white",
            activebackground="#e94560",
            relief=tk.FLAT, width=3,
            command=cmd
        )
        btn.pack(side=tk.LEFT, padx=2)
        
        # Tooltip
        btn.bind("<Enter>", lambda e, t=tooltip: self._show_tooltip(e, t))
        btn.bind("<Leave>", lambda e: self._hide_tooltip())
    
    def _setup_main_layout(self):
        """Erstellt das Haupt-Layout"""
        self.main_paned = tk.PanedWindow(
            self, orient=tk.HORIZONTAL,
            bg="#1a1a2e", sashwidth=5, sashrelief=tk.RAISED
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Links: Szenen-Panel mit Tabs (Szenen + Bosse)
        self.left_frame = tk.Frame(self.main_paned, bg="#16213e", width=280)
        self.main_paned.add(self.left_frame, minsize=200)
        
        # Tab-Container für Szenen und Bosse
        self.left_notebook = ttk.Notebook(self.left_frame)
        self.left_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Szenen-Panel
        scenes_tab = tk.Frame(self.left_notebook, bg="#16213e")
        self.left_notebook.add(scenes_tab, text="📖 Szenen")
        self.scenes_panel = ScenesPanel(scenes_tab, self)
        
        # Tab 2: Boss-Panel
        boss_tab = tk.Frame(self.left_notebook, bg="#16213e")
        self.left_notebook.add(boss_tab, text="🐉 Bosse")
        self.boss_panel = BossPanel(boss_tab, on_change=self._mark_changed)
        self.boss_panel.pack(fill=tk.BOTH, expand=True)
        
        # Tab 3: Player-Panel (Spieler & Teams)
        player_tab = tk.Frame(self.left_notebook, bg="#16213e")
        self.left_notebook.add(player_tab, text="🎮 Spieler")
        self.player_panel = PlayerPanel(player_tab, on_change=self._mark_changed)
        self.player_panel.pack(fill=tk.BOTH, expand=True)
        
        # Mitte: Flow-Graph
        self.center_frame = tk.Frame(self.main_paned, bg="#0f3460")
        self.main_paned.add(self.center_frame, minsize=400)
        
        self.flow_panel = FlowGraphPanel(self.center_frame, self)
        
        # Rechts: Properties
        self.right_frame = tk.Frame(self.main_paned, bg="#16213e", width=320)
        self.main_paned.add(self.right_frame, minsize=250)
        
        self.props_panel = PropertiesPanel(self.right_frame, self)
    
    def _setup_statusbar(self):
        """Erstellt die Statusleiste"""
        self.statusbar = tk.Frame(self, bg="#0f3460", height=25)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar.pack_propagate(False)
        
        self.status_label = tk.Label(
            self.statusbar, text="Bereit",
            bg="#0f3460", fg="#aaa",
            font=("Arial", 9), anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.stats_label = tk.Label(
            self.statusbar, text="0 Kapitel | 0 Szenen",
            bg="#0f3460", fg="#888",
            font=("Arial", 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)
    
    def _setup_shortcuts(self):
        """Keyboard Shortcuts"""
        self.bind("<Control-n>", lambda e: self._new_storyboard())
        self.bind("<Control-o>", lambda e: self._open_storyboard())
        self.bind("<Control-s>", lambda e: self._save_storyboard())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<F5>", lambda e: self._preview_scene())
    
    # ============================================================
    # DATEI-OPERATIONEN
    # ============================================================
    
    def _new_storyboard(self):
        """Neues Storyboard"""
        if self.has_unsaved_changes:
            if not messagebox.askyesno("Änderungen verwerfen?",
                                       "Ungespeicherte Änderungen gehen verloren."):
                return
        
        self.storyboard = Storyboard(name="Neues Abenteuer")
        self.current_chapter = None
        self.current_scene = None
        self._current_file_path = None
        self.has_unsaved_changes = False
        
        # Boss-Panel zurücksetzen
        self.boss_panel.set_boss_manager(BossManager())
        
        # Player-Panel zurücksetzen
        self.player_panel.set_player_manager(PlayerManager())
        
        self._refresh_all()
        self._set_status("Neues Storyboard erstellt")
    
    def _open_storyboard(self):
        """Storyboard öffnen"""
        if self.has_unsaved_changes:
            if not messagebox.askyesno("Änderungen verwerfen?",
                                       "Ungespeicherte Änderungen gehen verloren."):
                return
        
        path = filedialog.askopenfilename(
            title="Storyboard öffnen",
            filetypes=[("Storyboard", "*.story.json"), ("JSON", "*.json"), ("Alle", "*.*")]
        )
        
        if path:
            try:
                self.storyboard = Storyboard.load(path)
                self._current_file_path = path
                self.has_unsaved_changes = False
                
                # Boss-Daten laden falls vorhanden
                if self.storyboard.boss_data:
                    self.boss_panel.from_dict(self.storyboard.boss_data)
                else:
                    self.boss_panel.set_boss_manager(BossManager())
                
                # Player-Daten laden falls vorhanden
                if hasattr(self.storyboard, 'player_data') and self.storyboard.player_data:
                    self.player_panel.from_dict(self.storyboard.player_data)
                else:
                    self.player_panel.set_player_manager(PlayerManager())
                
                self._refresh_all()
                self._set_status(f"Geladen: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Laden fehlgeschlagen:\n{e}")
    
    def _save_storyboard(self):
        """Storyboard speichern"""
        if self._current_file_path:
            try:
                # Boss-Daten synchronisieren
                self.storyboard.boss_data = self.boss_panel.to_dict()
                # Player-Daten synchronisieren
                self.storyboard.player_data = self.player_panel.to_dict()
                self.storyboard.save(self._current_file_path)
                self.has_unsaved_changes = False
                self._update_title()
                self._set_status(f"Gespeichert: {os.path.basename(self._current_file_path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
        else:
            self._save_storyboard_as()
    
    def _save_storyboard_as(self):
        """Storyboard speichern unter"""
        path = filedialog.asksaveasfilename(
            title="Storyboard speichern",
            filetypes=[("Storyboard", "*.story.json"), ("JSON", "*.json")],
            defaultextension=".story.json",
            initialfile=f"{self.storyboard.name}.story.json"
        )
        
        if path:
            try:
                # Boss-Daten synchronisieren
                self.storyboard.boss_data = self.boss_panel.to_dict()
                self.storyboard.save(path)
                self._current_file_path = path
                self.has_unsaved_changes = False
                self._update_title()
                self._set_status(f"Gespeichert: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
    
    def _export_json(self):
        """Als JSON exportieren"""
        path = filedialog.asksaveasfilename(
            title="Als JSON exportieren",
            filetypes=[("JSON", "*.json")],
            defaultextension=".json",
            initialfile=f"{self.storyboard.name}_export.json"
        )
        
        if path:
            import json
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.storyboard.to_dict(), f, indent=2, ensure_ascii=False)
                self._set_status(f"Exportiert: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
    
    # ============================================================
    # BEARBEITEN
    # ============================================================
    
    def _add_chapter(self):
        """Kapitel hinzufügen"""
        dialog = ChapterDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            chapter = Chapter(
                name=dialog.result["name"],
                icon=dialog.result["icon"],
                description=dialog.result["description"],
                locked=dialog.result["locked"],
                order=len(self.storyboard.chapters)
            )
            self.storyboard.chapters.append(chapter)
            
            self._mark_changed()
            self._refresh_all()
            self._set_status(f"Kapitel '{chapter.name}' hinzugefügt")
    
    def _add_scene(self):
        """Szene hinzufügen"""
        if not self.current_chapter:
            messagebox.showwarning("Kein Kapitel", "Bitte zuerst ein Kapitel auswählen.")
            return
        
        dialog = SceneTypeSelector(self)
        self.wait_window(dialog)
        
        if dialog.selected_type and dialog.result_name:
            scene = Scene(
                name=dialog.result_name,
                scene_type=dialog.selected_type
            )
            self.current_chapter.scenes.append(scene)
            
            if len(self.current_chapter.scenes) == 1:
                self.current_chapter.start_scene_id = scene.id
            
            self._mark_changed()
            self._refresh_all()
            self._set_status(f"Szene '{scene.name}' hinzugefügt")
    
    def _delete_selected(self):
        """Ausgewähltes löschen"""
        if hasattr(self.scenes_panel, '_delete_selected'):
            self.scenes_panel._delete_selected()
    
    # ============================================================
    # VORSCHAU & TEST
    # ============================================================
    
    def _preview_scene(self):
        """Aktuelle Szene anzeigen"""
        if not self.current_scene:
            messagebox.showinfo("Keine Szene", "Bitte eine Szene auswählen.")
            return
        
        if self.on_scene_preview:
            self.on_scene_preview(self.current_scene)
            self._set_status(f"Vorschau: {self.current_scene.name}")
        else:
            self._set_status("Vorschau nicht verfügbar (kein Callback)")
    
    def _test_mode(self):
        """Test-Modus starten"""
        if not self.storyboard.chapters:
            messagebox.showwarning("Leer", "Keine Kapitel vorhanden!")
            return
        
        # Hier könnte man einen Test-Modus starten
        self._set_status("Test-Modus: Noch nicht implementiert")
    
    def _start_split_view(self):
        """Split-View Projektor mit Story-Daten starten"""
        try:
            from split_view_projector import SplitViewProjector
            from player_system import PlayerManager
            from boss_system import BossManager
            
            # Player-Manager aus Player-Panel holen
            player_manager = None
            boss_manager = None
            
            if hasattr(self, 'player_panel') and self.player_panel:
                player_manager = self.player_panel.get_player_manager()
            
            if hasattr(self, 'boss_panel') and self.boss_panel:
                boss_manager = self.boss_panel.get_boss_manager()
            
            # Fallback
            if not player_manager:
                player_manager = PlayerManager()
            if not boss_manager:
                boss_manager = BossManager()
            
            # Aktuelle Szene für Map-Daten
            map_data = None
            svg_path = None
            
            if self.current_scene:
                print(f"🎬 Aktuelle Szene: {self.current_scene.name}")
                
                # Szene hat content_path (Pfad zur Map/SVG)
                content_path = getattr(self.current_scene, 'content_path', None) or \
                               getattr(self.current_scene, 'map_path', None) or \
                               getattr(self.current_scene, 'background_source', None)
                
                if content_path:
                    print(f"📁 Content-Pfad: {content_path}")
                    
                    # SVG-Pfad merken
                    if content_path.endswith('.svg'):
                        svg_path = content_path
                    
                    # JSON-Map laden
                    if content_path.endswith('.json'):
                        try:
                            import json
                            with open(content_path, 'r', encoding='utf-8') as f:
                                map_data = json.load(f)
                            print(f"✅ Map-Daten aus JSON geladen: {content_path}")
                        except Exception as e:
                            print(f"⚠️ Konnte JSON-Map nicht laden: {e}")
                
                # Embedded map_data aus Szene
                if not map_data and hasattr(self.current_scene, 'map_data') and self.current_scene.map_data:
                    map_data = self.current_scene.map_data
                    print(f"✅ Embedded Map-Daten aus Szene")
            
            # Versuche Map-Daten aus Parent zu holen
            if not map_data and hasattr(self.master, 'current_map_data') and self.master.current_map_data:
                map_data = self.master.current_map_data
                print("✅ Map-Daten aus Hauptfenster geladen")
            
            # Fallback: Beispiel-Hexagon-Karte erstellen
            if not map_data or not map_data.get("tiles"):
                print("⚠️ Keine Map-Daten - erstelle Beispiel-Hexagon-Karte")
                map_data = self._create_example_hex_map()
            
            # Split-View Projektor öffnen
            projector = SplitViewProjector(
                self,
                map_data=map_data,
                player_manager=player_manager,
                boss_manager=boss_manager,
                num_screens=2,
                svg_path=svg_path
            )
            
            # WICHTIG: Projektor registrieren für GM-Panel
            self.split_view_projector = projector
            
            # Parent-Fenster informieren (enhanced_main.py)
            if hasattr(self.master, 'projector_window'):
                self.master.projector_window = projector
            
            # GM-Panel updaten falls bereits offen
            if hasattr(self.master, 'gm_panel') and self.master.gm_panel:
                try:
                    if self.master.gm_panel.winfo_exists():
                        self.master.gm_panel.projector_window = projector
                        self.master.gm_panel.standalone_map_data = map_data
                        self.master.gm_panel.update_fog_map()
                        print("✅ GM-Panel mit Split-View Projektor verbunden")
                except:
                    pass
            
            # Spieler verteilen
            projector.distribute_players()
            
            self._set_status("Split-View Projektor geöffnet")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Split-View konnte nicht gestartet werden:\n{e}")
    
    def _create_example_hex_map(self):
        """Erstellt eine Beispiel-Hexagon-Karte für Tests"""
        import math
        
        hex_size = 40
        grid_size = 15  # 15x15 Hexagone
        
        tiles = {}
        terrain_types = ["PLAINS", "FOREST", "WATER", "MOUNTAINS", "HILLS"]
        terrain_colors = {
            "PLAINS": "#6ba868",
            "FOREST": "#3d6b3d", 
            "WATER": "#4db8c4",
            "MOUNTAINS": "#8a8a8a",
            "HILLS": "#9a9a6a"
        }
        
        for q in range(grid_size):
            for r in range(grid_size):
                # Terrain basierend auf Position
                if (q + r) % 7 == 0:
                    terrain = "WATER"
                elif (q * r) % 5 == 0:
                    terrain = "FOREST"
                elif q > grid_size - 3 and r > grid_size - 3:
                    terrain = "MOUNTAINS"
                else:
                    terrain = "PLAINS"
                
                # Pointy-Top Hexagon-Koordinaten
                center_x = hex_size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
                center_y = hex_size * (3 / 2 * r)
                
                tile_data = {
                    "q": q, "r": r,
                    "terrain": terrain,
                    "fill_color": terrain_colors.get(terrain, "#6ba868"),
                    "center_x": center_x,
                    "center_y": center_y,
                    "is_spawn_hex": (q == 2 and r == 2) or (q == 12 and r == 12),
                    "is_boss_hex": (q == 7 and r == 7)
                }
                
                tiles[f"{q},{r}"] = tile_data
        
        return {
            "name": "Beispiel-Hexagon-Karte",
            "width": grid_size,
            "height": grid_size,
            "hex_size": hex_size,
            "orientation": "pointy",
            "tiles": tiles
        }
    
    # ============================================================
    # ANSICHT
    # ============================================================
    
    def _toggle_panels(self):
        """Panels ein/ausblenden"""
        # Alle Panels entfernen
        try:
            self.main_paned.forget(self.center_frame)
        except:
            pass
        try:
            self.main_paned.forget(self.right_frame)
        except:
            pass
        
        # Panels nach Einstellung wieder hinzufügen
        if self.show_graph.get():
            self.main_paned.add(self.center_frame, after=self.left_frame)
        
        if self.show_props.get():
            self.main_paned.add(self.right_frame)
    
    def _auto_layout_graph(self):
        """Flow-Graph: Auto-Layout"""
        if hasattr(self.flow_panel, 'graph'):
            self.flow_panel.graph._auto_layout()
    
    def _center_graph(self):
        """Flow-Graph zentrieren"""
        if hasattr(self.flow_panel, 'graph'):
            self.flow_panel.graph._center_view()
    
    # ============================================================
    # HELPER
    # ============================================================
    
    def _refresh_all(self):
        """Alle Panels aktualisieren"""
        self.scenes_panel.storyboard = self.storyboard
        self.scenes_panel.refresh()
        
        if self.current_chapter:
            self.flow_panel.set_scenes(self.current_chapter.scenes)
        else:
            self.flow_panel.refresh()
        
        self.props_panel.refresh()
        self._update_title()
    
    def _refresh_chapter_list(self):
        """Alias für scenes_panel.refresh"""
        self.scenes_panel.refresh()
    
    def _refresh_properties(self):
        """Properties aktualisieren"""
        self.props_panel.refresh()
    
    def _update_flow_graph(self):
        """Flow-Graph aktualisieren"""
        if self.current_chapter:
            self.flow_panel.set_scenes(self.current_chapter.scenes)
    
    def _mark_changed(self):
        """Änderungen markieren"""
        self.has_unsaved_changes = True
        self._update_title()
    
    def _update_title(self):
        """Titel aktualisieren"""
        title = f"🎬 Story Editor - {self.storyboard.name}"
        if self.has_unsaved_changes:
            title += " *"
        self.title(title)
        self.name_label.config(text=f"📚 {self.storyboard.name}")
    
    def _set_status(self, msg: str):
        """Status setzen"""
        self.status_label.config(text=msg)
    
    # ============================================================
    # TOOLTIP
    # ============================================================
    
    def _show_tooltip(self, event, text: str):
        if hasattr(self, '_tooltip'):
            self._tooltip.destroy()
        
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        tk.Label(
            self._tooltip, text=text,
            bg="#ffffe0", fg="black",
            relief=tk.SOLID, borderwidth=1,
            font=("Arial", 9)
        ).pack()
    
    def _hide_tooltip(self):
        if hasattr(self, '_tooltip'):
            self._tooltip.destroy()
    
    # ============================================================
    # DIALOGE
    # ============================================================
    
    def _show_shortcuts(self):
        shortcuts = """
Tastenkürzel:

Ctrl+N     Neues Storyboard
Ctrl+O     Öffnen
Ctrl+S     Speichern

Del        Löschen
F5         Vorschau

Flow-Graph:
  Doppelklick    Verbindung erstellen
  Mittlere Taste Pan
  Mausrad        Zoom
  Escape         Abbrechen
"""
        messagebox.showinfo("Tastenkürzel", shortcuts)
    
    def _show_about(self):
        about = """
🎬 Story Editor
für "Der Eine Ring" VTT

Version 1.0.0

Erstelle interaktive Geschichten mit:
• Kapitel und Szenen
• Trigger und Actions
• Video/Image Overlays
• Szenen-Übergänge

© VTT Development Team
"""
        messagebox.showinfo("Über Story Editor", about)
    
    # ============================================================
    # SCHLIESSEN
    # ============================================================
    
    def _on_close(self):
        """Schließen-Handler"""
        if self.has_unsaved_changes:
            result = messagebox.askyesnocancel(
                "Änderungen speichern?",
                "Das Storyboard wurde geändert. Speichern?"
            )
            if result is True:
                self._save_storyboard()
            elif result is None:
                return
        
        self.destroy()


# ============================================================
# HELPER: Story Editor öffnen
# ============================================================

def open_story_editor(parent=None, storyboard: Optional[Storyboard] = None,
                     on_scene_preview: Optional[Callable[[Scene], None]] = None) -> StoryEditor:
    """
    Öffnet den Story Editor.
    
    Args:
        parent: Eltern-Fenster (optional, erstellt eigenes wenn None)
        storyboard: Bestehendes Storyboard zum Bearbeiten
        on_scene_preview: Callback für Szenen-Vorschau
    
    Returns:
        StoryEditor-Instanz
    """
    if parent is None:
        parent = tk.Tk()
        parent.withdraw()
    
    editor = StoryEditor(parent, storyboard, on_scene_preview)
    return editor


# ============================================================
# STANDALONE AUSFÜHRUNG
# ============================================================

if __name__ == "__main__":
    # Test-Storyboard erstellen
    story = Storyboard(name="Der Eine Ring - Demo")
    
    # Kapitel 1: Prolog
    ch1 = Chapter(name="Prolog", icon="📖", description="Die Geschichte beginnt...")
    
    s1 = Scene(name="Einführung", scene_type=SceneType.CUTSCENE)
    t1 = Trigger(name="Weiter", trigger_type=TriggerType.CLICK)
    s1.triggers.append(t1)
    
    s2 = Scene(name="Das Auenland", scene_type=SceneType.MAP_JSON)
    t2 = Trigger(name="Beutelsend betreten", trigger_type=TriggerType.ENTER_AREA)
    t2.params["area_id"] = "bag_end"
    s2.triggers.append(t2)
    
    ch1.scenes = [s1, s2]
    ch1.start_scene_id = s1.id
    
    # Kapitel 2: Die Reise
    ch2 = Chapter(name="Die Reise beginnt", icon="⚔️")
    
    s3 = Scene(name="Der Alte Wald", scene_type=SceneType.VIDEO)
    s3.background_source = "old_forest.mp4"
    
    s4 = Scene(name="Bree", scene_type=SceneType.MAP_JSON)
    
    ch2.scenes = [s3, s4]
    ch2.start_scene_id = s3.id
    
    story.chapters = [ch1, ch2]
    
    # Editor öffnen
    def preview_callback(scene: Scene):
        print(f"Vorschau für Szene: {scene.name}")
    
    editor = open_story_editor(
        storyboard=story,
        on_scene_preview=preview_callback
    )
    
    editor.mainloop()
