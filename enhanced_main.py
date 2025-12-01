"""
Der Eine Ring PRO - Erweiterte Hauptanwendung
Mit Editor-Modus, Projektor-Modus und VTT-Features
Unterstützt JSON-Maps und SVG-Maps

V2.0 - Verbessertes UI-Framework mit FoundryVTT-inspirierten Features
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json

# UI-Framework importieren für konsistentes Design
try:
    from ui_framework import (
        UIColors, UISizes, WindowManager, BaseDialog
    )
    UI_FRAMEWORK_AVAILABLE = True
except ImportError:
    UI_FRAMEWORK_AVAILABLE = False
    print("⚠️ UI-Framework nicht gefunden - verwende Fallbacks")
    # Fallback-Klassen
    class UIColors:
        BG_DARK = "#1a1a2e"
        BG_MEDIUM = "#16213e"
        BG_LIGHT = "#0f3460"
        BG_PANEL = "#1a1a1a"
        ACCENT = "#e94560"
        ACCENT_GOLD = "#d4af37"
        TEXT = "#eaeaea"
        TEXT_SECONDARY = "#888888"
        SUCCESS = "#4ecca3"
        WARNING = "#ffc107"
        DANGER = "#ff6b6b"

# FoundryVTT-ähnliche Features importieren
try:
    from token_system import Token, TokenLayer, TokenToolbar
    from combat_tracker import CombatEncounter, CombatTrackerWindow, Combatant
    from walls_doors_system import WallManager, WallLayer, WallToolbar
    from ambient_sound_system import SoundManager, SoundLayer
    from journal_system import JournalManager, JournalWindow
    from hotbar_macros import MacroManager, HotbarWidget
    from settings_system import get_settings_manager, SettingsWindow
    FOUNDRY_FEATURES_AVAILABLE = True
    print("✅ FoundryVTT-Features geladen")
except ImportError as e:
    FOUNDRY_FEATURES_AVAILABLE = False
    print(f"⚠️ FoundryVTT-Features nicht vollständig verfügbar: {e}")

# Hexagon-Map-System importieren
try:
    from hexagon_map_system import HexagonMap, TerrainType, WeatherType
    from hexagon_map_editor import HexagonMapEditor, open_hexagon_editor
    HEXAGON_AVAILABLE = True
    print("✅ Hexagon-Map-System geladen")
except ImportError as e:
    HEXAGON_AVAILABLE = False
    print(f"⚠️ Hexagon-Map-System nicht verfügbar: {e}")


class DerEineRingProApp(tk.Tk):
    """
    Hauptanwendung für "Der Eine Ring" VTT.
    
    Verbesserungen V2.0:
    - Konsistentes UI-Framework
    - Bessere Fenster-Verwaltung (keine Duplikate)
    - Korrigierte Dialog-Größen
    - Keyboard-Shortcuts
    """
    
    def __init__(self):
        super().__init__()
        self.title("Der Eine Ring PRO VTT")
        
        # Bessere Startgröße (nicht mehr 1920x1080 fest!)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 70% der Bildschirmgröße, mindestens 800x600
        app_width = max(800, int(screen_width * 0.7))
        app_height = max(600, int(screen_height * 0.7))
        
        # Zentriert starten
        x = (screen_width - app_width) // 2
        y = (screen_height - app_height) // 2
        self.geometry(f"{app_width}x{app_height}+{x}+{y}")
        
        # Mindestgröße setzen
        self.minsize(800, 600)
        
        # Farben aus UI-Framework oder Fallback
        bg_color = UIColors.BG_DARK if UI_FRAMEWORK_AVAILABLE else "#0a0a0a"
        self.configure(bg=bg_color)
        
        # Aktuell geladene Karte
        self.current_map_data = None
        self.current_editor = None
        self.projector_window = None
        self.gm_panel = None
        self.story_editor = None  # Story Editor Referenz
        self.loaded_svg_path = None  # SVG-Pfad Tracking
        
        # FoundryVTT-Features
        self.combat_tracker = None
        self.combat_tracker_window = None
        self.journal_window = None
        self.settings_window = None
        
        # Manager für neue Features
        if FOUNDRY_FEATURES_AVAILABLE:
            self.token_layer = TokenLayer()  # Token-Verwaltung
            self.wall_manager = WallManager()
            self.sound_manager = SoundManager()
            self.macro_manager = MacroManager()
            self.journal_manager = JournalManager()
            self.settings_manager = get_settings_manager()
            self.combat_tracker = CombatEncounter()  # Combat Tracker initialisieren
        else:
            self.token_layer = None
            self.wall_manager = None
            self.sound_manager = None
            self.macro_manager = None
            self.journal_manager = None
            self.settings_manager = None
        
        # Webcam-Tracker initialisieren
        try:
            from webcam_tracker import WebcamTracker
            self.webcam_tracker = WebcamTracker(camera_index=0)
        except Exception as e:
            print(f"⚠️ Webcam-Tracker nicht verfügbar: {e}")
            self.webcam_tracker = None
        
        self.setup_ui()
        self.setup_keyboard_shortcuts()
    
    def setup_keyboard_shortcuts(self):
        """Globale Tastenkürzel registrieren"""
        self.bind("<F1>", lambda e: self.show_help())
        self.bind("<F2>", lambda e: self.open_combat_tracker())
        self.bind("<F3>", lambda e: self.open_journal())
        self.bind("<F4>", lambda e: self.open_settings())
        self.bind("<Control-o>", lambda e: self.load_map())
        self.bind("<Control-e>", lambda e: self.start_editor())
        self.bind("<Control-p>", lambda e: self.start_projector())
        self.bind("<Control-g>", lambda e: self.start_gm_panel())
        self.bind("<Control-s>", lambda e: self.start_story_editor())
        self.bind("<Escape>", lambda e: self._on_escape())
    
    def _on_escape(self):
        """ESC-Taste Handler - zeigt Beenden-Dialog"""
        if messagebox.askyesno("Beenden", "Möchtest du das Programm wirklich beenden?"):
            self.quit()
    
    def _show_message(self, msg_type: str, title: str, message: str):
        """Zentrale Message-Anzeige"""
        if msg_type == "info":
            messagebox.showinfo(title, message)
        elif msg_type == "warning":
            messagebox.showwarning(title, message)
        elif msg_type == "error":
            messagebox.showerror(title, message)
    
    def _ask_yes_no(self, title: str, message: str, dangerous: bool = False) -> bool:
        """Zentrale Ja/Nein-Abfrage"""
        return messagebox.askyesno(title, message)
    
    def setup_ui(self):
        """Hauptmenü erstellen - FoundryVTT-inspiriertes Layout"""
        # Farben aus UI-Framework
        bg_dark = UIColors.BG_DARK if UI_FRAMEWORK_AVAILABLE else "#0a0a0a"
        bg_panel = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
        bg_medium = UIColors.BG_MEDIUM if UI_FRAMEWORK_AVAILABLE else "#16213e"
        accent_gold = UIColors.ACCENT_GOLD if UI_FRAMEWORK_AVAILABLE else "#d4af37"
        text_secondary = UIColors.TEXT_SECONDARY if UI_FRAMEWORK_AVAILABLE else "#888888"
        
        # ═══════════════════════════════════════════════════════════════
        # HAUPT-CONTAINER: 3-Spalten-Layout wie FoundryVTT
        # ═══════════════════════════════════════════════════════════════
        
        # Header (ganz oben)
        header = tk.Frame(self, bg=bg_dark, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=bg_dark)
        title_frame.pack(expand=True)
        
        tk.Label(title_frame, text="🗺️ Der Eine Ring", 
                font=("Arial", 28, "bold"),
                bg=bg_dark, fg=accent_gold).pack(side=tk.LEFT, padx=10)
        
        tk.Label(title_frame, text="Virtual Tabletop",
                font=("Arial", 12),
                bg=bg_dark, fg=text_secondary).pack(side=tk.LEFT, padx=5, pady=8)
        
        # Haupt-Content-Bereich
        main_container = tk.Frame(self, bg=bg_dark)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # ═══════════════════════════════════════════════════════════════
        # LINKE SEITE: Scene Controls (wie FoundryVTT)
        # ═══════════════════════════════════════════════════════════════
        left_toolbar = tk.Frame(main_container, bg=bg_panel, width=60)
        left_toolbar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_toolbar.pack_propagate(False)
        
        tk.Label(left_toolbar, text="TOOLS", font=("Arial", 8, "bold"),
                bg=bg_panel, fg="#666").pack(pady=(10, 5))
        
        # Tool-Buttons (links)
        tool_buttons = [
            ("🎨", "Editor", self.start_editor, "Karten bearbeiten (Ctrl+E)"),
            ("🔷", "Hex-Map", self.start_hexagon_editor, "Hexagon-Karten Editor"),
            ("📺", "Projektor", self.start_projector, "Kartenprojektion (Ctrl+P)"),
            ("🎮", "GM Panel", self.start_gm_panel, "Spielleiter-Kontrolle (Ctrl+G)"),
            ("🎬", "Story", self.start_story_editor, "Story/Szenen Editor"),
        ]
        
        for icon, label, cmd, tooltip in tool_buttons:
            btn_frame = tk.Frame(left_toolbar, bg=bg_panel)
            btn_frame.pack(pady=5, padx=5, fill=tk.X)
            
            btn = tk.Button(btn_frame, text=icon, font=("Arial", 18),
                          bg="#2a2a2a", fg="white", width=2, height=1,
                          relief=tk.FLAT, cursor="hand2", command=cmd)
            btn.pack()
            
            lbl = tk.Label(btn_frame, text=label, font=("Arial", 7),
                          bg=bg_panel, fg="#888")
            lbl.pack()
            
            # Tooltip
            self._create_tooltip(btn, tooltip)
        
        tk.Frame(left_toolbar, bg="#333", height=1).pack(fill=tk.X, pady=10)
        
        # Datei-Buttons
        file_buttons = [
            ("📁", "Laden", self.load_map, "Karte laden (Ctrl+O)"),
            ("🖼️", "Import", self.import_png_map, "PNG importieren"),
            ("📋", "Liste", self.show_map_list, "Gespeicherte Karten"),
        ]
        
        for icon, label, cmd, tooltip in file_buttons:
            btn_frame = tk.Frame(left_toolbar, bg=bg_panel)
            btn_frame.pack(pady=5, padx=5, fill=tk.X)
            
            btn = tk.Button(btn_frame, text=icon, font=("Arial", 16),
                          bg="#333", fg="white", width=2, height=1,
                          relief=tk.FLAT, cursor="hand2", command=cmd)
            btn.pack()
            
            lbl = tk.Label(btn_frame, text=label, font=("Arial", 7),
                          bg=bg_panel, fg="#666")
            lbl.pack()
            
            self._create_tooltip(btn, tooltip)
        
        # ═══════════════════════════════════════════════════════════════
        # MITTE: Hauptbereich mit Willkommens-Info
        # ═══════════════════════════════════════════════════════════════
        center_frame = tk.Frame(main_container, bg=bg_dark)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # Willkommens-Bereich
        welcome_frame = tk.Frame(center_frame, bg=bg_panel, relief=tk.FLAT)
        welcome_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Karten-Status
        self.map_status_frame = tk.Frame(welcome_frame, bg=bg_panel)
        self.map_status_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.map_status_icon = tk.Label(self.map_status_frame, text="🗺️",
                                        font=("Arial", 48), bg=bg_panel, fg="#444")
        self.map_status_icon.pack()
        
        self.map_status_label = tk.Label(self.map_status_frame,
                                         text="Keine Karte geladen",
                                         font=("Arial", 14), bg=bg_panel, fg="#666")
        self.map_status_label.pack(pady=10)
        
        self.map_status_hint = tk.Label(self.map_status_frame,
                                        text="Lade eine Karte oder erstelle eine neue im Editor",
                                        font=("Arial", 10), bg=bg_panel, fg="#555")
        self.map_status_hint.pack()
        
        # Quick Actions
        quick_frame = tk.Frame(welcome_frame, bg=bg_panel)
        quick_frame.pack(pady=30)
        
        tk.Label(quick_frame, text="Schnellstart", font=("Arial", 12, "bold"),
                bg=bg_panel, fg="#888").pack(pady=(0, 15))
        
        quick_btns_frame = tk.Frame(quick_frame, bg=bg_panel)
        quick_btns_frame.pack()
        
        quick_actions = [
            ("Neue Karte erstellen", "#2a7d2a", self.start_editor),
            ("Karte laden", "#2a5d8d", self.load_map),
            ("Letzte Sitzung fortsetzen", "#7d5d2a", self._continue_session),
        ]
        
        for text, color, cmd in quick_actions:
            btn = tk.Button(quick_btns_frame, text=text,
                          font=("Arial", 11), bg=color, fg="white",
                          padx=20, pady=8, relief=tk.FLAT, cursor="hand2",
                          command=cmd)
            btn.pack(side=tk.LEFT, padx=5)
            btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=self._lighten_color(c)))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))
        
        # Tastenkürzel-Hinweis
        shortcut_frame = tk.Frame(welcome_frame, bg=bg_panel)
        shortcut_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20, padx=20)
        
        tk.Label(shortcut_frame, text="Tastenkürzel: F1=Hilfe | F2=Combat | F3=Journal | F4=Settings | Ctrl+E/P/G=Editor/Projektor/GM",
                font=("Arial", 9), bg=bg_panel, fg="#555").pack()
        
        # ═══════════════════════════════════════════════════════════════
        # RECHTE SEITE: Sidebar mit Tabs (wie FoundryVTT)
        # ═══════════════════════════════════════════════════════════════
        right_sidebar = tk.Frame(main_container, bg=bg_panel, width=280)
        right_sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_sidebar.pack_propagate(False)
        
        # Tab-Buttons oben
        tab_header = tk.Frame(right_sidebar, bg="#222")
        tab_header.pack(fill=tk.X)
        
        self.sidebar_tabs = {}
        self.active_tab = tk.StringVar(value="combat")
        
        tab_defs = [
            ("combat", "⚔️", "Combat"),
            ("journal", "📚", "Journal"),
            ("actors", "👤", "Akteure"),
            ("settings", "⚙️", "Settings"),
        ]
        
        for tab_id, icon, label in tab_defs:
            btn = tk.Button(tab_header, text=icon, font=("Arial", 14),
                          bg="#222" if tab_id != "combat" else "#3a3a3a",
                          fg="white", width=3, height=1, relief=tk.FLAT,
                          cursor="hand2",
                          command=lambda t=tab_id: self._switch_sidebar_tab(t))
            btn.pack(side=tk.LEFT, padx=2, pady=5)
            self.sidebar_tabs[tab_id] = btn
            self._create_tooltip(btn, label)
        
        # Tab-Content-Bereich
        self.sidebar_content = tk.Frame(right_sidebar, bg=bg_panel)
        self.sidebar_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initial: Combat-Tab anzeigen
        self._show_sidebar_combat()
        
        # ═══════════════════════════════════════════════════════════════
        # FOOTER: Hotbar-Style Status
        # ═══════════════════════════════════════════════════════════════
        footer = tk.Frame(self, bg="#111", height=40)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        # Status links
        self.status_label = tk.Label(footer, text="● Bereit",
                                    font=("Arial", 10), bg="#111", fg="#4ecca3")
        self.status_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Version rechts
        tk.Label(footer, text="Der Eine Ring VTT v2.1",
                font=("Arial", 9), bg="#111", fg="#444").pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Hilfe-Button
        tk.Button(footer, text="❓ Hilfe (F1)", font=("Arial", 9),
                 bg="#333", fg="#888", relief=tk.FLAT, cursor="hand2",
                 command=self.show_help).pack(side=tk.RIGHT, padx=5, pady=8)
    
    def _create_tooltip(self, widget, text):
        """Erstellt Tooltip für ein Widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, font=("Arial", 9),
                           bg="#ffffe0", fg="#333", relief=tk.SOLID,
                           borderwidth=1, padx=5, pady=2)
            label.pack()
            
            widget._tooltip = tooltip
            
        def hide_tooltip(event):
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                del widget._tooltip
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def _switch_sidebar_tab(self, tab_id: str):
        """Wechselt den aktiven Sidebar-Tab"""
        self.active_tab.set(tab_id)
        
        # Tab-Buttons updaten
        for tid, btn in self.sidebar_tabs.items():
            btn.config(bg="#3a3a3a" if tid == tab_id else "#222")
        
        # Content leeren und neu füllen
        for widget in self.sidebar_content.winfo_children():
            widget.destroy()
        
        if tab_id == "combat":
            self._show_sidebar_combat()
        elif tab_id == "journal":
            self._show_sidebar_journal()
        elif tab_id == "actors":
            self._show_sidebar_actors()
        elif tab_id == "settings":
            self._show_sidebar_settings()
    
    def _show_sidebar_combat(self):
        """Zeigt Combat-Tab Inhalt"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
        
        tk.Label(self.sidebar_content, text="⚔️ Combat Tracker",
                font=("Arial", 12, "bold"), bg=bg, fg="#c23616").pack(pady=10, anchor=tk.W)
        
        # Aktueller Kampf-Status
        status_frame = tk.Frame(self.sidebar_content, bg="#252525", relief=tk.FLAT)
        status_frame.pack(fill=tk.X, pady=5)
        
        if self.combat_tracker and hasattr(self.combat_tracker, 'is_active') and self.combat_tracker.is_active:
            tk.Label(status_frame, text="🔴 Kampf aktiv",
                    font=("Arial", 10), bg="#252525", fg="#ff6b6b").pack(pady=8)
            tk.Label(status_frame, text=f"Runde: {getattr(self.combat_tracker, 'round', 1)}",
                    font=("Arial", 9), bg="#252525", fg="#888").pack()
        else:
            tk.Label(status_frame, text="⚪ Kein aktiver Kampf",
                    font=("Arial", 10), bg="#252525", fg="#666").pack(pady=8)
        
        # Buttons
        tk.Button(self.sidebar_content, text="🎯 Combat Tracker öffnen",
                 font=("Arial", 10), bg="#c23616", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=10, pady=5,
                 command=self.open_combat_tracker).pack(pady=10, fill=tk.X)
        
        tk.Button(self.sidebar_content, text="➕ Neuen Kampf starten",
                 font=("Arial", 9), bg="#333", fg="#aaa",
                 relief=tk.FLAT, cursor="hand2", padx=8, pady=4,
                 command=self._start_new_combat).pack(pady=2, fill=tk.X)
        
        # Teilnehmer-Vorschau
        tk.Label(self.sidebar_content, text="Teilnehmer:",
                font=("Arial", 9, "bold"), bg=bg, fg="#888").pack(pady=(15, 5), anchor=tk.W)
        
        participants_frame = tk.Frame(self.sidebar_content, bg=bg)
        participants_frame.pack(fill=tk.X)
        
        if self.combat_tracker and hasattr(self.combat_tracker, 'combatants') and self.combat_tracker.combatants:
            # combatants ist ein Dict
            combatant_list = list(self.combat_tracker.combatants.values())[:5]
            for combatant in combatant_list:
                tk.Label(participants_frame, text=f"• {combatant.name}",
                        font=("Arial", 9), bg=bg, fg="#aaa").pack(anchor=tk.W)
        else:
            tk.Label(participants_frame, text="Keine Teilnehmer",
                    font=("Arial", 9, "italic"), bg=bg, fg="#555").pack(anchor=tk.W)
    
    def _show_sidebar_journal(self):
        """Zeigt Journal-Tab Inhalt"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
        
        tk.Label(self.sidebar_content, text="📚 Journal & Notizen",
                font=("Arial", 12, "bold"), bg=bg, fg="#6c5ce7").pack(pady=10, anchor=tk.W)
        
        tk.Button(self.sidebar_content, text="📖 Journal öffnen",
                 font=("Arial", 10), bg="#6c5ce7", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=10, pady=5,
                 command=self.open_journal).pack(pady=10, fill=tk.X)
        
        tk.Button(self.sidebar_content, text="➕ Neuer Eintrag",
                 font=("Arial", 9), bg="#333", fg="#aaa",
                 relief=tk.FLAT, cursor="hand2", padx=8, pady=4,
                 command=self._new_journal_entry).pack(pady=2, fill=tk.X)
        
        # Letzte Einträge
        tk.Label(self.sidebar_content, text="Letzte Einträge:",
                font=("Arial", 9, "bold"), bg=bg, fg="#888").pack(pady=(15, 5), anchor=tk.W)
        
        entries_frame = tk.Frame(self.sidebar_content, bg=bg)
        entries_frame.pack(fill=tk.X)
        
        if self.journal_manager and hasattr(self.journal_manager, 'entries') and self.journal_manager.entries:
            # entries ist eine Liste, nicht ein Dict
            for entry in self.journal_manager.entries[:5]:
                name = getattr(entry, 'name', getattr(entry, 'title', 'Eintrag'))
                display_name = name[:25] + '...' if len(name) > 25 else name
                tk.Label(entries_frame, text=f"• {display_name}",
                        font=("Arial", 9), bg=bg, fg="#aaa").pack(anchor=tk.W)
        else:
            tk.Label(entries_frame, text="Noch keine Einträge",
                    font=("Arial", 9, "italic"), bg=bg, fg="#555").pack(anchor=tk.W)
    
    def _show_sidebar_actors(self):
        """Zeigt Actors/Token-Tab Inhalt"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
        
        tk.Label(self.sidebar_content, text="👤 Akteure & Tokens",
                font=("Arial", 12, "bold"), bg=bg, fg="#00cec9").pack(pady=10, anchor=tk.W)
        
        tk.Label(self.sidebar_content, 
                text="Tokens werden im Editor\nund Projektor verwaltet.",
                font=("Arial", 9), bg=bg, fg="#666").pack(pady=10)
        
        tk.Button(self.sidebar_content, text="🎨 Editor öffnen",
                 font=("Arial", 10), bg="#00cec9", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=10, pady=5,
                 command=self.start_editor).pack(pady=5, fill=tk.X)
    
    def _show_sidebar_settings(self):
        """Zeigt Settings-Tab Inhalt"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
        
        tk.Label(self.sidebar_content, text="⚙️ Einstellungen",
                font=("Arial", 12, "bold"), bg=bg, fg="#636e72").pack(pady=10, anchor=tk.W)
        
        tk.Button(self.sidebar_content, text="🔧 Einstellungen öffnen",
                 font=("Arial", 10), bg="#636e72", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=10, pady=5,
                 command=self.open_settings).pack(pady=10, fill=tk.X)
        
        # Schnell-Einstellungen
        tk.Label(self.sidebar_content, text="Schnelleinstellungen:",
                font=("Arial", 9, "bold"), bg=bg, fg="#888").pack(pady=(15, 5), anchor=tk.W)
        
        settings_frame = tk.Frame(self.sidebar_content, bg=bg)
        settings_frame.pack(fill=tk.X)
        
        # Beispiel-Schnelleinstellung
        self.dark_mode_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Dunkles Theme",
                      variable=self.dark_mode_var, bg=bg, fg="#aaa",
                      selectcolor="#333", activebackground=bg).pack(anchor=tk.W)
        
        self.show_grid_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Raster anzeigen",
                      variable=self.show_grid_var, bg=bg, fg="#aaa",
                      selectcolor="#333", activebackground=bg).pack(anchor=tk.W)
    
    def _continue_session(self):
        """Versucht die letzte Sitzung fortzusetzen"""
        # Prüfe ob es gespeicherte Daten gibt
        if self.current_map_data:
            self.start_editor()
        else:
            messagebox.showinfo("Keine Sitzung", 
                              "Keine vorherige Sitzung gefunden.\n\nLade eine Karte oder erstelle eine neue.")
    
    def _start_new_combat(self):
        """Startet einen neuen Kampf"""
        self.open_combat_tracker()
    
    def _new_journal_entry(self):
        """Erstellt einen neuen Journal-Eintrag"""
        self.open_journal()
    
    def _lighten_color(self, hex_color: str) -> str:
        """Hellt eine Hex-Farbe auf für Hover-Effekt"""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = min(255, int(r * 1.2))
            g = min(255, int(g * 1.2))
            b = min(255, int(b * 1.2))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    
    def _update_status(self, message: str):
        """Aktualisiert die Status-Leiste"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
    
    def start_editor(self):
        """Editor-Fenster öffnen - mit WindowManager für bessere Verwaltung"""
        try:
            from map_editor import MapEditor, ask_canvas_size
            
            # Prüfe ob Editor bereits offen (WindowManager)
            if UI_FRAMEWORK_AVAILABLE:
                existing = WindowManager.get("map_editor")
                if existing:
                    existing.lift()
                    existing.focus_force()
                    self._update_status("Editor bereits geöffnet")
                    return
            
            print(f"\n🔍 DEBUG start_editor:")
            print(f"   self.current_map_data: {'vorhanden' if self.current_map_data else 'None'}")
            
            # Wenn keine Map geladen ist, frage nach Größe
            if not self.current_map_data:
                print(f"   → Keine Map geladen, frage nach Größe...")
                size = ask_canvas_size(self)
                
                if not size["confirmed"]:
                    return  # Benutzer hat abgebrochen
                
                width = size["width"]
                height = size["height"]
                map_data_to_pass = None
            else:
                # Map bereits geladen, nutze deren Größe UND Daten
                width = self.current_map_data.get("width", 50)
                height = self.current_map_data.get("height", 50)
                map_data_to_pass = self.current_map_data
                print(f"   → Map vorhanden: {width}×{height}")
                print(f"   → map_data_to_pass wird übergeben!")
            
            print(f"📋 Erstelle Editor mit: width={width}, height={height}, map_data={'JA' if map_data_to_pass else 'NEIN'}")
            
            # Editor-Fenster erstellen
            bg_color = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1a1a1a"
            
            editor_win = tk.Toplevel(self)
            editor_win.title("Map Editor - Der Eine Ring")
            editor_win.configure(bg=bg_color)
            
            # Mindestgröße setzen BEVOR maximiert
            editor_win.minsize(1200, 800)
            
            # Maximiert starten
            editor_win.state('zoomed')
            
            # Bei WindowManager registrieren
            if UI_FRAMEWORK_AVAILABLE:
                WindowManager.register("map_editor", editor_win)
            
            # MapEditor mit aktuellen Daten oder neu
            editor = MapEditor(editor_win, width=width, height=height, map_data=map_data_to_pass)
            editor.pack(fill=tk.BOTH, expand=True)
            
            self.current_editor = editor
            self._update_status(f"Editor geöffnet | Map: {width}×{height}")
            
            # Beim Schließen Map-Daten speichern
            def on_close():
                self.current_map_data = editor.get_map_data()
                self.current_editor = None
                self._update_status("Editor geschlossen | Map im Speicher")
                editor_win.destroy()
            
            editor_win.protocol("WM_DELETE_WINDOW", on_close)
            
        except Exception as e:
            self._show_message("error", "Fehler", f"Editor konnte nicht gestartet werden:\n{e}")
    
    def start_projector(self):
        """Projektor-Fenster öffnen - unterstützt JSON und SVG"""
        try:
            from projector_window import ProjectorWindow
            
            # Hole Map-Daten
            map_data = self.current_map_data
            if self.current_editor:
                map_data = self.current_editor.get_map_data()
            
            # Prüfe ob SVG-Path in Map-Daten oder als loaded_svg_path
            svg_path = None
            if hasattr(self, 'loaded_svg_path') and self.loaded_svg_path:
                svg_path = self.loaded_svg_path
            elif map_data and map_data.get("svg_path"):
                svg_path = map_data.get("svg_path")
            
            # SVG-Modus: Öffne Projektor mit Original-SVG
            if svg_path:
                if self.projector_window and self.projector_window.winfo_exists():
                    self.projector_window.destroy()
                
                # Projektor mit map_data UND svg_path erstellen
                self.projector_window = ProjectorWindow(
                    self, 
                    map_data=map_data,
                    svg_path=svg_path, 
                    webcam_tracker=self.webcam_tracker
                )
                self._update_status(f"Projektor geöffnet | SVG: {os.path.basename(svg_path)}")
                return
            
            # JSON-Modus: Normale Tile-basierte Map
            # Wenn keine Daten vorhanden, Standardkarte laden
            if self.current_editor:
                map_data = self.current_editor.get_map_data()
            
            # Wenn keine Daten vorhanden, Standardkarte laden
            if not map_data:
                from map_system import MapSystem
                ms = MapSystem()
                map_data = ms.create_default_map()
                self._show_message("info", "Info", "Keine Karte geladen - Zeige Beispielkarte")
            
            # Webcam-Tracker vorbereiten
            if self.webcam_tracker:
                map_width = map_data.get("width", 50)
                map_height = map_data.get("height", 50)
                self.webcam_tracker.map_size = (map_width, map_height)
            
            # Projektor öffnen/aktualisieren
            if self.projector_window and self.projector_window.winfo_exists():
                self.projector_window.update_map(map_data)
                self.projector_window.lift()
                self._update_status("Projektor aktualisiert")
            else:
                self.projector_window = ProjectorWindow(self, map_data, self.webcam_tracker)
                map_name = map_data.get("name", "Unbenannt")
                self._update_status(f"Projektor geöffnet | Map: {map_name}")
            
        except Exception as e:
            self._show_message("error", "Fehler", f"Projektor konnte nicht gestartet werden:\n{e}")
    
    def start_gm_panel(self):
        """Gamemaster-Kontrollpanel öffnen - mit WindowManager"""
        try:
            from gm_controls import GamemasterControlPanel
            
            # Prüfe ob GM-Panel bereits offen (WindowManager)
            if UI_FRAMEWORK_AVAILABLE:
                existing = WindowManager.get("gm_panel")
                if existing:
                    existing.lift()
                    existing.focus_force()
                    self._update_status("GM-Panel bereits geöffnet")
                    return
            
            # Fallback: Alte Methode
            if self.gm_panel and self.gm_panel.winfo_exists():
                self.gm_panel.lift()
                return
            
            # Neues Panel erstellen
            self.gm_panel = GamemasterControlPanel(self, self.projector_window, self.webcam_tracker)
            
            # Bei WindowManager registrieren
            if UI_FRAMEWORK_AVAILABLE:
                WindowManager.register("gm_panel", self.gm_panel)
            
            self._update_status("GM-Panel geöffnet")
            
        except Exception as e:
            self._show_message("error", "Fehler", f"GM-Panel konnte nicht gestartet werden:\n{e}")
    
    def _open_hexagon_editor_with_map(self, map_path: str):
        """Öffne Hexagon-Editor mit einer vorhandenen Map-Datei"""
        if not HEXAGON_AVAILABLE:
            self._show_message("error", "Nicht verfügbar", 
                "Hexagon-Map-System nicht geladen.")
            return
        
        try:
            from PIL import Image
            
            # Lade die Hexagon-Map
            hex_map = HexagonMap.load(map_path)
            
            if not hex_map:
                self._show_message("error", "Fehler", f"Konnte Map nicht laden:\n{map_path}")
                return
            
            # Prüfe ob bereits offen
            if UI_FRAMEWORK_AVAILABLE:
                existing = WindowManager.get("hexagon_editor")
                if existing:
                    existing.destroy()  # Schließe alte Instanz
            
            # Editor mit geladener Map öffnen
            editor = HexagonMapEditor(self, hex_map)
            editor.current_file_path = map_path  # Merke Dateipfad für Speichern
            
            # ===== WICHTIG: Lade Hintergrundbild wenn vorhanden =====
            bg_path = getattr(hex_map, 'background_image_path', None)
            if bg_path and os.path.exists(bg_path):
                try:
                    # Prüfe ob SVG oder Bild
                    if bg_path.lower().endswith('.svg'):
                        try:
                            import cairosvg
                            from io import BytesIO
                            print(f"🖼️ Lade SVG-Hintergrund: {bg_path}")
                            png_data = cairosvg.svg2png(url=bg_path, scale=1)
                            editor.bg_image = Image.open(BytesIO(png_data))
                        except ImportError:
                            print(f"⚠️ cairosvg nicht installiert, SVG-Hintergrund wird nicht angezeigt")
                            editor.bg_image = None
                    else:
                        print(f"🖼️ Lade Hintergrundbild: {bg_path}")
                        editor.bg_image = Image.open(bg_path)
                    
                    if editor.bg_image:
                        editor.bg_image_path = bg_path
                        editor.bg_visible = getattr(hex_map, 'background_visible', True)
                        editor.bg_on_top = getattr(hex_map, 'background_on_top', False)
                        editor.bg_visible_var.set(editor.bg_visible)
                        editor.bg_on_top_var.set(editor.bg_on_top)
                        print(f"✅ Hintergrundbild geladen: {editor.bg_image.size}")
                        editor._redraw()
                except Exception as e:
                    print(f"⚠️ Hintergrundbild konnte nicht geladen werden: {e}")
            else:
                if bg_path:
                    print(f"⚠️ Hintergrundbild nicht gefunden: {bg_path}")
            # ==========================================================
            
            if UI_FRAMEWORK_AVAILABLE:
                WindowManager.register("hexagon_editor", editor)
            
            self._update_status(f"Hexagon-Map geladen: {os.path.basename(map_path)}")
            
        except Exception as e:
            self._show_message("error", "Fehler", f"Hexagon-Editor konnte nicht gestartet werden:\n{e}")
            import traceback
            traceback.print_exc()
    
    def start_hexagon_editor(self):
        """Hexagon-Karten-Editor öffnen"""
        if not HEXAGON_AVAILABLE:
            self._show_message("error", "Nicht verfügbar", 
                "Hexagon-Map-System nicht geladen.\n\n"
                "Stelle sicher, dass hexagon_map_system.py und\n"
                "hexagon_map_editor.py vorhanden sind.")
            return
        
        try:
            # Prüfe ob bereits offen
            if UI_FRAMEWORK_AVAILABLE:
                existing = WindowManager.get("hexagon_editor")
                if existing:
                    existing.lift()
                    existing.focus_force()
                    self._update_status("Hexagon-Editor bereits geöffnet")
                    return
            
            # Erstelle neue Hexagon-Map oder lade vorhandene
            hex_map = HexagonMap("Neue Hexagon-Karte")
            
            # Editor öffnen
            editor = HexagonMapEditor(self, hex_map)
            
            if UI_FRAMEWORK_AVAILABLE:
                WindowManager.register("hexagon_editor", editor)
            
            self._update_status("Hexagon-Editor geöffnet")
            
        except Exception as e:
            self._show_message("error", "Fehler", f"Hexagon-Editor konnte nicht gestartet werden:\n{e}")
            import traceback
            traceback.print_exc()
    
    def start_story_editor(self):
        """Story Editor für interaktive Abenteuer öffnen - mit WindowManager"""
        try:
            from story_editor import StoryEditor
            
            # Prüfe ob Story Editor bereits offen (WindowManager)
            if UI_FRAMEWORK_AVAILABLE:
                existing = WindowManager.get("story_editor")
                if existing:
                    existing.lift()
                    existing.focus_force()
                    self._update_status("Story Editor bereits geöffnet")
                    return
            
            # Fallback: Alte Methode
            if hasattr(self, 'story_editor') and self.story_editor and self.story_editor.winfo_exists():
                self.story_editor.lift()
                return
            
            # Callback für Szenen-Vorschau im Projektor
            def preview_scene(scene):
                """Zeigt die aktuelle Szene im Projektor an"""
                from storyboard_system import SceneType
                import json
                
                # Prüfe ob eine Quelle gesetzt ist
                source = scene.background_source or scene.content_path
                if not source:
                    self._show_message("warning", "Keine Quelle", 
                        f"Die Szene '{scene.name}' hat keine Hintergrund-Datei.\n\n"
                        "Doppelklicke auf die Szene und wähle eine Datei unter '🎬 Medien'.")
                    return
                
                # Prüfe ob Datei existiert
                if not os.path.exists(source):
                    self._show_message("error", "Datei nicht gefunden", 
                        f"Die Datei wurde nicht gefunden:\n{source}")
                    return
                
                # Projektor prüfen/öffnen
                if not self.projector_window or not self.projector_window.winfo_exists():
                    # Projektor öffnen mit der Szene direkt
                    if self._ask_yes_no("Projektor öffnen?",
                        "Der Projektor ist nicht geöffnet.\n\n"
                        "Soll der Projektor-Modus gestartet werden?"):
                        # Öffne Projektor direkt mit Szenen-Daten (nicht start_projector!)
                        self._open_projector_for_scene(scene, source)
                    return
                
                self._load_scene_to_projector(scene, source)
            
            # Story Editor öffnen
            self.story_editor = StoryEditor(
                self,
                storyboard=None,  # Neues Storyboard
                on_scene_preview=preview_scene
            )
            
            # Bei WindowManager registrieren
            if UI_FRAMEWORK_AVAILABLE:
                WindowManager.register("story_editor", self.story_editor)
            
            self._update_status("Story Editor geöffnet")
            
        except ImportError as e:
            self._show_message("error", "Fehler", 
                f"Story Editor Module nicht gefunden:\n{e}\n\n"
                "Bitte stelle sicher, dass alle story_editor_*.py Dateien vorhanden sind.")
        except Exception as e:
            self._show_message("error", "Fehler", f"Story Editor konnte nicht gestartet werden:\n{e}")

    def start_hexagon_editor(self):
        """Hexagon-Karten-Editor öffnen"""
        if not HEXAGON_AVAILABLE:
            self._show_message("error", "Nicht verfügbar", 
                "Das Hexagon-Map-System ist nicht verfügbar.\n\n"
                "Bitte stelle sicher, dass hexagon_map_system.py und hexagon_map_editor.py vorhanden sind.")
            return
        
        try:
            # Frage ob neue oder bestehende Karte
            choice = messagebox.askyesnocancel(
                "Hexagon-Editor",
                "Möchtest du eine SVG-Karte laden?\n\n"
                "Ja = SVG laden und Hexagone erkennen\n"
                "Nein = Leeres Grid erstellen\n"
                "Abbrechen = Zurück"
            )
            
            if choice is None:
                return
            
            hex_map = HexagonMap("Neue Hexagon-Karte")
            bg_image = None  # Hintergrundbild
            
            if choice:  # SVG laden
                filepath = filedialog.askopenfilename(
                    title="SVG-Karte für Hexagon-Editor laden",
                    filetypes=[("SVG Dateien", "*.svg"), ("PNG Bilder", "*.png"), ("Alle Dateien", "*.*")]
                )
                if filepath:
                    # WICHTIG: Lade Hintergrundbild ZUERST
                    if filepath.lower().endswith('.svg'):
                        try:
                            import cairosvg
                            from io import BytesIO
                            from PIL import Image
                            print(f"📂 Lade SVG als Hintergrund: {filepath}")
                            png_data = cairosvg.svg2png(url=filepath, scale=1)
                            bg_image = Image.open(BytesIO(png_data))
                            hex_map.image_width = bg_image.width
                            hex_map.image_height = bg_image.height
                            print(f"✅ Hintergrundbild geladen: {bg_image.size}")
                        except Exception as e:
                            print(f"⚠️ Konnte SVG nicht als Bild laden: {e}")
                    else:
                        try:
                            from PIL import Image
                            bg_image = Image.open(filepath)
                            hex_map.image_width = bg_image.width
                            hex_map.image_height = bg_image.height
                            print(f"✅ Bild geladen: {bg_image.size}")
                        except Exception as e:
                            print(f"⚠️ Konnte Bild nicht laden: {e}")
                    
                    # Dann Hexagone erkennen
                    success = hex_map.load_from_svg(filepath)
                    if not success:
                        # Frage nach manuellem Grid
                        if self._ask_yes_no("Keine Hexagone erkannt",
                            "In der SVG wurden keine Hexagone erkannt.\n\n"
                            "Soll ein Grid manuell erstellt werden?"):
                            hex_map.create_grid(10, 8, hex_size=45)
                else:
                    return
            else:  # Neues Grid
                hex_map.create_grid(10, 8, hex_size=45)
            
            # Editor öffnen MIT Hintergrundbild
            editor = HexagonMapEditor(self, hex_map)
            if bg_image:
                editor.bg_image = bg_image
                editor._redraw()
            self._update_status(f"Hexagon-Editor geöffnet: {len(hex_map.tiles)} Tiles")
            
        except Exception as e:
            self._show_message("error", "Fehler", f"Hexagon-Editor konnte nicht gestartet werden:\n{e}")
            import traceback
            traceback.print_exc()

    def _open_projector_for_scene(self, scene, source):
        """Öffnet den Projektor direkt mit einer Szene (ohne Beispielmap)"""
        from storyboard_system import SceneType
        from projector_window import ProjectorWindow
        import json
        import os
        
        try:
            print(f"🎬 Öffne Projektor für Szene '{scene.name}'...")
            print(f"   Szenen-Typ: {scene.scene_type}")
            print(f"   Quelle: {source}")
            
            # Schließe existierenden Projektor
            if self.projector_window and self.projector_window.winfo_exists():
                self.projector_window.destroy()
            
            # Map-Daten basierend auf Szenentyp vorbereiten
            map_data = None
            svg_path = None
            
            if scene.scene_type == SceneType.MAP_JSON:
                # JSON-Map laden
                with open(source, 'r', encoding='utf-8') as f:
                    map_data = json.load(f)
                print(f"   ✅ JSON-Map geladen:")
                print(f"      Größe: {map_data.get('width', '?')}x{map_data.get('height', '?')}")
                print(f"      Name: {map_data.get('name', 'unbenannt')}")
                tiles = map_data.get('tiles', [])
                print(f"      Tiles: {len(tiles) if isinstance(tiles, list) else 'dict' if isinstance(tiles, dict) else 'keine'}")
                
                # Prüfe ob die JSON-Map einen SVG-Hintergrund hat
                if map_data.get('is_svg_mode') and map_data.get('svg_path'):
                    svg_path = map_data.get('svg_path')
                    print(f"      🎨 SVG-Modus aktiv: {os.path.basename(svg_path)}")
                    
            elif scene.scene_type == SceneType.MAP_SVG:
                # SVG-Map - parse zu Map-Daten
                svg_path = source
                map_data = self.parse_svg_to_map(source)
                if map_data:
                    map_data["svg_path"] = source
                print(f"   ✅ SVG-Map vorbereitet")
                    
            elif scene.scene_type == SceneType.IMAGE:
                # Bild - erstelle minimale Map-Daten
                from PIL import Image
                img = Image.open(source)
                map_data = {
                    "width": max(1, img.width // 32),
                    "height": max(1, img.height // 32),
                    "tile_size": 32,
                    "background_image": source,
                    "tiles": {},
                    "name": scene.name
                }
                print(f"   ✅ Bild-Map erstellt ({img.width}x{img.height})")
            else:
                # Fallback: Minimale leere Map
                map_data = {
                    "width": 30,
                    "height": 20,
                    "tile_size": 32,
                    "tiles": {},
                    "name": scene.name
                }
                print(f"   ⚠️ Fallback zu leerer Map")
            
            # Projektor öffnen
            if svg_path:
                self.projector_window = ProjectorWindow(
                    self,
                    map_data=map_data,
                    svg_path=svg_path,
                    webcam_tracker=self.webcam_tracker
                )
            else:
                self.projector_window = ProjectorWindow(
                    self,
                    map_data,
                    self.webcam_tracker
                )
            
            print(f"   ✅ Projektor geöffnet mit Szene '{scene.name}'")
            
            # Status im Story Editor aktualisieren
            if hasattr(self, 'story_editor') and self.story_editor:
                self.story_editor._set_status(f"✅ Projektor geöffnet mit '{scene.name}'")
                
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Fehler", 
                f"Projektor konnte nicht mit Szene geöffnet werden:\n\n{e}")

    def _load_scene_to_projector(self, scene, source):
        """Lädt eine Szene in den Projektor"""
        from storyboard_system import SceneType
        import json
        import os
        
        try:
            if not self.projector_window or not self.projector_window.winfo_exists():
                print("⚠️ Projektor nicht verfügbar")
                return
            
            print(f"🎬 Lade Szene '{scene.name}' in Projektor...")
            print(f"   Typ: {scene.scene_type.value}")
            print(f"   Quelle: {source}")
            
            # Je nach Szenentyp laden
            if scene.scene_type == SceneType.MAP_JSON:
                # JSON-Map laden
                with open(source, 'r', encoding='utf-8') as f:
                    map_data = json.load(f)
                self.projector_window.update_map(map_data)
                print(f"   ✅ JSON-Map geladen")
                
            elif scene.scene_type == SceneType.MAP_SVG:
                # SVG-Map laden
                if hasattr(self.projector_window, 'load_svg_map'):
                    self.projector_window.load_svg_map(source)
                    print(f"   ✅ SVG-Map geladen")
                else:
                    # Fallback: Parse SVG zu Map-Daten
                    map_data = self.parse_svg_to_map(source)
                    if map_data:
                        self.projector_window.update_map(map_data)
                        print(f"   ✅ SVG als Map-Daten geladen")
                    
            elif scene.scene_type == SceneType.IMAGE:
                # Bild als Hintergrund laden
                from PIL import Image, ImageTk
                img = Image.open(source)
                
                # Erstelle einfache Map-Daten mit Bild als Hintergrund
                map_data = {
                    "width": img.width // 32 + 1,
                    "height": img.height // 32 + 1,
                    "tile_size": 32,
                    "background_image": source,
                    "tiles": {},
                    "name": scene.name
                }
                
                # Wenn Projektor Bild-Modus unterstützt
                if hasattr(self.projector_window, 'set_background_image'):
                    self.projector_window.set_background_image(source)
                else:
                    self.projector_window.update_map(map_data)
                print(f"   ✅ Bild geladen")
                
            elif scene.scene_type == SceneType.VIDEO:
                # Video-Szene (noch nicht implementiert)
                messagebox.showinfo("Video-Szene", 
                    f"Video-Szenen werden noch nicht unterstützt.\n\n"
                    f"Datei: {source}")
                print(f"   ⚠️ Video noch nicht unterstützt")
                
            elif scene.scene_type == SceneType.CUTSCENE:
                # Cutscene (noch nicht implementiert)
                messagebox.showinfo("Cutscene", 
                    f"Cutscenes werden noch nicht unterstützt.\n\n"
                    f"Datei: {source}")
                print(f"   ⚠️ Cutscene noch nicht unterstützt")
            
            # Status aktualisieren
            if hasattr(self, 'story_editor') and self.story_editor:
                self.story_editor._set_status(f"✅ Szene '{scene.name}' im Projektor geladen")
                
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
            messagebox.showerror("Fehler beim Laden", 
                f"Die Szene konnte nicht geladen werden:\n\n{e}")

    def parse_svg_to_map(self, svg_path):
        """Parst SVG und erstellt Map-Daten für Editor"""
        try:
            import xml.etree.ElementTree as ET
            from PIL import Image, ImageTk
            import io
            import base64
            
            print(f"🔍 Parse SVG: {svg_path}")
            
            # Parse SVG
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # SVG-Dimensionen
            svg_width = float(root.get('width', '1000').replace('px', ''))
            svg_height = float(root.get('height', '1000').replace('px', ''))
            
            print(f"   SVG-Größe: {svg_width}×{svg_height}px")
            
            # Zähle embedded images
            images = [elem for elem in root.iter() if 'image' in elem.tag]
            print(f"   Gefundene <image> Elemente: {len(images)}")
            
            # STRATEGIE: SVGs mit vielen embedded images
            # → Verwende FESTE Tile-Größe für bessere Auflösung (nicht Image-Größe!)
            # Die Images in der SVG sind oft zu groß (z.B. 206px)
            # Wir wollen aber eine editierbare Map mit vielen Tiles
            tile_size = 64  # FESTE Tile-Größe für gute Balance zwischen Detail und Performance
            
            if images:
                first_img = images[0]
                img_width = float(first_img.get('width', 32))
                img_height = float(first_img.get('height', 32))
                print(f"   SVG enthält {len(images)} Images à {int(img_width)}×{int(img_height)}px")
                print(f"   → Konvertiere zu {tile_size}px Tiles für bessere Editierbarkeit")
            else:
                print(f"   → Verwende {tile_size}px Tiles")
            
            # Berechne Grid-Größe basierend auf SVG-Dimensionen und Tile-Größe
            # Runde auf, um sicherzustellen dass alle Tiles passen
            import math
            grid_width = max(10, math.ceil(svg_width / tile_size))
            grid_height = max(7, math.ceil(svg_height / tile_size))
            
            print(f"   Grid: {grid_width}×{grid_height} tiles")
            
            # Erstelle leeres Tile-Array
            tiles = [["empty" for _ in range(grid_width)] for _ in range(grid_height)]
            
            # Sammle Materials aus SVG
            materials_found = set()
            tiles_filled = 0
            
            # Tracking: Welche Tiles wurden bereits gefüllt?
            filled_positions = set()
            
            # Parse alle <image> Elemente
            for img_elem in images:
                try:
                    x = float(img_elem.get('x', 0))
                    y = float(img_elem.get('y', 0))
                    w = float(img_elem.get('width', 64))
                    h = float(img_elem.get('height', 64))
                    
                    # href kann base64-kodiertes Bild sein
                    href = img_elem.get('{http://www.w3.org/1999/xlink}href', img_elem.get('href', ''))
                    
                    # Versuche Material aus base64-Daten zu erraten
                    material = 'grass'  # Default
                    
                    if href.startswith('data:image'):
                        # Base64-kodiertes Bild → Analysiere Bildfarben
                        try:
                            # Extrahiere base64-Daten
                            base64_data = href.split(',')[1] if ',' in href else href
                            img_data = base64.b64decode(base64_data)
                            pil_img = Image.open(io.BytesIO(img_data))
                            
                            # Analysiere dominante Farbe (vereinfacht)
                            pil_img_small = pil_img.resize((10, 10), Image.Resampling.LANCZOS)
                            colors = pil_img_small.convert('RGB').getcolors(maxcolors=100)
                            if colors:
                                # Häufigste Farbe
                                dominant_color = max(colors, key=lambda x: x[0])[1]
                                r, g, b = dominant_color
                                
                                # Material aus dominanter Farbe erraten
                                if g > r and g > b:  # Grünlich
                                    if g > 150:
                                        material = 'grass'
                                    else:
                                        material = 'forest'
                                elif b > r and b > g and b > 100:  # Bläulich
                                    material = 'water'
                                elif r > 150 and g > 150 and b < 100:  # Gelblich
                                    material = 'sand'
                                elif r < 100 and g < 100 and b < 100:  # Dunkel
                                    material = 'mountain'
                                elif r > 100 and g > 100 and b > 100:  # Hell grau
                                    material = 'stone'
                                elif r > 100 and g > 80 and b < 80:  # Bräunlich
                                    material = 'road'
                        except:
                            pass
                    
                    materials_found.add(material)
                    
                    # Tile-Koordinaten berechnen: Ein Image deckt mehrere Tiles ab
                    # Berechne welche Tiles von diesem Image abgedeckt werden
                    tx_start = int(x / tile_size)
                    ty_start = int(y / tile_size)
                    tx_end = min(grid_width, int((x + w) / tile_size) + 1)
                    ty_end = min(grid_height, int((y + h) / tile_size) + 1)
                    
                    # Fülle alle Tiles die von diesem Image abgedeckt werden
                    for ty in range(ty_start, ty_end):
                        for tx in range(tx_start, tx_end):
                            if 0 <= ty < grid_height and 0 <= tx < grid_width:
                                pos_key = (ty, tx)
                                if pos_key not in filled_positions:
                                    tiles[ty][tx] = material
                                    filled_positions.add(pos_key)
                                    tiles_filled += 1
                
                except Exception as e:
                    print(f"      Fehler bei Image-Element: {e}")
                    continue
            
            # Parse alle <rect> Elemente (falls vorhanden)
            rects = [elem for elem in root.iter() if 'rect' in elem.tag]
            for rect_elem in rects:
                try:
                    x = float(rect_elem.get('x', 0))
                    y = float(rect_elem.get('y', 0))
                    w = float(rect_elem.get('width', tile_size))
                    h = float(rect_elem.get('height', tile_size))
                    
                    fill = rect_elem.get('fill', 'grass')
                    elem_id = rect_elem.get('id', '')
                    
                    material = self.guess_material_from_svg(elem_id, fill)
                    materials_found.add(material)
                    
                    # Tile-Koordinaten
                    tx1 = int(x / tile_size)
                    ty1 = int(y / tile_size)
                    tx2 = min(grid_width, int((x + w) / tile_size) + 1)
                    ty2 = min(grid_height, int((y + h) / tile_size) + 1)
                    
                    for ty in range(ty1, ty2):
                        for tx in range(tx1, tx2):
                            if 0 <= ty < grid_height and 0 <= tx < grid_width:
                                tiles[ty][tx] = material
                                tiles_filled += 1
                except:
                    continue
            
            # Fülle leere Tiles mit grass (falls SVG Lücken hat)
            empty_count = 0
            for ty in range(grid_height):
                for tx in range(grid_width):
                    if tiles[ty][tx] == "empty":
                        tiles[ty][tx] = "grass"
                        empty_count += 1
            
            print(f"   Materials gefunden: {materials_found}")
            print(f"   Tiles gefüllt: {tiles_filled}/{grid_width * grid_height} ({empty_count} mit 'grass' aufgefüllt)")
            print(f"   ℹ️ Hinweis: SVG-Texturen werden farbanalysiert und in Tiles konvertiert")
            
            return {
                "is_svg_mode": True,
                "svg_path": svg_path,
                "width": grid_width,
                "height": grid_height,
                "tiles": tiles,
                "river_directions": {},
                "version": "2.0-svg",
                "original_svg_size": (svg_width, svg_height)
            }
            
        except Exception as e:
            print(f"❌ SVG-Parse-Fehler: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def guess_material_from_svg(self, elem_id, fill_color):
        """Errät Material aus SVG-Element-ID, Farbe oder base64 data"""
        elem_id = elem_id.lower()
        fill_color = fill_color.lower()
        
        # Material-Keywords
        if 'grass' in elem_id or 'wiese' in elem_id or '#90ee90' in fill_color:
            return 'grass'
        elif 'water' in elem_id or 'wasser' in elem_id or '#4169e1' in fill_color:
            return 'water'
        elif 'forest' in elem_id or 'wald' in elem_id or 'tree' in elem_id or '#228b22' in fill_color:
            return 'forest'
        elif 'mountain' in elem_id or 'berg' in elem_id or '#808080' in fill_color:
            return 'mountain'
        elif 'sand' in elem_id or 'desert' in elem_id or '#f4a460' in fill_color:
            return 'sand'
        elif 'stone' in elem_id or 'stein' in elem_id or 'rock' in elem_id:
            return 'stone'
        elif 'road' in elem_id or 'weg' in elem_id or 'path' in elem_id:
            return 'road'
        elif 'village' in elem_id or 'dorf' in elem_id or 'town' in elem_id:
            return 'village'
        else:
            return 'grass'  # Default
    
    def load_map(self):
        """Karte laden - unterstützt JSON und SVG"""
        print(f"\n🔍 DEBUG load_map() aufgerufen!")
        print(f"   Vor Laden: self.current_map_data = {'vorhanden' if self.current_map_data else 'None'}")
        
        filename = filedialog.askopenfilename(
            title="Karte laden",
            filetypes=[("Alle Dateien", "*.*"), ("JSON Dateien", "*.json"), ("SVG Dateien", "*.svg")],
            initialdir="maps"
        )
        
        print(f"   Ausgewählte Datei: {filename if filename else 'ABGEBROCHEN'}")
        
        if filename:
            # SVG? → Parse und konvertiere zu editierbarem Format
            if filename.lower().endswith('.svg'):
                self.loaded_svg_path = filename
                print(f"📌 SVG wird geladen: {filename}")
                
                try:
                    # Für komplexe SVGs: Biete zwei Optionen an
                    choice = messagebox.askquestion(
                        "SVG laden",
                        f"SVG-Datei: {os.path.basename(filename)}\n\n"
                        f"Wie möchtest du die SVG öffnen?\n\n"
                        f"JA = Im Projektor anzeigen (empfohlen für komplexe SVGs)\n"
                        f"NEIN = In Editor konvertieren (nur für einfache SVGs)",
                        icon='question'
                    )
                    
                    if choice == 'yes':
                        # Projektor-Modus
                        messagebox.showinfo("SVG geladen", 
                            f"✅ SVG-Karte geladen!\n\n"
                            f"Datei: {os.path.basename(filename)}\n\n"
                            f"Öffne jetzt '📺 Projektor-Modus' um die SVG anzuzeigen.\n\n"
                            f"Tipp: Im Projektor kannst du zoomen, pannen und Fog-of-War nutzen!")
                        return
                    
                    # Editor-Modus: Parse SVG
                    svg_map_data = self.parse_svg_to_map(filename)
                    
                    if svg_map_data:
                        self.current_map_data = svg_map_data
                        
                        msg = (f"✅ SVG-Karte geladen!\n\n"
                               f"Datei: {os.path.basename(filename)}\n"
                               f"Größe: {svg_map_data.get('width')}×{svg_map_data.get('height')}\n\n"
                               f"Die SVG wurde in ein editierbares Tile-Grid konvertiert.\n"
                               f"Du kannst sie jetzt mit allen Tools bearbeiten!\n\n"
                               f"Im Editor öffnen?")
                        
                        if messagebox.askyesno("SVG geladen", msg):
                            self.start_editor()
                        else:
                            messagebox.showinfo("Info", "SVG geladen! Öffne Editor oder Projektor.")
                    else:
                        messagebox.showerror("Fehler", "SVG konnte nicht geparst werden")
                        
                except Exception as e:
                    import traceback
                    print(f"❌ SVG-Fehler:\n{traceback.format_exc()}")
                    messagebox.showerror("SVG-Fehler", f"Fehler beim Laden:\n{e}")
                return
            
            # JSON → Prüfe ob Hexagon-Map oder normale Karte
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # Prüfe ob es eine Hexagon-Map ist (hat "hex_size" und "tiles" als Dict mit Koordinaten)
                if "hex_size" in json_data and "tiles" in json_data and isinstance(json_data["tiles"], dict):
                    # Das ist eine Hexagon-Map → öffne im Hexagon-Editor
                    print(f"📐 Hexagon-Map erkannt: {os.path.basename(filename)}")
                    
                    tile_count = len(json_data.get("tiles", {}))
                    hex_size = json_data.get("hex_size", 0)
                    name = json_data.get("name", "Unbenannt")
                    
                    msg = (f"🗺️ Hexagon-Karte erkannt!\n\n"
                           f"Name: {name}\n"
                           f"Hex-Größe: {hex_size:.1f}\n"
                           f"Tiles: {tile_count}\n\n"
                           f"Im Hexagon-Editor öffnen?")
                    
                    if messagebox.askyesno("Hexagon-Map", msg):
                        self._open_hexagon_editor_with_map(filename)
                    return
                
                # Normale Karte → Lade mit MapSystem
                from map_system import MapSystem
                ms = MapSystem()
                map_data = ms.load_map(filename)
                
                print(f"\n🔍 DEBUG load_map:")
                print(f"   Datei: {os.path.basename(filename)}")
                print(f"   map_data: {'vorhanden' if map_data else 'None'}")
                if map_data:
                    print(f"   Größe: {map_data.get('width')}×{map_data.get('height')}")
                    print(f"   Keys: {list(map_data.keys())}")
                
                if map_data:
                    self.current_map_data = map_data
                    self.loaded_svg_path = None  # Reset SVG-Modus
                    
                    print(f"✅ self.current_map_data gesetzt!")
                    print(f"   self.current_map_data ist: {'vorhanden' if self.current_map_data else 'None'}")
                    
                    # Frage ob Editor geöffnet werden soll
                    msg = f"Karte geladen:\n{os.path.basename(filename)}\n\nGröße: {map_data.get('width')}×{map_data.get('height')}\n\nIm Editor öffnen?"
                    
                    if messagebox.askyesno("Karte geladen", msg):
                        print(f"🚀 Rufe start_editor() auf...")
                        self.start_editor()
                    else:
                        messagebox.showinfo("Info", "Karte geladen! Du kannst sie jetzt im Editor oder Projektor öffnen.")
                else:
                    messagebox.showerror("Fehler", "Karte konnte nicht geladen werden")
            except Exception as e:
                import traceback
                print(f"❌ FEHLER beim Laden:\n{traceback.format_exc()}")
                messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
    
    def show_map_list(self):
        """Liste aller gespeicherten Karten anzeigen"""
        try:
            from map_system import MapSystem
            ms = MapSystem()
            maps = ms.list_maps()
            
            if not maps:
                messagebox.showinfo("Keine Karten", "Noch keine Karten gespeichert.\nErstelle zuerst eine Karte im Editor!")
                return
            
            # Listenfenster erstellen
            list_win = tk.Toplevel(self)
            list_win.title("Gespeicherte Karten")
            list_win.geometry("600x400")
            list_win.configure(bg="#1a1a1a")
            
            tk.Label(list_win, text="📋 Gespeicherte Karten", 
                    font=("Arial", 16, "bold"),
                    bg="#1a1a1a", fg="white").pack(pady=10)
            
            # Listbox mit Scrollbar
            frame = tk.Frame(list_win, bg="#1a1a1a")
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                               bg="#2a2a2a", fg="white",
                               font=("Courier", 10),
                               selectmode=tk.SINGLE)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Karten einfügen
            for filename, created, size in maps:
                listbox.insert(tk.END, f"{filename:30} | {size:8} | {created[:19]}")
            
            # Buttons
            btn_frame = tk.Frame(list_win, bg="#1a1a1a")
            btn_frame.pack(pady=10)
            
            def load_selected():
                selection = listbox.curselection()
                if selection:
                    idx = selection[0]
                    filename = maps[idx][0]
                    
                    # SVG? → Merke Pfad für Projektor
                    if filename.lower().endswith('.svg'):
                        self.loaded_svg_path = os.path.join('maps', filename)
                        messagebox.showinfo("SVG geladen", 
                            f"✅ {filename} geladen!\n\n"
                            f"Öffne nun '📺 Projektor-Modus'")
                        list_win.destroy()
                        return
                    
                    # JSON → Lade als normale Karte
                    map_data = ms.load_map(filename)
                    if map_data:
                        self.current_map_data = map_data
                        self.loaded_svg_path = None  # Reset SVG-Modus
                        messagebox.showinfo("Erfolg", f"Karte geladen: {filename}")
                        list_win.destroy()
            
            tk.Button(btn_frame, text="📂 Laden", bg="#2a7d2a", fg="white",
                     padx=20, command=load_selected).pack(side=tk.LEFT, padx=5)
            
            tk.Button(btn_frame, text="❌ Schließen", bg="#7d2a2a", fg="white",
                     padx=20, command=list_win.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Liste:\n{e}")
    
    def show_help(self):
        """Hilfe anzeigen"""
        help_text = """
