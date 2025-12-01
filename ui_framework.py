"""
UI Framework für "Der Eine Ring" VTT
=====================================

Zentrale UI-Komponenten für konsistentes Design und Verhalten.
Behebt häufige Probleme wie:
- Fenster zu schmal/klein
- Dialoge kehren zum Hauptmenü zurück
- Inkonsistentes Styling

Inspiriert von FoundryVTT's UI-Patterns.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List, Tuple
import os

# ═══════════════════════════════════════════════════════════════════════════
# GLOBALE UI-KONSTANTEN
# ═══════════════════════════════════════════════════════════════════════════

class UIColors:
    """Zentrale Farbdefinitionen - Dark Theme wie FoundryVTT"""
    
    # Hintergründe
    BG_DARK = "#0a0a0a"
    BG_DARKER = "#060606"
    BG_MEDIUM = "#16213e"  # Mittlerer Hintergrund
    BG_LIGHT = "#0f3460"   # Heller Hintergrund
    BG_PANEL = "#1a1a1a"
    BG_PANEL_LIGHT = "#2a2a2a"
    BG_INPUT = "#3a3a3a"
    BG_HOVER = "#4a4a4a"
    
    # Akzente
    ACCENT_GOLD = "#d4af37"
    ACCENT_BLUE = "#2a5d8d"
    ACCENT_GREEN = "#2a7d2a"
    ACCENT_RED = "#7d2a2a"
    ACCENT_ORANGE = "#8d5a2a"
    ACCENT_PURPLE = "#5d2a7d"
    
    # Text
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#888888"
    TEXT_MUTED = "#666666"
    TEXT_SUCCESS = "#44ff44"
    TEXT_ERROR = "#ff4444"
    TEXT_WARNING = "#ffaa00"
    
    # Borders
    BORDER_LIGHT = "#444444"
    BORDER_DARK = "#333333"
    
    # Selection
    SELECT_BG = "#2a5d8d"
    SELECT_FG = "#ffffff"


class UISizes:
    """Zentrale Größendefinitionen"""
    
    # Mindestgrößen für Fenster (breiter als standard!)
    MIN_DIALOG_WIDTH = 450  # War oft 300
    MIN_DIALOG_HEIGHT = 250
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    MIN_PANEL_WIDTH = 280  # Sidepanels
    
    # Standard-Fenstergrößen
    SMALL_DIALOG = (500, 350)
    MEDIUM_DIALOG = (650, 450)
    LARGE_DIALOG = (900, 700)
    FULLSCREEN_MARGIN = 50
    
    # Padding/Margins
    PAD_SMALL = 5
    PAD_MEDIUM = 10
    PAD_LARGE = 20
    
    # Fonts
    FONT_TITLE = ("Arial", 18, "bold")
    FONT_HEADER = ("Arial", 14, "bold")
    FONT_NORMAL = ("Arial", 11)
    FONT_SMALL = ("Arial", 9)
    FONT_TINY = ("Arial", 8)
    FONT_MONO = ("Courier New", 10)


class UIIcons:
    """Standard-Icons (Emoji-basiert)"""
    
    # Datei-Operationen
    NEW = "📄"
    OPEN = "📂"
    SAVE = "💾"
    EXPORT = "📤"
    IMPORT = "📥"
    
    # Bearbeiten
    UNDO = "↶"
    REDO = "↷"
    CUT = "✂️"
    COPY = "📋"
    PASTE = "📎"
    DELETE = "🗑️"
    
    # Ansicht
    ZOOM_IN = "🔍+"
    ZOOM_OUT = "🔍-"
    FULLSCREEN = "⛶"
    
    # Tools
    BRUSH = "🖌️"
    FILL = "🪣"
    ERASER = "🧹"
    SELECT = "✂️"
    EYEDROPPER = "💧"
    
    # VTT-spezifisch
    MAP = "🗺️"
    TOKEN = "🎭"
    LIGHT = "💡"
    FOG = "🌫️"
    WALL = "🧱"
    DOOR = "🚪"
    SOUND = "🔊"
    NOTES = "📝"
    COMBAT = "⚔️"
    DICE = "🎲"
    
    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"


# ═══════════════════════════════════════════════════════════════════════════
# WINDOW MANAGER - Zentrale Fenster-Verwaltung
# ═══════════════════════════════════════════════════════════════════════════

class WindowManager:
    """
    Zentraler Window-Manager für alle VTT-Fenster.
    Verhindert doppelte Fenster, trackt offene Fenster.
    """
    
    _instance = None
    _windows: Dict[str, tk.Toplevel] = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def register(cls, window_id: str, window: tk.Toplevel):
        """Registriert ein Fenster"""
        cls._windows[window_id] = window
        
        # Cleanup wenn Fenster geschlossen wird
        def on_destroy(event):
            if event.widget == window:
                cls._windows.pop(window_id, None)
        
        window.bind("<Destroy>", on_destroy)
    
    @classmethod
    def get(cls, window_id: str) -> Optional[tk.Toplevel]:
        """Holt registriertes Fenster"""
        win = cls._windows.get(window_id)
        if win and win.winfo_exists():
            return win
        return None
    
    @classmethod
    def show_or_create(cls, window_id: str, 
                       create_func: Callable[[], tk.Toplevel]) -> tk.Toplevel:
        """
        Zeigt bestehendes Fenster oder erstellt neues.
        Verhindert doppelte Fenster-Instanzen.
        """
        existing = cls.get(window_id)
        if existing:
            existing.lift()
            existing.focus_force()
            return existing
        
        new_window = create_func()
        cls.register(window_id, new_window)
        return new_window
    
    @classmethod
    def close_all(cls):
        """Schließt alle registrierten Fenster"""
        for window in list(cls._windows.values()):
            try:
                window.destroy()
            except:
                pass
        cls._windows.clear()


# ═══════════════════════════════════════════════════════════════════════════
# BASE DIALOG - Basis für alle Dialoge
# ═══════════════════════════════════════════════════════════════════════════

class BaseDialog(tk.Toplevel):
    """
    Basis-Dialog-Klasse mit korrektem Verhalten:
    - Bleibt über Parent-Fenster (modal)
    - Kehrt NICHT zum Hauptmenü zurück
    - Korrekte Mindestgröße
    - Zentrale Positionierung
    - Einheitliches Styling
    """
    
    def __init__(self, parent, title: str = "Dialog",
                 width: int = None, height: int = None,
                 resizable: bool = True, modal: bool = True):
        super().__init__(parent)
        
        self.parent = parent
        self.result = None
        self._cancelled = False
        
        # Titel und Styling
        self.title(title)
        self.configure(bg=UIColors.BG_PANEL)
        
        # Größe berechnen
        if width is None:
            width = UISizes.MIN_DIALOG_WIDTH
        if height is None:
            height = UISizes.MIN_DIALOG_HEIGHT
        
        # Mindestgröße erzwingen
        width = max(width, UISizes.MIN_DIALOG_WIDTH)
        height = max(height, UISizes.MIN_DIALOG_HEIGHT)
        
        # Zentral positionieren
        self._center_on_parent(width, height)
        
        # Mindestgröße setzen
        if resizable:
            self.minsize(UISizes.MIN_DIALOG_WIDTH, UISizes.MIN_DIALOG_HEIGHT)
        else:
            self.resizable(False, False)
        
        # Modal-Verhalten (WICHTIG: Verhindert Rücksprung zum Hauptmenü!)
        if modal:
            self.transient(parent)  # Bleibt über Parent
            self.grab_set()  # Blockiert Parent-Input
        
        # Schließen mit ESC
        self.bind("<Escape>", lambda e: self._on_cancel())
        
        # Window-Manager registrieren
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Content-Frame mit Padding
        self.content_frame = tk.Frame(self, bg=UIColors.BG_PANEL)
        self.content_frame.pack(fill=tk.BOTH, expand=True, 
                               padx=UISizes.PAD_LARGE, pady=UISizes.PAD_LARGE)
        
        # Button-Frame unten (wird von Subklassen gefüllt)
        self.button_frame = tk.Frame(self, bg=UIColors.BG_PANEL)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, 
                              padx=UISizes.PAD_LARGE, pady=UISizes.PAD_MEDIUM)
    
    def _center_on_parent(self, width: int, height: int):
        """Zentriert Dialog auf Parent oder Bildschirm"""
        self.update_idletasks()
        
        try:
            # Versuche Parent-Position zu bekommen
            if self.parent and self.parent.winfo_exists():
                px = self.parent.winfo_rootx()
                py = self.parent.winfo_rooty()
                pw = self.parent.winfo_width()
                ph = self.parent.winfo_height()
                
                x = px + (pw - width) // 2
                y = py + (ph - height) // 2
            else:
                # Fallback: Bildschirm-Mitte
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = (sw - width) // 2
                y = (sh - height) // 2
        except:
            # Fallback
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw - width) // 2
            y = (sh - height) // 2
        
        # Position setzen
        x = max(0, x)
        y = max(0, y)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _on_cancel(self):
        """Wird bei Abbruch aufgerufen (ESC oder Schließen)"""
        self._cancelled = True
        self.result = None
        self.destroy()
    
    def _on_confirm(self):
        """Wird bei Bestätigung aufgerufen (muss überschrieben werden)"""
        self.destroy()
    
    def add_standard_buttons(self, confirm_text: str = "OK", 
                            cancel_text: str = "Abbrechen"):
        """Fügt Standard OK/Abbrechen Buttons hinzu"""
        tk.Button(
            self.button_frame,
            text=f"{UIIcons.SUCCESS} {confirm_text}",
            bg=UIColors.ACCENT_GREEN, fg="white",
            font=UISizes.FONT_NORMAL,
            padx=20, pady=8,
            command=self._on_confirm
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            self.button_frame,
            text=f"{UIIcons.ERROR} {cancel_text}",
            bg=UIColors.ACCENT_RED, fg="white",
            font=UISizes.FONT_NORMAL,
            padx=20, pady=8,
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=5)
    
    def was_cancelled(self) -> bool:
        """Prüft ob Dialog abgebrochen wurde"""
        return self._cancelled


# ═══════════════════════════════════════════════════════════════════════════
# STANDARD DIALOGE
# ═══════════════════════════════════════════════════════════════════════════

class MessageDialog(BaseDialog):
    """Verbesserter Message-Dialog (ersetzt messagebox teilweise)"""
    
    def __init__(self, parent, title: str, message: str, 
                 icon: str = UIIcons.INFO, 
                 buttons: List[Tuple[str, str, str]] = None):
        """
        Args:
            parent: Parent-Fenster
            title: Titel
            message: Nachricht (mehrzeilig möglich)
            icon: Icon-Emoji
            buttons: Liste von (text, color, return_value)
        """
        super().__init__(parent, title, width=500, height=250, modal=True)
        
        # Icon und Nachricht
        msg_frame = tk.Frame(self.content_frame, bg=UIColors.BG_PANEL)
        msg_frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon links
        tk.Label(
            msg_frame, text=icon,
            font=("Arial", 48),
            bg=UIColors.BG_PANEL, fg=UIColors.TEXT_PRIMARY
        ).pack(side=tk.LEFT, padx=20)
        
        # Text rechts
        tk.Label(
            msg_frame, text=message,
            font=UISizes.FONT_NORMAL,
            bg=UIColors.BG_PANEL, fg=UIColors.TEXT_PRIMARY,
            justify=tk.LEFT, wraplength=350
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # Buttons
        if buttons is None:
            buttons = [("OK", UIColors.ACCENT_BLUE, True)]
        
        for text, color, return_value in buttons:
            tk.Button(
                self.button_frame,
                text=text,
                bg=color, fg="white",
                font=UISizes.FONT_NORMAL,
                padx=20, pady=8,
                command=lambda v=return_value: self._set_result(v)
            ).pack(side=tk.RIGHT, padx=5)
    
    def _set_result(self, value):
        self.result = value
        self.destroy()


class InputDialog(BaseDialog):
    """Verbesserter Eingabe-Dialog"""
    
    def __init__(self, parent, title: str, prompt: str,
                 default_value: str = "", placeholder: str = "",
                 validate: Callable[[str], bool] = None):
        super().__init__(parent, title, width=500, height=200, modal=True)
        
        self.validate = validate
        
        # Prompt
        tk.Label(
            self.content_frame, text=prompt,
            font=UISizes.FONT_NORMAL,
            bg=UIColors.BG_PANEL, fg=UIColors.TEXT_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Eingabefeld
        self.entry_var = tk.StringVar(value=default_value)
        self.entry = tk.Entry(
            self.content_frame,
            textvariable=self.entry_var,
            font=UISizes.FONT_NORMAL,
            bg=UIColors.BG_INPUT, fg=UIColors.TEXT_PRIMARY,
            insertbackground=UIColors.TEXT_PRIMARY,
            relief=tk.FLAT
        )
        self.entry.pack(fill=tk.X, ipady=8)
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)
        
        # Enter zum Bestätigen
        self.entry.bind("<Return>", lambda e: self._on_confirm())
        
        # Buttons
        self.add_standard_buttons()
    
    def _on_confirm(self):
        value = self.entry_var.get().strip()
        
        if self.validate:
            if not self.validate(value):
                self.entry.config(bg="#4a2a2a")
                return
        
        self.result = value
        self.destroy()


class ConfirmDialog(BaseDialog):
    """Bestätigungs-Dialog mit Ja/Nein"""
    
    def __init__(self, parent, title: str, message: str,
                 yes_text: str = "Ja", no_text: str = "Nein",
                 dangerous: bool = False):
        super().__init__(parent, title, width=500, height=200, modal=True)
        
        # Icon
        icon = UIIcons.WARNING if dangerous else UIIcons.INFO
        icon_color = UIColors.TEXT_WARNING if dangerous else UIColors.ACCENT_BLUE
        
        msg_frame = tk.Frame(self.content_frame, bg=UIColors.BG_PANEL)
        msg_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            msg_frame, text=icon,
            font=("Arial", 36),
            bg=UIColors.BG_PANEL, fg=icon_color
        ).pack(side=tk.LEFT, padx=20)
        
        tk.Label(
            msg_frame, text=message,
            font=UISizes.FONT_NORMAL,
            bg=UIColors.BG_PANEL, fg=UIColors.TEXT_PRIMARY,
            justify=tk.LEFT, wraplength=350
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # Buttons
        yes_color = UIColors.ACCENT_RED if dangerous else UIColors.ACCENT_GREEN
        
        tk.Button(
            self.button_frame,
            text=f"{UIIcons.SUCCESS} {yes_text}",
            bg=yes_color, fg="white",
            font=UISizes.FONT_NORMAL,
            padx=20, pady=8,
            command=lambda: self._set_result(True)
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            self.button_frame,
            text=f"{UIIcons.ERROR} {no_text}",
            bg=UIColors.BG_HOVER, fg="white",
            font=UISizes.FONT_NORMAL,
            padx=20, pady=8,
            command=lambda: self._set_result(False)
        ).pack(side=tk.RIGHT, padx=5)
    
    def _set_result(self, value):
        self.result = value
        self.destroy()


class ProgressDialog(BaseDialog):
    """Progress-Dialog mit Fortschrittsanzeige"""
    
    def __init__(self, parent, title: str, message: str = "Bitte warten..."):
        super().__init__(parent, title, width=450, height=180, 
                        resizable=False, modal=True)
        
        # Message
        self.message_label = tk.Label(
            self.content_frame, text=message,
            font=UISizes.FONT_NORMAL,
            bg=UIColors.BG_PANEL, fg=UIColors.TEXT_PRIMARY
        )
        self.message_label.pack(pady=10)
        
        # Progress Bar
        style = ttk.Style()
        style.configure("VTT.Horizontal.TProgressbar", 
                       troughcolor=UIColors.BG_INPUT,
                       background=UIColors.ACCENT_GOLD)
        
        self.progress = ttk.Progressbar(
            self.content_frame,
            style="VTT.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL,
            length=350,
            mode='determinate'
        )
        self.progress.pack(pady=10)
        
        # Prozent-Anzeige
        self.percent_label = tk.Label(
            self.content_frame, text="0%",
            font=UISizes.FONT_NORMAL,
            bg=UIColors.BG_PANEL, fg=UIColors.TEXT_SECONDARY
        )
        self.percent_label.pack()
    
    def set_progress(self, value: float, message: str = None):
        """
        Aktualisiert Fortschritt (0.0 bis 1.0)
        """
        percent = int(value * 100)
        self.progress['value'] = percent
        self.percent_label.config(text=f"{percent}%")
        
        if message:
            self.message_label.config(text=message)
        
        self.update_idletasks()


# ═══════════════════════════════════════════════════════════════════════════
# STYLED WIDGETS
# ═══════════════════════════════════════════════════════════════════════════

class VTTButton(tk.Button):
    """Gestylter Button für VTT"""
    
    def __init__(self, parent, text: str = "", icon: str = "", 
                 color: str = None, size: str = "normal", **kwargs):
        
        # Farbe
        if color is None:
            color = UIColors.BG_INPUT
        
        # Font basierend auf Größe
        fonts = {
            "small": UISizes.FONT_SMALL,
            "normal": UISizes.FONT_NORMAL,
            "large": UISizes.FONT_HEADER
        }
        font = fonts.get(size, UISizes.FONT_NORMAL)
        
        # Text mit Icon
        display_text = f"{icon} {text}".strip() if icon else text
        
        # Standard-Einstellungen
        defaults = {
            "bg": color,
            "fg": UIColors.TEXT_PRIMARY,
            "font": font,
            "relief": tk.FLAT,
            "cursor": "hand2",
            "activebackground": UIColors.BG_HOVER,
            "activeforeground": UIColors.TEXT_PRIMARY,
            "padx": 15,
            "pady": 8
        }
        defaults.update(kwargs)
        
        super().__init__(parent, text=display_text, **defaults)
        
        # Hover-Effekt
        self.default_bg = color
        self.bind("<Enter>", lambda e: self.config(bg=UIColors.BG_HOVER))
        self.bind("<Leave>", lambda e: self.config(bg=self.default_bg))


class VTTEntry(tk.Entry):
    """Gestyltes Entry für VTT"""
    
    def __init__(self, parent, placeholder: str = "", **kwargs):
        defaults = {
            "bg": UIColors.BG_INPUT,
            "fg": UIColors.TEXT_PRIMARY,
            "insertbackground": UIColors.TEXT_PRIMARY,
            "font": UISizes.FONT_NORMAL,
            "relief": tk.FLAT,
            "highlightthickness": 1,
            "highlightbackground": UIColors.BORDER_DARK,
            "highlightcolor": UIColors.ACCENT_BLUE
        }
        defaults.update(kwargs)
        
        super().__init__(parent, **defaults)
        
        self.placeholder = placeholder
        self._has_placeholder = False
        
        if placeholder:
            self._show_placeholder()
            self.bind("<FocusIn>", self._on_focus_in)
            self.bind("<FocusOut>", self._on_focus_out)
    
    def _show_placeholder(self):
        if not self.get():
            self._has_placeholder = True
            self.insert(0, self.placeholder)
            self.config(fg=UIColors.TEXT_MUTED)
    
    def _on_focus_in(self, event):
        if self._has_placeholder:
            self.delete(0, tk.END)
            self.config(fg=UIColors.TEXT_PRIMARY)
            self._has_placeholder = False
    
    def _on_focus_out(self, event):
        if not self.get():
            self._show_placeholder()
    
    def get_value(self) -> str:
        """Gibt Wert zurück (ohne Placeholder)"""
        if self._has_placeholder:
            return ""
        return self.get()


class VTTLabel(tk.Label):
    """Gestyltes Label für VTT"""
    
    def __init__(self, parent, text: str = "", style: str = "normal", **kwargs):
        
        styles = {
            "title": {"font": UISizes.FONT_TITLE, "fg": UIColors.ACCENT_GOLD},
            "header": {"font": UISizes.FONT_HEADER, "fg": UIColors.TEXT_PRIMARY},
            "normal": {"font": UISizes.FONT_NORMAL, "fg": UIColors.TEXT_PRIMARY},
            "small": {"font": UISizes.FONT_SMALL, "fg": UIColors.TEXT_SECONDARY},
            "muted": {"font": UISizes.FONT_NORMAL, "fg": UIColors.TEXT_MUTED},
            "success": {"font": UISizes.FONT_NORMAL, "fg": UIColors.TEXT_SUCCESS},
            "error": {"font": UISizes.FONT_NORMAL, "fg": UIColors.TEXT_ERROR},
            "warning": {"font": UISizes.FONT_NORMAL, "fg": UIColors.TEXT_WARNING}
        }
        
        style_config = styles.get(style, styles["normal"])
        
        defaults = {
            "bg": UIColors.BG_PANEL,
            **style_config
        }
        defaults.update(kwargs)
        
        super().__init__(parent, text=text, **defaults)


class VTTFrame(tk.Frame):
    """Gestylter Frame für VTT"""
    
    def __init__(self, parent, style: str = "panel", **kwargs):
        
        styles = {
            "panel": UIColors.BG_PANEL,
            "dark": UIColors.BG_DARK,
            "light": UIColors.BG_PANEL_LIGHT,
            "input": UIColors.BG_INPUT
        }
        
        bg = styles.get(style, UIColors.BG_PANEL)
        
        defaults = {"bg": bg}
        defaults.update(kwargs)
        
        super().__init__(parent, **defaults)


class VTTScrollableFrame(tk.Frame):
    """Scrollbarer Frame für VTT"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=UIColors.BG_PANEL)
        
        # Canvas für Scrolling
        self.canvas = tk.Canvas(self, bg=UIColors.BG_PANEL, 
                               highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, 
                                      command=self.canvas.yview)
        
        # Innerer Frame
        self.inner_frame = tk.Frame(self.canvas, bg=UIColors.BG_PANEL)
        
        # Window im Canvas
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor=tk.NW
        )
        
        # Scrollbar konfigurieren
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Layout
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Events
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mausrad-Scrolling
        self.inner_frame.bind("<Enter>", self._bind_mousewheel)
        self.inner_frame.bind("<Leave>", self._unbind_mousewheel)
    
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def show_info(parent, title: str, message: str):
    """Zeigt Info-Dialog"""
    dialog = MessageDialog(parent, title, message, UIIcons.INFO)
    parent.wait_window(dialog)
    return dialog.result


