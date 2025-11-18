# 🔧 QUICK FIXES - Implementation Guide

## ✅ ÄNDERUNGEN die SOFORT gemacht werden müssen

### 1. **FULLSCREEN START** (2 Dateien)

#### File: `enhanced_main.py` Zeile ~107
```python
# VORHER:
editor_win = tk.Toplevel(self)
editor_win.title("Map Editor - Der Eine Ring")
editor_win.geometry("1400x900")

# NACHHER:
editor_win = tk.Toplevel(self)
editor_win.title("Map Editor - Der Eine Ring")
editor_win.state('zoomed')  # ← MAXIMIERT starten
```

#### File: `gm_controls.py` Zeile ~12
```python
# VORHER:
self.title("Gamemaster Kontrollpanel")
self.geometry("800x600")

# NACHHER:
self.title("Gamemaster Kontrollpanel")
self.state('zoomed')  # ← MAXIMIERT starten
```

---

### 2. **SELECT-TOOL für Lichtquellen** (map_editor.py)

#### A) Tool hinzufügen (Zeile ~140 - nach `self.active_tool`)
```python
# Nach: self.active_tool = tk.StringVar(value="brush")
self.selected_light = None  # Index der ausgewählten Lichtquelle
self.selected_polygon = None  # Index des ausgewählten Polygons
```

#### B) Tool-Button hinzufügen (Zeile ~380 - bei anderen Tools)
```python
# Im tools_frame nach anderen Tool-Buttons:
tk.Radiobutton(tools_frame, text="🖱️ Auswählen", 
              variable=self.active_tool, value="select",
              bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
              font=("Arial", 9)).pack(anchor=tk.W, padx=5)
```

#### C) Click-Handler erweitern (Zeile ~1300 - in `on_canvas_click`)
```python
# Nach: if tool == "light":
# NEU:
if tool == "select":
    # Prüfe ob Lichtquelle geklickt
    light_index = self.lighting_engine.get_light_at(x, y, tolerance=2)
    if light_index is not None:
        self.selected_light = light_index
        self.selected_polygon = None
        self.show_light_context_menu(light_index)
        self.draw_grid()  # Zeige Auswahl-Marker
        return
    
    # Prüfe ob Polygon geklickt
    for i, polygon in enumerate(self.lighting_engine.darkness_polygons):
        if self.point_in_polygon(x, y, polygon):
            self.selected_polygon = i
            self.selected_light = None
            self.show_polygon_context_menu(i)
            self.draw_grid()
            return
    
    # Nichts getroffen - Auswahl aufheben
    self.selected_light = None
    self.selected_polygon = None
    self.hide_context_menu()
    self.draw_grid()
    return
```

---

### 3. **CONTEXT-MENU** (map_editor.py)

#### NEU nach `setup_ui()` Methode (Zeile ~650):
```python
def create_context_panel(self):
    """Erstellt kontextabhängiges Properties-Panel (rechts)"""
    # Panel wird nur bei Auswahl sichtbar
    self.context_panel = tk.Frame(self, bg="#1a1a1a", width=250)
    # Nicht packen - wird nur bei Bedarf angezeigt
    
    # Light Context
    self.light_context = tk.LabelFrame(self.context_panel, text="💡 Lichtquelle", 
                                      bg="#1a1a1a", fg="white")
    
    tk.Label(self.light_context, text="Position:", bg="#1a1a1a", fg="white").pack()
    self.light_pos_label = tk.Label(self.light_context, text="(0, 0)", 
                                    bg="#1a1a1a", fg="#aaa")
    self.light_pos_label.pack()
    
    tk.Label(self.light_context, text="Radius:", bg="#1a1a1a", fg="white").pack()
    self.light_radius_var = tk.DoubleVar(value=5.0)
    tk.Scale(self.light_context, from_=1, to=15, resolution=0.5,
            variable=self.light_radius_var, command=self.update_selected_light_radius,
            orient=tk.HORIZONTAL, bg="#2a2a2a", fg="white").pack(fill=tk.X, padx=5)
    
    tk.Button(self.light_context, text="🗑️ Löschen", bg="#7d2a2a", fg="white",
             command=self.delete_selected_light).pack(pady=5)
    
    # Polygon Context
    self.polygon_context = tk.LabelFrame(self.context_panel, text="🌑 Dunkelzone",
                                        bg="#1a1a1a", fg="white")
    
    tk.Label(self.polygon_context, text="Punkte:", bg="#1a1a1a", fg="white").pack()
    self.polygon_points_label = tk.Label(self.polygon_context, text="0", 
                                        bg="#1a1a1a", fg="#aaa")
    self.polygon_points_label.pack()
    
    tk.Button(self.polygon_context, text="✏️ Bearbeiten", bg="#2a5d8d", fg="white",
             command=self.edit_selected_polygon).pack(pady=5)
    tk.Button(self.polygon_context, text="🗑️ Löschen", bg="#7d2a2a", fg="white",
             command=self.delete_selected_polygon).pack(pady=5)

def show_light_context_menu(self, light_index):
    """Zeigt Context-Menu für Lichtquelle"""
    self.context_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
    self.light_context.pack(fill=tk.X, padx=5, pady=5)
    self.polygon_context.pack_forget()
    
    light = self.lighting_engine.lights[light_index]
    self.light_pos_label.config(text=f"({light.x}, {light.y})")
    self.light_radius_var.set(light.radius)

def show_polygon_context_menu(self, polygon_index):
    """Zeigt Context-Menu für Polygon"""
    self.context_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
    self.polygon_context.pack(fill=tk.X, padx=5, pady=5)
    self.light_context.pack_forget()
    
    polygon = self.lighting_engine.darkness_polygons[polygon_index]
    self.polygon_points_label.config(text=str(len(polygon)))

def hide_context_menu(self):
    """Versteckt Context-Menu"""
    self.context_panel.pack_forget()
```