🗺️ Der Eine Ring VTT - Anleitung

📝 EDITOR-MODUS:
• Klicke auf ein Terrain (Gras, Wasser, etc.)
• Klicke oder ziehe auf der Karte zum Zeichnen
• Speichere deine Karte mit dem 💾 Button

📺 PROJEKTOR-MODUS:
• Zeigt die Karte im Vollbild
• Perfekt für einen zweiten Monitor/Beamer
• Fog-of-War System für verborgene Bereiche
• Klicke und ziehe zum Bewegen
• Mausrad zum Zoomen
• ESC zum Beenden
• F11 für Vollbild an/aus

🎮 GAMEMASTER PANEL:
• Webcam-Tracking aktivieren
• Fog-of-War manuell steuern
• Zoom und Kamera kontrollieren
• Live-Vorschau der Webcam
• Spieltisch kalibrieren

📹 WEBCAM-TRACKING:
• Webcam über dem Spieltisch montieren
• Im GM-Panel "Start Tracking" klicken
• Spieltisch kalibrieren (4 Ecken markieren)
• Hand oder Figuren bewegen - Fog lichtet sich automatisch
• Sichtweite im GM-Panel anpassen

🌫️ FOG-OF-WAR:
• Anfangs ist gesamte Karte verborgen
• Fog lichtet sich automatisch durch Spielerbewegung
• Gamemaster kann manuell Bereiche auf/zudecken
• Sichtweite anpassbar (1-10 Tiles)

