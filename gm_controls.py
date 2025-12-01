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
        self.minsize(900, 700)  # Breiter als vorher
        
        # Position auf primären Monitor (links oben, nicht zoomed sofort)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 80% der Bildschirmhöhe, 50% Breite
        win_width = max(900, int(screen_width * 0.5))
        win_height = max(700, int(screen_height * 0.8))
        
        # Links positionieren (Projektor ist rechts/auf zweitem Monitor)
        self.geometry(f"{win_width}x{win_height}+50+50")
        
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
        """Fog-of-War Tab"""
        title = tk.Label(parent, text="Fog-of-War Steuerung", font=("Arial", 16, "bold"),
                        bg="#1e1e1e", fg="white")
        title.pack(pady=10)
        
        # Fog aktivieren/deaktivieren
        toggle_frame = tk.Frame(parent, bg="#1e1e1e")
        toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.fog_enabled_var = tk.BooleanVar(value=True)
        fog_checkbox = tk.Checkbutton(toggle_frame, text="Fog-of-War aktiviert",
                                     variable=self.fog_enabled_var,
                                     command=self.toggle_fog,
                                     bg="#1e1e1e", fg="white", selectcolor="#2d2d2d",
                                     font=("Arial", 11, "bold"))
        fog_checkbox.pack(side=tk.LEFT, padx=5)
        
        # Sichtweite
        sight_frame = tk.LabelFrame(parent, text="Sichtweite", bg="#2d2d2d", fg="white")
        sight_frame.pack(fill=tk.X, padx=10, pady=5)
        
        sight_label = tk.Label(sight_frame, text="Aufdeckungs-Radius:", bg="#2d2d2d", fg="white")
        sight_label.pack(side=tk.LEFT, padx=5)
        
        self.sight_range_var = tk.IntVar(value=3)
        sight_slider = tk.Scale(sight_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                               variable=self.sight_range_var,
                               command=self.update_sight_range,
                               bg="#2d2d2d", fg="white", highlightthickness=0)
        sight_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.sight_value_label = tk.Label(sight_frame, text="3 Tiles", bg="#2d2d2d", fg="white")
        self.sight_value_label.pack(side=tk.LEFT, padx=5)
        
        # SCHNELL-PRESETS
        preset_frame = tk.LabelFrame(parent, text="⚡ Schnell-Presets", bg="#2d2d2d", fg="white")
        preset_frame.pack(fill=tk.X, padx=10, pady=5)
        
        preset_row1 = tk.Frame(preset_frame, bg="#2d2d2d")
        preset_row1.pack(fill=tk.X, padx=5, pady=3)
        
        presets_top = [
            ("🏠 Nur Mitte (5x5)", self.preset_center_only, "#4CAF50"),
            ("🚪 Eingang", self.preset_entrance, "#2196F3"),
            ("⚔️ Kampfbereich (15x15)", self.preset_combat_area, "#FF9800")
        ]
        
        for text, command, color in presets_top:
            btn = tk.Button(preset_row1, text=text, command=command,
                           bg=color, fg="white", font=("Arial", 9, "bold"),
                           padx=8, pady=4)
            btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        preset_row2 = tk.Frame(preset_frame, bg="#2d2d2d")
        preset_row2.pack(fill=tk.X, padx=5, pady=3)
        
        presets_bottom = [
            ("🗺️ Ohne Ränder", self.preset_except_borders, "#9C27B0"),
            ("🔦 Korridor (vertikal)", self.preset_corridor_v, "#607D8B"),
            ("↔️ Korridor (horizontal)", self.preset_corridor_h, "#607D8B")
        ]
        
        for text, command, color in presets_bottom:
            btn = tk.Button(preset_row2, text=text, command=command,
                           bg=color, fg="white", font=("Arial", 9, "bold"),
                           padx=8, pady=4)
            btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # NEUE INTERAKTIVE KARTENANSICHT
        map_frame = tk.LabelFrame(parent, text="🗺️ Interaktive Kartenansicht (Klick zum Enthüllen/Verbergen)", 
                                 bg="#2d2d2d", fg="white")
        map_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Info-Text
        info_text = ("Linksklick: Bereich enthüllen | Rechtsklick: Bereich verbergen\n"
                    "Die Karte zeigt alle Tiles aufgedeckt - Grau = verborgen, Farbig = sichtbar")
        info_label = tk.Label(map_frame, text=info_text, bg="#2d2d2d", fg="#aaaaaa",
                            font=("Arial", 8), justify=tk.LEFT)
        info_label.pack(padx=5, pady=2)
        
        # Canvas für interaktive Karte
        canvas_frame = tk.Frame(map_frame, bg="#1e1e1e")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
        self.fog_map_canvas.bind("<Button-1>", self.on_fog_map_left_click)   # Linksklick = Enthüllen
        self.fog_map_canvas.bind("<Button-3>", self.on_fog_map_right_click)  # Rechtsklick = Verbergen
        self.fog_map_canvas.bind("<B1-Motion>", self.on_fog_map_drag)        # Ziehen = Mehrere enthüllen
        
        # Brush-Größe für Klick-Bereich
        brush_frame = tk.Frame(map_frame, bg="#2d2d2d")
        brush_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(brush_frame, text="Pinsel-Größe:", bg="#2d2d2d", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.fog_brush_size = tk.IntVar(value=3)
        brush_slider = tk.Scale(brush_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                               variable=self.fog_brush_size,
                               bg="#2d2d2d", fg="white", highlightthickness=0)
        brush_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Karte initial zeichnen
        self.update_fog_map()
        
        # Schnell-Buttons
        btn_frame = tk.Frame(map_frame, bg="#2d2d2d")
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        reveal_all_btn = tk.Button(btn_frame, text="🌞 Alles aufdecken",
                                   command=self.reveal_all_fog,
                                   bg="#4CAF50", fg="white", font=("Arial", 9, "bold"),
                                   padx=8, pady=3)
        reveal_all_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        hide_all_btn = tk.Button(btn_frame, text="🌑 Alles verbergen",
                                command=self.hide_all_fog,
                                bg="#f44336", fg="white", font=("Arial", 9, "bold"),
                                padx=8, pady=3)
        hide_all_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        refresh_btn = tk.Button(btn_frame, text="🔄 Aktualisieren",
                               command=self.update_fog_map,
                               bg="#2196F3", fg="white", font=("Arial", 9, "bold"),
                               padx=8, pady=3)
        refresh_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
    
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
    
    def update_fog_map(self):
        """Zeichnet die interaktive Fog-Karte"""
        if not self.projector_window or not hasattr(self, 'fog_map_canvas'):
            return
        
        # Canvas leeren
        self.fog_map_canvas.delete("all")
        
        # SVG-Modus: Parse SVG und rendere Tiles
        if self.projector_window.is_svg_mode:
            self.update_fog_map_svg()
            return
        
        # JSON-Modus: Map-Daten holen
        map_data = self.projector_window.map_data
        width = map_data.get("width", 50)
        height = map_data.get("height", 50)
        tiles = map_data.get("tiles", [])
        
        # Größere Tile-Größe für bessere GM-Übersicht (war 8, jetzt 16)
        tile_size = 16
        
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
            from PIL import Image, ImageTk, ImageDraw
            
            # Parse SVG
            root = ET.fromstring(self.projector_window.svg_renderer.svg_data)
            svg_width = int(root.get('width', '1000').replace('px', ''))
            svg_height = int(root.get('height', '1000').replace('px', ''))
            
            # Berechne Mini-Größe (max 500px für bessere Sicht, war 400)
            max_size = 500
            scale = min(max_size / svg_width, max_size / svg_height)
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
        
        except Exception as e:
            print(f"⚠️ Fehler beim Rendern der SVG-Miniatur: {e}")
            # Fallback: Einfache farbige Rechtecke (8px Tiles)
            self.fog_map_canvas.tile_size = 8
    
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
        
        # Fog updaten
        if reveal:
            self.projector_window.fog.reveal_area(x1, y1, x2, y2)
        else:
            self.projector_window.fog.hide_area(x1, y1, x2, y2)
        
        # Projektor-Karte neu rendern
        self.projector_window.render_map()
        
        # Eigene Karte lokal updaten (schneller)
        self._update_fog_tiles_local(x1, y1, x2, y2, reveal)
    
    def _update_fog_tiles_local(self, x1, y1, x2, y2, reveal):
        """Updatet nur die geänderten Tiles lokal (Performance)"""
        if not hasattr(self, 'fog_map_canvas'):
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
