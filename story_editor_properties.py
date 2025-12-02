"""
Story Editor - Teil 4: Properties Panel
========================================

Detaillierte Bearbeitung von Triggern, Actions, Conditions und Overlays.

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from typing import Optional, Callable, List, Dict, Any, Tuple
import os

from storyboard_system import (
    Scene, Chapter, Trigger, Action, Condition, Overlay,
    SceneType, TriggerType, ActionType
)


class PropertyEditor:
    """Basisklasse für Property-Editoren"""
    
    def __init__(self, parent: tk.Frame, on_change: Optional[Callable] = None):
        self.parent = parent
        self.on_change = on_change
        self.widgets: Dict[str, tk.Widget] = {}
    
    def notify_change(self):
        """Benachrichtigt über Änderungen"""
        if self.on_change:
            self.on_change()
    
    def create_label(self, parent: tk.Frame, text: str) -> tk.Label:
        """Erstellt ein Label"""
        return tk.Label(
            parent, text=text,
            bg="#16213e", fg="white",
            font=("Arial", 9)
        )
    
    def create_entry(self, parent: tk.Frame, value: str = "") -> tk.Entry:
        """Erstellt ein Entry-Feld"""
        entry = tk.Entry(
            parent, bg="#0f3460", fg="white",
            insertbackground="white", font=("Arial", 10)
        )
        if value:
            entry.insert(0, value)
        entry.bind("<FocusOut>", lambda e: self.notify_change())
        return entry
    
    def create_combo(self, parent: tk.Frame, values: List[str], 
                    current: str = "") -> ttk.Combobox:
        """Erstellt eine Combobox"""
        style = ttk.Style()
        style.configure("Props.TCombobox", 
                       background="#0f3460", foreground="white")
        
        combo = ttk.Combobox(parent, values=values, state="readonly")
        if current and current in values:
            combo.set(current)
        combo.bind("<<ComboboxSelected>>", lambda e: self.notify_change())
        return combo
    
    def create_checkbox(self, parent: tk.Frame, text: str, 
                       value: bool = False) -> Tuple[tk.Checkbutton, tk.BooleanVar]:
        """Erstellt eine Checkbox"""
        var = tk.BooleanVar(value=value)
        cb = tk.Checkbutton(
            parent, text=text,
            variable=var,
            bg="#16213e", fg="white",
            selectcolor="#0f3460",
            activebackground="#16213e",
            command=self.notify_change
        )
        return cb, var
    
    def create_section(self, parent: tk.Frame, title: str) -> tk.Frame:
        """Erstellt eine Sektion mit Titel"""
        frame = tk.Frame(parent, bg="#16213e")
        frame.pack(fill=tk.X, pady=(10, 5))
        
        # Separator
        sep = tk.Frame(frame, bg="#e94560", height=2)
        sep.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Titel
        tk.Label(
            frame, text=title,
            bg="#16213e", fg="#e94560",
            font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, padx=10)
        
        # Content Frame
        content = tk.Frame(frame, bg="#16213e")
        content.pack(fill=tk.X, padx=15, pady=5)
        
        return content


class TriggerEditor(PropertyEditor):
    """Editor für Trigger"""
    
    def __init__(self, parent: tk.Frame, trigger: Trigger, 
                 on_change: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None):
        super().__init__(parent, on_change)
        
        self.trigger = trigger
        self.on_delete = on_delete
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Haupt-Frame
        self.frame = tk.Frame(self.parent, bg="#1a2a4e", relief=tk.RAISED, bd=1)
        self.frame.pack(fill=tk.X, pady=5)
        
        # Header
        header = tk.Frame(self.frame, bg="#0f3460")
        header.pack(fill=tk.X)
        
        # Icon basierend auf Typ
        icon = self._get_trigger_icon()
        tk.Label(
            header, text=icon,
            bg="#0f3460", fg="white",
            font=("Arial", 14)
        ).pack(side=tk.LEFT, padx=5, pady=3)
        
        # Name
        self.name_entry = tk.Entry(
            header, bg="#16213e", fg="white",
            insertbackground="white", font=("Arial", 10, "bold"),
            width=20
        )
        self.name_entry.insert(0, self.trigger.name or "Unbenannt")
        self.name_entry.pack(side=tk.LEFT, padx=5, pady=3)
        self.name_entry.bind("<FocusOut>", self._on_name_change)
        
        # Löschen-Button
        tk.Button(
            header, text="🗑️",
            bg="#0f3460", fg="#e94560",
            relief=tk.FLAT,
            command=self._on_delete
        ).pack(side=tk.RIGHT, padx=5)
        
        # Typ-Auswahl
        type_frame = tk.Frame(self.frame, bg="#1a2a4e")
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.create_label(type_frame, "Typ:").pack(side=tk.LEFT)
        
        type_values = [t.value for t in TriggerType]
        self.type_combo = self.create_combo(
            type_frame, type_values, self.trigger.trigger_type.value
        )
        self.type_combo.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        
        # Typ-spezifische Parameter
        self.params_frame = tk.Frame(self.frame, bg="#1a2a4e")
        self.params_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self._update_params_ui()
        
        # Actions
        actions_header = tk.Frame(self.frame, bg="#1a2a4e")
        actions_header.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        tk.Label(
            actions_header, text="⚡ Actions:",
            bg="#1a2a4e", fg="#888",
            font=("Arial", 9)
        ).pack(side=tk.LEFT)
        
        tk.Button(
            actions_header, text="+",
            bg="#2a7d2a", fg="white",
            font=("Arial", 8), width=3,
            command=self._add_action
        ).pack(side=tk.RIGHT)
        
        self.actions_frame = tk.Frame(self.frame, bg="#1a2a4e")
        self.actions_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self._update_actions_ui()
    
    def _get_trigger_icon(self) -> str:
        icons = {
            TriggerType.CLICK: "👆",
            TriggerType.HOVER: "🔍",
            TriggerType.TIMER: "⏱️",
            TriggerType.ENTER_AREA: "📍",
            TriggerType.LEAVE_AREA: "🚶",
            TriggerType.CONDITION: "❓",
            TriggerType.CUSTOM: "⚙️"
        }
        return icons.get(self.trigger.trigger_type, "⚡")
    
    def _on_name_change(self, event):
        self.trigger.name = self.name_entry.get()
        self.notify_change()
    
    def _on_type_change(self, event):
        self.trigger.trigger_type = TriggerType(self.type_combo.get())
        self._update_params_ui()
        self.notify_change()
    
    def _update_params_ui(self):
        """Aktualisiert die Parameter-UI basierend auf Trigger-Typ"""
        # Alte Widgets löschen
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        tt = self.trigger.trigger_type
        
        if tt == TriggerType.TIMER:
            # Timer-Parameter
            row = tk.Frame(self.params_frame, bg="#1a2a4e")
            row.pack(fill=tk.X, pady=2)
            
            self.create_label(row, "Verzögerung (Sek):").pack(side=tk.LEFT)
            
            delay = self.trigger.params.get("delay", 1.0)
            self.delay_entry = self.create_entry(row, str(delay))
            self.delay_entry.pack(side=tk.LEFT, padx=10)
            self.delay_entry.bind("<FocusOut>", self._on_delay_change)
        
        elif tt == TriggerType.ENTER_AREA or tt == TriggerType.LEAVE_AREA:
            # Area-Parameter
            row = tk.Frame(self.params_frame, bg="#1a2a4e")
            row.pack(fill=tk.X, pady=2)
            
            self.create_label(row, "Area-ID:").pack(side=tk.LEFT)
            
            area_id = self.trigger.params.get("area_id", "")
            self.area_entry = self.create_entry(row, area_id)
            self.area_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            self.area_entry.bind("<FocusOut>", self._on_area_change)
        
        elif tt == TriggerType.CONDITION:
            # Condition-Parameter
            row = tk.Frame(self.params_frame, bg="#1a2a4e")
            row.pack(fill=tk.X, pady=2)
            
            self.create_label(row, "Variable:").pack(side=tk.LEFT)
            
            var_name = self.trigger.params.get("variable", "")
            self.var_entry = self.create_entry(row, var_name)
            self.var_entry.pack(side=tk.LEFT, padx=10)
            
            self.create_label(row, "=").pack(side=tk.LEFT)
            
            var_value = self.trigger.params.get("value", "")
            self.val_entry = self.create_entry(row, str(var_value))
            self.val_entry.pack(side=tk.LEFT, padx=5)
    
    def _on_delay_change(self, event):
        try:
            self.trigger.params["delay"] = float(self.delay_entry.get())
            self.notify_change()
        except ValueError:
            pass
    
    def _on_area_change(self, event):
        self.trigger.params["area_id"] = self.area_entry.get()
        self.notify_change()
    
    def _add_action(self):
        """Fügt eine neue Action hinzu"""
        action = Action(action_type=ActionType.SHOW_TEXT)
        self.trigger.actions.append(action)
        self._update_actions_ui()
        self.notify_change()
    
    def _update_actions_ui(self):
        """Aktualisiert die Actions-Liste"""
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        
        for i, action in enumerate(self.trigger.actions):
            ActionMiniEditor(
                self.actions_frame, action,
                on_change=self.notify_change,
                on_delete=lambda a=action: self._delete_action(a)
            )
    
    def _delete_action(self, action: Action):
        if action in self.trigger.actions:
            self.trigger.actions.remove(action)
            self._update_actions_ui()
            self.notify_change()
    
    def _on_delete(self):
        if self.on_delete:
            self.on_delete(self.trigger)


class ActionMiniEditor(PropertyEditor):
    """Kompakter Editor für Actions"""
    
    def __init__(self, parent: tk.Frame, action: Action,
                 on_change: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None):
        super().__init__(parent, on_change)
        
        self.action = action
        self.on_delete = on_delete
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        self.frame = tk.Frame(self.parent, bg="#0f2040")
        self.frame.pack(fill=tk.X, pady=2)
        
        # Icon
        icon = self._get_action_icon()
        tk.Label(
            self.frame, text=icon,
            bg="#0f2040", fg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=3)
        
        # Typ
        type_values = [t.value for t in ActionType]
        self.type_combo = ttk.Combobox(
            self.frame, values=type_values,
            state="readonly", width=15
        )
        self.type_combo.set(self.action.action_type.value)
        self.type_combo.pack(side=tk.LEFT, padx=3)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        
        # Parameter-Button
        tk.Button(
            self.frame, text="⚙️",
            bg="#0f2040", fg="white",
            relief=tk.FLAT, font=("Arial", 8),
            command=self._edit_params
        ).pack(side=tk.LEFT, padx=2)
        
        # Löschen
        tk.Button(
            self.frame, text="✕",
            bg="#0f2040", fg="#e94560",
            relief=tk.FLAT, font=("Arial", 8),
            command=lambda: self.on_delete() if self.on_delete else None
        ).pack(side=tk.RIGHT, padx=2)
    
    def _get_action_icon(self) -> str:
        icons = {
            ActionType.TRANSITION: "🚪",
            ActionType.PLAY_SOUND: "🔊",
            ActionType.SHOW_TEXT: "💬",
            ActionType.SET_VARIABLE: "📝",
            ActionType.ADD_OVERLAY: "🎭",
            ActionType.REMOVE_OVERLAY: "❌",
            ActionType.CAMERA_MOVE: "📷",
            ActionType.SPAWN_TOKEN: "👤",
            ActionType.TRIGGER_WEATHER: "🌧️",
            ActionType.RUN_SCRIPT: "📜"
        }
        return icons.get(self.action.action_type, "⚡")
    
    def _on_type_change(self, event):
        self.action.action_type = ActionType(self.type_combo.get())
        self.notify_change()
    
    def _edit_params(self):
        """Öffnet den Parameter-Dialog"""
        ActionParamsDialog(self.frame, self.action, self.notify_change)


class ActionParamsDialog(tk.Toplevel):
    """Dialog zur Bearbeitung von Action-Parametern"""
    
    def __init__(self, parent, action: Action, on_save: Optional[Callable] = None):
        super().__init__(parent)
        
        self.action = action
        self.on_save = on_save
        
        self.title(f"Action: {action.action_type.value}")
        self.configure(bg="#1a1a2e")
        self.geometry("450x350")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Header
        tk.Label(
            self,
            text=f"⚡ {self.action.action_type.value}",
            bg="#1a1a2e", fg="#e94560",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Parameter-Frame
        params_frame = tk.Frame(self, bg="#1a1a2e")
        params_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        at = self.action.action_type
        
        if at == ActionType.TRANSITION:
            self._setup_transition_params(params_frame)
        elif at == ActionType.SHOW_TEXT:
            self._setup_text_params(params_frame)
        elif at == ActionType.PLAY_SOUND:
            self._setup_sound_params(params_frame)
        elif at == ActionType.SET_VARIABLE:
            self._setup_variable_params(params_frame)
        elif at == ActionType.ADD_OVERLAY:
            self._setup_overlay_params(params_frame)
        elif at == ActionType.CAMERA_MOVE:
            self._setup_camera_params(params_frame)
        elif at == ActionType.TRIGGER_WEATHER:
            self._setup_weather_params(params_frame)
        else:
            # Generische JSON-Bearbeitung
            self._setup_generic_params(params_frame)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
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
    
    def _setup_transition_params(self, parent):
        """Parameter für Szenen-Übergang"""
        # Ziel-Szene
        row = tk.Frame(parent, bg="#1a1a2e")
        row.pack(fill=tk.X, pady=5)
        
        tk.Label(row, text="Ziel-Szene ID:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.target_entry = tk.Entry(row, bg="#0f3460", fg="white", insertbackground="white")
        self.target_entry.insert(0, self.action.params.get("target_scene_id", ""))
        self.target_entry.pack(fill=tk.X, pady=2)
        
        # Übergangs-Typ
        row2 = tk.Frame(parent, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Übergang:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.trans_combo = ttk.Combobox(
            row2, values=["fade", "slide_left", "slide_right", "zoom", "instant"],
            state="readonly"
        )
        self.trans_combo.set(self.action.params.get("transition_type", "fade"))
        self.trans_combo.pack(fill=tk.X, pady=2)
        
        # Dauer
        row3 = tk.Frame(parent, bg="#1a1a2e")
        row3.pack(fill=tk.X, pady=5)
        
        tk.Label(row3, text="Dauer (Sek):", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.duration_entry = tk.Entry(row3, bg="#0f3460", fg="white", insertbackground="white")
        self.duration_entry.insert(0, str(self.action.params.get("duration", 0.5)))
        self.duration_entry.pack(fill=tk.X, pady=2)
    
    def _setup_text_params(self, parent):
        """Parameter für Text-Anzeige"""
        tk.Label(parent, text="Text:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        self.text_widget = tk.Text(
            parent, bg="#0f3460", fg="white",
            height=5, insertbackground="white"
        )
        self.text_widget.insert("1.0", self.action.params.get("text", ""))
        self.text_widget.pack(fill=tk.X, pady=5)
        
        # Position
        row = tk.Frame(parent, bg="#1a1a2e")
        row.pack(fill=tk.X, pady=5)
        
        tk.Label(row, text="Position:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.pos_combo = ttk.Combobox(
            row, values=["center", "top", "bottom", "left", "right"],
            state="readonly"
        )
        self.pos_combo.set(self.action.params.get("position", "center"))
        self.pos_combo.pack(side=tk.LEFT, padx=10)
        
        # Dauer
        row2 = tk.Frame(parent, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Anzeigedauer (Sek, 0=permanent):", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.text_duration = tk.Entry(row2, bg="#0f3460", fg="white", insertbackground="white")
        self.text_duration.insert(0, str(self.action.params.get("duration", 3)))
        self.text_duration.pack(fill=tk.X, pady=2)
    
    def _setup_sound_params(self, parent):
        """Parameter für Sound"""
        row = tk.Frame(parent, bg="#1a1a2e")
        row.pack(fill=tk.X, pady=5)
        
        tk.Label(row, text="Audio-Datei:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        file_row = tk.Frame(row, bg="#1a1a2e")
        file_row.pack(fill=tk.X, pady=2)
        
        self.sound_entry = tk.Entry(file_row, bg="#0f3460", fg="white", insertbackground="white")
        self.sound_entry.insert(0, self.action.params.get("file", ""))
        self.sound_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(
            file_row, text="📂",
            bg="#0f3460", fg="white",
            command=self._browse_sound
        ).pack(side=tk.RIGHT, padx=5)
        
        # Lautstärke
        row2 = tk.Frame(parent, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Lautstärke:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        
        self.volume_var = tk.DoubleVar(value=self.action.params.get("volume", 1.0))
        tk.Scale(
            row2, variable=self.volume_var,
            from_=0, to=1, resolution=0.1,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Loop
        self.loop_var = tk.BooleanVar(value=self.action.params.get("loop", False))
        tk.Checkbutton(
            parent, text="Loop",
            variable=self.loop_var,
            bg="#1a1a2e", fg="white",
            selectcolor="#0f3460"
        ).pack(anchor=tk.W, pady=5)
    
    def _setup_variable_params(self, parent):
        """Parameter für Variable setzen"""
        row = tk.Frame(parent, bg="#1a1a2e")
        row.pack(fill=tk.X, pady=5)
        
        tk.Label(row, text="Variable:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.var_name = tk.Entry(row, bg="#0f3460", fg="white", insertbackground="white")
        self.var_name.insert(0, self.action.params.get("variable", ""))
        self.var_name.pack(fill=tk.X, pady=2)
        
        row2 = tk.Frame(parent, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Wert:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.var_value = tk.Entry(row2, bg="#0f3460", fg="white", insertbackground="white")
        self.var_value.insert(0, str(self.action.params.get("value", "")))
        self.var_value.pack(fill=tk.X, pady=2)
        
        # Operation
        row3 = tk.Frame(parent, bg="#1a1a2e")
        row3.pack(fill=tk.X, pady=5)
        
        tk.Label(row3, text="Operation:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.op_combo = ttk.Combobox(
            row3, values=["set", "add", "subtract", "toggle"],
            state="readonly"
        )
        self.op_combo.set(self.action.params.get("operation", "set"))
        self.op_combo.pack(side=tk.LEFT, padx=10)
    
    def _setup_overlay_params(self, parent):
        """Parameter für Overlay"""
        tk.Label(parent, text="Overlay-Typ:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.overlay_combo = ttk.Combobox(
            parent, values=["image", "video", "weather", "color"],
            state="readonly"
        )
        self.overlay_combo.set(self.action.params.get("overlay_type", "image"))
        self.overlay_combo.pack(fill=tk.X, pady=5)
        
        tk.Label(parent, text="Datei/Wert:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.overlay_source = tk.Entry(parent, bg="#0f3460", fg="white", insertbackground="white")
        self.overlay_source.insert(0, self.action.params.get("source", ""))
        self.overlay_source.pack(fill=tk.X, pady=5)
        
        # Blend Mode
        tk.Label(parent, text="Blend-Modus:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.blend_combo = ttk.Combobox(
            parent, values=["normal", "multiply", "screen", "overlay", "add"],
            state="readonly"
        )
        self.blend_combo.set(self.action.params.get("blend_mode", "normal"))
        self.blend_combo.pack(fill=tk.X, pady=5)
        
        # Opacity
        row = tk.Frame(parent, bg="#1a1a2e")
        row.pack(fill=tk.X, pady=5)
        
        tk.Label(row, text="Deckkraft:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.opacity_var = tk.DoubleVar(value=self.action.params.get("opacity", 1.0))
        tk.Scale(
            row, variable=self.opacity_var,
            from_=0, to=1, resolution=0.1,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _setup_camera_params(self, parent):
        """Parameter für Kamera-Bewegung"""
        # Position
        pos_frame = tk.Frame(parent, bg="#1a1a2e")
        pos_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(pos_frame, text="Position (X, Y):", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        pos_row = tk.Frame(pos_frame, bg="#1a1a2e")
        pos_row.pack(fill=tk.X)
        
        self.cam_x = tk.Entry(pos_row, bg="#0f3460", fg="white", width=10, insertbackground="white")
        self.cam_x.insert(0, str(self.action.params.get("x", 0)))
        self.cam_x.pack(side=tk.LEFT, padx=2)
        
        tk.Label(pos_row, text=",", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        
        self.cam_y = tk.Entry(pos_row, bg="#0f3460", fg="white", width=10, insertbackground="white")
        self.cam_y.insert(0, str(self.action.params.get("y", 0)))
        self.cam_y.pack(side=tk.LEFT, padx=2)
        
        # Zoom
        row2 = tk.Frame(parent, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Zoom:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.zoom_var = tk.DoubleVar(value=self.action.params.get("zoom", 1.0))
        tk.Scale(
            row2, variable=self.zoom_var,
            from_=0.5, to=3.0, resolution=0.1,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Dauer
        row3 = tk.Frame(parent, bg="#1a1a2e")
        row3.pack(fill=tk.X, pady=5)
        
        tk.Label(row3, text="Dauer (Sek):", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.cam_duration = tk.Entry(row3, bg="#0f3460", fg="white", insertbackground="white")
        self.cam_duration.insert(0, str(self.action.params.get("duration", 1.0)))
        self.cam_duration.pack(fill=tk.X, pady=2)
    
    def _setup_weather_params(self, parent):
        """Parameter für Wetter"""
        tk.Label(parent, text="Wetter-Typ:", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.weather_combo = ttk.Combobox(
            parent, values=["clear", "cloudy", "rain", "storm", "snow", "fog", "wind"],
            state="readonly"
        )
        self.weather_combo.set(self.action.params.get("weather_type", "clear"))
        self.weather_combo.pack(fill=tk.X, pady=5)
        
        # Intensität
        row = tk.Frame(parent, bg="#1a1a2e")
        row.pack(fill=tk.X, pady=5)
        
        tk.Label(row, text="Intensität:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.weather_intensity = tk.DoubleVar(value=self.action.params.get("intensity", 0.5))
        tk.Scale(
            row, variable=self.weather_intensity,
            from_=0, to=1, resolution=0.1,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e", fg="white",
            highlightthickness=0
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Übergangszeit
        row2 = tk.Frame(parent, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Übergangszeit (Sek):", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        self.weather_trans = tk.Entry(row2, bg="#0f3460", fg="white", insertbackground="white")
        self.weather_trans.insert(0, str(self.action.params.get("transition_time", 2.0)))
        self.weather_trans.pack(fill=tk.X, pady=2)
    
    def _setup_generic_params(self, parent):
        """Generische Parameter-Bearbeitung"""
        import json
        
        tk.Label(parent, text="Parameter (JSON):", bg="#1a1a2e", fg="white").pack(anchor=tk.W)
        
        self.json_text = tk.Text(
            parent, bg="#0f3460", fg="white",
            height=10, insertbackground="white"
        )
        self.json_text.insert("1.0", json.dumps(self.action.params, indent=2))
        self.json_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def _browse_sound(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Audio", "*.mp3;*.wav;*.ogg"), ("Alle", "*.*")]
        )
        if filepath:
            self.sound_entry.delete(0, tk.END)
            self.sound_entry.insert(0, filepath)
    
    def _save(self):
        """Speichert die Parameter"""
        at = self.action.action_type
        
        if at == ActionType.TRANSITION:
            self.action.params["target_scene_id"] = self.target_entry.get()
            self.action.params["transition_type"] = self.trans_combo.get()
            try:
                self.action.params["duration"] = float(self.duration_entry.get())
            except ValueError:
                pass
        
        elif at == ActionType.SHOW_TEXT:
            self.action.params["text"] = self.text_widget.get("1.0", tk.END).strip()
            self.action.params["position"] = self.pos_combo.get()
            try:
                self.action.params["duration"] = float(self.text_duration.get())
            except ValueError:
                pass
        
        elif at == ActionType.PLAY_SOUND:
            self.action.params["file"] = self.sound_entry.get()
            self.action.params["volume"] = self.volume_var.get()
            self.action.params["loop"] = self.loop_var.get()
        
        elif at == ActionType.SET_VARIABLE:
            self.action.params["variable"] = self.var_name.get()
            self.action.params["value"] = self.var_value.get()
            self.action.params["operation"] = self.op_combo.get()
        
        elif at == ActionType.ADD_OVERLAY:
            self.action.params["overlay_type"] = self.overlay_combo.get()
            self.action.params["source"] = self.overlay_source.get()
            self.action.params["blend_mode"] = self.blend_combo.get()
            self.action.params["opacity"] = self.opacity_var.get()
        
        elif at == ActionType.CAMERA_MOVE:
            try:
                self.action.params["x"] = float(self.cam_x.get())
                self.action.params["y"] = float(self.cam_y.get())
                self.action.params["zoom"] = self.zoom_var.get()
                self.action.params["duration"] = float(self.cam_duration.get())
            except ValueError:
                pass
        
        elif at == ActionType.TRIGGER_WEATHER:
            self.action.params["weather_type"] = self.weather_combo.get()
            self.action.params["intensity"] = self.weather_intensity.get()
            try:
                self.action.params["transition_time"] = float(self.weather_trans.get())
            except ValueError:
                pass
        
        else:
            # Generisch
            import json
            try:
                self.action.params = json.loads(self.json_text.get("1.0", tk.END))
            except json.JSONDecodeError:
                messagebox.showerror("Fehler", "Ungültiges JSON!")
                return
        
        if self.on_save:
            self.on_save()
        
        self.destroy()


class OverlayEditor(PropertyEditor):
    """Editor für Overlays"""
    
    def __init__(self, parent: tk.Frame, overlay: Overlay,
                 on_change: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None):
        super().__init__(parent, on_change)
        
        self.overlay = overlay
        self.on_delete = on_delete
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        self.frame = tk.Frame(self.parent, bg="#2a1a4e", relief=tk.RAISED, bd=1)
        self.frame.pack(fill=tk.X, pady=5)
        
        # Header
        header = tk.Frame(self.frame, bg="#3a2a5e")
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="🎭",
            bg="#3a2a5e", fg="white",
            font=("Arial", 14)
        ).pack(side=tk.LEFT, padx=5, pady=3)
        
        self.name_entry = tk.Entry(
            header, bg="#2a1a4e", fg="white",
            insertbackground="white", font=("Arial", 10, "bold"),
            width=20
        )
        self.name_entry.insert(0, self.overlay.name or "Overlay")
        self.name_entry.pack(side=tk.LEFT, padx=5, pady=3)
        self.name_entry.bind("<FocusOut>", self._on_name_change)
        
        # Visibility Toggle
        self.visible_var = tk.BooleanVar(value=self.overlay.visible)
        tk.Checkbutton(
            header, text="👁️",
            variable=self.visible_var,
            bg="#3a2a5e", fg="white",
            selectcolor="#2a1a4e",
            command=self._on_visible_change
        ).pack(side=tk.RIGHT, padx=2)
        
        # Löschen
        tk.Button(
            header, text="🗑️",
            bg="#3a2a5e", fg="#e94560",
            relief=tk.FLAT,
            command=lambda: self.on_delete(self.overlay) if self.on_delete else None
        ).pack(side=tk.RIGHT, padx=2)
        
        # Parameter
        params = tk.Frame(self.frame, bg="#2a1a4e")
        params.pack(fill=tk.X, padx=10, pady=5)
        
        # Source (file_path)
        row = tk.Frame(params, bg="#2a1a4e")
        row.pack(fill=tk.X, pady=2)
        
        self.create_label(row, "Quelle:").pack(side=tk.LEFT)
        self.source_entry = tk.Entry(row, bg="#0f3460", fg="white", insertbackground="white")
        self.source_entry.insert(0, self.overlay.file_path or "")
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Button(
            row, text="📂",
            bg="#0f3460", fg="white",
            command=self._browse_source
        ).pack(side=tk.RIGHT)
        
        # Blend & Opacity
        row2 = tk.Frame(params, bg="#2a1a4e")
        row2.pack(fill=tk.X, pady=2)
        
        self.create_label(row2, "Blend:").pack(side=tk.LEFT)
        self.blend_combo = ttk.Combobox(
            row2, values=["normal", "multiply", "screen", "overlay", "add"],
            state="readonly", width=10
        )
        self.blend_combo.set(self.overlay.blend_mode)
        self.blend_combo.pack(side=tk.LEFT, padx=5)
        self.blend_combo.bind("<<ComboboxSelected>>", self._on_blend_change)
        
        self.create_label(row2, "Alpha:").pack(side=tk.LEFT, padx=(10, 0))
        self.opacity_scale = tk.Scale(
            row2, from_=0, to=1, resolution=0.05,
            orient=tk.HORIZONTAL, length=80,
            bg="#2a1a4e", fg="white", highlightthickness=0
        )
        self.opacity_scale.set(self.overlay.opacity)
        self.opacity_scale.pack(side=tk.LEFT, padx=5)
        self.opacity_scale.bind("<ButtonRelease-1>", self._on_opacity_change)
    
    def _on_name_change(self, event):
        self.overlay.name = self.name_entry.get()
        self.notify_change()
    
    def _on_visible_change(self):
        self.overlay.visible = self.visible_var.get()
        self.notify_change()
    
    def _on_blend_change(self, event):
        self.overlay.blend_mode = self.blend_combo.get()
        self.notify_change()
    
    def _on_opacity_change(self, event):
        self.overlay.opacity = self.opacity_scale.get()
        self.notify_change()
    
    def _browse_source(self):
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("Alle unterstützten", "*.png;*.jpg;*.gif;*.mp4;*.webm"),
                ("Bilder", "*.png;*.jpg;*.jpeg;*.gif"),
                ("Videos", "*.mp4;*.webm"),
                ("Alle", "*.*")
            ]
        )
        if filepath:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, filepath)
            self.overlay.file_path = filepath
            self.notify_change()


class PropertiesPanel:
    """
    Vollständiges Properties-Panel für den Story Editor
    """
    
    def __init__(self, parent_frame: tk.Frame, editor):
        self.parent = parent_frame
        self.editor = editor
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Header
        header = tk.Frame(self.parent, bg="#0f3460")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header,
            text="⚙️ Eigenschaften",
            bg="#0f3460", fg="white",
            font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Scrollbarer Bereich
        canvas_frame = tk.Frame(self.parent, bg="#16213e")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#16213e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.content_frame = tk.Frame(self.canvas, bg="#16213e")
        
        self.canvas.create_window((0, 0), window=self.content_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.content_frame.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Mausrad-Scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Initial-Inhalt
        self._show_empty()
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _clear(self):
        """Leert das Panel"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def _show_empty(self):
        """Zeigt Platzhalter"""
        self._clear()
        
        tk.Label(
            self.content_frame,
            text="Wähle ein Element aus,\num seine Eigenschaften\nzu bearbeiten.",
            bg="#16213e", fg="#666",
            font=("Arial", 10),
            justify=tk.CENTER
        ).pack(pady=50)
    
    def show_scene_properties(self, scene: Scene):
        """Zeigt Szenen-Eigenschaften"""
        self._clear()
        
        # Szenen-Header
        icon = self._get_scene_icon(scene.scene_type)
        
        header = tk.Frame(self.content_frame, bg="#0f3460")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header, text=icon,
            bg="#0f3460", font=("Arial", 24)
        ).pack(side=tk.LEFT, padx=10)
        
        name_entry = tk.Entry(
            header, bg="#16213e", fg="white",
            font=("Arial", 14, "bold"), insertbackground="white"
        )
        name_entry.insert(0, scene.name)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        name_entry.bind("<FocusOut>", lambda e: self._update_scene_name(scene, name_entry.get()))
        
        # Typ-Anzeige
        tk.Label(
            self.content_frame,
            text=f"Typ: {scene.scene_type.value}",
            bg="#16213e", fg="#888",
            font=("Arial", 9)
        ).pack(anchor=tk.W, padx=15)
        
        # Trigger-Sektion
        self._create_section_header("⚡ Trigger")
        
        triggers_frame = tk.Frame(self.content_frame, bg="#16213e")
        triggers_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for trigger in scene.triggers:
            TriggerEditor(
                triggers_frame, trigger,
                on_change=lambda: self._on_change(),
                on_delete=lambda t: self._delete_trigger(scene, t)
            )
        
        # Trigger hinzufügen
        tk.Button(
            triggers_frame, text="+ Trigger hinzufügen",
            bg="#2a7d2a", fg="white",
            command=lambda: self._add_trigger(scene)
        ).pack(fill=tk.X, pady=5)
        
        # Overlays-Sektion
        self._create_section_header("🎭 Overlays")
        
        overlays_frame = tk.Frame(self.content_frame, bg="#16213e")
        overlays_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for overlay in scene.overlays:
            OverlayEditor(
                overlays_frame, overlay,
                on_change=lambda: self._on_change(),
                on_delete=lambda o: self._delete_overlay(scene, o)
            )
        
        # Overlay hinzufügen
        tk.Button(
            overlays_frame, text="+ Overlay hinzufügen",
            bg="#5a2d82", fg="white",
            command=lambda: self._add_overlay(scene)
        ).pack(fill=tk.X, pady=5)
    
    def show_chapter_properties(self, chapter: Chapter):
        """Zeigt Kapitel-Eigenschaften"""
        self._clear()
        
        # Header
        header = tk.Frame(self.content_frame, bg="#0f3460")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header, text=chapter.icon,
            bg="#0f3460", font=("Arial", 24)
        ).pack(side=tk.LEFT, padx=10)
        
        name_entry = tk.Entry(
            header, bg="#16213e", fg="white",
            font=("Arial", 14, "bold"), insertbackground="white"
        )
        name_entry.insert(0, chapter.name)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        name_entry.bind("<FocusOut>", lambda e: self._update_chapter_name(chapter, name_entry.get()))
        
        # Info
        info_frame = tk.Frame(self.content_frame, bg="#16213e")
        info_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(
            info_frame,
            text=f"📊 {len(chapter.scenes)} Szenen",
            bg="#16213e", fg="#888"
        ).pack(anchor=tk.W)
        
        if chapter.start_scene_id:
            start_scene = next((s for s in chapter.scenes if s.id == chapter.start_scene_id), None)
            if start_scene:
                tk.Label(
                    info_frame,
                    text=f"🏁 Start: {start_scene.name}",
                    bg="#16213e", fg="#4ade80"
                ).pack(anchor=tk.W)
        
        # Beschreibung
        self._create_section_header("📝 Beschreibung")
        
        desc_frame = tk.Frame(self.content_frame, bg="#16213e")
        desc_frame.pack(fill=tk.X, padx=10, pady=5)
        
        desc_text = tk.Text(
            desc_frame, bg="#0f3460", fg="white",
            height=4, insertbackground="white"
        )
        desc_text.insert("1.0", chapter.description)
        desc_text.pack(fill=tk.X)
        desc_text.bind("<FocusOut>", lambda e: self._update_chapter_desc(chapter, desc_text))
        
        # Optionen
        self._create_section_header("⚙️ Optionen")
        
        opts_frame = tk.Frame(self.content_frame, bg="#16213e")
        opts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        locked_var = tk.BooleanVar(value=chapter.locked)
        tk.Checkbutton(
            opts_frame, text="🔒 Kapitel gesperrt",
            variable=locked_var,
            bg="#16213e", fg="white",
            selectcolor="#0f3460",
            command=lambda: self._update_chapter_locked(chapter, locked_var)
        ).pack(anchor=tk.W)
    
    def _create_section_header(self, text: str):
        """Erstellt einen Sektions-Header"""
        sep = tk.Frame(self.content_frame, bg="#e94560", height=2)
        sep.pack(fill=tk.X, padx=10, pady=(15, 5))
        
        tk.Label(
            self.content_frame,
            text=text,
            bg="#16213e", fg="#e94560",
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W, padx=10, pady=5)
    
    def _get_scene_icon(self, scene_type: SceneType) -> str:
        icons = {
            SceneType.VIDEO: "🎥",
            SceneType.MAP_JSON: "🗺️",
            SceneType.MAP_SVG: "📐",
            SceneType.IMAGE: "🖼️",
            SceneType.CUTSCENE: "🎞️"
        }
        return icons.get(scene_type, "🎬")
    
    def _on_change(self):
        """Bei Änderungen"""
        if hasattr(self.editor, '_mark_changed'):
            self.editor._mark_changed()
    
    def _update_scene_name(self, scene: Scene, name: str):
        if name:
            scene.name = name
            self._on_change()
            if hasattr(self.editor, '_refresh_chapter_list'):
                self.editor._refresh_chapter_list()
    
    def _update_chapter_name(self, chapter: Chapter, name: str):
        if name:
            chapter.name = name
            self._on_change()
            if hasattr(self.editor, '_refresh_chapter_list'):
                self.editor._refresh_chapter_list()
    
    def _update_chapter_desc(self, chapter: Chapter, text_widget: tk.Text):
        chapter.description = text_widget.get("1.0", tk.END).strip()
        self._on_change()
    
    def _update_chapter_locked(self, chapter: Chapter, var: tk.BooleanVar):
        chapter.locked = var.get()
        self._on_change()
    
    def _add_trigger(self, scene: Scene):
        trigger = Trigger(name="Neuer Trigger", trigger_type=TriggerType.CLICK)
        scene.triggers.append(trigger)
        self._on_change()
        self.show_scene_properties(scene)
    
    def _delete_trigger(self, scene: Scene, trigger: Trigger):
        if trigger in scene.triggers:
            scene.triggers.remove(trigger)
            self._on_change()
            self.show_scene_properties(scene)
    
    def _add_overlay(self, scene: Scene):
        overlay = Overlay(name="Neues Overlay")
        scene.overlays.append(overlay)
        self._on_change()
        self.show_scene_properties(scene)
    
    def _delete_overlay(self, scene: Scene, overlay: Overlay):
        if overlay in scene.overlays:
            scene.overlays.remove(overlay)
            self._on_change()
            self.show_scene_properties(scene)
    
    def refresh(self):
        """Aktualisiert die Anzeige"""
        if hasattr(self.editor, 'current_scene') and self.editor.current_scene:
            self.show_scene_properties(self.editor.current_scene)
        elif hasattr(self.editor, 'current_chapter') and self.editor.current_chapter:
            self.show_chapter_properties(self.editor.current_chapter)
        else:
            self._show_empty()


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    from storyboard_system import Storyboard
    
    root = tk.Tk()
    root.title("Properties Panel Test")
    root.geometry("400x700")
    root.configure(bg="#1a1a2e")
    
    # Mock Editor
    class MockEditor:
        def __init__(self):
            self.current_scene = Scene(
                name="Test-Szene",
                scene_type=SceneType.MAP_JSON
            )
            
            # Test-Trigger
            t1 = Trigger(name="Klick auf Tür", trigger_type=TriggerType.CLICK)
            t1.actions.append(Action(action_type=ActionType.TRANSITION))
            t1.actions.append(Action(action_type=ActionType.PLAY_SOUND))
            
            t2 = Trigger(name="Timer", trigger_type=TriggerType.TIMER)
            t2.params["delay"] = 5.0
            
            self.current_scene.triggers = [t1, t2]
            
            # Test-Overlay
            o1 = Overlay(name="Nebel", source="fog.mp4")
            self.current_scene.overlays = [o1]
            
            self.current_chapter = None
        
        def _mark_changed(self):
            print("Changed!")
        
        def _refresh_chapter_list(self):
            pass
    
    mock = MockEditor()
    
    frame = tk.Frame(root, bg="#16213e")
    frame.pack(fill=tk.BOTH, expand=True)
    
    panel = PropertiesPanel(frame, mock)
    panel.show_scene_properties(mock.current_scene)
    
    root.mainloop()
