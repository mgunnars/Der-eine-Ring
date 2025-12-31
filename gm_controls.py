"""
Gamemaster-Kontrollpanel für VTT-System
Steuert Webcam, Fog-of-War, Zoom und weitere Features

V2.0 - Verbesserte UI mit Framework-Integration
"""
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk

# UI-Framework importieren für konsistentes Design
try:
    from ui_framework import (
        UIColors, UISizes, UIIcons, WindowManager,
        VTTButton, VTTLabel, VTTFrame,
        show_info, show_warning, show_error, ask_confirm,
        ensure_minimum_size, center_window
    )
    UI_FRAMEWORK_AVAILABLE = True
except ImportError:
    UI_FRAMEWORK_AVAILABLE = False

# Boss-System importieren
try:
    from boss_system import BossControlPanel
    BOSS_SYSTEM_AVAILABLE = True
except ImportError:
    BOSS_SYSTEM_AVAILABLE = False


class GamemasterControlPanel(tk.Toplevel):
    """
    Kontrollpanel für den Spielleiter.
    
    Verbesserungen V2.0:
    - Mindestgröße für lesbare UI
    - Konsistentes Farbschema
    - Bessere Tab-Organisation
    - Status-Leiste
    """
    
    def __init__(self, parent, projector_window=None, webcam_tracker=None):
        super().__init__(parent)
        
        self.title("🎮 Gamemaster Kontrollpanel")
        
        # Farben aus UI-Framework
        bg_color = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        self.configure(bg=bg_color)
        
        # WICHTIG: Mindestgröße setzen BEVOR Fenster positioniert wird!
        self.minsize(1200, 900)  # GROSS für Karten-Fokus
        
        # Position auf primären Monitor (links oben, nicht zoomed sofort)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # GROSSES FENSTER: 75% Breite, 90% Höhe - Karte ist das Hauptelement!
        win_width = max(1200, int(screen_width * 0.75))
        win_height = max(900, int(screen_height * 0.9))
        
        # Links positionieren (Projektor ist rechts/auf zweitem Monitor)
        self.geometry(f"{win_width}x{win_height}+20+20")
        
        self.projector_window = projector_window
        self.webcam_tracker = webcam_tracker
        
        # Webcam-Preview
        self.preview_running = False
        self.preview_label = None
        
        # Style für ttk-Widgets
        self._setup_ttk_style()
        
        self.setup_ui()
        self._create_status_bar()
    
    def _setup_ttk_style(self):
        """Konfiguriert ttk-Styles für dunkles Theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_dark = UIColors.BG_DARK if UI_FRAMEWORK_AVAILABLE else "#0a0a0a"
        bg_panel = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        text_primary = UIColors.TEXT_PRIMARY if UI_FRAMEWORK_AVAILABLE else "#ffffff"
        
        style.configure('TNotebook', background=bg_panel)
        style.configure('TNotebook.Tab', 
                       background=bg_dark, 
                       foreground=text_primary,
                       padding=[15, 8])
        style.map('TNotebook.Tab',
                 background=[('selected', bg_panel)],
                 foreground=[('selected', '#d4af37')])
    
    def _create_status_bar(self):
        """Erstellt Status-Leiste unten"""
        bg_dark = UIColors.BG_DARK if UI_FRAMEWORK_AVAILABLE else "#0a0a0a"
        
        status_bar = tk.Frame(self, bg=bg_dark, height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(status_bar, 
                                    text="✅ GM-Panel bereit",
                                    font=("Arial", 9),
                                    bg=bg_dark, fg="#888888")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Projektor-Status
        self.projector_status = tk.Label(status_bar, 
                                        text="📺 Projektor: Nicht verbunden",
                                        font=("Arial", 9),
                                        bg=bg_dark, fg="#ff8800")
        self.projector_status.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Prüfe Projektor-Verbindung
        self._update_projector_status()
    
    def _update_projector_status(self):
        """Aktualisiert Projektor-Status in der Status-Leiste"""
        if self.projector_window and self.projector_window.winfo_exists():
            self.projector_status.config(text="📺 Projektor: Verbunden", fg="#44ff44")
        else:
            self.projector_status.config(text="📺 Projektor: Nicht verbunden", fg="#ff8800")
        
        # Alle 2 Sekunden prüfen
        self.after(2000, self._update_projector_status)
    
    def _set_status(self, message: str):
        """Aktualisiert Status-Nachricht"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
        
    def setup_ui(self):
        """UI-Elemente erstellen - verbesserte Version"""
        bg_panel = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        
        # Notebook für verschiedene Tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Webcam-Steuerung
        webcam_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(webcam_frame, text="  📹 Webcam  ")
        self.setup_webcam_tab(webcam_frame)
        
        # Tab 2: Fog-of-War Steuerung
        fog_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(fog_frame, text="  🌫️ Fog-of-War  ")
        self.setup_fog_tab(fog_frame)
        
        # Tab 3: Kamera & Zoom
        camera_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(camera_frame, text="  🎥 Kamera  ")
        self.setup_camera_tab(camera_frame)
        
        # Tab 4: Einstellungen
        settings_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(settings_frame, text="  ⚙️ Einstellungen  ")
        self.setup_settings_tab(settings_frame)
        
        # Tab 5: Detail-Maps
        detail_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(detail_frame, text="  🏘️ Detail-Maps  ")
        self.setup_detail_maps_tab(detail_frame)
        
        # Tab 6: Overlay-Steuerung
        overlay_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(overlay_frame, text="  🌧️ Overlay  ")
        self.setup_overlay_tab(overlay_frame)
        
        # Tab 7: Boss-Steuerung
        boss_frame = tk.Frame(notebook, bg=bg_panel)
        notebook.add(boss_frame, text="  🐉 Bosse  ")
        self.setup_boss_tab(boss_frame)
    
    def setup_webcam_tab(self, parent):
        """Webcam-Steuerung Tab"""
        # Titel
        title = tk.Label(parent, text="Webcam-Tracking", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Webcam-Vorschau
        preview_frame = tk.LabelFrame(parent, text="Live-Vorschau", bg="#2d2d2d", fg="white")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.preview_label = tk.Label(preview_frame, bg="black")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Steuerung
        control_frame = tk.Frame(parent, bg="#1e1e1e")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.webcam_status = tk.Label(control_frame, text="Status: Gestoppt", 
                                      bg="#1e1e1e", fg="orange", font=("Arial", 10, "bold"))
        self.webcam_status.pack(side=tk.LEFT, padx=5)
        
        self.start_webcam_btn = tk.Button(control_frame, text="▶ Start Tracking",
                                         command=self.start_webcam,
                                         bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                                         padx=10, pady=5)
        self.start_webcam_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_webcam_btn = tk.Button(control_frame, text="⏹ Stop Tracking",
                                        command=self.stop_webcam,
                                        bg="#f44336", fg="white", font=("Arial", 10, "bold"),
                                        padx=10, pady=5, state=tk.DISABLED)
        self.stop_webcam_btn.pack(side=tk.LEFT, padx=5)
        
        self.calibrate_btn = tk.Button(control_frame, text="🎯 Kalibrieren",
                                       command=self.calibrate_webcam,
                                       bg="#2196F3", fg="white", font=("Arial", 10, "bold"),
                                       padx=10, pady=5)
        self.calibrate_btn.pack(side=tk.LEFT, padx=5)
        
        # Info
        info_text = ("Tracking aktivieren, dann mit der Hand über den Spieltisch fahren.\n"
                    "Kalibrierung: Die 4 Ecken des Spieltisches markieren.")
        info_label = tk.Label(parent, text=info_text, bg="#1e1e1e", fg="#aaaaaa",
                            font=("Arial", 9), justify=tk.LEFT)
        info_label.pack(padx=10, pady=5)
    
    def setup_fog_tab(self, parent):
        """Fog-of-War Tab - Kompaktes Layout für maximale Kartengröße"""
        # Kompakte Header-Zeile: Titel + Fog Toggle + Sichtweite alles in einer Reihe
        header_frame = tk.Frame(parent, bg="#1e1e1e")
        header_frame.pack(fill=tk.X, padx=10, pady=3)
        
        tk.Label(header_frame, text="🌫️ Fog-of-War", font=("Arial", 12, "bold"),
                bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.fog_enabled_var = tk.BooleanVar(value=True)
        fog_checkbox = tk.Checkbutton(header_frame, text="Aktiviert",
                                     variable=self.fog_enabled_var,
                                     command=self.toggle_fog,
                                     bg="#1e1e1e", fg="white", selectcolor="#2d2d2d",
                                     font=("Arial", 10))
        fog_checkbox.pack(side=tk.LEFT, padx=10)
        
        # Sichtweite kompakt in Header-Zeile
        tk.Label(header_frame, text="Radius:", bg="#1e1e1e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT, padx=(20, 5))
        
        self.sight_range_var = tk.IntVar(value=3)
        sight_slider = tk.Scale(header_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                               variable=self.sight_range_var,
                               command=self.update_sight_range,
                               bg="#2d2d2d", fg="white", highlightthickness=0,
                               length=120, sliderlength=15)
        sight_slider.pack(side=tk.LEFT, padx=2)
        
        self.sight_value_label = tk.Label(header_frame, text="3", bg="#1e1e1e", fg="white",
                                         font=("Arial", 9))
        self.sight_value_label.pack(side=tk.LEFT, padx=2)
        
        # SCHNELL-PRESETS - Kompakter in einer Zeile
        preset_frame = tk.LabelFrame(parent, text="⚡ Schnell-Presets", bg="#2d2d2d", fg="white")
        preset_frame.pack(fill=tk.X, padx=10, pady=2)
        
        preset_row = tk.Frame(preset_frame, bg="#2d2d2d")
        preset_row.pack(fill=tk.X, padx=3, pady=2)
        
        presets = [
            ("🏠 Mitte", self.preset_center_only, "#4CAF50"),
            ("🚪 Eingang", self.preset_entrance, "#2196F3"),
            ("⚔️ Kampf", self.preset_combat_area, "#FF9800"),
            ("🗺️ Ränder", self.preset_except_borders, "#9C27B0"),
            ("🔦 V-Korr", self.preset_corridor_v, "#607D8B"),
            ("↔️ H-Korr", self.preset_corridor_h, "#607D8B")
        ]
        
        for text, command, color in presets:
            btn = tk.Button(preset_row, text=text, command=command,
                           bg=color, fg="white", font=("Arial", 8, "bold"),
                           padx=4, pady=2)
            btn.pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
        
        # NEUE INTERAKTIVE KARTENANSICHT - HAUPTELEMENT!
        map_frame = tk.LabelFrame(parent, text="🗺️ Interaktive Kartenansicht (Klick zum Enthüllen/Verbergen)", 
                                 bg="#2d2d2d", fg="white")
        map_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
        
        # Kompakte Info-Leiste oben
        info_bar = tk.Frame(map_frame, bg="#2d2d2d")
        info_bar.pack(fill=tk.X, padx=3, pady=1)
        
        tk.Label(info_bar, text="LMB: Enthüllen | RMB: Verbergen | MMB: Boss", 
                bg="#2d2d2d", fg="#888888", font=("Arial", 7)).pack(side=tk.LEFT, padx=3)
        
        # Pinsel und Zoom in Info-Leiste
        tk.Label(info_bar, text="Pinsel:", bg="#2d2d2d", fg="white", 
                font=("Arial", 8)).pack(side=tk.LEFT, padx=(15, 2))
        
        self.fog_brush_size = tk.IntVar(value=3)
        brush_slider = tk.Scale(info_bar, from_=1, to=10, orient=tk.HORIZONTAL,
                               variable=self.fog_brush_size,
                               bg="#2d2d2d", fg="white", highlightthickness=0,
                               length=60, sliderlength=12)
        brush_slider.pack(side=tk.LEFT, padx=2)
        
        tk.Label(info_bar, text="Zoom:", bg="#2d2d2d", fg="white",
                font=("Arial", 8)).pack(side=tk.LEFT, padx=(10, 2))
        
        self.gm_map_zoom = tk.DoubleVar(value=1.0)
        zoom_slider = tk.Scale(info_bar, from_=0.5, to=3.0, resolution=0.1,
                              orient=tk.HORIZONTAL, variable=self.gm_map_zoom,
                              bg="#2d2d2d", fg="white", highlightthickness=0,
                              length=80, sliderlength=12, command=lambda v: self.update_fog_map())
        zoom_slider.pack(side=tk.LEFT, padx=2)
        
        # Quick-Buttons kompakt rechts
        tk.Button(info_bar, text="🌞", command=self.reveal_all_fog,
                 bg="#4CAF50", fg="white", width=3, font=("Arial", 9)).pack(side=tk.RIGHT, padx=1)
        tk.Button(info_bar, text="🌑", command=self.hide_all_fog,
                 bg="#f44336", fg="white", width=3, font=("Arial", 9)).pack(side=tk.RIGHT, padx=1)
        tk.Button(info_bar, text="🔄", command=self.update_fog_map,
                 bg="#2196F3", fg="white", width=3, font=("Arial", 9)).pack(side=tk.RIGHT, padx=1)
        
        # Canvas für interaktive Karte - MAXIMALER PLATZ
        canvas_frame = tk.Frame(map_frame, bg="#1e1e1e")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Scrollbars
        h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.fog_map_canvas = tk.Canvas(canvas_frame, bg="#1e1e1e",
                                        xscrollcommand=h_scroll.set,
                                        yscrollcommand=v_scroll.set)
        self.fog_map_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        h_scroll.config(command=self.fog_map_canvas.xview)
        v_scroll.config(command=self.fog_map_canvas.yview)
        
        # Maus-Events
        self.fog_map_canvas.bind("<Button-1>", self.on_fog_map_left_click)
        self.fog_map_canvas.bind("<Button-3>", self.on_fog_map_right_click)
        self.fog_map_canvas.bind("<B1-Motion>", self.on_fog_map_drag)
        
        # Karte initial zeichnen
        self.update_fog_map()
    
    def setup_camera_tab(self, parent):
        """Kamera & Zoom Tab"""
        title = tk.Label(parent, text="Kamera-Steuerung", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Zoom-Steuerung
        zoom_frame = tk.LabelFrame(parent, text="Zoom", bg="#2d2d2d", fg="white")
        zoom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        zoom_label = tk.Label(zoom_frame, text="Zoom-Level:", bg="#2d2d2d", fg="white")
        zoom_label.pack(side=tk.LEFT, padx=5)
        
        self.zoom_var = tk.DoubleVar(value=1.0)
        zoom_slider = tk.Scale(zoom_frame, from_=0.5, to=3.0, resolution=0.1,
                              orient=tk.HORIZONTAL, variable=self.zoom_var,
                              command=self.update_zoom,
                              bg="#2d2d2d", fg="white", highlightthickness=0)
        zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.zoom_value_label = tk.Label(zoom_frame, text="100%", bg="#2d2d2d", fg="white")
        self.zoom_value_label.pack(side=tk.LEFT, padx=5)
        
        # Auto-Zoom
        auto_zoom_frame = tk.LabelFrame(parent, text="Automatischer Zoom", bg="#2d2d2d", fg="white")
        auto_zoom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.auto_zoom_var = tk.BooleanVar(value=False)
        auto_zoom_check = tk.Checkbutton(auto_zoom_frame, 
                                        text="Auto-Zoom auf relevanten Bereich aktivieren",
                                        variable=self.auto_zoom_var,
                                        command=self.toggle_auto_zoom,
                                        bg="#2d2d2d", fg="white", selectcolor="#1e1e1e",
                                        font=("Arial", 10))
        auto_zoom_check.pack(padx=5, pady=5)
        
        info = tk.Label(auto_zoom_frame, 
                       text="Zoomt automatisch auf Bereiche, in denen Spieler aktiv sind.",
                       bg="#2d2d2d", fg="#aaaaaa", font=("Arial", 9))
        info.pack(padx=5, pady=2)
        
        # Kamera zurücksetzen
        reset_btn = tk.Button(parent, text="🎯 Kamera zurücksetzen",
                             command=self.reset_camera,
                             bg="#2196F3", fg="white", font=("Arial", 11, "bold"),
                             padx=15, pady=8)
        reset_btn.pack(padx=10, pady=10)
    
    def setup_settings_tab(self, parent):
        """Einstellungen Tab"""
        title = tk.Label(parent, text="Einstellungen", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Webcam-Auswahl
        webcam_frame = tk.LabelFrame(parent, text="Webcam", bg="#2d2d2d", fg="white")
        webcam_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(webcam_frame, text="Webcam-Index:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        self.webcam_index_var = tk.IntVar(value=0)
        webcam_spin = tk.Spinbox(webcam_frame, from_=0, to=5, textvariable=self.webcam_index_var, width=5)
        webcam_spin.pack(side=tk.LEFT, padx=5)
        
        # Performance
        perf_frame = tk.LabelFrame(parent, text="Performance", bg="#2d2d2d", fg="white")
        perf_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(perf_frame, text="Tracking-Empfindlichkeit:", bg="#2d2d2d", fg="white").pack(anchor=tk.W, padx=5, pady=2)
        self.sensitivity_var = tk.IntVar(value=500)
        sens_slider = tk.Scale(perf_frame, from_=100, to=2000, orient=tk.HORIZONTAL,
                              variable=self.sensitivity_var,
                              bg="#2d2d2d", fg="white", highlightthickness=0)
        sens_slider.pack(fill=tk.X, padx=5, pady=2)
    
    def setup_detail_maps_tab(self, parent):
        """Detail-Maps Tab"""
        title = tk.Label(parent, text="Detail-Maps Verwaltung", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Info
        info = tk.Label(parent, 
                       text="Detail-Maps werden beim Betreten von Dörfern/Gebäuden automatisch geladen.",
                       bg="#1e1e1e", fg="#aaaaaa", font=("Arial", 9))
        info.pack(padx=10, pady=5)
        
        # Auto-Switch Toggle
        auto_frame = tk.Frame(parent, bg="#1e1e1e")
        auto_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.auto_detail_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(auto_frame, 
                                    text="Automatischer Wechsel zu Detail-Maps aktiviert",
                                    variable=self.auto_detail_var,
                                    command=self.toggle_auto_detail,
                                    bg="#1e1e1e", fg="white", selectcolor="#2d2d2d",
                                    font=("Arial", 10, "bold"))
        auto_check.pack(side=tk.LEFT, padx=5)
        
        # Detail-Map erstellen
        create_frame = tk.LabelFrame(parent, text="Neue Detail-Map erstellen", bg="#2d2d2d", fg="white")
        create_frame.pack(fill=tk.X, padx=10, pady=10)
        
        coords_frame = tk.Frame(create_frame, bg="#2d2d2d")
        coords_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(coords_frame, text="Position (X, Y):", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        self.detail_x = tk.Spinbox(coords_frame, from_=0, to=100, width=5)
        self.detail_x.pack(side=tk.LEFT, padx=2)
        self.detail_y = tk.Spinbox(coords_frame, from_=0, to=100, width=5)
        self.detail_y.pack(side=tk.LEFT, padx=2)
        
        type_frame = tk.Frame(create_frame, bg="#2d2d2d")
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(type_frame, text="Typ:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        self.detail_type_var = tk.StringVar(value="village")
        tk.Radiobutton(type_frame, text="Dorf", variable=self.detail_type_var, value="village",
                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(type_frame, text="Gebäude", variable=self.detail_type_var, value="building",
                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e").pack(side=tk.LEFT, padx=5)
        
        btn_frame = tk.Frame(create_frame, bg="#2d2d2d")
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        create_btn = tk.Button(btn_frame, text="➕ Detail-Map erstellen",
                              command=self.create_detail_map,
                              bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                              padx=10, pady=5)
        create_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Liste vorhandener Detail-Maps
        list_frame = tk.LabelFrame(parent, text="Vorhandene Detail-Maps", bg="#2d2d2d", fg="white")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.detail_listbox = tk.Listbox(list_frame, bg="#1e1e1e", fg="white", font=("Courier", 9))
        self.detail_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        list_btn_frame = tk.Frame(list_frame, bg="#2d2d2d")
        list_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        refresh_btn = tk.Button(list_btn_frame, text="🔄 Aktualisieren",
                               command=self.refresh_detail_list,
                               bg="#2196F3", fg="white", padx=10, pady=3)
        refresh_btn.pack(side=tk.LEFT, padx=2)
        
        delete_btn = tk.Button(list_btn_frame, text="🗑️ Löschen",
                              command=self.delete_detail_map,
                              bg="#f44336", fg="white", padx=10, pady=3)
        delete_btn.pack(side=tk.LEFT, padx=2)
        
        # Initial Liste laden
        self.refresh_detail_list()
    
    def setup_overlay_tab(self, parent):
        """Overlay-Steuerung Tab für Wetter-/Umgebungseffekte"""
        title = tk.Label(parent, text="Overlay-Effekte", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Info
        info = tk.Label(parent, 
                       text="Wähle ein Overlay für die aktuelle Szene (Regen, Schnee, Nebel...)",
                       bg="#1e1e1e", fg="#aaaaaa", font=("Arial", 9))
        info.pack(padx=10, pady=5)
        
        # Overlay an/aus Toggle
        toggle_frame = tk.Frame(parent, bg="#1e1e1e")
        toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.overlay_enabled_var = tk.BooleanVar(value=False)
        self.overlay_toggle = tk.Checkbutton(toggle_frame, 
                                             text="Overlay aktiviert",
                                             variable=self.overlay_enabled_var,
                                             command=self.toggle_overlay,
                                             bg="#1e1e1e", fg="white", selectcolor="#2d2d2d",
                                             font=("Arial", 12, "bold"))
        self.overlay_toggle.pack(side=tk.LEFT, padx=5)
        
        # Aktuelles Overlay-Info
        self.overlay_status = tk.Label(toggle_frame, text="Kein Overlay geladen", 
                                       bg="#1e1e1e", fg="orange", font=("Arial", 10))
        self.overlay_status.pack(side=tk.RIGHT, padx=5)
        
        # Overlay-Auswahl aus Szene
        scene_frame = tk.LabelFrame(parent, text="Szenen-Overlays", bg="#2d2d2d", fg="white")
        scene_frame.pack(fill=tk.X, padx=10, pady=10)
        
        scene_info = tk.Label(scene_frame, 
                             text="Overlays die für die aktuelle Szene definiert sind:",
                             bg="#2d2d2d", fg="#aaaaaa", font=("Arial", 9))
        scene_info.pack(anchor=tk.W, padx=5, pady=2)
        
        # Listbox für Szenen-Overlays
        list_frame = tk.Frame(scene_frame, bg="#2d2d2d")
        list_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.scene_overlay_listbox = tk.Listbox(list_frame, bg="#1e1e1e", fg="white", 
                                                 font=("Courier", 10), height=4,
                                                 selectbackground="#4CAF50")
        self.scene_overlay_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.scene_overlay_listbox.bind('<<ListboxSelect>>', self.on_scene_overlay_select)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.scene_overlay_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scene_overlay_listbox.config(yscrollcommand=scrollbar.set)
        
        # Datei-Overlay laden
        file_frame = tk.LabelFrame(parent, text="Eigenes Overlay laden", bg="#2d2d2d", fg="white")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        file_btn_frame = tk.Frame(file_frame, bg="#2d2d2d")
        file_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        load_gif_btn = tk.Button(file_btn_frame, text="📁 GIF laden",
                                 command=lambda: self.load_overlay_file("gif"),
                                 bg="#2196F3", fg="white", font=("Arial", 10),
                                 padx=10, pady=5)
        load_gif_btn.pack(side=tk.LEFT, padx=5)
        
        load_video_btn = tk.Button(file_btn_frame, text="🎬 Video laden (MP4/WebM)",
                                   command=lambda: self.load_overlay_file("video"),
                                   bg="#9C27B0", fg="white", font=("Arial", 10),
                                   padx=10, pady=5)
        load_video_btn.pack(side=tk.LEFT, padx=5)
        
        # Aktuell geladene Datei
        self.overlay_file_label = tk.Label(file_frame, text="Keine Datei geladen", 
                                           bg="#2d2d2d", fg="#aaaaaa", font=("Arial", 9))
        self.overlay_file_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Overlay-Einstellungen
        settings_frame = tk.LabelFrame(parent, text="Einstellungen", bg="#2d2d2d", fg="white")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Opacity Slider
        opacity_frame = tk.Frame(settings_frame, bg="#2d2d2d")
        opacity_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(opacity_frame, text="Deckkraft:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.overlay_opacity_var = tk.DoubleVar(value=0.7)
        opacity_slider = tk.Scale(opacity_frame, from_=0.0, to=1.0, resolution=0.05,
                                  orient=tk.HORIZONTAL, variable=self.overlay_opacity_var,
                                  command=self.update_overlay_opacity,
                                  bg="#2d2d2d", fg="white", highlightthickness=0)
        opacity_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.opacity_value_label = tk.Label(opacity_frame, text="70%", bg="#2d2d2d", fg="white", width=5)
        self.opacity_value_label.pack(side=tk.RIGHT, padx=5)
        
        # Playback Speed
        speed_frame = tk.Frame(settings_frame, bg="#2d2d2d")
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(speed_frame, text="Geschwindigkeit:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.overlay_speed_var = tk.DoubleVar(value=1.0)
        speed_slider = tk.Scale(speed_frame, from_=0.1, to=3.0, resolution=0.1,
                                orient=tk.HORIZONTAL, variable=self.overlay_speed_var,
                                command=self.update_overlay_speed,
                                bg="#2d2d2d", fg="white", highlightthickness=0)
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.speed_value_label = tk.Label(speed_frame, text="1.0x", bg="#2d2d2d", fg="white", width=5)
        self.speed_value_label.pack(side=tk.RIGHT, padx=5)
        
        # Position & Größe
        transform_frame = tk.LabelFrame(parent, text="Position & Größe", bg="#2d2d2d", fg="white")
        transform_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Position X/Y
        pos_frame = tk.Frame(transform_frame, bg="#2d2d2d")
        pos_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(pos_frame, text="Position X:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        self.overlay_x_var = tk.IntVar(value=0)
        x_spin = tk.Spinbox(pos_frame, from_=-2000, to=2000, increment=10,
                            textvariable=self.overlay_x_var, width=6,
                            command=self.update_overlay_transform)
        x_spin.pack(side=tk.LEFT, padx=2)
        x_spin.bind('<Return>', lambda e: self.update_overlay_transform())
        
        tk.Label(pos_frame, text="Y:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        self.overlay_y_var = tk.IntVar(value=0)
        y_spin = tk.Spinbox(pos_frame, from_=-2000, to=2000, increment=10,
                            textvariable=self.overlay_y_var, width=6,
                            command=self.update_overlay_transform)
        y_spin.pack(side=tk.LEFT, padx=2)
        y_spin.bind('<Return>', lambda e: self.update_overlay_transform())
        
        # Größe (Scale)
        scale_frame = tk.Frame(transform_frame, bg="#2d2d2d")
        scale_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(scale_frame, text="Größe:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.overlay_scale_var = tk.DoubleVar(value=1.0)
        scale_slider = tk.Scale(scale_frame, from_=0.1, to=3.0, resolution=0.1,
                                orient=tk.HORIZONTAL, variable=self.overlay_scale_var,
                                command=self.update_overlay_transform,
                                bg="#2d2d2d", fg="white", highlightthickness=0)
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.scale_value_label = tk.Label(scale_frame, text="100%", bg="#2d2d2d", fg="white", width=5)
        self.scale_value_label.pack(side=tk.RIGHT, padx=5)
        
        # Modus: Kacheln oder Skalieren
        mode_frame = tk.Frame(transform_frame, bg="#2d2d2d")
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(mode_frame, text="Modus:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.overlay_mode_var = tk.StringVar(value="tile")
        tk.Radiobutton(mode_frame, text="Kacheln", variable=self.overlay_mode_var, value="tile",
                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e",
                      command=self.update_overlay_transform).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Strecken", variable=self.overlay_mode_var, value="stretch",
                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e",
                      command=self.update_overlay_transform).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Zentriert", variable=self.overlay_mode_var, value="center",
                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e",
                      command=self.update_overlay_transform).pack(side=tk.LEFT, padx=5)
        
        # Abdunkelung (für Wetter-Overlays)
        darken_frame = tk.LabelFrame(parent, text="🌑 Karten-Abdunkelung", bg="#2d2d2d", fg="white")
        darken_frame.pack(fill=tk.X, padx=10, pady=10)
        
        darken_toggle_frame = tk.Frame(darken_frame, bg="#2d2d2d")
        darken_toggle_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.darken_map_var = tk.BooleanVar(value=False)
        darken_check = tk.Checkbutton(darken_toggle_frame, 
                                      text="Karte abdunkeln (für Regen/Sturm)",
                                      variable=self.darken_map_var,
                                      command=self.update_darken_map,
                                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e",
                                      font=("Arial", 10))
        darken_check.pack(side=tk.LEFT, padx=5)
        
        darken_slider_frame = tk.Frame(darken_frame, bg="#2d2d2d")
        darken_slider_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(darken_slider_frame, text="Stärke:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.darken_amount_var = tk.DoubleVar(value=0.3)
        darken_slider = tk.Scale(darken_slider_frame, from_=0.1, to=0.7, resolution=0.05,
                                 orient=tk.HORIZONTAL, variable=self.darken_amount_var,
                                 command=self.update_darken_amount,
                                 bg="#2d2d2d", fg="white", highlightthickness=0)
        darken_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.darken_value_label = tk.Label(darken_slider_frame, text="30%", bg="#2d2d2d", fg="white", width=5)
        self.darken_value_label.pack(side=tk.RIGHT, padx=5)
        
        # Random Overlay System
        random_frame = tk.LabelFrame(parent, text="Zufälliges Overlay", bg="#2d2d2d", fg="white")
        random_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Random aktivieren
        random_toggle_frame = tk.Frame(random_frame, bg="#2d2d2d")
        random_toggle_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.random_overlay_var = tk.BooleanVar(value=False)
        random_check = tk.Checkbutton(random_toggle_frame, 
                                      text="Zufälliges Overlay aktiviert",
                                      variable=self.random_overlay_var,
                                      command=self.toggle_random_overlay,
                                      bg="#2d2d2d", fg="white", selectcolor="#1e1e1e",
                                      font=("Arial", 10, "bold"))
        random_check.pack(side=tk.LEFT, padx=5)
        
        # Intervall
        interval_frame = tk.Frame(random_frame, bg="#2d2d2d")
        interval_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(interval_frame, text="Wechsel alle:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.random_interval_var = tk.IntVar(value=60)
        interval_spin = tk.Spinbox(interval_frame, from_=10, to=600, increment=10,
                                   textvariable=self.random_interval_var, width=5)
        interval_spin.pack(side=tk.LEFT, padx=5)
        
        tk.Label(interval_frame, text="Sekunden", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Random-Status
        self.random_status_label = tk.Label(random_frame, text="Deaktiviert", 
                                            bg="#2d2d2d", fg="orange", font=("Arial", 9))
        self.random_status_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Aktionsbuttons
        action_frame = tk.Frame(parent, bg="#1e1e1e")
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        clear_btn = tk.Button(action_frame, text="❌ Overlay entfernen",
                              command=self.clear_overlay,
                              bg="#f44336", fg="white", font=("Arial", 10, "bold"),
                              padx=15, pady=5)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        editor_btn = tk.Button(action_frame, text="🎨 Partikel-Editor öffnen",
                               command=self.open_particle_editor,
                               bg="#FF9800", fg="white", font=("Arial", 10, "bold"),
                               padx=15, pady=5)
        editor_btn.pack(side=tk.RIGHT, padx=5)
        
        # Overlay-Daten initialisieren
        self.current_overlay_frames = []
        self.current_overlay_path = None
    
    def setup_boss_tab(self, parent):
        """Boss-Steuerung Tab für Kampf-Bosse"""
        title = tk.Label(parent, text="Boss-Steuerung", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Info
        info = tk.Label(parent, 
                       text="Verwalte enthüllte Bosse und füge ihnen Schaden zu",
                       bg="#1e1e1e", fg="#aaaaaa", font=("Arial", 9))
        info.pack(padx=10, pady=5)
        
        if not BOSS_SYSTEM_AVAILABLE:
            # Fallback wenn Boss-System nicht geladen werden konnte
            error_label = tk.Label(parent, 
                                   text="⚠️ Boss-System konnte nicht geladen werden.\nBitte boss_system.py prüfen.",
                                   bg="#1e1e1e", fg="#f44336", font=("Arial", 11))
            error_label.pack(pady=20)
            return
        
        # Boss Control Panel einbetten
        if self.projector_window and hasattr(self.projector_window, 'boss_manager'):
            boss_manager = self.projector_window.boss_manager
            
            def on_boss_damage(boss, placement):
                """Callback wenn ein Boss Schaden erhält"""
                if self.projector_window:
                    # Prüfe ob Boss besiegt wurde
                    if boss.is_defeated:
                        self._set_status(f"👑 Boss '{boss.name}' BESIEGT!")
                        print(f"👑 Boss '{boss.name}' wurde besiegt!")
                        # Zeige Sieges-Karte im Projektor
                        self.projector_window.show_victory_screen(boss)
                    else:
                        self._set_status(f"⚔️ Boss '{boss.name}' HP: {boss.current_health}/{boss.max_health}")
                    
                    # Karte neu rendern (zeigt Boss-Overlays automatisch)
                    self.projector_window.render_map()
                    self.update_fog_map()
            
            def on_boss_reveal(boss, placement):
                """Callback wenn ein Boss enthüllt wird"""
                if self.projector_window:
                    self.projector_window.render_map()
                    self._set_status(f"🐉 Boss '{boss.name}' enthüllt!")
            
            self.boss_control_panel = BossControlPanel(
                parent, 
                boss_manager,
                on_damage_callback=on_boss_damage,
                on_reveal_callback=on_boss_reveal
            )
            self.boss_control_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        else:
            # Kein Projektor oder Boss-Manager verfügbar
            no_projector = tk.Label(parent, 
                                    text="⚠️ Projektor-Fenster nicht aktiv.\nBitte erst den Projektor-Modus starten.",
                                    bg="#1e1e1e", fg="orange", font=("Arial", 11))
            no_projector.pack(pady=20)
            
            # Button zum Aktualisieren
            refresh_btn = tk.Button(parent, text="🔄 Verbindung prüfen",
                                   command=self.refresh_boss_panel,
                                   bg="#2196F3", fg="white", font=("Arial", 11),
                                   padx=15, pady=8)
            refresh_btn.pack(pady=10)
    
    def refresh_boss_panel(self):
        """Aktualisiert das Boss-Panel mit aktuellem Projektor-Status"""
        if hasattr(self, 'boss_control_panel'):
            self.boss_control_panel.refresh()
        self._set_status("Boss-Panel aktualisiert")

    def toggle_overlay(self):
        """Overlay an/aus schalten"""
        enabled = self.overlay_enabled_var.get()
        if self.projector_window:
            self.projector_window.overlay_enabled = enabled
            if enabled and self.current_overlay_frames:
                # Animation starten (set_overlay_frames ruft start_overlay_animation auf)
                self.projector_window.set_overlay_frames(self.current_overlay_frames)
            else:
                self.projector_window.stop_overlay_animation()
        status = "aktiviert" if enabled else "deaktiviert"
        self._set_status(f"Overlay {status}")
    
    def on_scene_overlay_select(self, event):
        """Wenn ein Szenen-Overlay ausgewählt wird"""
        selection = self.scene_overlay_listbox.curselection()
        if selection and hasattr(self, '_scene_overlays') and self._scene_overlays:
            idx = selection[0]
            if idx < len(self._scene_overlays):
                overlay = self._scene_overlays[idx]
                if hasattr(overlay, 'file_path') and overlay.file_path:
                    self.load_overlay_from_path(overlay.file_path)
                    
                    # Übernehme darken_map Einstellungen aus dem Overlay
                    if hasattr(overlay, 'darken_map'):
                        self.darken_map_var.set(overlay.darken_map)
                        if self.projector_window:
                            self.projector_window.darken_map = overlay.darken_map
                    if hasattr(overlay, 'darken_amount'):
                        self.darken_amount_var.set(overlay.darken_amount)
                        self.darken_value_label.config(text=f"{int(overlay.darken_amount * 100)}%")
                        if self.projector_window:
                            self.projector_window.darken_amount = overlay.darken_amount
    
    def load_overlay_file(self, file_type):
        """Lädt eine Overlay-Datei (GIF oder Video)"""
        from tkinter import filedialog
        
        if file_type == "gif":
            filetypes = [("GIF Dateien", "*.gif"), ("Alle Dateien", "*.*")]
        else:
            filetypes = [("Video Dateien", "*.mp4 *.webm"), ("Alle Dateien", "*.*")]
        
        filepath = filedialog.askopenfilename(
            title=f"Overlay-Datei auswählen",
            filetypes=filetypes
        )
        
        if filepath:
            self.load_overlay_from_path(filepath)
    
    def load_overlay_from_path(self, filepath):
        """Lädt Overlay aus Dateipfad"""
        import os
        from PIL import Image
        import numpy as np
        
        try:
            ext = os.path.splitext(filepath)[1].lower()
            frames = []
            
            if ext == '.gif':
                # GIF laden - hat oft schon Transparenz
                img = Image.open(filepath)
                try:
                    while True:
                        frame = img.copy().convert('RGBA')
                        frames.append(frame)
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
            elif ext in ['.mp4', '.webm']:
                # Video mit cv2 laden
                try:
                    import cv2
                    
                    cap = cv2.VideoCapture(filepath)
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    
                    # Limitiere auf max 150 Frames für bessere Performance
                    max_frames = min(total_frames, 150)
                    skip = max(1, total_frames // max_frames)
                    
                    frame_idx = 0
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        
                        # Frame-Skipping für Performance
                        frame_idx += 1
                        if skip > 1 and frame_idx % skip != 0:
                            continue
                        
                        # Prüfe ob WebM mit Alpha-Kanal (4 Channels)
                        if len(frame.shape) == 3 and frame.shape[2] == 4:
                            # Hat Alpha - BGRA zu RGBA
                            frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)
                        else:
                            # Kein Alpha (MP4) - nutze Additive Blending statt Transparenz!
                            # Das funktioniert besser für Regen/Schnee-Effekte
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            
                            # Erstelle Alpha basierend auf Helligkeit (Luminanz)
                            # Formel: 0.299*R + 0.587*G + 0.114*B
                            luminance = (0.299 * frame_rgb[:,:,0] + 
                                        0.587 * frame_rgb[:,:,1] + 
                                        0.114 * frame_rgb[:,:,2])
                            
                            # Alpha = Helligkeit (weiß = sichtbar, schwarz = transparent)
                            alpha = luminance.astype(np.uint8)
                            
                            # RGBA zusammenbauen
                            frame_rgba = np.dstack([frame_rgb, alpha])
                        
                        pil_frame = Image.fromarray(frame_rgba, 'RGBA')
                        frames.append(pil_frame)
                        
                        if len(frames) >= max_frames:
                            break
                    
                    cap.release()
                    print(f"✅ Video geladen: {len(frames)} Frames (von {total_frames})")
                except ImportError:
                    messagebox.showerror("Fehler", "OpenCV (cv2) nicht installiert für Video-Support")
                    return
            
            if frames:
                self.current_overlay_frames = frames
                self.current_overlay_path = filepath
                
                filename = os.path.basename(filepath)
                self.overlay_file_label.config(text=f"Geladen: {filename} ({len(frames)} Frames)")
                self.overlay_status.config(text=f"✓ {filename}", fg="#44ff44")
                
                # Frames an Projector senden UND aktivieren
                if self.projector_window:
                    self.projector_window.set_overlay_frames(frames)
                    self.projector_window.overlay_enabled = True
                    self.projector_window.render_map()
                    print(f"✅ Overlay aktiviert im Projector: {len(frames)} Frames")
                
                # Checkbox aktivieren
                self.overlay_enabled_var.set(True)
                
                self._set_status(f"Overlay geladen: {filename}")
            else:
                messagebox.showwarning("Warnung", "Keine Frames in der Datei gefunden")
                
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Overlay nicht laden: {e}")
    
    def update_overlay_opacity(self, value):
        """Aktualisiert Overlay-Deckkraft"""
        opacity = float(value)
        self.opacity_value_label.config(text=f"{int(opacity * 100)}%")
        if self.projector_window:
            self.projector_window.overlay_opacity = opacity
            self.projector_window.render_map()
    
    def update_overlay_speed(self, value):
        """Aktualisiert Overlay-Geschwindigkeit"""
        speed = float(value)
        self.speed_value_label.config(text=f"{speed:.1f}x")
        if self.projector_window:
            self.projector_window.overlay_speed = speed
    
    def update_overlay_transform(self, *args):
        """Aktualisiert Position, Größe und Modus des Overlays"""
        if self.projector_window:
            self.projector_window.overlay_x = self.overlay_x_var.get()
            self.projector_window.overlay_y = self.overlay_y_var.get()
            self.projector_window.overlay_scale = self.overlay_scale_var.get()
            self.projector_window.overlay_mode = self.overlay_mode_var.get()
            self.scale_value_label.config(text=f"{int(self.overlay_scale_var.get() * 100)}%")
            self.projector_window.render_map()
    
    def update_darken_map(self):
        """Aktiviert/Deaktiviert Karten-Abdunkelung"""
        darken = self.darken_map_var.get()
        if self.projector_window:
            self.projector_window.darken_map = darken
            self.projector_window.render_map()
        self._set_status(f"Karten-Abdunkelung {'aktiviert' if darken else 'deaktiviert'}")
    
    def update_darken_amount(self, value):
        """Aktualisiert Stärke der Karten-Abdunkelung"""
        amount = float(value)
        self.darken_value_label.config(text=f"{int(amount * 100)}%")
        if self.projector_window:
            self.projector_window.darken_amount = amount
            if self.projector_window.darken_map:
                self.projector_window.render_map()
    
    def clear_overlay(self):
        """Entfernt aktuelles Overlay"""
        self.current_overlay_frames = []
        self.current_overlay_path = None
        self.overlay_enabled_var.set(False)
        self.overlay_file_label.config(text="Keine Datei geladen")
        self.overlay_status.config(text="Kein Overlay geladen", fg="orange")
        
        # Random stoppen
        self.random_overlay_var.set(False)
        self.stop_random_overlay()
        
        if self.projector_window:
            self.projector_window.overlay_enabled = False
            self.projector_window.set_overlay_frames([])
            self.projector_window.render_map()
        
        self._set_status("Overlay entfernt")
    
    def toggle_random_overlay(self):
        """Aktiviert/Deaktiviert zufällige Overlay-Wechsel"""
        if self.random_overlay_var.get():
            self.start_random_overlay()
        else:
            self.stop_random_overlay()
    
    def start_random_overlay(self):
        """Startet zufällige Overlay-Wechsel"""
        if not hasattr(self, '_scene_overlays') or not self._scene_overlays:
            messagebox.showwarning("Warnung", "Keine Szenen-Overlays verfügbar!\n\nLade zuerst Overlays über das Storyboard.")
            self.random_overlay_var.set(False)
            return
        
        if len(self._scene_overlays) < 2:
            messagebox.showwarning("Warnung", "Mindestens 2 Overlays für Random-Modus benötigt!")
            self.random_overlay_var.set(False)
            return
        
        self.random_status_label.config(text="🔀 Random aktiv", fg="#44ff44")
        self._schedule_random_overlay()
        self._set_status("Random-Overlay gestartet")
    
    def stop_random_overlay(self):
        """Stoppt zufällige Overlay-Wechsel"""
        if hasattr(self, '_random_overlay_timer'):
            self.after_cancel(self._random_overlay_timer)
            self._random_overlay_timer = None
        self.random_status_label.config(text="Deaktiviert", fg="orange")
    
    def _schedule_random_overlay(self):
        """Plant den nächsten zufälligen Overlay-Wechsel"""
        if not self.random_overlay_var.get():
            return
        
        interval = self.random_interval_var.get() * 1000  # In Millisekunden
        self._random_overlay_timer = self.after(interval, self._switch_random_overlay)
    
    def _switch_random_overlay(self):
        """Wechselt zu einem zufälligen Overlay"""
        import random
        import os
        
        if not hasattr(self, '_scene_overlays') or not self._scene_overlays:
            self.stop_random_overlay()
            return
        
        # Zufälliges Overlay wählen (nicht das aktuelle)
        available = [o for o in self._scene_overlays 
                     if hasattr(o, 'file_path') and o.file_path and o.file_path != self.current_overlay_path]
        
        if available:
            overlay = random.choice(available)
            self.load_overlay_from_path(overlay.file_path)
            self._set_status(f"🔀 Random: {os.path.basename(overlay.file_path)}")
        
        # Nächsten Wechsel planen
        self._schedule_random_overlay()
    
    def open_particle_editor(self):
        """Öffnet den Partikel-Editor"""
        import subprocess
        import sys
        import os
        
        editor_path = os.path.join(os.path.dirname(__file__), "particle_editor_2d.py")
        if os.path.exists(editor_path):
            subprocess.Popen([sys.executable, editor_path])
            self._set_status("Partikel-Editor geöffnet")
        else:
            messagebox.showerror("Fehler", "particle_editor_2d.py nicht gefunden")
    
    def update_scene_overlays(self, overlays):
        """Aktualisiert die Liste der Szenen-Overlays"""
        self._scene_overlays = overlays  # Speichere für spätere Auswahl
        self.scene_overlay_listbox.delete(0, tk.END)
        for overlay in overlays:
            if hasattr(overlay, 'file_path') and overlay.file_path:
                import os
                name = overlay.name if overlay.name else os.path.basename(overlay.file_path)
                self.scene_overlay_listbox.insert(tk.END, f"📎 {name}")
        
        # HINWEIS: Overlay wird NICHT automatisch geladen!
        # User kann es manuell aus der Liste auswählen
        if overlays and len(overlays) > 0:
            print(f"🌧️ {len(overlays)} Overlay(s) verfügbar - klicke zum Laden")
    
    # Callback-Funktionen
    
    def start_webcam(self):
        """Startet Webcam-Tracking"""
        if self.webcam_tracker:
            success = self.webcam_tracker.start()
            if success:
                self.webcam_status.config(text="Status: Läuft", fg="green")
                self.start_webcam_btn.config(state=tk.DISABLED)
                self.stop_webcam_btn.config(state=tk.NORMAL)
                self.preview_running = True
                self.update_preview()
            else:
                messagebox.showerror("Fehler", "Konnte Webcam nicht starten!")
    
    def stop_webcam(self):
        """Stoppt Webcam-Tracking"""
        if self.webcam_tracker:
            self.webcam_tracker.stop()
            self.webcam_status.config(text="Status: Gestoppt", fg="orange")
            self.start_webcam_btn.config(state=tk.NORMAL)
            self.stop_webcam_btn.config(state=tk.DISABLED)
            self.preview_running = False
    
    def calibrate_webcam(self):
        """Öffnet Kalibrierungs-Dialog"""
        messagebox.showinfo("Kalibrierung", 
                          "Klicken Sie nacheinander auf die 4 Ecken des Spieltisches:\n"
                          "1. Oben links\n2. Oben rechts\n3. Unten rechts\n4. Unten links")
        # TODO: Implementiere interaktive Kalibrierung
    
    def toggle_fog(self):
        """Fog-of-War ein/ausschalten"""
        if self.projector_window:
            self.projector_window.fog_enabled = self.fog_enabled_var.get()
            self.projector_window.render_map()
    
    def update_sight_range(self, value):
        """Aktualisiert Sichtweite"""
        val = int(float(value))
        self.sight_value_label.config(text=f"{val} Tiles")
        if self.projector_window and self.projector_window.fog:
            self.projector_window.fog.sight_range = val
    
    def reveal_all_fog(self):
        """Deckt gesamte Karte auf"""
        if self.projector_window and self.projector_window.fog:
            self.projector_window.fog.reveal_all()
            self.projector_window.render_map()
            self.update_fog_map()
    
    def hide_all_fog(self):
        """Verbirgt gesamte Karte"""
        if self.projector_window and self.projector_window.fog:
            self.projector_window.fog.hide_all()
            self.projector_window.render_map()
            self.update_fog_map()
    
    def _adjust_gm_zoom(self, delta):
        """Passt den GM-Map-Zoom an"""
        if hasattr(self, 'gm_map_zoom'):
            new_zoom = max(0.5, min(2.0, self.gm_map_zoom.get() + delta))
            self.gm_map_zoom.set(new_zoom)
            self.update_fog_map()
    
    def _fit_gm_map(self):
        """Passt Zoom so an, dass die ganze Karte sichtbar ist"""
        if hasattr(self, 'gm_map_zoom'):
            self.gm_map_zoom.set(1.0)
            self.update_fog_map()
    
    def update_fog_map(self):
        """Zeichnet die interaktive Fog-Karte"""
        if not self.projector_window or not hasattr(self, 'fog_map_canvas'):
            return
        
        # Canvas leeren
        self.fog_map_canvas.delete("all")
        
        # Reset Hexagon-Mode Flag
        self.fog_map_canvas.is_hexagon_mode = False
        
        # SVG-Modus: Parse SVG und rendere Tiles
        if self.projector_window.is_svg_mode:
            self.update_fog_map_svg()
            return
        
        # JSON-Modus: Map-Daten holen
        map_data = self.projector_window.map_data
        
        # Hexagon-Map-Erkennung: Prüfe auf hex_size
        if map_data.get("hex_size"):
            self.update_fog_map_hexagon()
            return
        
        width = map_data.get("width", 50)
        height = map_data.get("height", 50)
        tiles = map_data.get("tiles", [])
        
        # Größere Tile-Größe für bessere GM-Übersicht - DEUTLICH VERGRÖSSERT
        tile_size = 24  # Erhöht von 16 für bessere Sichtbarkeit
        
        # Farben für Terrain-Typen (vereinfacht)
        terrain_colors = {
            "grass": "#6ba868",
            "water": "#4db8c4",
            "water_h": "#4db8c4",
            "water_v": "#4db8c4",
            "mountain": "#8a8a8a",
            "forest": "#3d6b3d",
            "sand": "#d4c8a0",
            "village": "#b8956f",
            "road": "#8a7f6f",
            "default": "#4a4a4a"
        }
        
        # Karte zeichnen
        for y in range(height):
            for x in range(width):
                # Terrain-Farbe
                if y < len(tiles) and x < len(tiles[y]):
                    terrain = tiles[y][x]
                else:
                    terrain = "grass"
                
                base_color = terrain_colors.get(terrain, terrain_colors["default"])
                
                # Fog-Status prüfen
                is_revealed = self.projector_window.fog.is_revealed(x, y)
                
                # Farbe anpassen je nach Fog-Status
                if is_revealed:
                    fill_color = base_color  # Normal sichtbar
                    outline = "#444444"  # Hellere Grid-Lines für GM (war #2a2a2a)
                else:
                    fill_color = "#3a3a3a"   # Grau = verborgen
                    outline = "#444444"
                
                # Tile zeichnen
                x1 = x * tile_size
                y1 = y * tile_size
                x2 = x1 + tile_size
                y2 = y1 + tile_size
                
                tile_id = self.fog_map_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill_color,
                    outline=outline,
                    tags=f"tile_{x}_{y}"
                )
        
        # Canvas-Scroll-Region setzen
        self.fog_map_canvas.config(scrollregion=(0, 0, width * tile_size, height * tile_size))
        
        # Referenz für spätere Nutzung
        if not hasattr(self.fog_map_canvas, 'tile_size'):
            self.fog_map_canvas.tile_size = tile_size
        
        # WICHTIG: Event-Bindings nach jedem Update neu setzen!
        # (gehen nach Tab-Wechsel verloren)
        self.fog_map_canvas.bind("<Button-1>", self.on_fog_map_left_click)
        self.fog_map_canvas.bind("<Button-3>", self.on_fog_map_right_click)
        self.fog_map_canvas.bind("<B1-Motion>", self.on_fog_map_drag)
    
    def update_fog_map_svg(self):
        """Rendert SVG-Miniatur mit Texturen für GM-Panel"""
        try:
            import xml.etree.ElementTree as ET
            import math
            from PIL import Image, ImageTk, ImageDraw
            
            # Prüfe ob es eine Hexagon-Map ist - dann delegiere an Hexagon-Methode
            map_data = self.projector_window.map_data
            if map_data.get("hex_size"):
                self.update_fog_map_svg_hexagon()
                return
            
            # Parse SVG
            root = ET.fromstring(self.projector_window.svg_renderer.svg_data)
            svg_width = int(root.get('width', '1000').replace('px', ''))
            svg_height = int(root.get('height', '1000').replace('px', ''))
            
            # Berechne verfügbare Größe - WARTE auf korrektes Layout
            self.fog_map_canvas.update_idletasks()
            self.update_idletasks()
            
            # Hole ECHTE Canvas-Größe
            canvas_actual_width = self.fog_map_canvas.winfo_width()
            canvas_actual_height = self.fog_map_canvas.winfo_height()
            
            # Fallback wenn Canvas noch nicht initialisiert
            if canvas_actual_width < 100 or canvas_actual_height < 100:
                canvas_actual_width = 1200
                canvas_actual_height = 800
            
            # Skaliere so, dass die Karte den verfügbaren Platz ausfüllt
            scale_x = canvas_actual_width / svg_width
            scale_y = canvas_actual_height / svg_height
            base_scale = min(scale_x, scale_y)
            
            # User-Zoom anwenden
            user_zoom = self.gm_map_zoom.get() if hasattr(self, 'gm_map_zoom') else 1.0
            scale = base_scale * user_zoom
            
            mini_width = int(svg_width * scale)
            mini_height = int(svg_height * scale)
            
            # Rendere kleines SVG
            mini_img = self.projector_window.svg_renderer.render_to_size(mini_width, mini_height, cache=False)
            
            if mini_img:
                # Fog-Overlay anwenden
                if mini_img.mode != 'RGBA':
                    mini_img = mini_img.convert('RGBA')
                
                fog_layer = Image.new('RGBA', mini_img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(fog_layer)
                
                # Tile-Größe im Mini-Bild
                tile_width = mini_width / self.projector_window.fog.width
                tile_height = mini_height / self.projector_window.fog.height
                
                # Nur Fog zeichnen (KEIN GRID - das kommt als Canvas-Overlay)
                for ty in range(self.projector_window.fog.height):
                    for tx in range(self.projector_window.fog.width):
                        x1 = int(tx * tile_width)
                        y1 = int(ty * tile_height)
                        x2 = int((tx + 1) * tile_width)
                        y2 = int((ty + 1) * tile_height)
                        
                        # Fog wenn nicht revealed
                        if not self.projector_window.fog.is_revealed(tx, ty):
                            draw.rectangle([x1, y1, x2, y2], fill=(20, 20, 20, 200))
                
                mini_img = Image.alpha_composite(mini_img, fog_layer)
                mini_img = mini_img.convert('RGB')
                
                # Auf Canvas anzeigen
                photo = ImageTk.PhotoImage(mini_img)
                self.fog_map_canvas.delete("all")  # Vorherige Inhalte löschen
                self.fog_map_canvas.create_image(0, 0, image=photo, anchor=tk.NW, tags="svg_preview")
                self.fog_map_canvas.image = photo  # Referenz behalten
                
                # Grid-Lines als Canvas-Overlay (NUR für GM-Panel, NICHT im Projektor!)
                # Diese Lines werden nur hier im GM-Control-Panel gezeichnet
                for ty in range(self.projector_window.fog.height + 1):
                    y = int(ty * tile_height)
                    self.fog_map_canvas.create_line(0, y, mini_width, y, fill='#505050', width=1, tags="grid")
                
                for tx in range(self.projector_window.fog.width + 1):
                    x = int(tx * tile_width)
                    self.fog_map_canvas.create_line(x, 0, x, mini_height, fill='#505050', width=1, tags="grid")
                
                # Scroll-Region
                self.fog_map_canvas.config(scrollregion=(0, 0, mini_width, mini_height))
                
                # Tile-Größe für Klick-Erkennung
                self.fog_map_canvas.tile_size = tile_width
                self.fog_map_canvas.mini_scale = scale
                
                # WICHTIG: Event-Bindings nach jedem Update neu setzen!
                # (gehen nach Tab-Wechsel verloren)
                self.fog_map_canvas.bind("<Button-1>", self.on_fog_map_left_click)
                self.fog_map_canvas.bind("<Button-3>", self.on_fog_map_right_click)
                self.fog_map_canvas.bind("<B1-Motion>", self.on_fog_map_drag)
                # Mittelklick für Boss-Enthüllung
                self.fog_map_canvas.bind("<Button-2>", self.on_boss_hex_click)
        
        except Exception as e:
            print(f"⚠️ Fehler beim Rendern der SVG-Miniatur: {e}")
            # Fallback: Einfache farbige Rechtecke (8px Tiles)
            self.fog_map_canvas.tile_size = 8
    
    def update_fog_map_svg_hexagon(self):
        """Rendert SVG-Miniatur MIT Hexagon-Grid für Hexagon-Maps im GM-Panel"""
        try:
            import xml.etree.ElementTree as ET
            import math
            from PIL import Image, ImageTk, ImageDraw
            
            map_data = self.projector_window.map_data
            hex_size = map_data.get("hex_size", 40)
            tiles = map_data.get("tiles", {})
            orientation = map_data.get("orientation", "pointy")
            
            # Parse SVG für Hintergrund
            root = ET.fromstring(self.projector_window.svg_renderer.svg_data)
            svg_width = int(root.get('width', '1000').replace('px', ''))
            svg_height = int(root.get('height', '1000').replace('px', ''))
            
            # Berechne verfügbare Größe - WARTE auf korrektes Layout
            self.fog_map_canvas.update_idletasks()
            self.update_idletasks()  # Warte auf Fenster-Layout
            
            # Hole ECHTE Canvas-Größe (nach Layout)
            canvas_actual_width = self.fog_map_canvas.winfo_width()
            canvas_actual_height = self.fog_map_canvas.winfo_height()
            
            # Fallback wenn Canvas noch nicht initialisiert
            if canvas_actual_width < 100 or canvas_actual_height < 100:
                canvas_actual_width = 1200
                canvas_actual_height = 800
            
            # KEINE künstliche Begrenzung - nutze vollen verfügbaren Platz!
            # Skaliere so, dass die Karte den verfügbaren Platz ausfüllt
            scale_x = canvas_actual_width / svg_width
            scale_y = canvas_actual_height / svg_height
            base_scale = min(scale_x, scale_y)  # Aspect Ratio beibehalten
            
            # User-Zoom anwenden
            user_zoom = self.gm_map_zoom.get() if hasattr(self, 'gm_map_zoom') else 1.0
            scale = base_scale * user_zoom
            
            mini_width = int(svg_width * scale)
            mini_height = int(svg_height * scale)
            
            print(f"🗺️ GM-Panel SVG Hexagon: Original={svg_width}x{svg_height}, Canvas={canvas_actual_width}x{canvas_actual_height}, Scale={scale:.2f}, Render={mini_width}x{mini_height}")
            
            # Rendere SVG-Hintergrund
            mini_img = self.projector_window.svg_renderer.render_to_size(mini_width, mini_height, cache=False)
            
            if not mini_img:
                return
            
            # Konvertiere zu RGBA
            if mini_img.mode != 'RGBA':
                mini_img = mini_img.convert('RGBA')
            
            # Berechne Hexagon-Bounding-Box
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')
            
            for key, tile_data in tiles.items():
                if isinstance(tile_data, dict):
                    cx = tile_data.get("center_x", 0)
                    cy = tile_data.get("center_y", 0)
                else:
                    parts = key.split(",")
                    if len(parts) == 2:
                        q, r = int(parts[0]), int(parts[1])
                        if orientation == "pointy":
                            cx = hex_size * 1.5 * q
                            cy = hex_size * math.sqrt(3) * (r + q / 2)
                        else:
                            cx = hex_size * math.sqrt(3) * (q + r / 2)
                            cy = hex_size * 1.5 * r
                    else:
                        continue
                
                min_x = min(min_x, cx)
                min_y = min(min_y, cy)
                max_x = max(max_x, cx)
                max_y = max(max_y, cy)
            
            # Berechne Hex-Skalierung auf SVG-Größe
            hex_map_width = max_x - min_x + hex_size * 2 if tiles else svg_width
            hex_map_height = max_y - min_y + hex_size * 2 if tiles else svg_height
            
            hex_scale_x = svg_width / hex_map_width if hex_map_width > 0 else 1.0
            hex_scale_y = svg_height / hex_map_height if hex_map_height > 0 else 1.0
            hex_scale = min(hex_scale_x, hex_scale_y)
            
            # Finale Skalierung für Mini-Darstellung
            final_scale = scale
            mini_hex_size = hex_size * hex_scale * final_scale
            
            # Offset zum Zentrieren der Hexagone auf dem SVG
            offset_x = (hex_size - min_x) * hex_scale * final_scale if tiles else 0
            offset_y = (hex_size - min_y) * hex_scale * final_scale if tiles else 0
            
            # Speichere Hexagon-Daten für Klick-Handler
            self.fog_map_canvas.hex_tiles = {}
            self.fog_map_canvas.hex_size = mini_hex_size
            self.fog_map_canvas.hex_scale = final_scale
            self.fog_map_canvas.hex_offset_x = offset_x
            self.fog_map_canvas.hex_offset_y = offset_y
            self.fog_map_canvas.is_hexagon_mode = True
            
            # Auf Canvas anzeigen
            photo = ImageTk.PhotoImage(mini_img.convert('RGB'))
            self.fog_map_canvas.delete("all")
            self.fog_map_canvas.create_image(0, 0, image=photo, anchor=tk.NW, tags="svg_preview")
            self.fog_map_canvas.image = photo
            
            # Terrain-Farben
            terrain_colors = {
                "PLAINS": "#6ba868",
                "DARK_FOREST": "#2d4a2d",
                "FOREST": "#3d6b3d",
                "MOUNTAINS": "#8a8a8a",
                "WATER": "#4db8c4",
                "SWAMP": "#5a7a5a",
                "HILLS": "#9a9a6a",
                "ROAD": "#8a7f6f",
                "VILLAGE": "#b8956f",
                "default": "#4a4a4a"
            }
            
            # Zeichne jedes Hexagon als Canvas-Polygon
            for key, tile_data in tiles.items():
                if isinstance(tile_data, dict):
                    terrain = tile_data.get("terrain", "PLAINS")
                    cx = tile_data.get("center_x", 0)
                    cy = tile_data.get("center_y", 0)
                else:
                    terrain = tile_data if isinstance(tile_data, str) else "PLAINS"
                    parts = key.split(",")
                    if len(parts) == 2:
                        q, r = int(parts[0]), int(parts[1])
                        if orientation == "pointy":
                            cx = hex_size * 1.5 * q
                            cy = hex_size * math.sqrt(3) * (r + q / 2)
                        else:
                            cx = hex_size * math.sqrt(3) * (q + r / 2)
                            cy = hex_size * 1.5 * r
                    else:
                        continue
                
                # Skalierte Koordinaten
                scaled_cx = cx * hex_scale * final_scale + offset_x
                scaled_cy = cy * hex_scale * final_scale + offset_y
                
                # Hexagon-Punkte berechnen
                points = []
                for i in range(6):
                    if orientation == "pointy":
                        angle = math.pi / 3 * i - math.pi / 6
                    else:
                        angle = math.pi / 3 * i
                    px = scaled_cx + mini_hex_size * 0.9 * math.cos(angle)
                    py = scaled_cy + mini_hex_size * 0.9 * math.sin(angle)
                    points.append((px, py))
                
                # Prüfe Fog-Status (basierend auf Hexagon-Position im Fog-Grid)
                fog_x = int((scaled_cx / mini_width) * self.projector_window.fog.width) if mini_width > 0 else 0
                fog_y = int((scaled_cy / mini_height) * self.projector_window.fog.height) if mini_height > 0 else 0
                fog_x = max(0, min(fog_x, self.projector_window.fog.width - 1))
                fog_y = max(0, min(fog_y, self.projector_window.fog.height - 1))
                
                is_revealed = self.projector_window.fog.is_revealed(fog_x, fog_y)
                
                # Farbe basierend auf Fog-Status
                if is_revealed:
                    fill_color = ""  # Transparent - zeigt Hintergrundbild
                    outline_color = "#606060"  # Hellerer Rand für sichtbare Bereiche
                else:
                    fill_color = "#1a1a1a"  # Dunkel für verdeckte Bereiche
                    outline_color = "#303030"
                
                # Zeichne Hexagon
                hex_id = self.fog_map_canvas.create_polygon(
                    points, fill=fill_color, outline=outline_color, width=2,
                    tags=f"hex_{key}",
                    stipple="gray50" if not is_revealed else ""
                )
                
                # Speichere für Klick-Erkennung
                self.fog_map_canvas.hex_tiles[key] = {
                    "id": hex_id,
                    "center": (scaled_cx, scaled_cy),
                    "terrain": terrain,
                    "fog_x": fog_x,
                    "fog_y": fog_y
                }
            
            # Boss-Markierungen zeichnen
            self._draw_boss_hexagon_markers_svg(map_data, scale, mini_width, mini_height)
            
            # Scroll-Region
            self.fog_map_canvas.config(scrollregion=(0, 0, mini_width, mini_height))
            
            # Tile-Größe für Fallback-Klick-Erkennung
            self.fog_map_canvas.tile_size = mini_hex_size
            self.fog_map_canvas.mini_scale = scale
            
            # Event-Bindings
            self.fog_map_canvas.bind("<Button-1>", self.on_fog_map_left_click)
            self.fog_map_canvas.bind("<Button-3>", self.on_fog_map_right_click)
            self.fog_map_canvas.bind("<B1-Motion>", self.on_fog_map_drag)
            self.fog_map_canvas.bind("<Button-2>", self.on_boss_hex_click)
            
            print(f"🗺️ GM-Panel: Hexagon-SVG-Map gerendert mit {len(tiles)} Hexagonen")
        
        except Exception as e:
            import traceback
            print(f"⚠️ Fehler beim Rendern der Hexagon-SVG-Miniatur: {e}")
            traceback.print_exc()
            self.fog_map_canvas.tile_size = 8
    
    def update_fog_map_hexagon(self):
        """Zeichnet die interaktive Fog-Karte für Hexagon-Maps"""
        import math
        
        map_data = self.projector_window.map_data
        hex_size = map_data.get("hex_size", 40)
        tiles = map_data.get("tiles", {})
        orientation = map_data.get("orientation", "pointy")
        
        # Debug: Zeige Tile-Struktur
        if tiles:
            first_key = next(iter(tiles))
            first_val = tiles[first_key]
            is_boss_check = first_val.get("is_boss_hex", "NO KEY") if isinstance(first_val, dict) else "NOT DICT"
            print(f"🗺️ GM Hexagon Map: {len(tiles)} tiles, Typ={type(first_val).__name__}, is_boss_hex={is_boss_check}")
        
        # Terrain-Farben (passend zu Hexagon-Map-Terrain-Typen)
        terrain_colors = {
            "PLAINS": "#6ba868",
            "DARK_FOREST": "#2d4a2d",
            "FOREST": "#3d6b3d",
            "MOUNTAINS": "#8a8a8a",
            "WATER": "#4db8c4",
            "SWAMP": "#5a7a5a",
            "HILLS": "#9a9a6a",
            "ROAD": "#8a7f6f",
            "VILLAGE": "#b8956f",
            "default": "#4a4a4a"
        }
        
        if not tiles:
            return
        
        # Berechne Bounding-Box der Hexagone
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for key, tile_data in tiles.items():
            if isinstance(tile_data, dict):
                cx = tile_data.get("center_x", 0)
                cy = tile_data.get("center_y", 0)
            else:
                # Fallback: Koordinaten aus Key berechnen
                parts = key.split(",")
                if len(parts) == 2:
                    q, r = int(parts[0]), int(parts[1])
                    if orientation == "pointy":
                        cx = hex_size * 1.5 * q
                        cy = hex_size * math.sqrt(3) * (r + q / 2)
                    else:
                        cx = hex_size * math.sqrt(3) * (q + r / 2)
                        cy = hex_size * 1.5 * r
                else:
                    continue
            
            min_x = min(min_x, cx)
            min_y = min(min_y, cy)
            max_x = max(max_x, cx)
            max_y = max(max_y, cy)
        
        # Skalierung für GM-Panel (passe Hexagon-Größe an Canvas-Größe an)
        map_width = max_x - min_x + hex_size * 2
        map_height = max_y - min_y + hex_size * 2
        
        # Hole ECHTE Canvas-Größe - warte auf Layout
        self.fog_map_canvas.update_idletasks()
        self.update_idletasks()
        
        canvas_actual_width = self.fog_map_canvas.winfo_width()
        canvas_actual_height = self.fog_map_canvas.winfo_height()
        
        # Fallback wenn Canvas noch nicht initialisiert
        if canvas_actual_width < 100 or canvas_actual_height < 100:
            canvas_actual_width = 1200
            canvas_actual_height = 800
        
        # Skaliere so, dass die Karte den verfügbaren Platz ausfüllt
        scale_x = canvas_actual_width / map_width if map_width > 0 else 1.0
        scale_y = canvas_actual_height / map_height if map_height > 0 else 1.0
        base_scale = min(scale_x, scale_y)  # Keine künstliche Begrenzung!
        
        # User-Zoom anwenden
        user_zoom = self.gm_map_zoom.get() if hasattr(self, 'gm_map_zoom') else 1.0
        scale = base_scale * user_zoom
        
        mini_hex_size = hex_size * scale
        canvas_width = int(map_width * scale)
        canvas_height = int(map_height * scale)
        
        # Offset zum Zentrieren
        offset_x = (hex_size - min_x) * scale
        offset_y = (hex_size - min_y) * scale
        
        # Speichere Hexagon-Daten für Klick-Handler
        self.fog_map_canvas.hex_tiles = {}
        self.fog_map_canvas.hex_size = mini_hex_size
        self.fog_map_canvas.hex_scale = scale
        self.fog_map_canvas.hex_offset_x = offset_x
        self.fog_map_canvas.hex_offset_y = offset_y
        self.fog_map_canvas.is_hexagon_mode = True
        
        # Zeichne jedes Hexagon
        for key, tile_data in tiles.items():
            if isinstance(tile_data, dict):
                terrain = tile_data.get("terrain", "PLAINS")
                cx = tile_data.get("center_x", 0)
                cy = tile_data.get("center_y", 0)
            else:
                terrain = tile_data if isinstance(tile_data, str) else "PLAINS"
                parts = key.split(",")
                if len(parts) == 2:
                    q, r = int(parts[0]), int(parts[1])
                    if orientation == "pointy":
                        cx = hex_size * 1.5 * q
                        cy = hex_size * math.sqrt(3) * (r + q / 2)
                    else:
                        cx = hex_size * math.sqrt(3) * (q + r / 2)
                        cy = hex_size * 1.5 * r
                else:
                    continue
            
            # Skalierte Koordinaten
            scaled_cx = cx * scale + offset_x
            scaled_cy = cy * scale + offset_y
            
            # Terrain-Farbe
            color = terrain_colors.get(terrain, terrain_colors["default"])
            
            # Hexagon-Punkte berechnen
            points = []
            for i in range(6):
                if orientation == "pointy":
                    angle = math.pi / 3 * i - math.pi / 6
                else:
                    angle = math.pi / 3 * i
                px = scaled_cx + mini_hex_size * 0.9 * math.cos(angle)
                py = scaled_cy + mini_hex_size * 0.9 * math.sin(angle)
                points.append((px, py))
            
            # Zeichne Hexagon
            hex_id = self.fog_map_canvas.create_polygon(
                points, fill=color, outline="#303030", width=1, tags=f"hex_{key}"
            )
            
            # Speichere für Klick-Erkennung
            self.fog_map_canvas.hex_tiles[key] = {
                "id": hex_id,
                "center": (scaled_cx, scaled_cy),
                "terrain": terrain
            }
        
        # Fog-Overlay für verdeckte Bereiche
        # (Hexagon-Maps nutzen das Fog-System des Projektors)
        if hasattr(self.projector_window, 'fog') and self.projector_window.fog:
            fog_revealed = self.projector_window.fog.revealed  # numpy array, True=sichtbar
            fog_width = self.projector_window.fog.width
            fog_height = self.projector_window.fog.height
            
            for key, tile_info in self.fog_map_canvas.hex_tiles.items():
                cx, cy = tile_info["center"]
                
                # Berechne Fog-Grid-Position (approximativ)
                fog_x = int((cx / canvas_width) * fog_width) if canvas_width > 0 else 0
                fog_y = int((cy / canvas_height) * fog_height) if canvas_height > 0 else 0
                fog_x = max(0, min(fog_x, fog_width - 1))
                fog_y = max(0, min(fog_y, fog_height - 1))
                
                # revealed ist numpy array: True = sichtbar, False = Nebel
                if not fog_revealed[fog_y, fog_x]:  # Verdeckt (nicht revealed)
                    # Zeichne dunkles Overlay
                    self.fog_map_canvas.itemconfig(
                        tile_info["id"], 
                        fill="#1a1a1a",
                        stipple="gray50"
                    )
        
        # === BOSS-HEXAGONE MARKIEREN ===
        # Zeige Boss-Hexagone mit orangem Rand an
        self._draw_boss_hexagon_markers(tiles, scale, offset_x, offset_y, mini_hex_size, orientation, hex_size)
        
        # Scroll-Region setzen
        self.fog_map_canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Event-Bindings
        self.fog_map_canvas.bind("<Button-1>", self.on_fog_map_left_click)
        self.fog_map_canvas.bind("<Button-3>", self.on_fog_map_right_click)
        self.fog_map_canvas.bind("<B1-Motion>", self.on_fog_map_drag)
        # Mittelklick für Boss-Enthüllung
        self.fog_map_canvas.bind("<Button-2>", self.on_boss_hex_click)
    
    def _draw_boss_hexagon_markers(self, tiles, scale, offset_x, offset_y, mini_hex_size, orientation, hex_size):
        """Zeichnet orangene Markierungen für Boss-Hexagone"""
        import math
        
        boss_hex_count = 0
        for key, tile_data in tiles.items():
            if not isinstance(tile_data, dict):
                continue
                
            is_boss_hex = tile_data.get("is_boss_hex", False)
            if not is_boss_hex:
                continue
            
            boss_hex_count += 1
            
            # Berechne Koordinaten
            cx = tile_data.get("center_x", 0)
            cy = tile_data.get("center_y", 0)
            scaled_cx = cx * scale + offset_x
            scaled_cy = cy * scale + offset_y
            
            # Prüfe ob Boss bereits enthüllt
            is_revealed = False
            boss_placed = False
            if hasattr(self, 'projector_window') and self.projector_window:
                if hasattr(self.projector_window, 'boss_manager'):
                    parts = key.split(",")
                    if len(parts) == 2:
                        q, r = int(parts[0]), int(parts[1])
                        for placement in self.projector_window.boss_manager.placements:
                            if placement.hex_q == q and placement.hex_r == r:
                                boss_placed = True
                                is_revealed = placement.revealed
                                break
            
            # Farbe basierend auf Status
            if is_revealed:
                outline_color = "#ff0000"  # Rot = Enthüllt (Boss sichtbar)
                fill_stipple = ""
            elif boss_placed:
                outline_color = "#ff8800"  # Orange = Boss vorhanden, nicht enthüllt
                fill_stipple = ""
            else:
                outline_color = "#ffaa00"  # Gelb-Orange = Boss-Hex ohne Boss
                fill_stipple = "gray25"
            
            # Hexagon-Punkte für Rahmen
            points = []
            for i in range(6):
                if orientation == "pointy":
                    angle = math.pi / 3 * i - math.pi / 6
                else:
                    angle = math.pi / 3 * i
                px = scaled_cx + mini_hex_size * 0.85 * math.cos(angle)
                py = scaled_cy + mini_hex_size * 0.85 * math.sin(angle)
                points.append((px, py))
            
            # Zeichne Boss-Markierung (nur Umriss)
            self.fog_map_canvas.create_polygon(
                points, fill="", outline=outline_color, width=3, 
                tags=f"boss_marker_{key}"
            )
            
            # Zeichne kleines Boss-Icon in der Mitte
            icon = "🐉" if boss_placed else "❓"
            if is_revealed:
                # Zeige Boss-Name wenn enthüllt
                for placement in self.projector_window.boss_manager.placements:
                    parts = key.split(",")
                    if len(parts) == 2:
                        q, r = int(parts[0]), int(parts[1])
                        if placement.hex_q == q and placement.hex_r == r:
                            boss = self.projector_window.boss_manager.get_boss(placement.boss_id)
                            if boss:
                                icon = "💀" if boss.is_defeated else "🐉"
            
            self.fog_map_canvas.create_text(
                scaled_cx, scaled_cy, text=icon, 
                font=("Arial", max(8, int(mini_hex_size * 0.5))),
                fill="white", tags=f"boss_icon_{key}"
            )
        
        # Debug-Ausgabe
        if boss_hex_count > 0:
            print(f"🗺️ GM-Panel: {boss_hex_count} Boss-Hexagone markiert")
        else:
            # Prüfe warum keine Boss-Hexagone gefunden wurden
            dict_count = sum(1 for t in tiles.values() if isinstance(t, dict))
            print(f"⚠️ GM-Panel: Keine Boss-Hexagone! ({dict_count} dict-tiles von {len(tiles)})")
    
    def _draw_boss_hexagon_markers_svg(self, map_data, scale, canvas_width, canvas_height):
        """Zeichnet Boss-Hexagon-Markierungen für SVG-Maps mit Hexagon-Overlay"""
        import math
        
        hex_size = map_data.get("hex_size", 40)
        tiles = map_data.get("tiles", {})
        orientation = map_data.get("orientation", "pointy")
        
        if not tiles:
            print("⚠️ GM-Panel SVG: Keine Tiles vorhanden")
            return
        
        # Berechne Bounding-Box der Hexagone
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for key, tile_data in tiles.items():
            if isinstance(tile_data, dict):
                cx = tile_data.get("center_x", 0)
                cy = tile_data.get("center_y", 0)
            else:
                parts = key.split(",")
                if len(parts) == 2:
                    q, r = int(parts[0]), int(parts[1])
                    if orientation == "pointy":
                        cx = hex_size * 1.5 * q
                        cy = hex_size * math.sqrt(3) * (r + q / 2)
                    else:
                        cx = hex_size * math.sqrt(3) * (q + r / 2)
                        cy = hex_size * 1.5 * r
                else:
                    continue
            
            min_x = min(min_x, cx)
            min_y = min(min_y, cy)
            max_x = max(max_x, cx)
            max_y = max(max_y, cy)
        
        # Berechne Skalierung und Offset für Hexagon-Overlay
        map_width = max_x - min_x + hex_size * 2
        map_height = max_y - min_y + hex_size * 2
        
        # Skalierung passend zur Canvas-Größe
        hex_scale = min(canvas_width / map_width, canvas_height / map_height) if map_width > 0 and map_height > 0 else 1.0
        mini_hex_size = hex_size * hex_scale
        
        # Offset zum Zentrieren
        offset_x = (hex_size - min_x) * hex_scale
        offset_y = (hex_size - min_y) * hex_scale
        
        # Speichere Hexagon-Daten für Klick-Handler
        self.fog_map_canvas.hex_tiles = {}
        self.fog_map_canvas.hex_size = mini_hex_size
        self.fog_map_canvas.hex_scale = hex_scale
        self.fog_map_canvas.hex_offset_x = offset_x
        self.fog_map_canvas.hex_offset_y = offset_y
        self.fog_map_canvas.is_hexagon_mode = True
        
        boss_hex_count = 0
        
        # Zeichne nur Boss-Hexagone
        for key, tile_data in tiles.items():
            if not isinstance(tile_data, dict):
                continue
            
            # Speichere alle Hexagone für Klick-Erkennung
            cx = tile_data.get("center_x", 0)
            cy = tile_data.get("center_y", 0)
            scaled_cx = cx * hex_scale + offset_x
            scaled_cy = cy * hex_scale + offset_y
            
            self.fog_map_canvas.hex_tiles[key] = {
                "center": (scaled_cx, scaled_cy),
                "terrain": tile_data.get("terrain", "PLAINS")
            }
            
            is_boss_hex = tile_data.get("is_boss_hex", False)
            if not is_boss_hex:
                continue
            
            boss_hex_count += 1
            
            # Extrahiere Koordinaten
            parts = key.split(",")
            q, r = 0, 0
            if len(parts) == 2:
                q, r = int(parts[0]), int(parts[1])
            
            # Prüfe ob Boss-Hex bereits enthüllt wurde (unabhängig von Boss-Definition)
            is_revealed = False
            boss_placed = False
            has_boss_definition = False
            
            if hasattr(self, 'projector_window') and self.projector_window:
                # Prüfe revealed_boss_hexes (Mittelklick-Enthüllung)
                if hasattr(self.projector_window, 'revealed_boss_hexes'):
                    is_revealed = (q, r) in self.projector_window.revealed_boss_hexes
                
                # Prüfe ob ein Boss hier platziert ist
                if hasattr(self.projector_window, 'boss_manager'):
                    for placement in self.projector_window.boss_manager.placements:
                        if placement.hex_q == q and placement.hex_r == r:
                            boss_placed = True
                            has_boss_definition = True
                            is_revealed = is_revealed or placement.revealed
                            break
            
            # Farbe basierend auf Status - deutlichere Unterscheidung
            # Tkinter unterstützt kein Alpha, daher stipple für Transparenz-Effekt
            if is_revealed:
                if boss_placed:
                    outline_color = "#ff0000"  # Rot = Enthüllt MIT Boss
                    fill_color = "#ff4444"  # Roter Hintergrund
                    use_stipple = True
                else:
                    outline_color = "#00ff00"  # Grün = Enthüllt, KEIN Boss
                    fill_color = "#44ff44"  # Grüner Hintergrund
                    use_stipple = True
            elif boss_placed:
                outline_color = "#ff8800"  # Orange = Boss vorhanden, nicht enthüllt
                fill_color = ""
                use_stipple = False
            else:
                outline_color = "#ffaa00"  # Gelb-Orange = Boss-Hex, unbekannt
                fill_color = ""
                use_stipple = False
            
            # Hexagon-Punkte für Rahmen
            points = []
            for i in range(6):
                if orientation == "pointy":
                    angle = math.pi / 3 * i - math.pi / 6
                else:
                    angle = math.pi / 3 * i
                px = scaled_cx + mini_hex_size * 0.85 * math.cos(angle)
                py = scaled_cy + mini_hex_size * 0.85 * math.sin(angle)
                points.append((px, py))
            
            # Zeichne Boss-Markierung (mit Füllung wenn enthüllt)
            if fill_color and use_stipple:
                self.fog_map_canvas.create_polygon(
                    points, fill=fill_color, outline=outline_color, width=3, 
                    stipple="gray50", tags=f"boss_marker_{key}"
                )
            else:
                self.fog_map_canvas.create_polygon(
                    points, fill="", outline=outline_color, width=3, 
                    tags=f"boss_marker_{key}"
                )
            
            # Zeichne Icon basierend auf Status
            if is_revealed:
                if boss_placed:
                    icon = "🐉"  # Boss war hier!
                    # Prüfe ob besiegt
                    if hasattr(self.projector_window, 'boss_manager'):
                        for placement in self.projector_window.boss_manager.placements:
                            if placement.hex_q == q and placement.hex_r == r:
                                boss = self.projector_window.boss_manager.get_boss(placement.boss_id)
                                if boss and boss.is_defeated:
                                    icon = "💀"
                                break
                else:
                    icon = "✓"  # Enthüllt, kein Boss
            else:
                icon = "❓"  # Noch nicht enthüllt
            
            self.fog_map_canvas.create_text(
                scaled_cx, scaled_cy, text=icon, 
                font=("Arial", max(10, int(mini_hex_size * 0.5))),
                fill="white", tags=f"boss_icon_{key}"
            )
        
        if boss_hex_count > 0:
            print(f"🗺️ GM-Panel SVG: {boss_hex_count} Boss-Hexagone markiert")
        else:
            dict_count = sum(1 for t in tiles.values() if isinstance(t, dict))
            boss_count = sum(1 for t in tiles.values() if isinstance(t, dict) and t.get("is_boss_hex", False))
            print(f"⚠️ GM-Panel SVG: Keine Boss-Hexagone gefunden! ({boss_count} von {dict_count} dict-tiles)")
    
    def on_boss_hex_click(self, event):
        """Mittelklick auf Boss-Hexagon = Boss enthüllen/verbergen"""
        import math
        
        if not hasattr(self, 'fog_map_canvas') or not hasattr(self.fog_map_canvas, 'hex_tiles'):
            return
        
        # Canvas-Koordinaten mit Scrolling
        canvas_x = self.fog_map_canvas.canvasx(event.x)
        canvas_y = self.fog_map_canvas.canvasy(event.y)
        
        hex_tiles = self.fog_map_canvas.hex_tiles
        hex_size = self.fog_map_canvas.hex_size
        
        # Finde das nächste Hexagon zum Klickpunkt
        closest_hex = None
        closest_dist = float('inf')
        
        for key, tile_info in hex_tiles.items():
            cx, cy = tile_info["center"]
            dist = math.sqrt((canvas_x - cx)**2 + (canvas_y - cy)**2)
            if dist < closest_dist and dist < hex_size * 1.2:
                closest_dist = dist
                closest_hex = key
        
        if not closest_hex:
            return
        
        # Prüfe ob es ein Boss-Hexagon ist
        map_data = self.projector_window.map_data
        tiles = map_data.get("tiles", {})
        tile_data = tiles.get(closest_hex, {})
        
        if not isinstance(tile_data, dict):
            self._set_status("❌ Kein Boss-Hexagon")
            return
        
        if not tile_data.get("is_boss_hex", False):
            self._set_status("❌ Kein Boss-Hexagon")
            return
        
        # Extrahiere Koordinaten
        parts = closest_hex.split(",")
        if len(parts) != 2:
            return
        q, r = int(parts[0]), int(parts[1])
        
        # Prüfe ob bereits enthüllt
        if hasattr(self.projector_window, 'revealed_boss_hexes'):
            if (q, r) in self.projector_window.revealed_boss_hexes:
                self._set_status("ℹ️ Bereits enthüllt")
                return
        
        # Boss-Hexagon enthüllen
        if hasattr(self.projector_window, 'boss_manager'):
            # Prüfe ob ein Boss hier platziert ist
            has_boss = False
            boss = None
            
            for placement in self.projector_window.boss_manager.placements:
                if placement.hex_q == q and placement.hex_r == r:
                    has_boss = True
                    if not placement.revealed:
                        boss = self.projector_window.boss_manager.reveal_boss_at_hex(q, r)
                    else:
                        # Bereits enthüllt, hole Boss-Info
                        boss = self.projector_window.boss_manager.get_boss(placement.boss_id)
                    break
            
            # Markiere das Hex als enthüllt (mit oder ohne Boss)
            if hasattr(self.projector_window, 'mark_boss_hex_revealed'):
                self.projector_window.mark_boss_hex_revealed(q, r, has_boss)
            
            # Status-Meldung mit Boss-Details
            if boss:
                hp_text = f"{boss.current_health}/{boss.max_health} HP"
                self._set_status(f"🐉 BOSS: {boss.name} ({hp_text})")
                # Boss zu revealed_bosses hinzufügen
                if not hasattr(self.projector_window, 'revealed_bosses'):
                    self.projector_window.revealed_bosses = {}
                self.projector_window.revealed_bosses[(q, r)] = boss
                
                # ═══════════════════════════════════════════════════════════
                # PRÜFE OB ALLE BOSSE ENTHÜLLT - wenn ja, restliche Hexe als leer markieren
                # ═══════════════════════════════════════════════════════════
                self._check_all_bosses_revealed()
            else:
                self._set_status("✨ Kein Boss hier!")
            
            # Karte und Boss-Panel aktualisieren
            self.projector_window.render_map()
            if hasattr(self, 'boss_control_panel'):
                self.boss_control_panel.refresh()
            self.update_fog_map()  # Verwendet SVG wenn verfügbar
    
    def _check_all_bosses_revealed(self):
        """
        Prüft ob alle Bosse enthüllt wurden.
        Wenn ja, markiert alle restlichen Boss-Hexagone als 'kein Boss'.
        """
        if not hasattr(self.projector_window, 'boss_manager'):
            return
        
        boss_manager = self.projector_window.boss_manager
        
        # Zähle definierte Bosse und enthüllte Bosse
        total_bosses = len(boss_manager.placements)
        revealed_bosses = sum(1 for p in boss_manager.placements if p.revealed)
        
        if total_bosses == 0:
            return
        
        # Wenn alle Bosse enthüllt wurden
        if revealed_bosses >= total_bosses:
            print(f"🎉 ALLE {total_bosses} BOSSE ENTHÜLLT! Restliche Hexagone werden markiert...")
            
            # Sammle alle Boss-Hexagone
            map_data = self.projector_window.map_data
            tiles = map_data.get("tiles", {})
            
            # Markiere alle nicht-enthüllten Boss-Hexagone als "kein Boss"
            for key, tile_data in tiles.items():
                if not isinstance(tile_data, dict):
                    continue
                if not tile_data.get("is_boss_hex", False):
                    continue
                
                parts = key.split(",")
                if len(parts) != 2:
                    continue
                q, r = int(parts[0]), int(parts[1])
                
                # Wenn noch nicht enthüllt, als "leer" markieren
                if (q, r) not in self.projector_window.revealed_boss_hexes:
                    self.projector_window.mark_boss_hex_revealed(q, r, has_boss=False)
            
            self._set_status(f"🎉 Alle {total_bosses} Bosse gefunden! Restliche Hexe sind leer.")

    def on_fog_map_left_click(self, event):
        """Linksklick auf Karte = Bereich enthüllen"""
        self._fog_map_click(event, reveal=True)
    
    def on_fog_map_right_click(self, event):
        """Rechtsklick auf Karte = Bereich verbergen"""
        self._fog_map_click(event, reveal=False)
    
    def on_fog_map_drag(self, event):
        """Ziehen mit Maus = Mehrere Tiles enthüllen"""
        self._fog_map_click(event, reveal=True)
    
    def _fog_map_click(self, event, reveal=True):
        """Verarbeitet Klick auf Fog-Karte"""
        if not self.projector_window or not hasattr(self, 'fog_map_canvas'):
            return
        
        # WICHTIG: Bei scrollbaren Canvas ist event.x/y relativ zum sichtbaren Bereich
        # canvasx/canvasy konvertieren zur absoluten Position im Canvas
        canvas_x = self.fog_map_canvas.canvasx(event.x)
        canvas_y = self.fog_map_canvas.canvasy(event.y)
        
        # Hexagon-Modus: Finde geklicktes Hexagon
        if getattr(self.fog_map_canvas, 'is_hexagon_mode', False):
            self._fog_map_click_hexagon(canvas_x, canvas_y, reveal)
            return
        
        # Map-Dimensionen
        map_width = self.projector_window.fog.width
        map_height = self.projector_window.fog.height
        
        # SVG-Modus: Berechne Tile-Koordinaten basierend auf Canvas-Größe
        if self.projector_window.is_svg_mode:
            # Hole Canvas-Scrollregion (die tatsächliche Bildgröße)
            scrollregion = self.fog_map_canvas.cget('scrollregion')
            if scrollregion:
                coords = [float(x) for x in scrollregion.split()]
                canvas_width = coords[2] - coords[0]
                canvas_height = coords[3] - coords[1]
            else:
                canvas_width = self.fog_map_canvas.winfo_width()
                canvas_height = self.fog_map_canvas.winfo_height()
            
            # Tile-Koordinaten berechnen (Canvas-Pixel → Grid-Koordinaten)
            tile_x = int((canvas_x / canvas_width) * map_width)
            tile_y = int((canvas_y / canvas_height) * map_height)
        else:
            # JSON-Modus: Tile-Größe verwenden (war 8px, jetzt 16px)
            tile_size = getattr(self.fog_map_canvas, 'tile_size', 16)
            tile_x = int(canvas_x / tile_size)
            tile_y = int(canvas_y / tile_size)
        
        # Bounds-Check
        tile_x = max(0, min(tile_x, map_width - 1))
        tile_y = max(0, min(tile_y, map_height - 1))
        
        # Brush-Größe
        brush_size = self.fog_brush_size.get()
        
        # Bereich berechnen
        x1 = max(0, tile_x - brush_size // 2)
        y1 = max(0, tile_y - brush_size // 2)
        x2 = min(map_width - 1, tile_x + brush_size // 2)
        y2 = min(map_height - 1, tile_y + brush_size // 2)
        
        # Fog updaten (Boss-System ist NICHT an Fog gekoppelt)
        if reveal:
            self.projector_window.fog.reveal_area(x1, y1, x2, y2)
        else:
            self.projector_window.fog.hide_area(x1, y1, x2, y2)
        
        # Projektor-Karte neu rendern
        self.projector_window.render_map()
        
        # Eigene Karte lokal updaten (schneller)
        self._update_fog_tiles_local(x1, y1, x2, y2, reveal)
    
    def _fog_map_click_hexagon(self, canvas_x, canvas_y, reveal):
        """Verarbeitet Klick auf Hexagon-Fog-Karte"""
        import math
        
        hex_tiles = getattr(self.fog_map_canvas, 'hex_tiles', {})
        hex_size = getattr(self.fog_map_canvas, 'hex_size', 20)
        
        if not hex_tiles:
            return
        
        # Finde das nächste Hexagon zum Klickpunkt
        closest_hex = None
        closest_dist = float('inf')
        
        for key, tile_info in hex_tiles.items():
            cx, cy = tile_info["center"]
            dist = math.sqrt((canvas_x - cx)**2 + (canvas_y - cy)**2)
            if dist < closest_dist and dist < hex_size * 1.2:
                closest_dist = dist
                closest_hex = key
        
        if not closest_hex:
            return
        
        # Berechne Fog-Grid-Position für dieses Hexagon
        tile_info = hex_tiles[closest_hex]
        cx, cy = tile_info["center"]
        
        # Hole Canvas-Scrollregion (die tatsächliche Bildgröße)
        scrollregion = self.fog_map_canvas.cget('scrollregion')
        if scrollregion:
            coords = [float(x) for x in scrollregion.split()]
            canvas_width = coords[2] - coords[0]
            canvas_height = coords[3] - coords[1]
        else:
            canvas_width = self.fog_map_canvas.winfo_width()
            canvas_height = self.fog_map_canvas.winfo_height()
        
        # Map-Dimensionen (Fog-Grid)
        map_width = self.projector_window.fog.width
        map_height = self.projector_window.fog.height
        
        # Berechne Fog-Grid-Position
        tile_x = int((cx / canvas_width) * map_width) if canvas_width > 0 else 0
        tile_y = int((cy / canvas_height) * map_height) if canvas_height > 0 else 0
        tile_x = max(0, min(tile_x, map_width - 1))
        tile_y = max(0, min(tile_y, map_height - 1))
        
        # Brush-Größe (für Hexagone etwas größeren Bereich)
        brush_size = self.fog_brush_size.get()
        
        # Bereich berechnen (Hexagon-angepasst)
        x1 = max(0, tile_x - brush_size)
        y1 = max(0, tile_y - brush_size)
        x2 = min(map_width - 1, tile_x + brush_size)
        y2 = min(map_height - 1, tile_y + brush_size)
        
        # Fog updaten
        if reveal:
            self.projector_window.fog.reveal_area(x1, y1, x2, y2)
        else:
            self.projector_window.fog.hide_area(x1, y1, x2, y2)
        
        # Projektor-Karte neu rendern
        self.projector_window.render_map()
        
        # GM-Karte aktualisieren (verwendet SVG wenn verfügbar)
        self.update_fog_map()

    def _update_fog_tiles_local(self, x1, y1, x2, y2, reveal):
        """Updatet nur die geänderten Tiles lokal (Performance)"""
        if not hasattr(self, 'fog_map_canvas'):
            return
        
        # Bei Hexagon-Mode: Komplettes Neu-Rendering (verwendet SVG wenn verfügbar)
        if getattr(self.fog_map_canvas, 'is_hexagon_mode', False):
            self.update_fog_map()
            return
        
        # Bei SVG-Mode: Komplettes Neu-Rendering nötig (kein Tile-basiertes Canvas)
        if self.projector_window.is_svg_mode:
            self.update_fog_map_svg()
            return
        
        # JSON-Mode: Nur geänderte Tiles updaten
        map_data = self.projector_window.map_data
        tiles = map_data.get("tiles", [])
        
        terrain_colors = {
            "grass": "#6ba868",
            "water": "#4db8c4",
            "water_h": "#4db8c4",
            "water_v": "#4db8c4",
            "mountain": "#8a8a8a",
            "forest": "#3d6b3d",
            "sand": "#d4c8a0",
            "village": "#b8956f",
            "road": "#8a7f6f",
            "default": "#4a4a4a"
        }
        
        # Nur geänderte Tiles updaten
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                # Terrain-Farbe
                if y < len(tiles) and x < len(tiles[y]):
                    terrain = tiles[y][x]
                else:
                    terrain = "grass"
                
                base_color = terrain_colors.get(terrain, terrain_colors["default"])
                
                # Neue Farbe je nach Reveal-Status
                if reveal:
                    fill_color = base_color
                else:
                    fill_color = "#3a3a3a"
                
                # Tile updaten
                self.fog_map_canvas.itemconfig(f"tile_{x}_{y}", fill=fill_color)
    
    def reveal_area_fog(self):
        """Deckt ausgewählten Bereich auf (alte Methode mit Koordinaten)"""
        try:
            x1 = int(self.area_x1.get())
            y1 = int(self.area_y1.get())
            x2 = int(self.area_x2.get())
            y2 = int(self.area_y2.get())
            
            if self.projector_window and self.projector_window.fog:
                self.projector_window.fog.reveal_area(x1, y1, x2, y2)
                self.projector_window.render_map()
                self.update_fog_map()
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Koordinaten!")
    
    def hide_area_fog(self):
        """Verbirgt ausgewählten Bereich (alte Methode mit Koordinaten)"""
        try:
            x1 = int(self.area_x1.get())
            y1 = int(self.area_y1.get())
            x2 = int(self.area_x2.get())
            y2 = int(self.area_y2.get())
            
            if self.projector_window and self.projector_window.fog:
                self.projector_window.fog.hide_area(x1, y1, x2, y2)
                self.projector_window.render_map()
                self.update_fog_map()
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Koordinaten!")
    
    def update_zoom(self, value):
        """Aktualisiert Zoom-Level"""
        val = float(value)
        self.zoom_value_label.config(text=f"{int(val * 100)}%")
        if self.projector_window:
            self.projector_window.zoom_level = val
            self.projector_window.render_map()
    
    def toggle_auto_zoom(self):
        """Auto-Zoom ein/ausschalten"""
        if self.projector_window and hasattr(self.projector_window, 'camera'):
            enabled = self.auto_zoom_var.get()
            self.projector_window.camera.enable_auto_zoom(enabled)
            
            if enabled:
                messagebox.showinfo("Auto-Zoom", 
                                  "Auto-Zoom aktiviert!\n\n"
                                  "Die Kamera zoomt automatisch auf Bereiche,\n"
                                  "in denen Spieler aktiv sind (aufgedeckte Tiles).")
            else:
                # Kamera zurücksetzen
                self.projector_window.camera.reset()
                self.projector_window.zoom_level = 1.0
                self.zoom_var.set(1.0)
    
    def reset_camera(self):
        """Setzt Kamera zurück"""
        if self.projector_window:
            # Kamera-Controller zurücksetzen
            if hasattr(self.projector_window, 'camera'):
                self.projector_window.camera.reset()
                self.projector_window.camera.enable_auto_zoom(False)
                self.auto_zoom_var.set(False)
            
            # Zoom zurücksetzen
            self.projector_window.zoom_level = 1.0
            self.zoom_var.set(1.0)
            self.projector_window.render_map()
            self.projector_window.center_view()
    
    def update_preview(self):
        """Aktualisiert Webcam-Vorschau"""
        if not self.preview_running or not self.webcam_tracker:
            return
        
        if self.webcam_tracker.cap and self.webcam_tracker.cap.isOpened():
            ret, frame = self.webcam_tracker.cap.read()
            if ret:
                # Frame skalieren für Vorschau
                frame = cv2.resize(frame, (640, 480))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Position einzeichnen
                current_pos = self.webcam_tracker.get_current_tile()
                if current_pos:
                    cv2.circle(frame, (320, 240), 10, (255, 0, 0), -1)
                    cv2.putText(frame, f"Tile: {current_pos}", (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                
                # Zu PIL Image konvertieren
                img = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(img)
                
                self.preview_label.config(image=photo)
                self.preview_label.image = photo
        
        # Nächstes Update
        self.after(33, self.update_preview)  # ~30 FPS
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        self.preview_running = False
        super().destroy()
    
    # Preset-Funktionen für Fog-of-War
    
    def preset_center_only(self):
        """Nur Kartenmitte aufdecken (5x5)"""
        if not self.projector_window or not self.projector_window.map_data:
            return
        
        width = self.projector_window.map_data.get("width", 50)
        height = self.projector_window.map_data.get("height", 50)
        
        # Alle verbergen
        self.projector_window.fog.hide_all()
        
        # Nur Mitte aufdecken
        center_x = width // 2
        center_y = height // 2
        
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    self.projector_window.fog.revealed[ny][nx] = True
        
        self.projector_window.render_map()
        self.update_fog_map()
    
    def preset_entrance(self):
        """Eingangsbereich aufdecken (untere 30%)"""
        if not self.projector_window or not self.projector_window.map_data:
            return
        
        width = self.projector_window.map_data.get("width", 50)
        height = self.projector_window.map_data.get("height", 50)
        
        # Alle verbergen
        self.projector_window.fog.hide_all()
        
        # Untere 30% aufdecken
        start_y = int(height * 0.7)
        self.projector_window.fog.reveal_area(0, start_y, width - 1, height - 1)
        
        self.projector_window.render_map()
        self.update_fog_map()
    
    def preset_combat_area(self):
        """Großen Kampfbereich aufdecken (15x15)"""
        if not self.projector_window or not self.projector_window.map_data:
            return
        
        width = self.projector_window.map_data.get("width", 50)
        height = self.projector_window.map_data.get("height", 50)
        
        # Alle verbergen
        self.projector_window.fog.hide_all()
        
        # 15x15 Bereich in der Mitte
        center_x = width // 2
        center_y = height // 2
        
        self.projector_window.fog.reveal_area(
            max(0, center_x - 7),
            max(0, center_y - 7),
            min(width - 1, center_x + 7),
            min(height - 1, center_y + 7)
        )
        
        self.projector_window.render_map()
        self.update_fog_map()
    
    def preset_except_borders(self):
        """Alles außer Ränder aufdecken (2 Tiles vom Rand)"""
        if not self.projector_window or not self.projector_window.map_data:
            return
        
        width = self.projector_window.map_data.get("width", 50)
        height = self.projector_window.map_data.get("height", 50)
        
        # Alle verbergen
        self.projector_window.fog.hide_all()
        
        # Alles außer 2 Tiles Rand
        self.projector_window.fog.reveal_area(2, 2, width - 3, height - 3)
        
        self.projector_window.render_map()
        self.update_fog_map()
    
    def preset_corridor_v(self):
        """Vertikaler Korridor in der Mitte"""
        if not self.projector_window or not self.projector_window.map_data:
            return
        
        width = self.projector_window.map_data.get("width", 50)
        height = self.projector_window.map_data.get("height", 50)
        
        # Alle verbergen
        self.projector_window.fog.hide_all()
        
        # Vertikaler Streifen (5 Tiles breit)
        center_x = width // 2
        self.projector_window.fog.reveal_area(
            max(0, center_x - 2),
            0,
            min(width - 1, center_x + 2),
            height - 1
        )
        
        self.projector_window.render_map()
        self.update_fog_map()
    
    def preset_corridor_h(self):
        """Horizontaler Korridor in der Mitte"""
        if not self.projector_window or not self.projector_window.map_data:
            return
        
        width = self.projector_window.map_data.get("width", 50)
        height = self.projector_window.map_data.get("height", 50)
        
        # Alle verbergen
        self.projector_window.fog.hide_all()
        
        # Horizontaler Streifen (5 Tiles hoch)
        center_y = height // 2
        self.projector_window.fog.reveal_area(
            0,
            max(0, center_y - 2),
            width - 1,
            min(height - 1, center_y + 2)
        )
        
        self.projector_window.render_map()
        self.update_fog_map()
    
    # Detail-Maps Funktionen
    
    def toggle_auto_detail(self):
        """Auto-Detail-Switch ein/ausschalten"""
        if self.projector_window:
            self.projector_window.auto_detail_switch = self.auto_detail_var.get()
    
    def create_detail_map(self):
        """Erstellt neue Detail-Map"""
        try:
            x = int(self.detail_x.get())
            y = int(self.detail_y.get())
            map_type = self.detail_type_var.get()
            
            if self.projector_window and hasattr(self.projector_window, 'detail_system'):
                detail_system = self.projector_window.detail_system
                
                # Standard-Detail-Map erstellen
                if map_type == "village":
                    detail_map = detail_system.create_default_village_map(f"Dorf bei ({x}, {y})")
                else:
                    detail_map = detail_system.create_default_building_map(f"Gebäude bei ({x}, {y})")
                
                # Registrieren
                detail_system.register_detail_map(x, y, detail_map, auto_save=True)
                
                messagebox.showinfo("Erfolg", 
                                  f"Detail-Map für Position ({x}, {y}) erstellt!\n\n"
                                  f"Die Map wird automatisch geladen, wenn Spieler\n"
                                  f"diese Position betreten.")
                
                self.refresh_detail_list()
            else:
                messagebox.showerror("Fehler", "Projektor-Fenster nicht gefunden!")
        
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Koordinaten!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Erstellen: {e}")
    
    def refresh_detail_list(self):
        """Aktualisiert Liste der Detail-Maps"""
        self.detail_listbox.delete(0, tk.END)
        
        if self.projector_window and hasattr(self.projector_window, 'detail_system'):
            detail_system = self.projector_window.detail_system
            detail_maps = detail_system.list_detail_maps()
            
            if not detail_maps:
                self.detail_listbox.insert(tk.END, "Keine Detail-Maps vorhanden")
            else:
                for x, y, filename in detail_maps:
                    self.detail_listbox.insert(tk.END, f"Position ({x:2d}, {y:2d}) - {filename}")
    
    def delete_detail_map(self):
        """Löscht ausgewählte Detail-Map"""
        selection = self.detail_listbox.curselection()
        if not selection:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle eine Detail-Map aus!")
            return
        
        # Position aus Text extrahieren
        text = self.detail_listbox.get(selection[0])
        if "Position" not in text:
            return
        
        try:
            # Parse "Position (x, y)"
            pos_part = text.split("Position")[1].split("-")[0].strip()
            coords = pos_part.strip("()").split(",")
            x = int(coords[0].strip())
            y = int(coords[1].strip())
            
            if messagebox.askyesno("Löschen bestätigen", 
                                  f"Detail-Map bei Position ({x}, {y}) wirklich löschen?"):
                if self.projector_window and hasattr(self.projector_window, 'detail_system'):
                    detail_system = self.projector_window.detail_system
                    detail_system.delete_detail_map(x, y)
                    self.refresh_detail_list()
                    messagebox.showinfo("Erfolg", "Detail-Map gelöscht!")
        
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Löschen: {e}")
