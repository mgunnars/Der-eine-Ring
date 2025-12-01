"""
Story Editor - Teil 3: Flow-Graph
=================================

Visueller Graph zur Darstellung von Szenen-Verbindungen,
Triggern und Übergängen.

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, List, Tuple, Callable
import math

from storyboard_system import (
    Scene, Trigger, Action, ActionType, TriggerType, SceneType
)


class FlowNode:
    """Repräsentiert einen Knoten im Flow-Graph"""
    
    def __init__(self, scene: Scene, x: int = 0, y: int = 0):
        self.scene = scene
        self.x = x
        self.y = y
        self.width = 180
        self.height = 80
        
        # Canvas-IDs
        self.rect_id: Optional[int] = None
        self.text_id: Optional[int] = None
        self.icon_id: Optional[int] = None
        self.trigger_icons: List[int] = []
        
        # State
        self.selected = False
        self.hovered = False
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def contains_point(self, px: int, py: int) -> bool:
        return (self.x <= px <= self.x + self.width and 
                self.y <= py <= self.y + self.height)


class FlowConnection:
    """Repräsentiert eine Verbindung zwischen Szenen"""
    
    def __init__(self, source_node: FlowNode, target_scene_id: str, 
                 trigger: Optional[Trigger] = None, action: Optional[Action] = None):
        self.source_node = source_node
        self.target_scene_id = target_scene_id
        self.trigger = trigger
        self.action = action
        
        # Canvas-IDs
        self.line_id: Optional[int] = None
        self.arrow_id: Optional[int] = None
        self.label_id: Optional[int] = None
        
        # State
        self.selected = False
        self.hovered = False


class FlowGraph(tk.Canvas):
    """
    Visueller Flow-Graph für Szenen-Verbindungen
    """
    
    # Farbschema
    COLORS = {
        "background": "#0a0a1a",
        "grid": "#1a1a3a",
        "node_fill": "#16213e",
        "node_stroke": "#e94560",
        "node_selected": "#ff6b9d",
        "node_hover": "#4a5a8e",
        "text": "white",
        "text_dim": "#888",
        "connection": "#4a90d9",
        "connection_hover": "#7ab8ff",
        "trigger_click": "#e94560",
        "trigger_enter": "#4ade80",
        "trigger_timer": "#fbbf24",
        "trigger_condition": "#a855f7"
    }
    
    def __init__(self, parent, editor, **kwargs):
        super().__init__(parent, bg=self.COLORS["background"], 
                        highlightthickness=0, **kwargs)
        
        self.editor = editor
        
        # Nodes und Verbindungen
        self.nodes: Dict[str, FlowNode] = {}
        self.connections: List[FlowConnection] = []
        
        # State
        self.selected_node: Optional[FlowNode] = None
        self.selected_connection: Optional[FlowConnection] = None
        self.dragging_node: Optional[FlowNode] = None
        self.drag_offset: Tuple[int, int] = (0, 0)
        
        # Pan/Zoom
        self.pan_x = 0
        self.pan_y = 0
        self.zoom_level = 1.0
        self.panning = False
        self.pan_start: Tuple[int, int] = (0, 0)
        
        # Verbindungs-Modus
        self.connecting = False
        self.connection_start: Optional[FlowNode] = None
        self.connection_line_id: Optional[int] = None
        
        # Events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Double-1>", self._on_double_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<Motion>", self._on_motion)
        
        # Pan mit mittlerer Maustaste
        self.bind("<Button-2>", self._on_pan_start)
        self.bind("<B2-Motion>", self._on_pan_motion)
        self.bind("<ButtonRelease-2>", self._on_pan_end)
        
        # Zoom mit Mausrad
        self.bind("<MouseWheel>", self._on_mousewheel)
        
        # Tastatur
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<Escape>", lambda e: self._cancel_connecting())
        
        # Fokus für Tastatureingaben
        self.bind("<Enter>", lambda e: self.focus_set())
        
        # Initial zeichnen
        self.after(100, self._draw_grid)
    
    def set_scenes(self, scenes: List[Scene]):
        """Setzt die anzuzeigenden Szenen"""
        # Alte Nodes behalten ihre Position wenn möglich
        old_positions = {node.scene.id: (node.x, node.y) for node in self.nodes.values()}
        
        self.nodes.clear()
        self.connections.clear()
        
        # Nodes erstellen
        for i, scene in enumerate(scenes):
            # Position aus alten Daten oder neu berechnen
            if scene.id in old_positions:
                x, y = old_positions[scene.id]
            else:
                # Grid-Layout
                cols = 3
                x = 50 + (i % cols) * 250
                y = 50 + (i // cols) * 150
            
            self.nodes[scene.id] = FlowNode(scene, x, y)
        
        # Verbindungen aus Triggern extrahieren
        for scene in scenes:
            source_node = self.nodes.get(scene.id)
            if not source_node:
                continue
            
            for trigger in scene.triggers:
                for action in trigger.actions:
                    if action.action_type == ActionType.TRANSITION:
                        target_id = action.params.get("target_scene_id")
                        if target_id and target_id in self.nodes:
                            conn = FlowConnection(source_node, target_id, trigger, action)
                            self.connections.append(conn)
        
        self.redraw()
    
    def redraw(self):
        """Zeichnet den gesamten Graphen neu"""
        self.delete("all")
        
        self._draw_grid()
        self._draw_connections()
        self._draw_nodes()
        
        # Verbindungslinie während des Verbindens
        if self.connecting and self.connection_line_id:
            pass  # Wird in _on_drag gezeichnet
    
    def _draw_grid(self):
        """Zeichnet das Hintergrund-Gitter"""
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        
        grid_size = int(50 * self.zoom_level)
        
        # Offset durch Pan
        offset_x = self.pan_x % grid_size
        offset_y = self.pan_y % grid_size
        
        # Vertikale Linien
        x = offset_x
        while x < w:
            self.create_line(x, 0, x, h, fill=self.COLORS["grid"], tags="grid")
            x += grid_size
        
        # Horizontale Linien
        y = offset_y
        while y < h:
            self.create_line(0, y, w, y, fill=self.COLORS["grid"], tags="grid")
            y += grid_size
    
    def _draw_nodes(self):
        """Zeichnet alle Nodes"""
        for node in self.nodes.values():
            self._draw_node(node)
    
    def _draw_node(self, node: FlowNode):
        """Zeichnet einen einzelnen Node"""
        # Transformierte Position
        x = int(node.x * self.zoom_level + self.pan_x)
        y = int(node.y * self.zoom_level + self.pan_y)
        w = int(node.width * self.zoom_level)
        h = int(node.height * self.zoom_level)
        
        # Farben basierend auf State
        if node.selected:
            stroke = self.COLORS["node_selected"]
            stroke_width = 3
        elif node.hovered:
            stroke = self.COLORS["node_hover"]
            stroke_width = 2
        else:
            stroke = self.COLORS["node_stroke"]
            stroke_width = 2
        
        # Rechteck
        node.rect_id = self.create_rectangle(
            x, y, x + w, y + h,
            fill=self.COLORS["node_fill"],
            outline=stroke,
            width=stroke_width,
            tags=("node", node.scene.id)
        )
        
        # Icon
        icon = self._get_scene_icon(node.scene.scene_type)
        node.icon_id = self.create_text(
            x + 15, y + h // 2,
            text=icon,
            fill=self.COLORS["text"],
            font=("Arial", int(20 * self.zoom_level)),
            anchor=tk.W,
            tags=("node", node.scene.id)
        )
        
        # Name
        name = node.scene.name
        if len(name) > 15:
            name = name[:14] + "…"
        
        node.text_id = self.create_text(
            x + 40, y + h // 2 - 8,
            text=name,
            fill=self.COLORS["text"],
            font=("Arial", int(11 * self.zoom_level), "bold"),
            anchor=tk.W,
            tags=("node", node.scene.id)
        )
        
        # Trigger-Info
        trigger_count = len(node.scene.triggers)
        if trigger_count > 0:
            self.create_text(
                x + 40, y + h // 2 + 12,
                text=f"⚡ {trigger_count} Trigger",
                fill=self.COLORS["text_dim"],
                font=("Arial", int(9 * self.zoom_level)),
                anchor=tk.W,
                tags=("node", node.scene.id)
            )
        
        # Start-Markierung
        if hasattr(self.editor, 'current_chapter') and self.editor.current_chapter:
            if node.scene.id == self.editor.current_chapter.start_scene_id:
                self.create_text(
                    x + w - 10, y + 10,
                    text="🏁",
                    font=("Arial", int(12 * self.zoom_level)),
                    anchor=tk.E,
                    tags=("node", node.scene.id)
                )
    
    def _draw_connections(self):
        """Zeichnet alle Verbindungen"""
        for conn in self.connections:
            self._draw_connection(conn)
    
    def _draw_connection(self, conn: FlowConnection):
        """Zeichnet eine einzelne Verbindung"""
        source_node = conn.source_node
        target_node = self.nodes.get(conn.target_scene_id)
        
        if not target_node:
            return
        
        # Start- und Endpunkte berechnen
        sx, sy = self._transform_point(*source_node.center)
        tx, ty = self._transform_point(*target_node.center)
        
        # Farbe basierend auf Trigger-Typ
        if conn.trigger:
            color = self._get_trigger_color(conn.trigger.trigger_type)
        else:
            color = self.COLORS["connection"]
        
        if conn.hovered or conn.selected:
            color = self.COLORS["connection_hover"]
        
        # Bezier-Kurve für elegantere Verbindungen
        # Kontrollpunkte
        dx = tx - sx
        dy = ty - sy
        
        if abs(dx) > abs(dy):
            # Horizontal
            cx1, cy1 = sx + dx * 0.4, sy
            cx2, cy2 = tx - dx * 0.4, ty
        else:
            # Vertikal
            cx1, cy1 = sx, sy + dy * 0.4
            cx2, cy2 = tx, ty - dy * 0.4
        
        # Bezier als Liniensegmente approximieren
        points = self._bezier_curve(sx, sy, cx1, cy1, cx2, cy2, tx, ty, 20)
        
        # Linie zeichnen
        conn.line_id = self.create_line(
            *points,
            fill=color,
            width=2,
            smooth=True,
            tags=("connection", conn.source_node.scene.id)
        )
        
        # Pfeilspitze
        self._draw_arrow(tx, ty, sx, sy, color, conn)
        
        # Label (Trigger-Name)
        if conn.trigger and conn.trigger.name:
            mid_x = (sx + tx) / 2
            mid_y = (sy + ty) / 2
            
            conn.label_id = self.create_text(
                mid_x, mid_y - 10,
                text=conn.trigger.name,
                fill=color,
                font=("Arial", int(9 * self.zoom_level)),
                tags=("connection_label",)
            )
    
    def _draw_arrow(self, tx: float, ty: float, sx: float, sy: float, 
                    color: str, conn: FlowConnection):
        """Zeichnet eine Pfeilspitze"""
        angle = math.atan2(ty - sy, tx - sx)
        arrow_size = 12 * self.zoom_level
        
        # Pfeilspitze Punkte
        x1 = tx - arrow_size * math.cos(angle - math.pi / 6)
        y1 = ty - arrow_size * math.sin(angle - math.pi / 6)
        x2 = tx - arrow_size * math.cos(angle + math.pi / 6)
        y2 = ty - arrow_size * math.sin(angle + math.pi / 6)
        
        conn.arrow_id = self.create_polygon(
            tx, ty, x1, y1, x2, y2,
            fill=color,
            outline=color,
            tags=("arrow",)
        )
    
    def _bezier_curve(self, x0, y0, x1, y1, x2, y2, x3, y3, segments: int) -> List[float]:
        """Berechnet Punkte auf einer Bezier-Kurve"""
        points = []
        for i in range(segments + 1):
            t = i / segments
            t2 = t * t
            t3 = t2 * t
            mt = 1 - t
            mt2 = mt * mt
            mt3 = mt2 * mt
            
            x = mt3 * x0 + 3 * mt2 * t * x1 + 3 * mt * t2 * x2 + t3 * x3
            y = mt3 * y0 + 3 * mt2 * t * y1 + 3 * mt * t2 * y2 + t3 * y3
            
            points.extend([x, y])
        
        return points
    
    def _transform_point(self, x: int, y: int) -> Tuple[float, float]:
        """Transformiert einen Punkt mit Zoom und Pan"""
        return (x * self.zoom_level + self.pan_x,
                y * self.zoom_level + self.pan_y)
    
    def _inverse_transform_point(self, x: int, y: int) -> Tuple[float, float]:
        """Inverse Transformation"""
        return ((x - self.pan_x) / self.zoom_level,
                (y - self.pan_y) / self.zoom_level)
    
    def _get_scene_icon(self, scene_type: SceneType) -> str:
        icons = {
            SceneType.VIDEO: "🎥",
            SceneType.MAP_JSON: "🗺️",
            SceneType.MAP_SVG: "📐",
            SceneType.IMAGE: "🖼️",
            SceneType.CUTSCENE: "🎞️"
        }
        return icons.get(scene_type, "🎬")
    
    def _get_trigger_color(self, trigger_type: TriggerType) -> str:
        colors = {
            TriggerType.CLICK: self.COLORS["trigger_click"],
            TriggerType.HOVER: self.COLORS["trigger_enter"],
            TriggerType.TIMER: self.COLORS["trigger_timer"],
            TriggerType.CONDITION: self.COLORS["trigger_condition"],
            TriggerType.ENTER_AREA: self.COLORS["trigger_enter"]
        }
        return colors.get(trigger_type, self.COLORS["connection"])
    
    # ============================================================
    # EVENT HANDLERS
    # ============================================================
    
    def _on_click(self, event):
        """Klick-Handler"""
        # Inverse Transform für echte Koordinaten
        wx, wy = self._inverse_transform_point(event.x, event.y)
        
        clicked_node = None
        for node in self.nodes.values():
            if node.contains_point(wx, wy):
                clicked_node = node
                break
        
        if clicked_node:
            if self.connecting:
                # Verbindung abschließen
                self._finish_connecting(clicked_node)
            else:
                # Node auswählen
                self._select_node(clicked_node)
                self.dragging_node = clicked_node
                self.drag_offset = (wx - clicked_node.x, wy - clicked_node.y)
        else:
            # Deselektieren
            self._deselect_all()
    
    def _on_double_click(self, event):
        """Doppelklick - Szene bearbeiten oder Verbindung starten"""
        wx, wy = self._inverse_transform_point(event.x, event.y)
        
        for node in self.nodes.values():
            if node.contains_point(wx, wy):
                # Verbindungsmodus starten
                self._start_connecting(node)
                return
    
    def _on_drag(self, event):
        """Drag-Handler"""
        if self.dragging_node:
            wx, wy = self._inverse_transform_point(event.x, event.y)
            self.dragging_node.x = int(wx - self.drag_offset[0])
            self.dragging_node.y = int(wy - self.drag_offset[1])
            self.redraw()
        
        elif self.connecting and self.connection_start:
            # Verbindungslinie zeichnen
            self.delete("temp_connection")
            sx, sy = self._transform_point(*self.connection_start.center)
            self.create_line(
                sx, sy, event.x, event.y,
                fill=self.COLORS["connection_hover"],
                width=2,
                dash=(5, 5),
                tags="temp_connection"
            )
    
    def _on_release(self, event):
        """Maustaste losgelassen"""
        self.dragging_node = None
    
    def _on_right_click(self, event):
        """Rechtsklick - Kontext-Menü"""
        wx, wy = self._inverse_transform_point(event.x, event.y)
        
        # Prüfen ob auf Node
        clicked_node = None
        for node in self.nodes.values():
            if node.contains_point(wx, wy):
                clicked_node = node
                break
        
        self._show_context_menu(event, clicked_node)
    
    def _on_motion(self, event):
        """Mausbewegung - Hover-Effekte"""
        wx, wy = self._inverse_transform_point(event.x, event.y)
        
        any_hovered = False
        for node in self.nodes.values():
            was_hovered = node.hovered
            node.hovered = node.contains_point(wx, wy)
            
            if node.hovered != was_hovered:
                any_hovered = True
        
        if any_hovered:
            self.redraw()
    
    def _on_pan_start(self, event):
        """Pan-Start"""
        self.panning = True
        self.pan_start = (event.x, event.y)
        self.config(cursor="fleur")
    
    def _on_pan_motion(self, event):
        """Pan-Bewegung"""
        if self.panning:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start = (event.x, event.y)
            self.redraw()
    
    def _on_pan_end(self, event):
        """Pan-Ende"""
        self.panning = False
        self.config(cursor="")
    
    def _on_mousewheel(self, event):
        """Zoom mit Mausrad"""
        # Zoom-Faktor
        factor = 1.1 if event.delta > 0 else 0.9
        new_zoom = self.zoom_level * factor
        
        # Zoom-Grenzen
        if 0.3 <= new_zoom <= 3.0:
            # Zoom um Mausposition
            old_wx, old_wy = self._inverse_transform_point(event.x, event.y)
            
            self.zoom_level = new_zoom
            
            new_wx, new_wy = self._inverse_transform_point(event.x, event.y)
            
            # Pan anpassen damit Punkt unter Maus bleibt
            self.pan_x += (new_wx - old_wx) * self.zoom_level
            self.pan_y += (new_wy - old_wy) * self.zoom_level
            
            self.redraw()
    
    # ============================================================
    # AUSWAHL UND VERBINDUNGEN
    # ============================================================
    
    def _select_node(self, node: FlowNode):
        """Node auswählen"""
        self._deselect_all()
        node.selected = True
        self.selected_node = node
        
        # Editor informieren
        if hasattr(self.editor, 'current_scene'):
            self.editor.current_scene = node.scene
            self.editor._refresh_properties()
        
        self.redraw()
    
    def _deselect_all(self):
        """Alle Auswahlen aufheben"""
        for node in self.nodes.values():
            node.selected = False
        
        self.selected_node = None
        self.selected_connection = None
        self.redraw()
    
    def _start_connecting(self, node: FlowNode):
        """Verbindungsmodus starten"""
        self.connecting = True
        self.connection_start = node
        self.config(cursor="crosshair")
        
        if hasattr(self.editor, '_set_status'):
            self.editor._set_status("Klicke auf Ziel-Szene für Verbindung...")
    
    def _finish_connecting(self, target_node: FlowNode):
        """Verbindung abschließen"""
        if self.connection_start and target_node != self.connection_start:
            # Verbindung erstellen
            self._create_connection(self.connection_start, target_node)
        
        self._cancel_connecting()
    
    def _cancel_connecting(self):
        """Verbindungsmodus abbrechen"""
        self.connecting = False
        self.connection_start = None
        self.delete("temp_connection")
        self.config(cursor="")
        
        if hasattr(self.editor, '_set_status'):
            self.editor._set_status("Bereit")
    
    def _create_connection(self, source_node: FlowNode, target_node: FlowNode):
        """Erstellt eine neue Verbindung (Trigger + Action)"""
        # Trigger erstellen
        trigger = Trigger(
            name=f"Gehe zu {target_node.scene.name}",
            trigger_type=TriggerType.CLICK
        )
        
        # Action für Szenen-Übergang
        action = Action(
            action_type=ActionType.TRANSITION,
            params={
                "target_scene_id": target_node.scene.id,
                "transition_type": "fade"
            }
        )
        trigger.actions.append(action)
        
        # Trigger zur Quell-Szene hinzufügen
        source_node.scene.triggers.append(trigger)
        
        # Verbindung zum Graph hinzufügen
        conn = FlowConnection(source_node, target_node.scene.id, trigger, action)
        self.connections.append(conn)
        
        # Editor informieren
        if hasattr(self.editor, '_mark_changed'):
            self.editor._mark_changed()
        
        if hasattr(self.editor, '_set_status'):
            self.editor._set_status(f"Verbindung erstellt: {source_node.scene.name} → {target_node.scene.name}")
        
        self.redraw()
    
    def _delete_selected(self):
        """Ausgewählte Verbindung löschen"""
        if self.selected_connection:
            conn = self.selected_connection
            
            # Trigger aus Szene entfernen
            if conn.trigger and conn.trigger in conn.source_node.scene.triggers:
                conn.source_node.scene.triggers.remove(conn.trigger)
            
            # Verbindung entfernen
            if conn in self.connections:
                self.connections.remove(conn)
            
            self.selected_connection = None
            
            if hasattr(self.editor, '_mark_changed'):
                self.editor._mark_changed()
            
            self.redraw()
    
    # ============================================================
    # KONTEXT-MENÜ
    # ============================================================
    
    def _show_context_menu(self, event, node: Optional[FlowNode]):
        """Zeigt Kontext-Menü"""
        menu = tk.Menu(self, tearoff=0, bg="#2a2a4e", fg="white")
        
        if node:
            menu.add_command(label="🔗 Verbindung erstellen", 
                            command=lambda: self._start_connecting(node))
            menu.add_command(label="🏁 Als Startszene setzen",
                            command=lambda: self._set_as_start(node))
            menu.add_separator()
            menu.add_command(label="📝 Bearbeiten",
                            command=lambda: self._edit_node(node))
        else:
            menu.add_command(label="🔄 Auto-Layout", command=self._auto_layout)
            menu.add_command(label="🎯 Auf Ursprung zentrieren", command=self._center_view)
        
        menu.add_separator()
        menu.add_command(label="🔍 Zoom zurücksetzen", command=self._reset_zoom)
        
        menu.post(event.x_root, event.y_root)
    
    def _set_as_start(self, node: FlowNode):
        """Setzt Node als Startszene"""
        if hasattr(self.editor, 'current_chapter') and self.editor.current_chapter:
            self.editor.current_chapter.start_scene_id = node.scene.id
            
            if hasattr(self.editor, '_mark_changed'):
                self.editor._mark_changed()
            
            self.redraw()
    
    def _edit_node(self, node: FlowNode):
        """Öffnet Bearbeitung für Node"""
        # Editor informieren
        if hasattr(self.editor, 'current_scene'):
            self.editor.current_scene = node.scene
            self.editor._refresh_properties()
    
    def _auto_layout(self):
        """Automatisches Layout der Nodes"""
        if not self.nodes:
            return
        
        # Einfaches Grid-Layout
        cols = max(1, int(math.sqrt(len(self.nodes))))
        
        for i, node in enumerate(self.nodes.values()):
            node.x = 50 + (i % cols) * 250
            node.y = 50 + (i // cols) * 150
        
        self.redraw()
    
    def _center_view(self):
        """Zentriert die Ansicht"""
        if not self.nodes:
            return
        
        # Mittelpunkt aller Nodes berechnen
        avg_x = sum(n.x + n.width / 2 for n in self.nodes.values()) / len(self.nodes)
        avg_y = sum(n.y + n.height / 2 for n in self.nodes.values()) / len(self.nodes)
        
        # Pan setzen
        w = self.winfo_width() or 800
        h = self.winfo_height() or 600
        
        self.pan_x = w / 2 - avg_x * self.zoom_level
        self.pan_y = h / 2 - avg_y * self.zoom_level
        
        self.redraw()
    
    def _reset_zoom(self):
        """Zoom zurücksetzen"""
        self.zoom_level = 1.0
        self._center_view()


class FlowGraphPanel:
    """
    Panel-Wrapper für den Flow-Graph
    """
    
    def __init__(self, parent_frame: tk.Frame, editor):
        self.parent = parent_frame
        self.editor = editor
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI aufbauen"""
        # Toolbar
        toolbar = tk.Frame(self.parent, bg="#0f3460", height=35)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        tk.Label(
            toolbar,
            text="🔗 Flow-Graph",
            bg="#0f3460", fg="white",
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=10)
        
        # Buttons
        tk.Button(
            toolbar, text="🔄", font=("Arial", 10),
            bg="#0f3460", fg="white", relief=tk.FLAT,
            command=self._auto_layout
        ).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(
            toolbar, text="🎯", font=("Arial", 10),
            bg="#0f3460", fg="white", relief=tk.FLAT,
            command=self._center_view
        ).pack(side=tk.RIGHT, padx=2)
        
        # Graph-Canvas
        self.graph = FlowGraph(self.parent, self.editor)
        self.graph.pack(fill=tk.BOTH, expand=True)
    
    def set_scenes(self, scenes: List[Scene]):
        """Szenen setzen"""
        self.graph.set_scenes(scenes)
    
    def _auto_layout(self):
        """Auto-Layout"""
        self.graph._auto_layout()
    
    def _center_view(self):
        """Zentrieren"""
        self.graph._center_view()
    
    def refresh(self):
        """Aktualisieren"""
        if hasattr(self.editor, 'current_chapter') and self.editor.current_chapter:
            self.set_scenes(self.editor.current_chapter.scenes)
        else:
            self.graph.nodes.clear()
            self.graph.connections.clear()
            self.graph.redraw()


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    from storyboard_system import Storyboard, Chapter
    
    root = tk.Tk()
    root.title("Flow-Graph Test")
    root.geometry("900x700")
    root.configure(bg="#1a1a2e")
    
    # Mock Editor
    class MockEditor:
        def __init__(self):
            self.storyboard = Storyboard(name="Test")
            self.current_chapter = Chapter(name="Kapitel 1")
            self.current_scene = None
            
            # Test-Szenen
            s1 = Scene(name="Intro", scene_type=SceneType.CUTSCENE)
            s2 = Scene(name="Dorf", scene_type=SceneType.MAP_JSON)
            s3 = Scene(name="Wald", scene_type=SceneType.VIDEO)
            s4 = Scene(name="Höhle", scene_type=SceneType.MAP_SVG)
            s5 = Scene(name="Boss-Kampf", scene_type=SceneType.IMAGE)
            
            # Trigger/Verbindungen
            t1 = Trigger(name="Weiter", trigger_type=TriggerType.CLICK)
            t1.actions.append(Action(action_type=ActionType.TRANSITION, 
                                    params={"target_scene_id": s2.id}))
            s1.triggers.append(t1)
            
            t2 = Trigger(name="In den Wald", trigger_type=TriggerType.ENTER_AREA)
            t2.actions.append(Action(action_type=ActionType.TRANSITION,
                                    params={"target_scene_id": s3.id}))
            s2.triggers.append(t2)
            
            t3 = Trigger(name="Höhle betreten", trigger_type=TriggerType.CLICK)
            t3.actions.append(Action(action_type=ActionType.TRANSITION,
                                    params={"target_scene_id": s4.id}))
            s3.triggers.append(t3)
            
            self.current_chapter.scenes = [s1, s2, s3, s4, s5]
            self.current_chapter.start_scene_id = s1.id
        
        def _refresh_properties(self):
            pass
        
        def _mark_changed(self):
            print("Changed!")
        
        def _set_status(self, msg):
            print(f"Status: {msg}")
    
    mock = MockEditor()
    
    panel = FlowGraphPanel(root, mock)
    panel.set_scenes(mock.current_chapter.scenes)
    
    # Instructions
    info = tk.Label(
        root,
        text="Doppelklick = Verbindung starten | Mittlere Maustaste = Pan | Mausrad = Zoom",
        bg="#0f3460", fg="white"
    )
    info.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()