---

### 4. **LAYER-SYSTEM** (map_editor.py Zeile ~160)

#### Nach: `self.layer_manager = LayerManager()`
```python
# Füge spezielle Layer hinzu
self.layer_manager.add_layer("lights", "💡 Lichtquellen", visible=True, locked=False)
self.layer_manager.add_layer("darkness", "🌑 Dunkelzonen", visible=True, locked=False)
```

---

### 5. **AUSWAHL-MARKER ZEICHNEN** (map_editor.py in `draw_grid()`)

#### In draw_grid() nach Lighting-Rendering (Zeile ~1230):
```python
# Nach: for light in self.lighting_engine.lights:
# Am Ende der Lighting-Schleife:

# AUSWAHL-MARKER für Lichtquelle
if self.selected_light is not None and self.selected_light < len(self.lighting_engine.lights):
    light = self.lighting_engine.lights[self.selected_light]
    lx = light.x * self.tile_size + self.tile_size // 2
    ly = light.y * self.tile_size + self.tile_size // 2
    
    # Gelber Auswahl-Ring
    self.canvas.create_oval(
        lx - 15, ly - 15, lx + 15, ly + 15,
        outline="yellow", width=3, tags="selection_marker"
    )
    
    # Pulsierender Effekt (optional)
    self.canvas.create_oval(
        lx - 20, ly - 20, lx + 20, ly + 20,
        outline="yellow", width=1, dash=(5, 5), tags="selection_marker"
    )
```

---

### 6. **POLYGON SMOOTH DRAWING** (map_editor.py)

#### Idee: Während Zeichnen Canvas-Koordinaten nutzen, erst am Ende zu Tiles
```python
# In on_canvas_click für Darkness-Polygon:
if self.drawing_darkness_polygon:
    # Speichere EXAKTE Canvas-Koordinaten
    canvas_x = self.canvas.canvasx(event.x)
    canvas_y = self.canvas.canvasy(event.y)
    
    # Speichere als Float für smooth drawing
    self.current_darkness_polygon_raw.append((canvas_x, canvas_y))
    
    # Zeichne Preview-Line smooth
    self.draw_polygon_preview()
    return

# Beim Finish: Konvertiere zu Tile-Koordinaten
def finish_darkness_polygon(self):
    if len(self.current_darkness_polygon_raw) >= 3:
        # Konvertiere Canvas → Tiles
        tile_polygon = [
            (int(cx / self.tile_size), int(cy / self.tile_size))
            for cx, cy in self.current_darkness_polygon_raw
        ]
        self.lighting_engine.darkness_polygons.append(tile_polygon)
```

---

## 🎯 ZUSAMMENFASSUNG DER ÄNDERUNGEN

| Datei | Zeilen | Änderung |
|-------|--------|----------|
| `enhanced_main.py` | ~107 | Fullscreen: `.state('zoomed')` |
| `gm_controls.py` | ~12 | Fullscreen: `.state('zoomed')` |
| `map_editor.py` | ~140 | Neue Variablen: `selected_light`, `selected_polygon` |
| `map_editor.py` | ~160 | Layer für Lights & Darkness |
| `map_editor.py` | ~380 | Select-Tool Button |
| `map_editor.py` | ~650 | Context-Panel Methoden (NEU) |
| `map_editor.py` | ~1230 | Auswahl-Marker zeichnen |
| `map_editor.py` | ~1300 | Select-Tool Click-Handler |

---

## ⏱️ ZEITAUFWAND

- **Quick Fixes (P0)**: ~30 Min
- **Polygon Smooth**: ~1 Std
- **Polygon Edit**: ~2 Std
- **Geometrie-Tools**: ~3 Std
- **Kantenerkennung**: ~4 Std
- **GUI Redesign**: ~8 Std

**Total für alle Features**: ~18 Std

---

## 🚀 NÄCHSTE SCHRITTE

1. Implementiere Fullscreen (5 Min) ✓
2. Implementiere Select-Tool (20 Min)
3. Implementiere Context-Menu (30 Min)
4. Teste alles
5. Dann weiter mit Polygon-Features
