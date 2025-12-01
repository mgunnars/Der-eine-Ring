"""
Story Editor - Teil 2: Szenen-Panel
===================================

Erweiterte Kapitel- und Szenen-Verwaltung mit Drag & Drop,
Szenen-Typen und detaillierter Konfiguration.

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, List, Dict, Any
import os

from storyboard_system import (
    Storyboard, Chapter, Scene, Trigger, Action, Overlay,
    SceneType, TriggerType, ActionType
)


class SceneTypeSelector(tk.Toplevel):
    """Dialog zur Auswahl des Szenen-Typs"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Szenen-Typ wählen")
        self.configure(bg="#1a1a2e")
        self.geometry("400x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.selected_type: Optional[SceneType] = None
        self.result_name: str = ""
        
        self._setup_ui()
        self.center_window()
    
    def center_window(self):
        """Zentriert das Fenster"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 450) // 2
        self.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Header
        tk.Label(
            self,
            text="🎬 Neue Szene erstellen",
            bg="#1a1a2e", fg="#e94560",
            font=("Arial", 14, "bold")
        ).pack(pady=15)
        
        # Name
        name_frame = tk.Frame(self, bg="#1a1a2e")
        name_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(name_frame, text="Name:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.name_entry = tk.Entry(
            name_frame, bg="#0f3460", fg="white",
            insertbackground="white", font=("Arial", 11)
        )
        self.name_entry.pack(fill=tk.X, pady=5)
        self.name_entry.focus()
        
        # Typ-Auswahl
        tk.Label(
            self,
            text="Typ wählen:",
            bg="#1a1a2e", fg="white",
            font=("Arial", 11)
        ).pack(anchor=tk.W, padx=20, pady=(10, 5))
        
        types_frame = tk.Frame(self, bg="#1a1a2e")
        types_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        self.type_var = tk.StringVar(value=SceneType.MAP_JSON.value)
        
        type_options = [
            (SceneType.MAP_JSON, "🗺️", "JSON Map", "VTT-Karte im JSON-Format"),
            (SceneType.MAP_SVG, "📐", "SVG Map", "Vektor-basierte Karte"),
            (SceneType.VIDEO, "🎥", "Video Map", "MP4/Video als Hintergrund"),
            (SceneType.IMAGE, "🖼️", "Bild", "Statisches Bild"),
            (SceneType.CUTSCENE, "🎞️", "Cutscene", "Videosequenz ohne Interaktion")
        ]
        
        for scene_type, icon, title, desc in type_options:
            self._create_type_option(types_frame, scene_type, icon, title, desc)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Button(
            btn_frame, text="Abbrechen",
            bg="#555", fg="white",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame, text="Erstellen",
            bg="#e94560", fg="white",
            command=self._create
        ).pack(side=tk.RIGHT, padx=5)
        
        # Enter-Taste
        self.bind("<Return>", lambda e: self._create())
        self.bind("<Escape>", lambda e: self.destroy())
    
    def _create_type_option(self, parent, scene_type: SceneType, icon: str, title: str, desc: str):
        """Erstellt eine Typ-Option"""
        frame = tk.Frame(parent, bg="#16213e", cursor="hand2")
        frame.pack(fill=tk.X, pady=3)
        
        rb = tk.Radiobutton(
            frame,
            variable=self.type_var,
            value=scene_type.value,
            bg="#16213e", fg="white",
            selectcolor="#0f3460",
            activebackground="#16213e"
        )
        rb.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame, text=icon, bg="#16213e", font=("Arial", 16)).pack(side=tk.LEFT, padx=5)
        
        text_frame = tk.Frame(frame, bg="#16213e")
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
        
        tk.Label(text_frame, text=title, bg="#16213e", fg="white", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        tk.Label(text_frame, text=desc, bg="#16213e", fg="#888", font=("Arial", 9)).pack(anchor=tk.W)
        
        # Klick auf ganzen Frame
        for widget in [frame, text_frame]:
            widget.bind("<Button-1>", lambda e, t=scene_type: self._select_type(t))
    
    def _select_type(self, scene_type: SceneType):
        """Typ auswählen"""
        self.type_var.set(scene_type.value)
    
    def _create(self):
        """Szene erstellen"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name fehlt", "Bitte gib einen Namen ein.")
            return
        
        self.result_name = name
        self.selected_type = SceneType(self.type_var.get())
        self.destroy()


