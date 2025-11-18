"""
Layer Manager für professionelles 2.5D VTT
Verwaltet mehrere Zeichen-Ebenen (Base, Objects, Tokens, Annotations)
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Any
import json

class Layer:
    """Einzelne Zeichen-Ebene"""
    def __init__(self, name: str, layer_type: str, visible: bool = True, locked: bool = False):
        self.name = name
        self.type = layer_type  # 'base', 'objects', 'tokens', 'annotations'
        self.visible = visible
        self.locked = locked
        self.opacity = 1.0
        self.content = []  # Liste von Zeichen-Objekten
        
    def add_object(self, obj: Dict[str, Any]):
        """Füge Zeichen-Objekt hinzu"""
        if not self.locked:
            self.content.append(obj)
            
    def remove_object(self, index: int):
        """Entferne Zeichen-Objekt"""
        if not self.locked and 0 <= index < len(self.content):
            del self.content[index]
            
    def clear(self):
        """Lösche alle Objekte"""
        if not self.locked:
            self.content.clear()
            
    def to_dict(self) -> Dict[str, Any]:
        """Exportiere Layer als Dictionary"""
        return {
            "name": self.name,
            "type": self.type,
            "visible": self.visible,
            "locked": self.locked,
            "opacity": self.opacity,
            "content": self.content
        }
        
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Layer':
        """Importiere Layer aus Dictionary"""
        layer = Layer(
            name=data.get("name", "Unnamed"),
            layer_type=data.get("type", "objects"),
            visible=data.get("visible", True),
            locked=data.get("locked", False)
        )
        layer.opacity = data.get("opacity", 1.0)
        layer.content = data.get("content", [])
        return layer


class LayerManager:
    """Verwaltet alle Layer und deren Interaktion"""
    def __init__(self):
        self.layers: List[Layer] = []
        self.active_layer_index = 0
        self.create_default_layers()
        
    def create_default_layers(self):
        """Erstelle Standard-Layer-Stack"""
        self.layers = [
            Layer("Base Terrain", "base", visible=True, locked=False),
            Layer("Objects", "objects", visible=True, locked=False),
            Layer("Tokens", "tokens", visible=True, locked=False),
            Layer("Annotations", "annotations", visible=True, locked=False),
        ]
        self.active_layer_index = 1  # Objects als Standard
        
    def get_active_layer(self) -> Layer:
        """Gibt aktiven Layer zurück"""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return self.layers[0]
        
    def set_active_layer(self, index: int):
        """Setze aktiven Layer"""
        if 0 <= index < len(self.layers):
            self.active_layer_index = index
            
    def add_layer(self, name: str, layer_type: str = "objects", index: int = None):
        """Füge neuen Layer hinzu"""
        layer = Layer(name, layer_type)
        if index is None:
            self.layers.append(layer)
        else:
            self.layers.insert(index, layer)
            
    def remove_layer(self, index: int):
        """Entferne Layer (mindestens 1 muss bleiben)"""
        if len(self.layers) > 1 and 0 <= index < len(self.layers):
            del self.layers[index]
            # Aktiven Layer anpassen
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
                
    def move_layer(self, from_index: int, to_index: int):
        """Verschiebe Layer in der Reihenfolge"""
        if 0 <= from_index < len(self.layers) and 0 <= to_index < len(self.layers):
            layer = self.layers.pop(from_index)
            self.layers.insert(to_index, layer)
            
    def get_visible_layers(self) -> List[Layer]:
        """Gibt alle sichtbaren Layer zurück"""
        return [layer for layer in self.layers if layer.visible]
        
    def to_dict(self) -> Dict[str, Any]:
        """Exportiere Layer-Stack als Dictionary"""
        return {
            "layers": [layer.to_dict() for layer in self.layers],
            "active_layer": self.active_layer_index
        }
        
    def from_dict(self, data: Dict[str, Any]):
        """Importiere Layer-Stack aus Dictionary"""
        self.layers = [Layer.from_dict(l) for l in data.get("layers", [])]
        self.active_layer_index = data.get("active_layer", 0)
        
        # Fallback: Mindestens ein Layer
        if not self.layers:
            self.create_default_layers()


class LayerPanel(tk.Frame):
    """UI-Panel für Layer-Verwaltung"""
    def __init__(self, parent, layer_manager: LayerManager, on_layer_change=None):
        super().__init__(parent, bg="#2a2a2a")
        self.layer_manager = layer_manager
        self.on_layer_change = on_layer_change
        
        self.setup_ui()
        self.refresh()
        
    def setup_ui(self):
        """Erstelle UI-Elemente"""
        # Header
        header = tk.Frame(self, bg="#1a1a1a")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header, text="🎨 Layers", bg="#1a1a1a", fg="white",
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(header, bg="#1a1a1a")
        btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="+", bg="#2a7d2a", fg="white",
                 font=("Arial", 10, "bold"), width=2,
                 command=self.add_layer).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="−", bg="#7d2a2a", fg="white",
                 font=("Arial", 10, "bold"), width=2,
                 command=self.remove_layer).pack(side=tk.LEFT, padx=2)
        
        # Layer-Liste (Scrollbar)
        list_frame = tk.Frame(self, bg="#2a2a2a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.layer_listbox = tk.Listbox(list_frame, bg="#3a3a3a", fg="white",
                                        selectmode=tk.SINGLE,
                                        font=("Arial", 9),
                                        yscrollcommand=scrollbar.set,
                                        highlightthickness=0,
                                        borderwidth=0)
        self.layer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.layer_listbox.yview)
        
        self.layer_listbox.bind('<<ListboxSelect>>', self.on_select)
        
        # Layer-Details
        details_frame = tk.Frame(self, bg="#2a2a2a")
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.visible_var = tk.BooleanVar(value=True)
        self.locked_var = tk.BooleanVar(value=False)
        
        tk.Checkbutton(details_frame, text="👁 Visible", variable=self.visible_var,
                      bg="#2a2a2a", fg="white", selectcolor="#3a3a3a",
                      command=self.toggle_visible).pack(anchor=tk.W)
        
        tk.Checkbutton(details_frame, text="🔒 Locked", variable=self.locked_var,
                      bg="#2a2a2a", fg="white", selectcolor="#3a3a3a",
                      command=self.toggle_locked).pack(anchor=tk.W)
        
    def refresh(self):
        """Aktualisiere Layer-Liste"""
        self.layer_listbox.delete(0, tk.END)
        
        for i, layer in enumerate(self.layer_manager.layers):
            # Symbol basierend auf Layer-Typ
            icons = {
                'base': '🗺️',
                'objects': '🏰',
                'tokens': '🎭',
                'annotations': '📝'
            }
            icon = icons.get(layer.type, '📄')
            
            # Status-Icons
            status = ""
            if not layer.visible:
                status += "👁‍🗨"
            if layer.locked:
                status += "🔒"
            
            # Aktiver Layer hervorheben
            prefix = "▶ " if i == self.layer_manager.active_layer_index else "  "
            
            text = f"{prefix}{icon} {layer.name} {status}"
            self.layer_listbox.insert(tk.END, text)
            
            # Farbe für aktiven Layer
            if i == self.layer_manager.active_layer_index:
                self.layer_listbox.itemconfig(i, bg="#4a4a7a")
                
    def on_select(self, event):
        """Layer-Auswahl geändert"""
        selection = self.layer_listbox.curselection()
        if selection:
            index = selection[0]
            self.layer_manager.set_active_layer(index)
            
            # Update Checkboxen
            layer = self.layer_manager.get_active_layer()
            self.visible_var.set(layer.visible)
            self.locked_var.set(layer.locked)
            
            self.refresh()
            
            if self.on_layer_change:
                self.on_layer_change()
                
    def add_layer(self):
        """Neuen Layer hinzufügen"""
        name = f"Layer {len(self.layer_manager.layers) + 1}"
        self.layer_manager.add_layer(name, "objects")
        self.refresh()
        
        if self.on_layer_change:
            self.on_layer_change()
            
    def remove_layer(self):
        """Aktiven Layer entfernen"""
        if len(self.layer_manager.layers) > 1:
            self.layer_manager.remove_layer(self.layer_manager.active_layer_index)
            self.refresh()
            
            if self.on_layer_change:
                self.on_layer_change()
                
    def toggle_visible(self):
        """Sichtbarkeit umschalten"""
        layer = self.layer_manager.get_active_layer()
        layer.visible = self.visible_var.get()
        self.refresh()
        
        if self.on_layer_change:
            self.on_layer_change()
            
    def toggle_locked(self):
        """Lock-Status umschalten"""
        layer = self.layer_manager.get_active_layer()
        layer.locked = self.locked_var.get()
        self.refresh()