💡 TIPPS:
• Erstelle Karten im Editor
• Starte Projektor für Spieler (2. Monitor/Beamer)
• Öffne GM-Panel für Kontrolle
• Aktiviere Webcam-Tracking
• Nutze manuelle Fog-Steuerung für besondere Szenen

⌨️ TASTENKÜRZEL:
• ESC - Projektor beenden
• F11 - Vollbild umschalten
"""
        
        help_win = tk.Toplevel(self)
        help_win.title("Hilfe")
        help_win.geometry("650x700")
        help_win.configure(bg="#1a1a1a")
        
        text = tk.Text(help_win, wrap=tk.WORD, 
                      bg="#2a2a2a", fg="white",
                      font=("Courier", 10),
                      padx=20, pady=20)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", help_text)
        text.config(state=tk.DISABLED)
        
        tk.Button(help_win, text="OK", bg="#2a7d2a", fg="white",
                 padx=30, command=help_win.destroy).pack(pady=10)
    
    def import_png_map(self):
        """PNG-Karte importieren mit Dialog"""
        # PNG-Datei auswählen
        png_path = filedialog.askopenfilename(
            title="PNG-Karte auswählen",
            filetypes=[("PNG Bilder", "*.png"), ("Alle Dateien", "*.*")]
        )
        
        if not png_path:
            return
        
        # Import-Dialog erstellen (BREITER für mehr Platz!)
        dialog = tk.Toplevel(self)
        dialog.title("PNG-Karte importieren")
        dialog.geometry("950x750")  # Breiter: 750→950
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Canvas + Scrollbar für scrollbaren Inhalt
        main_canvas = tk.Canvas(dialog, bg="#1a1a1a", highlightthickness=0)
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg="#1a1a1a")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mausrad-Scrolling
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Header (in scrollable_frame)
        tk.Label(scrollable_frame, text="🖼️ PNG-Karte importieren",
                font=("Arial", 18, "bold"),
                bg="#1a1a1a", fg="#d4af37").pack(pady=10)
        
        # Dateiinfo
        info_frame = tk.LabelFrame(scrollable_frame, text="Datei-Info", 
                                  bg="#2a2a2a", fg="white", 
                                  font=("Arial", 10, "bold"))
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(info_frame, text=f"📁 {os.path.basename(png_path)}",
                bg="#2a2a2a", fg="white", 
                font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=5)
        
        # Bild laden für Info
        from PIL import Image, ImageTk
        img = Image.open(png_path)
        img_w, img_h = img.size
        
        tk.Label(info_frame, text=f"📐 Größe: {img_w} x {img_h} Pixel",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # AUTOMATISCHE EMPFEHLUNG basierend auf PNG-Größe
        max_dimension = max(img_w, img_h)
        recommended_tile_size = 64  # Default
        
        if max_dimension > 8000:
            recommended_tile_size = 512
            recommendation = "🔥🔥 EXTREM! Empfehlung: 512px Tiles"
            rec_color = "#ff0000"
        elif max_dimension > 6000:
            recommended_tile_size = 384
            recommendation = "🔥 Riesig! Empfehlung: 384px Tiles"
            rec_color = "#ff3333"
        elif max_dimension > 4000:
            recommended_tile_size = 256
            recommendation = "🔥 Sehr groß! Empfehlung: 256px Tiles"
            rec_color = "#ff6666"
        elif max_dimension > 3000:
            recommended_tile_size = 192
            recommendation = "⚠️ Groß! Empfehlung: 192px Tiles"
            rec_color = "#ffaa00"
        elif max_dimension > 2000:
            recommended_tile_size = 128
            recommendation = "⚠️ Mittel-groß! Empfehlung: 128px Tiles"
            rec_color = "#ffcc00"
        else:
            recommendation = "✅ Normale Größe - 64px Tiles OK"
            rec_color = "#44ff44"
        
        tk.Label(info_frame, text=recommendation,
                bg="#2a2a2a", fg=rec_color,
                font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        
        # Import-Optionen
        options_frame = tk.LabelFrame(scrollable_frame, text="Import-Optionen",
                                     bg="#2a2a2a", fg="white",
                                     font=("Arial", 10, "bold"))
        options_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Import-Modus
        mode_frame = tk.Frame(options_frame, bg="#2a2a2a")
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(mode_frame, text="Import-Modus:",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        import_mode = tk.StringVar(value="grid")
        
        tk.Radiobutton(mode_frame, text="🔲 Grid-Modus (PNG in Tiles aufteilen)",
                      variable=import_mode, value="grid",
                      bg="#2a2a2a", fg="white", selectcolor="#1a1a1a",
                      font=("Arial", 9)).pack(anchor=tk.W, padx=20, pady=2)
        
        tk.Radiobutton(mode_frame, text="🖼️ Single-Modus (PNG als eine Textur) ⭐ FÜR GROSSE BILDER",
                      variable=import_mode, value="single",
                      bg="#2a2a2a", fg="white", selectcolor="#1a1a1a",
                      font=("Arial", 9)).pack(anchor=tk.W, padx=20, pady=2)
        
        # Hilfe-Text
        tk.Label(mode_frame, 
                text="💡 Bei großen Bildern (>2000px) nutze Single-Modus!",
                bg="#2a2a2a", fg="#ffaa66", font=("Arial", 8, "italic")).pack(anchor=tk.W, padx=20, pady=2)
        
        # Tile-Größe (nur für Grid-Modus)
        tile_frame = tk.Frame(options_frame, bg="#2a2a2a")
        tile_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(tile_frame, text="Tile-Größe (Grid-Modus):",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # Nutze empfohlene Tile-Größe als Default
        tile_size_var = tk.IntVar(value=recommended_tile_size)
        
        tile_size_frame = tk.Frame(tile_frame, bg="#2a2a2a")
        tile_size_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Verbesserter Slider mit Markierungen (bis 512px!)
        slider = tk.Scale(tile_size_frame, from_=32, to=512, orient=tk.HORIZONTAL,
                variable=tile_size_var, bg="#2a2a2a", fg="white",
                font=("Arial", 9), length=400,
                tickinterval=64,  # Zeigt 32, 96, 160, 224, 288, 352, 416, 480
                resolution=16,  # Schritte von 16px
                troughcolor="#1a1a1a",
                highlightthickness=0)
        slider.pack(side=tk.LEFT)
        
        # Live-Info-Label (größer und besser sichtbar)
        tile_info_label = tk.Label(tile_size_frame, text=f"{recommended_tile_size}px → {img_w//recommended_tile_size}×{img_h//recommended_tile_size}",
                                   bg="#2a2a2a", fg="#66ff66",
                                   font=("Arial", 11, "bold"))
        tile_info_label.pack(side=tk.LEFT, padx=15)
        
        # Quick-Select Buttons für gängige Größen
        quick_frame = tk.Frame(tile_frame, bg="#2a2a2a")
        quick_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(quick_frame, text="Schnellwahl:",
                bg="#2a2a2a", fg="#888",
                font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        
        for size in [32, 64, 96, 128, 192, 256, 384, 512]:
            btn = tk.Button(quick_frame, text=f"{size}px",
                          bg="#3a3a3a", fg="white",
                          font=("Arial", 7),
                          padx=5, pady=2,
                          command=lambda s=size: tile_size_var.set(s))
            btn.pack(side=tk.LEFT, padx=2)
            
            # Empfohlenen Button hervorheben
            if size == recommended_tile_size:
                btn.config(bg="#2a7d2a", font=("Arial", 7, "bold"))
        
        def update_tile_info(*args):
            ts = tile_size_var.get()
            grid_w = img_w // ts
            grid_h = img_h // ts
            total_tiles = grid_w * grid_h
            
            # Größe und Grid-Info
            base_text = f"{ts}px → {grid_w}×{grid_h} = {total_tiles} Tiles"
            
            # Warnung bei zu vielen Tiles mit Emoji
            if total_tiles > 2500:
                tile_info_label.config(
                    text=f"{base_text} ❌",
                    fg="#ff3333"
                )
            elif total_tiles > 1500:
                tile_info_label.config(
                    text=f"{base_text} ⚠️",
                    fg="#ffaa00"
                )
            else:
                tile_info_label.config(
                    text=f"{base_text} ✅",
                    fg="#44ff44"
                )
        
        tile_size_var.trace('w', update_tile_info)
        
        # Map-Name
        name_frame = tk.Frame(options_frame, bg="#2a2a2a")
        name_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(name_frame, text="Map-Name:",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        map_name_var = tk.StringVar(value=os.path.splitext(os.path.basename(png_path))[0])
        tk.Entry(name_frame, textvariable=map_name_var,
                bg="#3a3a3a", fg="white", font=("Arial", 10),
                width=40).pack(anchor=tk.W, padx=20, pady=5)
        
        # Speicherpfad für Tile-Set (nur Grid-Modus)
        storage_frame = tk.Frame(options_frame, bg="#2a2a2a")
        storage_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(storage_frame, text="Speicherpfad für Tile-Set:",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        tk.Label(storage_frame, 
                text="💡 Gib einen Unterordner-Namen an. Tiles werden in imported_maps/DEIN_NAME/ gespeichert",
                bg="#2a2a2a", fg="#888", font=("Arial", 8, "italic")).pack(anchor=tk.W, padx=20, pady=2)
        
        storage_path_var = tk.StringVar(value=map_name_var.get().lower().replace(" ", "_"))
        
        storage_entry_frame = tk.Frame(storage_frame, bg="#2a2a2a")
        storage_entry_frame.pack(anchor=tk.W, padx=20, pady=5)
        
        tk.Label(storage_entry_frame, text="imported_maps/",
                bg="#2a2a2a", fg="#888", font=("Arial", 10)).pack(side=tk.LEFT)
        
        storage_entry = tk.Entry(storage_entry_frame, textvariable=storage_path_var,
                                bg="#3a3a3a", fg="white", font=("Arial", 10),
                                width=30)
        storage_entry.pack(side=tk.LEFT)
        
        tk.Label(storage_entry_frame, text="/",
                bg="#2a2a2a", fg="#888", font=("Arial", 10)).pack(side=tk.LEFT)
        
        # Map-Name ändert auch Speicherpfad
        def sync_storage_path(*args):
            if storage_path_var.get() == "" or not storage_entry.focus_get():
                storage_path_var.set(map_name_var.get().lower().replace(" ", "_"))
        
        map_name_var.trace('w', sync_storage_path)
        
        # Preview
        preview_frame = tk.LabelFrame(scrollable_frame, text="Vorschau",
                                     bg="#2a2a2a", fg="white",
                                     font=("Arial", 10, "bold"))
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        preview_label = tk.Label(preview_frame, bg="#1a1a1a")
        preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def update_preview(*args):
            from png_map_importer import PNGMapImporter
            importer = PNGMapImporter()
            
            if import_mode.get() == "grid":
                preview_img = importer.get_import_preview(png_path, tile_size_var.get(), preview_size=400)
            else:
                preview_img = Image.open(png_path)
                preview_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            if preview_img:
                photo = ImageTk.PhotoImage(preview_img)
                preview_label.config(image=photo)
                preview_label.image = photo
        
        import_mode.trace('w', update_preview)
        tile_size_var.trace('w', update_preview)
        update_preview()
        
        # Buttons (AUSSERHALB scrollable_frame, fixiert am unteren Rand)
        button_frame = tk.Frame(dialog, bg="#1a1a1a")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        def do_import():
            try:
                from png_map_importer import PNGMapImporter
                importer = PNGMapImporter()
                
                map_name = map_name_var.get()
                storage_path = storage_path_var.get().strip()
                
                # Validiere Speicherpfad
                if not storage_path:
                    storage_path = map_name.lower().replace(" ", "_")
                
                if import_mode.get() == "grid":
                    # Grid-Import mit Custom-Speicherpfad
                    # Ändere den texture_storage_dir des Importers
                    custom_storage_dir = os.path.join("imported_maps", storage_path)
                    importer.texture_storage_dir = custom_storage_dir
                    
                    self.current_map_data = importer.import_png_map(
                        png_path, 
                        tile_size=tile_size_var.get(),
                        map_name=map_name
                    )
                    msg = f"✅ Map importiert: {self.current_map_data['width']}x{self.current_map_data['height']} Tiles\n"
                    msg += f"📁 Tiles gespeichert in: {custom_storage_dir}"
                else:
                    # Single-Texture-Import
                    self.current_map_data = importer.import_png_as_single_texture(
                        png_path,
                        map_width=50,
                        map_height=50
                    )
                    msg = f"✅ Map als einzelne Textur importiert"
                
                # Info über Bundle (wird automatisch im Editor erstellt)
                if import_mode.get() == "grid" and "custom_materials" in self.current_map_data:
                    material_count = len(self.current_map_data["custom_materials"])
                    if material_count > 20:
                        msg += f"\n\n📦 Material-Bundle wird automatisch im Editor erstellt"
                
                messagebox.showinfo("Erfolg", 
                                   f"{msg}\n\n"
                                   f"Du kannst die Map jetzt:\n"
                                   f"• Im Editor bearbeiten\n"
                                   f"• Als SVG exportieren\n"
                                   f"• Im Projektor anzeigen")
                main_canvas.unbind_all("<MouseWheel>")
                dialog.destroy()
                
                # OPTIONAL: Frage ob Editor direkt öffnen
                if messagebox.askyesno("Editor öffnen?", 
                                      "Möchtest du die importierte Map jetzt im Editor öffnen?"):
                    self.start_editor()
                
            except Exception as e:
                messagebox.showerror("Fehler", f"Import fehlgeschlagen:\n{e}")
        
        def on_dialog_close():
            main_canvas.unbind_all("<MouseWheel>")
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        tk.Button(button_frame, text="✅ Importieren",
                 font=("Arial", 12, "bold"),
                 bg="#2a7d2a", fg="white",
                 padx=30, pady=10,
                 command=do_import).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="❌ Abbrechen",
                 font=("Arial", 12, "bold"),
                 bg="#7d2a2a", fg="white",
                 padx=30, pady=10,
                 command=on_dialog_close).pack(side=tk.LEFT, padx=10)
    
    # =====================================
    # NEUE FOUNDRYVTT-STYLE FEATURES
    # =====================================
    
    def open_combat_tracker(self):
        """Combat Tracker Fenster öffnen"""
        try:
            if self.combat_tracker_window and self.combat_tracker_window.winfo_exists():
                self.combat_tracker_window.lift()
                self.combat_tracker_window.focus_force()
                return
            
            self.combat_tracker_window = CombatTrackerWindow(
                self, 
                self.combat_tracker,
                self.token_layer if hasattr(self, 'token_layer') else None
            )
            self.combat_tracker_window.protocol("WM_DELETE_WINDOW", 
                lambda: self._close_window('combat_tracker_window'))
        except Exception as e:
            messagebox.showerror("Fehler", f"Combat Tracker konnte nicht geöffnet werden:\n{e}")
    
    def open_journal(self):
        """Journal/Notizen Fenster öffnen"""
        try:
            if self.journal_window and self.journal_window.winfo_exists():
                self.journal_window.lift()
                self.journal_window.focus_force()
                return
            
            if self.journal_manager:
                self.journal_window = JournalWindow(self, self.journal_manager)
                self.journal_window.protocol("WM_DELETE_WINDOW", 
                    lambda: self._close_window('journal_window'))
            else:
                messagebox.showwarning("Warnung", "Journal-System nicht verfügbar")
        except Exception as e:
            messagebox.showerror("Fehler", f"Journal konnte nicht geöffnet werden:\n{e}")
    
    def open_settings(self):
        """Einstellungen Fenster öffnen"""
        try:
            if self.settings_window and self.settings_window.winfo_exists():
                self.settings_window.lift()
                self.settings_window.focus_force()
                return
            
            if self.settings_manager:
                self.settings_window = SettingsWindow(self, self.settings_manager)
                self.settings_window.protocol("WM_DELETE_WINDOW", 
                    lambda: self._close_window('settings_window'))
            else:
                messagebox.showwarning("Warnung", "Settings-System nicht verfügbar")
        except Exception as e:
            messagebox.showerror("Fehler", f"Einstellungen konnten nicht geöffnet werden:\n{e}")
    
    def _close_window(self, window_name: str):
        """Hilfsmethode zum sicheren Schließen von Fenstern"""
        window = getattr(self, window_name, None)
        if window:
            try:
                window.destroy()
            except:
                pass
            setattr(self, window_name, None)
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        # Webcam stoppen
        if self.webcam_tracker:
            self.webcam_tracker.stop()
        super().destroy()

if __name__ == "__main__":
    DerEineRingProApp().mainloop()