class ChapterDialog(tk.Toplevel):
    """Dialog für Kapitel-Erstellung/Bearbeitung"""
    
    def __init__(self, parent, chapter: Optional[Chapter] = None):
        super().__init__(parent)
        
        self.chapter = chapter
        self.result: Optional[Dict[str, Any]] = None
        
        self.title("Kapitel bearbeiten" if chapter else "Neues Kapitel")
        self.configure(bg="#1a1a2e")
        self.geometry("450x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Header
        tk.Label(
            self,
            text="📖 Kapitel konfigurieren",
            bg="#1a1a2e", fg="#e94560",
            font=("Arial", 14, "bold")
        ).pack(pady=15)
        
        # Name
        name_frame = tk.Frame(self, bg="#1a1a2e")
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(name_frame, text="Name:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.name_entry = tk.Entry(
            name_frame, bg="#0f3460", fg="white",
            insertbackground="white", font=("Arial", 11)
        )
        self.name_entry.pack(fill=tk.X, pady=2)
        if self.chapter:
            self.name_entry.insert(0, self.chapter.name)
        self.name_entry.focus()
        
        # Icon
        icon_frame = tk.Frame(self, bg="#1a1a2e")
        icon_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(icon_frame, text="Icon:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        icons_row = tk.Frame(icon_frame, bg="#1a1a2e")
        icons_row.pack(fill=tk.X, pady=2)
        
        self.icon_var = tk.StringVar(value=self.chapter.icon if self.chapter else "📖")
        
        icons = ["📖", "⚔️", "🏰", "🌲", "🌙", "🔥", "💎", "🗡️", "🛡️", "🎭", "👑", "🧙"]
        for icon in icons:
            tk.Radiobutton(
                icons_row,
                text=icon,
                variable=self.icon_var,
                value=icon,
                bg="#1a1a2e",
                fg="white",
                selectcolor="#0f3460",
                font=("Arial", 14),
                indicatoron=False,
                width=3
            ).pack(side=tk.LEFT, padx=1)
        
        # Beschreibung
        desc_frame = tk.Frame(self, bg="#1a1a2e")
        desc_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(desc_frame, text="Beschreibung:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.desc_text = tk.Text(
            desc_frame, bg="#0f3460", fg="white",
            height=5, insertbackground="white"
        )
        self.desc_text.pack(fill=tk.X, pady=2)
        if self.chapter:
            self.desc_text.insert("1.0", self.chapter.description)
        
        # Bedingung für Freischaltung
        cond_frame = tk.Frame(self, bg="#1a1a2e")
        cond_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.locked_var = tk.BooleanVar(value=self.chapter.locked if self.chapter else False)
        tk.Checkbutton(
            cond_frame,
            text="Kapitel ist gesperrt (erfordert Freischaltung)",
            variable=self.locked_var,
            bg="#1a1a2e", fg="white",
            selectcolor="#0f3460",
            activebackground="#1a1a2e"
        ).pack(anchor=tk.W)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Button(
            btn_frame, text="Abbrechen",
            bg="#555", fg="white",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame, text="Speichern",
            bg="#e94560", fg="white",
            command=self._save
        ).pack(side=tk.RIGHT, padx=5)
    
    def _save(self):
        """Kapitel speichern"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name fehlt", "Bitte gib einen Namen ein.")
            return
        
        self.result = {
            "name": name,
            "icon": self.icon_var.get(),
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "locked": self.locked_var.get()
        }
        self.destroy()


class SceneConfigDialog(tk.Toplevel):
    """Erweiterte Szenen-Konfiguration"""
    
    def __init__(self, parent, scene: Scene):
        super().__init__(parent)
        
        self.scene = scene
        self.result: Optional[Dict[str, Any]] = None
        
        self.title(f"Szene konfigurieren: {scene.name}")
        self.configure(bg="#1a1a2e")
        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Scrollbarer Bereich
        canvas = tk.Canvas(self, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        
        main_frame = tk.Frame(canvas, bg="#1a1a2e")
        
        canvas.create_window((0, 0), window=main_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        main_frame.bind("<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Header
        icon = self._get_scene_icon(self.scene.scene_type)
        tk.Label(
            main_frame,
            text=f"{icon} Szene konfigurieren",
            bg="#1a1a2e", fg="#e94560",
            font=("Arial", 14, "bold")
        ).pack(pady=15)
        
        # Grundeinstellungen
        self._create_section(main_frame, "📋 Grundeinstellungen")
        
        # Name
        name_frame = tk.Frame(main_frame, bg="#1a1a2e")
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(name_frame, text="Name:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.name_entry = tk.Entry(name_frame, bg="#0f3460", fg="white", insertbackground="white")
        self.name_entry.insert(0, self.scene.name)
        self.name_entry.pack(fill=tk.X, pady=2)
        
        # Beschreibung
        desc_frame = tk.Frame(main_frame, bg="#1a1a2e")
        desc_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(desc_frame, text="Beschreibung:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.desc_text = tk.Text(desc_frame, bg="#0f3460", fg="white", height=3, insertbackground="white")
        self.desc_text.insert("1.0", self.scene.description)
        self.desc_text.pack(fill=tk.X, pady=2)
        
        # Medien-Einstellungen
        self._create_section(main_frame, "🎬 Medien")
        
        # Hintergrund
        bg_frame = tk.Frame(main_frame, bg="#1a1a2e")
        bg_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(bg_frame, text="Hintergrund:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        bg_row = tk.Frame(bg_frame, bg="#1a1a2e")
        bg_row.pack(fill=tk.X, pady=2)
        
        self.background_entry = tk.Entry(bg_row, bg="#0f3460", fg="white", insertbackground="white")
        self.background_entry.insert(0, self.scene.background_source or "")
        self.background_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(
            bg_row, text="📂",
            bg="#0f3460", fg="white",
            command=self._browse_background
        ).pack(side=tk.RIGHT, padx=5)
        
        # Audio
        audio_frame = tk.Frame(main_frame, bg="#1a1a2e")
        audio_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(audio_frame, text="Hintergrund-Audio:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        audio_row = tk.Frame(audio_frame, bg="#1a1a2e")
        audio_row.pack(fill=tk.X, pady=2)
        
        self.audio_entry = tk.Entry(audio_row, bg="#0f3460", fg="white", insertbackground="white")
        self.audio_entry.insert(0, self.scene.ambient_audio or "")
        self.audio_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(
            audio_row, text="📂",
            bg="#0f3460", fg="white",
            command=self._browse_audio
        ).pack(side=tk.RIGHT, padx=5)
        
        # Audio-Lautstärke
        vol_frame = tk.Frame(main_frame, bg="#1a1a2e")
        vol_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(vol_frame, text="Lautstärke:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        
        self.volume_var = tk.DoubleVar(value=self.scene.ambient_volume)
        volume_scale = tk.Scale(
            vol_frame,
            variable=self.volume_var,
            from_=0, to=1, resolution=0.1,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0, length=200
        )
        volume_scale.pack(side=tk.LEFT, padx=10)
        
        # Optionen
        self._create_section(main_frame, "⚙️ Optionen")
        
        opts_frame = tk.Frame(main_frame, bg="#1a1a2e")
        opts_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.loop_var = tk.BooleanVar(value=self.scene.loop_background)
        tk.Checkbutton(
            opts_frame,
            text="Hintergrund loopen (für Videos)",
            variable=self.loop_var,
            bg="#1a1a2e", fg="white",
            selectcolor="#0f3460"
        ).pack(anchor=tk.W)
        
        self.interactive_var = tk.BooleanVar(value=self.scene.interactive)
        tk.Checkbutton(
            opts_frame,
            text="Interaktiv (Token können bewegt werden)",
            variable=self.interactive_var,
            bg="#1a1a2e", fg="white",
            selectcolor="#0f3460"
        ).pack(anchor=tk.W)
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Button(
            btn_frame, text="Abbrechen",
            bg="#555", fg="white",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame, text="Speichern",
            bg="#e94560", fg="white",
            command=self._save
        ).pack(side=tk.RIGHT, padx=5)
    
    def _create_section(self, parent, title: str):
        """Erstellt eine Sektion mit Titel"""
        sep = tk.Frame(parent, bg="#e94560", height=2)
        sep.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        tk.Label(
            parent,
            text=title,
            bg="#1a1a2e", fg="white",
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W, padx=20, pady=5)
    
    def _get_scene_icon(self, scene_type: SceneType) -> str:
        icons = {
            SceneType.VIDEO: "🎥",
            SceneType.MAP_JSON: "🗺️",
            SceneType.MAP_SVG: "📐",
            SceneType.IMAGE: "🖼️",
            SceneType.CUTSCENE: "🎞️"
        }
        return icons.get(scene_type, "🎬")
    
    def _browse_background(self):
        """Hintergrund-Datei auswählen - basierend auf Szenentyp"""
        # Dateitypen basierend auf Szenentyp
        scene_type = self.scene.scene_type
        
        if scene_type == SceneType.VIDEO:
            filetypes = [
                ("Videos", "*.mp4;*.webm;*.avi;*.mkv"),
                ("MP4", "*.mp4"),
                ("WebM", "*.webm"),
                ("Alle", "*.*")
            ]
            title = "Video-Datei auswählen"
        elif scene_type == SceneType.MAP_JSON:
            filetypes = [
                ("JSON Maps", "*.json"),
                ("Alle", "*.*")
            ]
            title = "JSON Map-Datei auswählen"
        elif scene_type == SceneType.MAP_SVG:
            filetypes = [
                ("SVG Karten", "*.svg"),
                ("Alle", "*.*")
            ]
            title = "SVG Karten-Datei auswählen"
        elif scene_type == SceneType.IMAGE:
            filetypes = [
                ("Bilder", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("Alle", "*.*")
            ]
            title = "Bild-Datei auswählen"
        elif scene_type == SceneType.CUTSCENE:
            filetypes = [
                ("Cutscene Videos", "*.mp4;*.webm"),
                ("MP4", "*.mp4"),
                ("WebM", "*.webm"),
                ("Alle", "*.*")
            ]
            title = "Cutscene-Video auswählen"
        else:
            # Fallback für alle Typen
            filetypes = [
                ("Alle unterstützten", "*.mp4;*.webm;*.json;*.svg;*.png;*.jpg"),
                ("Videos", "*.mp4;*.webm"),
                ("JSON Maps", "*.json"),
                ("SVG", "*.svg"),
                ("Bilder", "*.png;*.jpg;*.jpeg"),
                ("Alle", "*.*")
            ]
            title = "Hintergrund-Datei auswählen"
        
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if filepath:
            self.background_entry.delete(0, tk.END)
            self.background_entry.insert(0, filepath)
    
    def _browse_audio(self):
        """Audio-Datei auswählen"""
        filetypes = [
            ("Audio", "*.mp3;*.wav;*.ogg"),
            ("Alle", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.audio_entry.delete(0, tk.END)
            self.audio_entry.insert(0, filepath)
    
    def _save(self):
        """Szene speichern"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Name fehlt", "Bitte gib einen Namen ein.")
            return
        
        self.result = {
            "name": name,
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "background_source": self.background_entry.get().strip() or None,
            "ambient_audio": self.audio_entry.get().strip() or None,
            "ambient_volume": self.volume_var.get(),
            "loop_background": self.loop_var.get(),
            "interactive": self.interactive_var.get()
        }
        self.destroy()


class ScenesPanel:
    """
    Erweitertes Szenen-Panel mit Drag & Drop
    """
    
    def __init__(self, parent_frame: tk.Frame, editor):
        self.parent = parent_frame
        self.editor = editor  # Referenz zum Haupt-Editor
        
        self.storyboard = editor.storyboard
        self.current_chapter: Optional[Chapter] = None
        self.current_scene: Optional[Scene] = None
        
        # Drag & Drop State
        self._drag_data = {"item": None, "type": None}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Header
        header = tk.Frame(self.parent, bg="#0f3460")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header,
            text="📚 Kapitel & Szenen",
            bg="#0f3460", fg="white",
            font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(header, bg="#0f3460")
        btn_frame.pack(side=tk.RIGHT)
        
        self.add_chapter_btn = tk.Button(
            btn_frame, text="+📖", font=("Arial", 10),
            bg="#2a7d2a", fg="white", relief=tk.FLAT,
            command=self._add_chapter_dialog
        )
        self.add_chapter_btn.pack(side=tk.LEFT, padx=2)
        
        self.add_scene_btn = tk.Button(
            btn_frame, text="+🎬", font=("Arial", 10),
            bg="#2a5d8d", fg="white", relief=tk.FLAT,
            command=self._add_scene_dialog
        )
        self.add_scene_btn.pack(side=tk.LEFT, padx=2)
        
        # Such-Feld
        search_frame = tk.Frame(self.parent, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(search_frame, text="🔍", bg="#16213e", fg="#888").pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg="#0f3460", fg="white",
            insertbackground="white"
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Treeview
        tree_frame = tk.Frame(self.parent, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Style
        style = ttk.Style()
        style.configure("Scenes.Treeview",
                       background="#1a1a2e",
                       foreground="white",
                       fieldbackground="#1a1a2e",
                       rowheight=30)
        style.map("Scenes.Treeview",
                 background=[("selected", "#e94560")],
                 foreground=[("selected", "white")])
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            style="Scenes.Treeview",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            selectmode="browse"
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # Spalten
        self.tree["columns"] = ("type", "triggers", "status")
        self.tree.column("#0", width=200, minwidth=150)
        self.tree.column("type", width=60, minwidth=50)
        self.tree.column("triggers", width=50, minwidth=40)
        self.tree.column("status", width=40, minwidth=40)
        
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Typ")
        self.tree.heading("triggers", text="⚡")
        self.tree.heading("status", text="🔗")
        
        # Events
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Delete>", self._on_delete)
        self.tree.bind("<Button-3>", self._on_right_click)
        
        # Drag & Drop
        self.tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_end)
        
        # Kontext-Menü
        self._create_context_menu()
        
        # Initial refresh
        self.refresh()
    
    def _create_context_menu(self):
        """Erstellt das Kontext-Menü"""
        self.context_menu = tk.Menu(self.parent, tearoff=0, bg="#2a2a4e", fg="white")
        
        self.context_menu.add_command(label="📝 Bearbeiten", command=self._edit_selected)
        self.context_menu.add_command(label="📋 Duplizieren", command=self._duplicate_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⬆️ Nach oben", command=self._move_up)
        self.context_menu.add_command(label="⬇️ Nach unten", command=self._move_down)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Löschen", command=self._delete_selected)
    
    def refresh(self):
        """Aktualisiert die Baumliste"""
        # Alle Items entfernen
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        search_term = self.search_var.get().lower()
        
        # Kapitel und Szenen einfügen
        for chapter in self.storyboard.chapters:
            # Filter prüfen
            if search_term:
                chapter_matches = search_term in chapter.name.lower()
                scenes_match = any(search_term in s.name.lower() for s in chapter.scenes)
                if not chapter_matches and not scenes_match:
                    continue
            
            # Kapitel-Status bestimmen
            status = "🔒" if chapter.locked else ""
            
            # Kapitel einfügen
            chapter_item = self.tree.insert(
                "",
                tk.END,
                iid=chapter.id,
                text=f"{chapter.icon} {chapter.name}",
                values=("📖", f"{len(chapter.scenes)}", status),
                open=True,
                tags=("chapter",)
            )
            
            # Szenen des Kapitels
            for scene in chapter.scenes:
                # Filter prüfen
                if search_term and search_term not in scene.name.lower():
                    continue
                
                scene_icon = self._get_scene_icon(scene.scene_type)
                trigger_count = len(scene.triggers)
                
                # Start-Szene markieren
                is_start = scene.id == chapter.start_scene_id
                status = "🏁" if is_start else ""
                
                self.tree.insert(
                    chapter_item,
                    tk.END,
                    iid=scene.id,
                    text=f"{scene_icon} {scene.name}",
                    values=("🎬", f"{trigger_count}", status),
                    tags=("scene",)
                )
        
        # Stats aktualisieren
        if hasattr(self.editor, 'stats_label'):
            total_chapters = len(self.storyboard.chapters)
            total_scenes = sum(len(c.scenes) for c in self.storyboard.chapters)
            self.editor.stats_label.config(text=f"{total_chapters} Kapitel | {total_scenes} Szenen")
    
    def _get_scene_icon(self, scene_type: SceneType) -> str:
        icons = {
            SceneType.VIDEO: "🎥",
            SceneType.MAP_JSON: "🗺️",
            SceneType.MAP_SVG: "📐",
            SceneType.IMAGE: "🖼️",
            SceneType.CUTSCENE: "🎞️"
        }
        return icons.get(scene_type, "🎬")
    
    # ============================================================
    # EVENT HANDLERS
    # ============================================================
    
    def _on_select(self, event):
        """Auswahl geändert"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.tree.parent(item_id)
        
        if not parent:
            # Kapitel ausgewählt
            for chapter in self.storyboard.chapters:
                if chapter.id == item_id:
                    self.current_chapter = chapter
                    self.current_scene = None
                    self.editor.current_chapter = chapter
                    self.editor.current_scene = None
                    self.editor._refresh_properties()
                    break
        else:
            # Szene ausgewählt
            for chapter in self.storyboard.chapters:
                if chapter.id == parent:
                    self.current_chapter = chapter
                    self.editor.current_chapter = chapter
                    for scene in chapter.scenes:
                        if scene.id == item_id:
                            self.current_scene = scene
                            self.editor.current_scene = scene
                            self.editor._refresh_properties()
                            self.editor._update_flow_graph()
                            break
                    break
    
    def _on_double_click(self, event):
        """Doppelklick - Bearbeiten"""
        self._edit_selected()
    
    def _on_delete(self, event):
        """Entf-Taste - Löschen"""
        self._delete_selected()
    
    def _on_right_click(self, event):
        """Rechtsklick - Kontext-Menü"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def _on_search(self, *args):
        """Such-Eingabe geändert"""
        self.refresh()
    
    # ============================================================
    # DRAG & DROP
    # ============================================================
    
    def _on_drag_start(self, event):
        """Drag gestartet"""
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item
            parent = self.tree.parent(item)
            self._drag_data["type"] = "scene" if parent else "chapter"
    
    def _on_drag_motion(self, event):
        """Drag in Bewegung"""
        # Optional: Visuelles Feedback
        pass
    
    def _on_drag_end(self, event):
        """Drag beendet"""
        if not self._drag_data["item"]:
            return
        
        target = self.tree.identify_row(event.y)
        
        if target and target != self._drag_data["item"]:
            self._perform_drop(self._drag_data["item"], target)
        
        self._drag_data = {"item": None, "type": None}
    
    def _perform_drop(self, source_id: str, target_id: str):
        """Führt den Drop durch"""
        source_parent = self.tree.parent(source_id)
        target_parent = self.tree.parent(target_id)
        
        if self._drag_data["type"] == "chapter":
            # Kapitel umsortieren
            source_idx = None
            target_idx = None
            
            for i, c in enumerate(self.storyboard.chapters):
                if c.id == source_id:
                    source_idx = i
                if c.id == target_id:
                    target_idx = i
            
            if source_idx is not None and target_idx is not None:
                chapter = self.storyboard.chapters.pop(source_idx)
                self.storyboard.chapters.insert(target_idx, chapter)
                self.editor._mark_changed()
                self.refresh()
        
        elif self._drag_data["type"] == "scene" and source_parent == target_parent:
            # Szene innerhalb des gleichen Kapitels umsortieren
            for chapter in self.storyboard.chapters:
                if chapter.id == source_parent:
                    source_idx = None
                    target_idx = None
                    
                    for i, s in enumerate(chapter.scenes):
                        if s.id == source_id:
                            source_idx = i
                        if s.id == target_id:
                            target_idx = i
                    
                    if source_idx is not None and target_idx is not None:
                        scene = chapter.scenes.pop(source_idx)
                        chapter.scenes.insert(target_idx, scene)
                        self.editor._mark_changed()
                        self.refresh()
                    break
    
    # ============================================================
    # AKTIONEN
    # ============================================================
    
    def _add_chapter_dialog(self):
        """Kapitel hinzufügen mit Dialog"""
        dialog = ChapterDialog(self.parent)
        self.parent.wait_window(dialog)
        
        if dialog.result:
            chapter = Chapter(
                name=dialog.result["name"],
                icon=dialog.result["icon"],
                description=dialog.result["description"],
                locked=dialog.result["locked"],
                order=len(self.storyboard.chapters)
            )
            self.storyboard.chapters.append(chapter)
            self.editor._mark_changed()
            self.refresh()
            self.editor._set_status(f"Kapitel '{chapter.name}' hinzugefügt")
    
    def _add_scene_dialog(self):
        """Szene hinzufügen mit Dialog"""
        if not self.current_chapter:
            messagebox.showwarning("Kein Kapitel", "Bitte wähle zuerst ein Kapitel aus.")
            return
        
        dialog = SceneTypeSelector(self.parent)
        self.parent.wait_window(dialog)
        
        if dialog.selected_type and dialog.result_name:
            scene = Scene(
                name=dialog.result_name,
                scene_type=dialog.selected_type
            )
            self.current_chapter.scenes.append(scene)
            
            # Erste Szene = Start-Szene
            if len(self.current_chapter.scenes) == 1:
                self.current_chapter.start_scene_id = scene.id
            
            self.editor._mark_changed()
            self.refresh()
            self.editor._set_status(f"Szene '{scene.name}' hinzugefügt")
    
    def _edit_selected(self):
        """Ausgewähltes Element bearbeiten"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.tree.parent(item_id)
        
        if not parent:
            # Kapitel bearbeiten
            for chapter in self.storyboard.chapters:
                if chapter.id == item_id:
                    dialog = ChapterDialog(self.parent, chapter)
                    self.parent.wait_window(dialog)
                    
                    if dialog.result:
                        chapter.name = dialog.result["name"]
                        chapter.icon = dialog.result["icon"]
                        chapter.description = dialog.result["description"]
                        chapter.locked = dialog.result["locked"]
                        self.editor._mark_changed()
                        self.refresh()
                    break
        else:
            # Szene bearbeiten
            for chapter in self.storyboard.chapters:
                for scene in chapter.scenes:
                    if scene.id == item_id:
                        dialog = SceneConfigDialog(self.parent, scene)
                        self.parent.wait_window(dialog)
                        
                        if dialog.result:
                            scene.name = dialog.result["name"]
                            scene.description = dialog.result["description"]
                            scene.background_source = dialog.result["background_source"]
                            scene.ambient_audio = dialog.result["ambient_audio"]
                            scene.ambient_volume = dialog.result["ambient_volume"]
                            scene.loop_background = dialog.result["loop_background"]
                            scene.interactive = dialog.result["interactive"]
                            self.editor._mark_changed()
                            self.refresh()
                        return
    
    def _duplicate_selected(self):
        """Ausgewähltes Element duplizieren"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.tree.parent(item_id)
        
        if parent:
            # Szene duplizieren
            for chapter in self.storyboard.chapters:
                if chapter.id == parent:
                    for scene in chapter.scenes:
                        if scene.id == item_id:
                            # Kopie erstellen
                            import copy
                            new_scene = Scene(
                                name=f"{scene.name} (Kopie)",
                                scene_type=scene.scene_type,
                                description=scene.description,
                                background_source=scene.background_source
                            )
                            # Trigger kopieren
                            for trigger in scene.triggers:
                                new_trigger = Trigger(
                                    name=trigger.name,
                                    trigger_type=trigger.trigger_type
                                )
                                new_scene.triggers.append(new_trigger)
                            
                            chapter.scenes.append(new_scene)
                            self.editor._mark_changed()
                            self.refresh()
                            self.editor._set_status(f"Szene dupliziert: {new_scene.name}")
                            return
    
    def _move_up(self):
        """Element nach oben verschieben"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.tree.parent(item_id)
        
        if not parent:
            # Kapitel nach oben
            for i, c in enumerate(self.storyboard.chapters):
                if c.id == item_id and i > 0:
                    self.storyboard.chapters[i], self.storyboard.chapters[i-1] = \
                        self.storyboard.chapters[i-1], self.storyboard.chapters[i]
                    self.editor._mark_changed()
                    self.refresh()
                    self.tree.selection_set(item_id)
                    break
        else:
            # Szene nach oben
            for chapter in self.storyboard.chapters:
                if chapter.id == parent:
                    for i, s in enumerate(chapter.scenes):
                        if s.id == item_id and i > 0:
                            chapter.scenes[i], chapter.scenes[i-1] = \
                                chapter.scenes[i-1], chapter.scenes[i]
                            self.editor._mark_changed()
                            self.refresh()
                            self.tree.selection_set(item_id)
                            return
    
    def _move_down(self):
        """Element nach unten verschieben"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.tree.parent(item_id)
        
        if not parent:
            # Kapitel nach unten
            for i, c in enumerate(self.storyboard.chapters):
                if c.id == item_id and i < len(self.storyboard.chapters) - 1:
                    self.storyboard.chapters[i], self.storyboard.chapters[i+1] = \
                        self.storyboard.chapters[i+1], self.storyboard.chapters[i]
                    self.editor._mark_changed()
                    self.refresh()
                    self.tree.selection_set(item_id)
                    break
        else:
            # Szene nach unten
            for chapter in self.storyboard.chapters:
                if chapter.id == parent:
                    for i, s in enumerate(chapter.scenes):
                        if s.id == item_id and i < len(chapter.scenes) - 1:
                            chapter.scenes[i], chapter.scenes[i+1] = \
                                chapter.scenes[i+1], chapter.scenes[i]
                            self.editor._mark_changed()
                            self.refresh()
                            self.tree.selection_set(item_id)
                            return
    
    def _delete_selected(self):
        """Ausgewähltes Element löschen"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.tree.parent(item_id)
        
        if not parent:
            # Kapitel löschen
            if messagebox.askyesno("Kapitel löschen", 
                                   "Kapitel wirklich löschen?\nAlle Szenen werden ebenfalls gelöscht!"):
                self.storyboard.chapters = [c for c in self.storyboard.chapters if c.id != item_id]
                self.current_chapter = None
                self.current_scene = None
                self.editor.current_chapter = None
                self.editor.current_scene = None
                self.editor._mark_changed()
                self.refresh()
        else:
            # Szene löschen
            if messagebox.askyesno("Szene löschen", "Szene wirklich löschen?"):
                for chapter in self.storyboard.chapters:
                    if chapter.id == parent:
                        chapter.scenes = [s for s in chapter.scenes if s.id != item_id]
                        self.current_scene = None
                        self.editor.current_scene = None
                        self.editor._mark_changed()
                        self.refresh()
                        break


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    # Einfacher Test
    root = tk.Tk()
    root.title("Szenen-Panel Test")
    root.geometry("400x600")
    root.configure(bg="#1a1a2e")
    
    # Mock Editor
    class MockEditor:
        def __init__(self):
            self.storyboard = Storyboard(name="Test")
            self.current_chapter = None
            self.current_scene = None
            
            # Test-Daten
            ch1 = Chapter(name="Prolog", icon="📖")
            ch1.scenes.append(Scene(name="Einführung", scene_type=SceneType.IMAGE))
            ch1.scenes.append(Scene(name="Dorf", scene_type=SceneType.MAP_JSON))
            
            ch2 = Chapter(name="Kapitel 1", icon="⚔️")
            ch2.scenes.append(Scene(name="Der Wald", scene_type=SceneType.VIDEO))
            
            self.storyboard.chapters = [ch1, ch2]
        
        def _refresh_properties(self):
            pass
        
        def _update_flow_graph(self):
            pass
        
        def _mark_changed(self):
            pass
        
        def _set_status(self, msg):
            print(msg)
    
    mock = MockEditor()
    mock.stats_label = tk.Label(root, text="")
    
    frame = tk.Frame(root, bg="#16213e")
    frame.pack(fill=tk.BOTH, expand=True)
    
    panel = ScenesPanel(frame, mock)
    
    root.mainloop()
