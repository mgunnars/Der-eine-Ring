"""
Partikel-Editor GUI - Blender-ähnliche Benutzeroberfläche
Zum Erstellen, Anpassen und Exportieren von Partikel-Effekten
"""

import sys
import os
import math
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QSlider, QComboBox, QSpinBox, QDoubleSpinBox,
        QGroupBox, QScrollArea, QFrame, QSplitter, QTabWidget,
        QFileDialog, QMessageBox, QProgressDialog, QColorDialog,
        QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QGridLayout,
        QToolBar, QAction, QMenu, QMenuBar, QStatusBar, QDockWidget,
        QSizePolicy
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
    from PyQt5.QtGui import (
        QImage, QPixmap, QPainter, QColor, QPen, QBrush,
        QIcon, QFont, QPalette
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt5 nicht verfügbar. Installieren mit: pip install PyQt5")

import numpy as np

from particle_system import (
    ParticleCanvas, ParticleEmitter, ParticleType, BlendMode,
    Vector3, Color, RectEmitter, CircleEmitter, PointEmitter, LineEmitter,
    GravityForce, WindForce, VortexForce, CollisionPlane
)
from particle_renderer import AdvancedParticleRenderer, TextureType
from particle_exporter import ParticleExporter, ExportSettings, ExportFormat


class ExportThread(QThread):
    """Thread für den Export-Prozess"""
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(bool)
    
    def __init__(self, canvas: ParticleCanvas, output_path: str, settings: ExportSettings):
        super().__init__()
        self.canvas = canvas
        self.output_path = output_path
        self.settings = settings
    
    def run(self):
        exporter = ParticleExporter()
        exporter.progress_callback = lambda p, m: self.progress.emit(p, m)
        
        # Kopie des Canvas erstellen (für Thread-Sicherheit)
        canvas_copy = ParticleCanvas(self.canvas.width, self.canvas.height)
        for emitter in self.canvas.emitters:
            # Emitter kopieren
            new_emitter = ParticleEmitter(emitter.particle_type)
            new_emitter.shape = emitter.shape
            new_emitter.emission_rate = emitter.emission_rate
            new_emitter.lifetime = emitter.lifetime
            new_emitter.start_speed = emitter.start_speed
            new_emitter.direction = emitter.direction
            new_emitter.spread = emitter.spread
            new_emitter.start_size = emitter.start_size
            new_emitter.end_size = emitter.end_size
            new_emitter.start_color = emitter.start_color
            new_emitter.end_color = emitter.end_color
            new_emitter.blend_mode = emitter.blend_mode
            new_emitter.forces = emitter.forces.copy()
            new_emitter.trail_length = emitter.trail_length
            canvas_copy.add_emitter(new_emitter)
        
        canvas_copy.glow_strength = self.canvas.glow_strength
        canvas_copy.glow_radius = self.canvas.glow_radius
        canvas_copy.motion_blur = self.canvas.motion_blur
        
        success = exporter.export(canvas_copy, self.output_path, self.settings)
        self.finished.emit(success)


class ParticlePreview(QWidget):
    """Vorschau-Widget für Partikel"""
    
    def __init__(self, width: int = 800, height: int = 600):
        super().__init__()
        self.preview_width = width
        self.preview_height = height
        
        self.setMinimumSize(400, 300)
        self.setMaximumSize(1920, 1080)
        
        self.canvas = ParticleCanvas(width, height)
        self.renderer = AdvancedParticleRenderer(width, height)
        
        self.current_frame: Optional[QPixmap] = None
        self.playing = False
        
        # Timer für Animation
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.fps = 60
        
        # Statistiken
        self.particle_count = 0
        self.frame_time = 0
    
    def set_canvas_size(self, width: int, height: int):
        """Ändere Canvas-Größe"""
        self.preview_width = width
        self.preview_height = height
        self.canvas = ParticleCanvas(width, height)
        self.renderer = AdvancedParticleRenderer(width, height)
    
    def add_emitter(self, emitter: ParticleEmitter):
        """Füge Emitter hinzu"""
        self.canvas.add_emitter(emitter)
    
    def clear_emitters(self):
        """Entferne alle Emitter"""
        self.canvas.emitters.clear()
    
    def play(self):
        """Starte Animation"""
        self.playing = True
        self.timer.start(1000 // self.fps)
    
    def pause(self):
        """Pausiere Animation"""
        self.playing = False
        self.timer.stop()
    
    def reset(self):
        """Setze zurück"""
        for emitter in self.canvas.emitters:
            emitter.clear()
        self._update_frame()
    
    def _update_frame(self):
        """Aktualisiere Frame"""
        import time
        start = time.time()
        
        # Update
        self.canvas.update(1.0 / self.fps)
        
        # Render
        frame = self.renderer.render(self.canvas)
        
        # Zu QPixmap konvertieren
        self._frame_to_pixmap(frame)
        
        self.particle_count = self.canvas.get_total_particles()
        self.frame_time = (time.time() - start) * 1000
        
        self.update()
    
    def _frame_to_pixmap(self, frame: np.ndarray):
        """Konvertiere numpy array zu QPixmap"""
        height, width = frame.shape[:2]
        
        # Sicherstellen dass es uint8 ist
        if frame.dtype != np.uint8:
            frame = (np.clip(frame, 0, 255)).astype(np.uint8)
        
        # Kopie erstellen für stabile Daten
        frame = np.ascontiguousarray(frame)
        
        # QImage erstellen
        bytes_per_line = 4 * width
        qimage = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        
        # Wichtig: Kopie erstellen da frame.data sonst ungültig wird
        self.current_frame = QPixmap.fromImage(qimage.copy())
    
    def paintEvent(self, event):
        """Zeichne Vorschau"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Hintergrund (Schachbrett für Transparenz)
        self._draw_checkerboard(painter)
        
        # Frame zeichnen
        if self.current_frame:
            # Skalieren um in Widget zu passen
            scaled = self.current_frame.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        
        # Stats
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 20, f"Partikel: {self.particle_count}")
        painter.drawText(10, 35, f"Frame: {self.frame_time:.1f}ms")
    
    def _draw_checkerboard(self, painter: QPainter):
        """Zeichne Schachbrett-Hintergrund (zeigt Transparenz)"""
        checker_size = 10
        colors = [QColor(60, 60, 60), QColor(80, 80, 80)]
        
        for y in range(0, self.height(), checker_size):
            for x in range(0, self.width(), checker_size):
                color_idx = ((x // checker_size) + (y // checker_size)) % 2
                painter.fillRect(x, y, checker_size, checker_size, colors[color_idx])


class ColorButton(QPushButton):
    """Button der eine Farbe anzeigt"""
    
    def __init__(self, color: Color = Color(1, 1, 1, 1)):
        super().__init__()
        self.color = color
        self.setFixedSize(60, 25)
        self.clicked.connect(self._pick_color)
        self._update_style()
    
    def _update_style(self):
        r, g, b, a = self.color.to_int_tuple()
        self.setStyleSheet(
            f"background-color: rgba({r}, {g}, {b}, {a}); "
            f"border: 1px solid #555; border-radius: 3px;"
        )
    
    def _pick_color(self):
        initial = QColor(*self.color.to_int_tuple())
        color = QColorDialog.getColor(initial, self, "Farbe wählen", 
                                      QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.color = Color(
                color.red() / 255,
                color.green() / 255,
                color.blue() / 255,
                color.alpha() / 255
            )
            self._update_style()
    
    def get_color(self) -> Color:
        return self.color
    
    def set_color(self, color: Color):
        self.color = color
        self._update_style()


class EmitterPanel(QWidget):
    """Panel für Emitter-Einstellungen"""
    
    emitter_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.emitter: Optional[ParticleEmitter] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Scroll-Bereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # === Partikel-Typ ===
        type_group = QGroupBox("Partikel-Typ")
        type_layout = QVBoxLayout(type_group)
        
        self.type_combo = QComboBox()
        for pt in ParticleType:
            self.type_combo.addItem(pt.name, pt)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)
        
        content_layout.addWidget(type_group)
        
        # === Emission ===
        emission_group = QGroupBox("Emission")
        emission_layout = QGridLayout(emission_group)
        
        emission_layout.addWidget(QLabel("Rate:"), 0, 0)
        self.emission_rate = QSpinBox()
        self.emission_rate.setRange(0, 10000)
        self.emission_rate.setValue(100)
        self.emission_rate.valueChanged.connect(self._on_value_changed)
        emission_layout.addWidget(self.emission_rate, 0, 1)
        
        emission_layout.addWidget(QLabel("Max:"), 1, 0)
        self.max_particles = QSpinBox()
        self.max_particles.setRange(100, 100000)
        self.max_particles.setValue(10000)
        self.max_particles.valueChanged.connect(self._on_value_changed)
        emission_layout.addWidget(self.max_particles, 1, 1)
        
        content_layout.addWidget(emission_group)
        
        # === Lebensdauer ===
        life_group = QGroupBox("Lebensdauer")
        life_layout = QGridLayout(life_group)
        
        life_layout.addWidget(QLabel("Dauer:"), 0, 0)
        self.lifetime = QDoubleSpinBox()
        self.lifetime.setRange(0.1, 30.0)
        self.lifetime.setValue(2.0)
        self.lifetime.setSingleStep(0.1)
        self.lifetime.valueChanged.connect(self._on_value_changed)
        life_layout.addWidget(self.lifetime, 0, 1)
        
        life_layout.addWidget(QLabel("Variation:"), 1, 0)
        self.lifetime_var = QDoubleSpinBox()
        self.lifetime_var.setRange(0, 10.0)
        self.lifetime_var.setValue(0.5)
        self.lifetime_var.valueChanged.connect(self._on_value_changed)
        life_layout.addWidget(self.lifetime_var, 1, 1)
        
        content_layout.addWidget(life_group)
        
        # === Geschwindigkeit ===
        speed_group = QGroupBox("Geschwindigkeit")
        speed_layout = QGridLayout(speed_group)
        
        speed_layout.addWidget(QLabel("Start:"), 0, 0)
        self.start_speed = QDoubleSpinBox()
        self.start_speed.setRange(0, 2000)
        self.start_speed.setValue(100)
        self.start_speed.valueChanged.connect(self._on_value_changed)
        speed_layout.addWidget(self.start_speed, 0, 1)
        
        speed_layout.addWidget(QLabel("Variation:"), 1, 0)
        self.speed_var = QDoubleSpinBox()
        self.speed_var.setRange(0, 500)
        self.speed_var.setValue(20)
        self.speed_var.valueChanged.connect(self._on_value_changed)
        speed_layout.addWidget(self.speed_var, 1, 1)
        
        speed_layout.addWidget(QLabel("Streuung:"), 2, 0)
        self.spread = QDoubleSpinBox()
        self.spread.setRange(0, 1)
        self.spread.setValue(0.1)
        self.spread.setSingleStep(0.05)
        self.spread.valueChanged.connect(self._on_value_changed)
        speed_layout.addWidget(self.spread, 2, 1)
        
        content_layout.addWidget(speed_group)
        
        # === Größe ===
        size_group = QGroupBox("Größe")
        size_layout = QGridLayout(size_group)
        
        size_layout.addWidget(QLabel("Start:"), 0, 0)
        self.start_size = QDoubleSpinBox()
        self.start_size.setRange(0.1, 200)
        self.start_size.setValue(5)
        self.start_size.valueChanged.connect(self._on_value_changed)
        size_layout.addWidget(self.start_size, 0, 1)
        
        size_layout.addWidget(QLabel("Ende:"), 1, 0)
        self.end_size = QDoubleSpinBox()
        self.end_size.setRange(0, 200)
        self.end_size.setValue(0)
        self.end_size.valueChanged.connect(self._on_value_changed)
        size_layout.addWidget(self.end_size, 1, 1)
        
        size_layout.addWidget(QLabel("Variation:"), 2, 0)
        self.size_var = QDoubleSpinBox()
        self.size_var.setRange(0, 50)
        self.size_var.setValue(2)
        self.size_var.valueChanged.connect(self._on_value_changed)
        size_layout.addWidget(self.size_var, 2, 1)
        
        content_layout.addWidget(size_group)
        
        # === Farbe ===
        color_group = QGroupBox("Farbe")
        color_layout = QGridLayout(color_group)
        
        color_layout.addWidget(QLabel("Start:"), 0, 0)
        self.start_color = ColorButton(Color(1, 1, 1, 1))
        color_layout.addWidget(self.start_color, 0, 1)
        
        color_layout.addWidget(QLabel("Ende:"), 1, 0)
        self.end_color = ColorButton(Color(1, 1, 1, 0))
        color_layout.addWidget(self.end_color, 1, 1)
        
        color_layout.addWidget(QLabel("Blend:"), 2, 0)
        self.blend_mode = QComboBox()
        for bm in BlendMode:
            self.blend_mode.addItem(bm.name, bm)
        self.blend_mode.currentIndexChanged.connect(self._on_value_changed)
        color_layout.addWidget(self.blend_mode, 2, 1)
        
        content_layout.addWidget(color_group)
        
        # === Trail ===
        trail_group = QGroupBox("Trail")
        trail_layout = QGridLayout(trail_group)
        
        trail_layout.addWidget(QLabel("Länge:"), 0, 0)
        self.trail_length = QSpinBox()
        self.trail_length.setRange(0, 50)
        self.trail_length.setValue(0)
        self.trail_length.valueChanged.connect(self._on_value_changed)
        trail_layout.addWidget(self.trail_length, 0, 1)
        
        content_layout.addWidget(trail_group)
        
        # === Physik ===
        physics_group = QGroupBox("Physik")
        physics_layout = QGridLayout(physics_group)
        
        physics_layout.addWidget(QLabel("Gravitation:"), 0, 0)
        self.gravity = QDoubleSpinBox()
        self.gravity.setRange(-500, 500)
        self.gravity.setValue(0)
        self.gravity.valueChanged.connect(self._on_value_changed)
        physics_layout.addWidget(self.gravity, 0, 1)
        
        physics_layout.addWidget(QLabel("Wind X:"), 1, 0)
        self.wind_x = QDoubleSpinBox()
        self.wind_x.setRange(-200, 200)
        self.wind_x.setValue(0)
        self.wind_x.valueChanged.connect(self._on_value_changed)
        physics_layout.addWidget(self.wind_x, 1, 1)
        
        physics_layout.addWidget(QLabel("Turbulenz:"), 2, 0)
        self.turbulence = QDoubleSpinBox()
        self.turbulence.setRange(0, 100)
        self.turbulence.setValue(0)
        self.turbulence.valueChanged.connect(self._on_value_changed)
        physics_layout.addWidget(self.turbulence, 2, 1)
        
        content_layout.addWidget(physics_group)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def set_emitter(self, emitter: ParticleEmitter):
        """Setze Emitter und lade Werte"""
        self.emitter = emitter
        
        # Blockiere Signals während des Ladens
        self._block_signals(True)
        
        # Werte laden
        idx = self.type_combo.findData(emitter.particle_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        
        self.emission_rate.setValue(int(emitter.emission_rate))
        self.max_particles.setValue(emitter.max_particles)
        self.lifetime.setValue(emitter.lifetime)
        self.lifetime_var.setValue(emitter.lifetime_variation)
        self.start_speed.setValue(emitter.start_speed)
        self.speed_var.setValue(emitter.speed_variation)
        self.spread.setValue(emitter.spread)
        self.start_size.setValue(emitter.start_size)
        self.end_size.setValue(emitter.end_size)
        self.size_var.setValue(emitter.size_variation)
        self.start_color.set_color(emitter.start_color)
        self.end_color.set_color(emitter.end_color)
        self.trail_length.setValue(emitter.trail_length)
        
        idx = self.blend_mode.findData(emitter.blend_mode)
        if idx >= 0:
            self.blend_mode.setCurrentIndex(idx)
        
        # Physik (erste Force von jedem Typ suchen)
        gravity = 0
        wind_x = 0
        turbulence = 0
        for force in emitter.forces:
            if isinstance(force, GravityForce):
                gravity = force.strength
            elif isinstance(force, WindForce):
                wind_x = force.direction.x * force.strength
                turbulence = force.turbulence
        
        self.gravity.setValue(gravity)
        self.wind_x.setValue(wind_x)
        self.turbulence.setValue(turbulence)
        
        self._block_signals(False)
    
    def _block_signals(self, block: bool):
        """Blockiere/Entsperre alle Signals"""
        widgets = [
            self.type_combo, self.emission_rate, self.max_particles,
            self.lifetime, self.lifetime_var, self.start_speed, self.speed_var,
            self.spread, self.start_size, self.end_size, self.size_var,
            self.trail_length, self.blend_mode, self.gravity, self.wind_x,
            self.turbulence
        ]
        for w in widgets:
            w.blockSignals(block)
    
    def _on_type_changed(self, index):
        """Partikel-Typ geändert"""
        if not self.emitter:
            return
        
        particle_type = self.type_combo.currentData()
        self.emitter.particle_type = particle_type
        self.emitter._apply_preset(particle_type)
        
        # UI aktualisieren
        self.set_emitter(self.emitter)
        self.emitter_changed.emit()
    
    def _on_value_changed(self):
        """Wert geändert"""
        if not self.emitter:
            return
        
        self.emitter.emission_rate = self.emission_rate.value()
        self.emitter.max_particles = self.max_particles.value()
        self.emitter.lifetime = self.lifetime.value()
        self.emitter.lifetime_variation = self.lifetime_var.value()
        self.emitter.start_speed = self.start_speed.value()
        self.emitter.speed_variation = self.speed_var.value()
        self.emitter.spread = self.spread.value()
        self.emitter.start_size = self.start_size.value()
        self.emitter.end_size = self.end_size.value()
        self.emitter.size_variation = self.size_var.value()
        self.emitter.start_color = self.start_color.get_color()
        self.emitter.end_color = self.end_color.get_color()
        self.emitter.trail_length = self.trail_length.value()
        self.emitter.blend_mode = self.blend_mode.currentData()
        
        # Physik aktualisieren
        self.emitter.forces.clear()
        
        gravity = self.gravity.value()
        if gravity != 0:
            direction = Vector3(0, 1, 0) if gravity > 0 else Vector3(0, -1, 0)
            self.emitter.forces.append(GravityForce(direction=direction, strength=abs(gravity)))
        
        wind_x = self.wind_x.value()
        turbulence = self.turbulence.value()
        if wind_x != 0 or turbulence > 0:
            direction = Vector3(1, 0, 0) if wind_x >= 0 else Vector3(-1, 0, 0)
            self.emitter.forces.append(WindForce(
                direction=direction, 
                strength=abs(wind_x),
                turbulence=turbulence,
                radius=10000
            ))
        
        self.emitter_changed.emit()


class ParticleEditorWindow(QMainWindow):
    """Hauptfenster des Partikel-Editors"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Partikel-Editor - Blender Style")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        
        # Standard-Emitter erstellen
        self._create_default_emitter()
        
        # Starte Animation
        self.preview.play()
    
    def _setup_ui(self):
        # Zentrales Widget
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        
        # Splitter für resizable Bereiche
        splitter = QSplitter(Qt.Horizontal)
        
        # === Linke Seite: Emitter-Liste und Eigenschaften ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Emitter-Liste
        emitter_group = QGroupBox("Emitter")
        emitter_layout = QVBoxLayout(emitter_group)
        
        self.emitter_list = QListWidget()
        self.emitter_list.currentRowChanged.connect(self._on_emitter_selected)
        emitter_layout.addWidget(self.emitter_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Hinzufügen")
        add_btn.clicked.connect(self._add_emitter)
        remove_btn = QPushButton("Entfernen")
        remove_btn.clicked.connect(self._remove_emitter)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        emitter_layout.addLayout(btn_layout)
        
        left_layout.addWidget(emitter_group)
        
        # Emitter-Eigenschaften
        self.emitter_panel = EmitterPanel()
        self.emitter_panel.emitter_changed.connect(self._on_emitter_changed)
        left_layout.addWidget(self.emitter_panel, stretch=1)
        
        left_panel.setMaximumWidth(350)
        splitter.addWidget(left_panel)
        
        # === Mitte: Vorschau ===
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        
        self.preview = ParticlePreview(800, 600)
        preview_layout.addWidget(self.preview, stretch=1)
        
        # Steuerung
        controls = QHBoxLayout()
        
        self.play_btn = QPushButton("⏸ Pause")
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)
        
        reset_btn = QPushButton("↺ Reset")
        reset_btn.clicked.connect(self._reset)
        controls.addWidget(reset_btn)
        
        controls.addStretch()
        
        controls.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 120)
        self.fps_spin.setValue(60)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        controls.addWidget(self.fps_spin)
        
        preview_layout.addLayout(controls)
        
        splitter.addWidget(preview_container)
        
        # === Rechte Seite: Canvas-Einstellungen und Export ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Canvas-Einstellungen
        canvas_group = QGroupBox("Canvas")
        canvas_layout = QGridLayout(canvas_group)
        
        canvas_layout.addWidget(QLabel("Breite:"), 0, 0)
        self.canvas_width = QSpinBox()
        self.canvas_width.setRange(100, 3840)
        self.canvas_width.setValue(1920)
        canvas_layout.addWidget(self.canvas_width, 0, 1)
        
        canvas_layout.addWidget(QLabel("Höhe:"), 1, 0)
        self.canvas_height = QSpinBox()
        self.canvas_height.setRange(100, 2160)
        self.canvas_height.setValue(1080)
        canvas_layout.addWidget(self.canvas_height, 1, 1)
        
        apply_size_btn = QPushButton("Anwenden")
        apply_size_btn.clicked.connect(self._apply_canvas_size)
        canvas_layout.addWidget(apply_size_btn, 2, 0, 1, 2)
        
        right_layout.addWidget(canvas_group)
        
        # Post-Effekte
        effects_group = QGroupBox("Effekte")
        effects_layout = QGridLayout(effects_group)
        
        effects_layout.addWidget(QLabel("Glow:"), 0, 0)
        self.glow_slider = QSlider(Qt.Horizontal)
        self.glow_slider.setRange(0, 100)
        self.glow_slider.setValue(0)
        self.glow_slider.valueChanged.connect(self._on_effect_changed)
        effects_layout.addWidget(self.glow_slider, 0, 1)
        
        effects_layout.addWidget(QLabel("Motion Blur:"), 1, 0)
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(0)
        self.blur_slider.valueChanged.connect(self._on_effect_changed)
        effects_layout.addWidget(self.blur_slider, 1, 1)
        
        right_layout.addWidget(effects_group)
        
        # Export
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("MP4 (Video)", ExportFormat.MP4)
        self.format_combo.addItem("WebM (Video + Alpha)", ExportFormat.WEBM)
        self.format_combo.addItem("GIF (Animiert)", ExportFormat.GIF)
        self.format_combo.addItem("APNG (Animiert + Alpha)", ExportFormat.APNG)
        self.format_combo.addItem("PNG-Sequenz", ExportFormat.PNG_SEQUENCE)
        format_layout.addWidget(self.format_combo)
        export_layout.addLayout(format_layout)
        
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Dauer (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.5, 60)
        self.duration_spin.setValue(5.0)
        duration_layout.addWidget(self.duration_spin)
        export_layout.addLayout(duration_layout)
        
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.export_fps = QSpinBox()
        self.export_fps.setRange(10, 60)
        self.export_fps.setValue(30)
        fps_layout.addWidget(self.export_fps)
        export_layout.addLayout(fps_layout)
        
        self.transparent_check = QCheckBox("Transparenter Hintergrund")
        self.transparent_check.setChecked(True)
        export_layout.addWidget(self.transparent_check)
        
        export_btn = QPushButton("📤 Exportieren...")
        export_btn.clicked.connect(self._export)
        export_btn.setMinimumHeight(40)
        export_layout.addWidget(export_btn)
        
        right_layout.addWidget(export_group)
        
        # Presets
        preset_group = QGroupBox("Schnell-Presets")
        preset_layout = QVBoxLayout(preset_group)
        
        presets = [
            ("🌧 Regen", ParticleType.RAIN),
            ("❄ Schnee", ParticleType.SNOW),
            ("🔥 Feuer", ParticleType.FIRE),
            ("💨 Rauch", ParticleType.SMOKE),
            ("✨ Funken", ParticleType.SPARK),
            ("🌟 Magie", ParticleType.MAGIC),
            ("🍂 Blätter", ParticleType.LEAVES),
            ("🌫 Nebel", ParticleType.FOG),
        ]
        
        for name, ptype in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, t=ptype: self._apply_preset(t))
            preset_layout.addWidget(btn)
        
        right_layout.addWidget(preset_group)
        right_layout.addStretch()
        
        right_panel.setMaximumWidth(300)
        splitter.addWidget(right_panel)
        
        main_layout.addWidget(splitter)
        
        # Statusbar
        self.statusBar().showMessage("Bereit")
    
    def _setup_menu(self):
        menubar = self.menuBar()
        
        # Datei
        file_menu = menubar.addMenu("Datei")
        
        new_action = QAction("Neu", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("Exportieren...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Beenden", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Ansicht
        view_menu = menubar.addMenu("Ansicht")
        
        reset_view = QAction("Ansicht zurücksetzen", self)
        reset_view.triggered.connect(self._reset)
        view_menu.addAction(reset_view)
        
        # Hilfe
        help_menu = menubar.addMenu("Hilfe")
        
        about_action = QAction("Über...", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        toolbar = self.addToolBar("Werkzeuge")
        toolbar.setMovable(False)
        
        # Play/Pause
        self.play_action = QAction("⏵", self)
        self.play_action.setToolTip("Abspielen/Pause")
        self.play_action.triggered.connect(self._toggle_play)
        toolbar.addAction(self.play_action)
        
        # Reset
        reset_action = QAction("↺", self)
        reset_action.setToolTip("Zurücksetzen")
        reset_action.triggered.connect(self._reset)
        toolbar.addAction(reset_action)
        
        toolbar.addSeparator()
        
        # Export
        export_action = QAction("📤", self)
        export_action.setToolTip("Exportieren")
        export_action.triggered.connect(self._export)
        toolbar.addAction(export_action)
    
    def _create_default_emitter(self):
        """Erstelle Standard-Emitter"""
        emitter = ParticleEmitter(ParticleType.RAIN)
        emitter.shape = RectEmitter(
            position=Vector3(400, -20, 0),
            width=850,
            height=20
        )
        emitter.collision_planes = [CollisionPlane(position=Vector3(0, 620, 0))]
        
        self.preview.add_emitter(emitter)
        self.emitter_list.addItem("Regen")
        self.emitter_list.setCurrentRow(0)
    
    def _add_emitter(self):
        """Füge neuen Emitter hinzu"""
        emitter = ParticleEmitter(ParticleType.RAIN)
        
        # Position in der Mitte
        w, h = self.preview.preview_width, self.preview.preview_height
        emitter.shape = CircleEmitter(position=Vector3(w/2, h/2, 0), radius=50)
        
        self.preview.add_emitter(emitter)
        
        count = self.emitter_list.count() + 1
        self.emitter_list.addItem(f"Emitter {count}")
        self.emitter_list.setCurrentRow(self.emitter_list.count() - 1)
    
    def _remove_emitter(self):
        """Entferne ausgewählten Emitter"""
        idx = self.emitter_list.currentRow()
        if idx >= 0 and len(self.preview.canvas.emitters) > 1:
            self.preview.canvas.emitters.pop(idx)
            self.emitter_list.takeItem(idx)
            
            if self.emitter_list.count() > 0:
                self.emitter_list.setCurrentRow(min(idx, self.emitter_list.count() - 1))
    
    def _on_emitter_selected(self, index):
        """Emitter ausgewählt"""
        if 0 <= index < len(self.preview.canvas.emitters):
            emitter = self.preview.canvas.emitters[index]
            self.emitter_panel.set_emitter(emitter)
    
    def _on_emitter_changed(self):
        """Emitter wurde geändert"""
        idx = self.emitter_list.currentRow()
        if idx >= 0:
            emitter = self.preview.canvas.emitters[idx]
            # Liste aktualisieren
            self.emitter_list.item(idx).setText(emitter.particle_type.name)
    
    def _toggle_play(self):
        """Play/Pause umschalten"""
        if self.preview.playing:
            self.preview.pause()
            self.play_btn.setText("▶ Play")
            self.play_action.setText("▶")
        else:
            self.preview.play()
            self.play_btn.setText("⏸ Pause")
            self.play_action.setText("⏸")
    
    def _reset(self):
        """Animation zurücksetzen"""
        self.preview.reset()
    
    def _on_fps_changed(self, value):
        """FPS geändert"""
        self.preview.fps = value
        if self.preview.playing:
            self.preview.timer.setInterval(1000 // value)
    
    def _apply_canvas_size(self):
        """Canvas-Größe anwenden"""
        w = self.canvas_width.value()
        h = self.canvas_height.value()
        
        # Emitter-Positionen anpassen
        old_w = self.preview.preview_width
        old_h = self.preview.preview_height
        
        scale_x = w / old_w
        scale_y = h / old_h
        
        for emitter in self.preview.canvas.emitters:
            if isinstance(emitter.shape, RectEmitter):
                emitter.shape.position.x *= scale_x
                emitter.shape.position.y *= scale_y
                emitter.shape.width *= scale_x
            elif isinstance(emitter.shape, CircleEmitter):
                emitter.shape.position.x *= scale_x
                emitter.shape.position.y *= scale_y
            
            # Kollisionsebenen anpassen
            for plane in emitter.collision_planes:
                plane.position.y *= scale_y
        
        self.preview.set_canvas_size(w, h)
        self._reset()
    
    def _on_effect_changed(self):
        """Effekt-Slider geändert"""
        self.preview.canvas.glow_strength = self.glow_slider.value() / 100
        self.preview.canvas.motion_blur = self.blur_slider.value() / 100
    
    def _apply_preset(self, particle_type: ParticleType):
        """Wende Preset an"""
        # Entferne alle Emitter
        self.preview.clear_emitters()
        self.emitter_list.clear()
        
        # Neuen Emitter mit Preset erstellen
        emitter = ParticleEmitter(particle_type)
        w, h = self.preview.preview_width, self.preview.preview_height
        
        if particle_type in [ParticleType.RAIN, ParticleType.SNOW, ParticleType.LEAVES]:
            emitter.shape = RectEmitter(
                position=Vector3(w/2, -30, 0),
                width=w + 200,
                height=20
            )
            if particle_type == ParticleType.RAIN:
                emitter.collision_planes = [CollisionPlane(position=Vector3(0, h + 10, 0))]
        elif particle_type in [ParticleType.FIRE, ParticleType.SMOKE]:
            emitter.shape = CircleEmitter(
                position=Vector3(w/2, h - 50, 0),
                radius=30
            )
            
            # Funken bei Feuer hinzufügen
            if particle_type == ParticleType.FIRE:
                sparks = ParticleEmitter(ParticleType.SPARK)
                sparks.shape = CircleEmitter(
                    position=Vector3(w/2, h - 70, 0),
                    radius=20
                )
                sparks.emission_rate = 15
                self.preview.add_emitter(sparks)
                self.emitter_list.addItem("Funken")
        elif particle_type == ParticleType.FOG:
            emitter.shape = RectEmitter(
                position=Vector3(-100, h/2, 0),
                width=50,
                height=h
            )
        else:
            emitter.shape = CircleEmitter(
                position=Vector3(w/2, h/2, 0),
                radius=50
            )
        
        self.preview.add_emitter(emitter)
        self.emitter_list.addItem(particle_type.name)
        self.emitter_list.setCurrentRow(0)
        
        self._reset()
        
        self.statusBar().showMessage(f"Preset '{particle_type.name}' angewendet")
    
    def _export(self):
        """Export-Dialog"""
        format_data = self.format_combo.currentData()
        
        # Dateiendung
        extensions = {
            ExportFormat.MP4: "MP4 Video (*.mp4)",
            ExportFormat.WEBM: "WebM Video (*.webm)",
            ExportFormat.GIF: "Animiertes GIF (*.gif)",
            ExportFormat.APNG: "Animiertes PNG (*.png)",
            ExportFormat.PNG_SEQUENCE: "PNG-Sequenz (*.png)",
        }
        
        default_names = {
            ExportFormat.MP4: "partikel.mp4",
            ExportFormat.WEBM: "partikel.webm",
            ExportFormat.GIF: "partikel.gif",
            ExportFormat.APNG: "partikel.png",
            ExportFormat.PNG_SEQUENCE: "partikel.png",
        }
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportieren als...",
            default_names.get(format_data, "partikel.mp4"),
            extensions.get(format_data, "Alle Dateien (*)")
        )
        
        if not filename:
            return
        
        # Export-Einstellungen
        settings = ExportSettings(
            format=format_data,
            width=self.canvas_width.value(),
            height=self.canvas_height.value(),
            fps=self.export_fps.value(),
            duration=self.duration_spin.value(),
            transparent_background=self.transparent_check.isChecked()
        )
        
        # Progress-Dialog
        progress = QProgressDialog("Exportiere...", "Abbrechen", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        # Export-Thread starten
        self.export_thread = ExportThread(self.preview.canvas, filename, settings)
        self.export_thread.progress.connect(
            lambda p, m: (progress.setValue(int(p * 100)), progress.setLabelText(m))
        )
        self.export_thread.finished.connect(
            lambda success: self._export_finished(success, filename, progress)
        )
        
        self.export_thread.start()
    
    def _export_finished(self, success: bool, filename: str, progress: QProgressDialog):
        """Export abgeschlossen"""
        progress.close()
        
        if success:
            QMessageBox.information(
                self, "Export abgeschlossen",
                f"Datei erfolgreich exportiert:\n{filename}"
            )
            self.statusBar().showMessage(f"Exportiert: {filename}")
        else:
            QMessageBox.warning(
                self, "Export fehlgeschlagen",
                "Der Export ist fehlgeschlagen.\n"
                "Bitte überprüfen Sie, ob ffmpeg installiert ist."
            )
    
    def _new_project(self):
        """Neues Projekt"""
        reply = QMessageBox.question(
            self, "Neues Projekt",
            "Möchten Sie wirklich ein neues Projekt beginnen?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.preview.clear_emitters()
            self.emitter_list.clear()
            self._create_default_emitter()
            self._reset()
    
    def _show_about(self):
        """Über-Dialog"""
        QMessageBox.about(
            self, "Über Partikel-Editor",
            "<h2>Partikel-Editor</h2>"
            "<p>Ein Blender-ähnlicher Partikel-Editor für das Erstellen "
            "von Regen, Schnee, Feuer und anderen Effekten.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Verschiedene Partikel-Typen</li>"
            "<li>Physik-Simulation</li>"
            "<li>Post-Processing-Effekte</li>"
            "<li>Export als MP4, WebM, GIF, APNG</li>"
            "</ul>"
            "<p>© 2024 Der-eine-Ring Projekt</p>"
        )


def launch_particle_editor():
    """Starte den Partikel-Editor"""
    if not PYQT_AVAILABLE:
        print("Fehler: PyQt5 ist erforderlich!")
        print("Installieren mit: pip install PyQt5")
        return
    
    app = QApplication(sys.argv)
    
    # Dark Theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
    app.setPalette(palette)
    
    window = ParticleEditorWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    launch_particle_editor()