def show_warning(parent, title: str, message: str):
    """Zeigt Warnung"""
    dialog = MessageDialog(parent, title, message, UIIcons.WARNING)
    parent.wait_window(dialog)
    return dialog.result


def show_error(parent, title: str, message: str):
    """Zeigt Fehler"""
    dialog = MessageDialog(parent, title, message, UIIcons.ERROR)
    parent.wait_window(dialog)
    return dialog.result


def ask_confirm(parent, title: str, message: str, dangerous: bool = False) -> bool:
    """Zeigt Bestätigungs-Dialog"""
    dialog = ConfirmDialog(parent, title, message, dangerous=dangerous)
    parent.wait_window(dialog)
    return dialog.result is True


def ask_input(parent, title: str, prompt: str, 
             default: str = "", validate: Callable = None) -> Optional[str]:
    """Zeigt Eingabe-Dialog"""
    dialog = InputDialog(parent, title, prompt, default, validate=validate)
    parent.wait_window(dialog)
    return dialog.result


def center_window(window: tk.Toplevel, width: int = None, height: int = None):
    """Zentriert ein Fenster auf dem Bildschirm"""
    window.update_idletasks()
    
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()
    
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    
    x = (sw - width) // 2
    y = (sh - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")


def ensure_minimum_size(window: tk.Toplevel, 
                        min_width: int = None, min_height: int = None):
    """Stellt sicher dass Fenster Mindestgröße hat"""
    if min_width is None:
        min_width = UISizes.MIN_DIALOG_WIDTH
    if min_height is None:
        min_height = UISizes.MIN_DIALOG_HEIGHT
    
    window.minsize(min_width, min_height)
    
    # Aktuelle Größe prüfen und ggf. anpassen
    window.update_idletasks()
    current_w = window.winfo_width()
    current_h = window.winfo_height()
    
    if current_w < min_width or current_h < min_height:
        new_w = max(current_w, min_width)
        new_h = max(current_h, min_height)
        window.geometry(f"{new_w}x{new_h}")


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    root.title("UI Framework Test")
    root.geometry("400x300")
    root.configure(bg=UIColors.BG_DARK)
    
    def test_dialogs():
        show_info(root, "Info", "Dies ist eine Info-Nachricht mit genug Platz!")
        
        if ask_confirm(root, "Bestätigung", "Möchtest du fortfahren?"):
            print("Bestätigt!")
        
        name = ask_input(root, "Eingabe", "Wie heißt du?", "Spieler 1")
        if name:
            print(f"Name: {name}")
    
    VTTButton(root, "Test Dialoge", UIIcons.INFO, 
             UIColors.ACCENT_BLUE, command=test_dialogs).pack(pady=20)
    
    VTTLabel(root, "UI Framework Test", "title").pack(pady=10)
    VTTLabel(root, "Subheader Text", "header").pack()
    VTTLabel(root, "Normal text", "normal").pack()
    VTTLabel(root, "Muted text", "muted").pack()
    
    entry = VTTEntry(root, placeholder="Suchen...")
    entry.pack(pady=10, padx=20, fill=tk.X)
    
    root.mainloop()
