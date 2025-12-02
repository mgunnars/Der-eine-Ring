"""
2D/2.5D Partikel-Editor mit Wasseroberfläche und Glas-Effekten
Spezialisiert auf realistische Regen-Overlays von oben/schräg
"""

import sys
import os
import math
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QSlider, QComboBox, QSpinBox, QDoubleSpinBox,
        QGroupBox, QScrollArea, QFrame, QSplitter, QTabWidget,
        QFileDialog, QMessageBox, QProgressDialog, QColorDialog,
        QCheckBox, QGridLayout, QToolBar, QAction, QStatusBar
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import (
        QImage, QPixmap, QPainter, QColor, QPen, QBrush, QPalette
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt5 nicht verfügbar. Installieren mit: pip install PyQt5")

import numpy as np

from particle_system_2d import (
    ParticleSystem2D, Renderer2D, WaterSurface, RaindropAppearance,
    ViewAngle, create_rain_scene_2d
)
from particle_system import Color, BlendMode
from particle_exporter import ExportFormat


class Export2DThread(QThread):
    """Export-Thread für 2D System"""
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, system: ParticleSystem2D, output_path: str, 
                 duration: float, fps: int, format_type: ExportFormat):
        super().__init__()
        self.system = system
        self.output_path = output_path
        self.duration = duration
        self.fps = fps
        self.format_type = format_type
    
    def run(self):
        try:
            from PIL import Image
            
            renderer = Renderer2D(self.system.width, self.system.height)
            frames = []
            
            total_frames = int(self.duration * self.fps)
            dt = 1.0 / self.fps
            
            # Reset
            for emitter in self.system.emitters:
                emitter.clear()
            if self.system.water_surface:
                self.system.water_surface.ripples.clear()
                self.system.water_surface.splashes.clear()
            
            # Frames generieren
            for i in range(total_frames):
                self.system.update(dt)
                frame = renderer.render(self.system)
                
                img = Image.fromarray(frame, 'RGBA')
                frames.append(img)
                
                self.progress.emit((i + 1) / total_frames * 0.8, f"Frame {i+1}/{total_frames}")
            
            self.progress.emit(0.85, "Speichere...")
            
            # Speichern
            if self.format_type == ExportFormat.GIF:
                frames[0].save(
                    self.output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=int(1000 / self.fps),
                    loop=0,
                    disposal=2
                )
            elif self.format_type == ExportFormat.APNG:
                frames[0].save(
                    self.output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=int(1000 / self.fps),
                    loop=0
                )
            elif self.format_type == ExportFormat.PNG_SEQUENCE:
                output_dir = os.path.splitext(self.output_path)[0]
                os.makedirs(output_dir, exist_ok=True)
                for i, frame in enumerate(frames):
                    frame.save(os.path.join(output_dir, f"frame_{i:05d}.png"))
            else:
                # MP4/WebM - braucht ffmpeg
                self._export_video(frames)
            
            self.progress.emit(1.0, "Fertig!")
            self.finished.emit(True, self.output_path)
            
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def _check_ffmpeg_available(self) -> bool:
        """Prüfe ob ffmpeg verfügbar ist"""
        import subprocess
        import shutil
        
        # Erst im PATH suchen
        if shutil.which("ffmpeg"):
            return True
        
        # Dann in gängigen Windows-Pfaden
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            os.path.join(os.path.dirname(__file__), "ffmpeg", "ffmpeg.exe"),
            os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return True
        
        return False
    
    def _get_ffmpeg_path(self) -> str:
        """Hole ffmpeg Pfad"""
        import shutil
        
        # Im PATH
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        
        # Gängige Windows-Pfade
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            os.path.join(os.path.dirname(__file__), "ffmpeg", "ffmpeg.exe"),
            os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return "ffmpeg"  # Fallback
    
    def _export_video(self, frames):
        """Export als Video mit ffmpeg"""
        import subprocess
        import tempfile
        import shutil
        
        # Prüfe ob ffmpeg verfügbar
        if not self._check_ffmpeg_available():
            # Kein ffmpeg - exportiere als GIF stattdessen
            self.progress.emit(0.90, "ffmpeg nicht gefunden - exportiere als GIF...")
            gif_path = self.output_path.rsplit(".", 1)[0] + ".gif"
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / self.fps),
                loop=0,
                disposal=2
            )
            self.output_path = gif_path
            self.progress.emit(1.0, "Als GIF gespeichert (kein ffmpeg)")
            # KEIN raise mehr - einfach als Erfolg mit geändertem Pfad zurückkehren
            return
        
        temp_dir = tempfile.mkdtemp()
        ffmpeg_path = self._get_ffmpeg_path()
        
        try:
            self.progress.emit(0.86, "Speichere Frames...")
            
            # Frames speichern
            for i, frame in enumerate(frames):
                frame.save(os.path.join(temp_dir, f"frame_{i:05d}.png"))
            
            self.progress.emit(0.92, "Konvertiere zu Video (ffmpeg)...")
            
            # ffmpeg
            ext = "webm" if self.format_type == ExportFormat.WEBM else "mp4"
            
            if ext == "webm":
                cmd = [
                    ffmpeg_path, "-y",
                    "-framerate", str(self.fps),
                    "-i", os.path.join(temp_dir, "frame_%05d.png"),
                    "-c:v", "libvpx-vp9",
                    "-pix_fmt", "yuva420p",
                    "-b:v", "2M",
                    self.output_path
                ]
            else:
                cmd = [
                    ffmpeg_path, "-y",
                    "-framerate", str(self.fps),
                    "-i", os.path.join(temp_dir, "frame_%05d.png"),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-crf", "18",
                    self.output_path
                ]
            
            self.progress.emit(0.95, "ffmpeg läuft...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"ffmpeg Fehler: {result.stderr}")
            
            self.progress.emit(1.0, "Fertig!")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class Preview2DWidget(QWidget):
    """Vorschau-Widget für 2D Partikel"""
    
    def __init__(self, width: int = 800, height: int = 600):
        super().__init__()
        self.preview_width = width
        self.preview_height = height
        
        self.setMinimumSize(400, 300)
        
        # System erstellen
        self.system = ParticleSystem2D(width, height)
        self.renderer = Renderer2D(width, height)
        
        self.current_frame: Optional[QPixmap] = None
        self.playing = False
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.fps = 60
        
        # Stats
        self.particle_count = 0
        self.ripple_count = 0
        self.frame_time = 0
    
    def setup_rain_scene(self, camera_angle: float = 30.0, 
                         intensity: float = 1.0,
                         with_water: bool = True):
        """Initialisiere Regen-Szene"""
        self.system = ParticleSystem2D(self.preview_width, self.preview_height)
        self.system.set_camera_angle(camera_angle)
        
        if with_water:
            self.system.enable_water_surface()
        
        self.system.add_rain_emitter(intensity=intensity)
    
    def play(self):
        self.playing = True
        self.timer.start(1000 // self.fps)
    
    def pause(self):
        self.playing = False
        self.timer.stop()
    
    def reset(self):
        for emitter in self.system.emitters:
            emitter.clear()
        if self.system.water_surface:
            self.system.water_surface.ripples.clear()
            self.system.water_surface.splashes.clear()
        self._update_frame()
    
    def _update_frame(self):
        import time
        start = time.time()
        
        self.system.update(1.0 / self.fps)
        frame = self.renderer.render(self.system)
        
        self._frame_to_pixmap(frame)
        
        self.particle_count = self.system.total_particles
        self.ripple_count = self.system.total_ripples
        self.frame_time = (time.time() - start) * 1000
        
        self.update()
    
    def _frame_to_pixmap(self, frame: np.ndarray):
        height, width = frame.shape[:2]
        frame = np.ascontiguousarray(frame)
        
        bytes_per_line = 4 * width
        qimage = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        self.current_frame = QPixmap.fromImage(qimage.copy())
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Schachbrett-Hintergrund
        self._draw_checkerboard(painter)
        
        if self.current_frame:
            scaled = self.current_frame.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        
        # Stats
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 20, f"Partikel: {self.particle_count}")
        painter.drawText(10, 35, f"Ripples: {self.ripple_count}")
        painter.drawText(10, 50, f"Frame: {self.frame_time:.1f}ms")
    
    def _draw_checkerboard(self, painter):
        checker_size = 10
        colors = [QColor(40, 40, 45), QColor(50, 50, 55)]
        
        for y in range(0, self.height(), checker_size):
            for x in range(0, self.width(), checker_size):
                idx = ((x // checker_size) + (y // checker_size)) % 2
                painter.fillRect(x, y, checker_size, checker_size, colors[idx])


class ColorButton(QPushButton):
    """Farbauswahl-Button"""
    
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


class ParticleEditor2DWindow(QMainWindow):
    """Hauptfenster des 2D Partikel-Editors"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D/2.5D Regen-Editor - Mit Wasseroberfläche")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
        self._setup_menu()
        
        # Standard-Szene
        self._apply_settings()
        self.preview.play()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # === Linke Seite: Einstellungen ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # --- Kamera ---
        camera_group = QGroupBox("Kamera / Perspektive")
        camera_layout = QGridLayout(camera_group)
        
        camera_layout.addWidget(QLabel("Ansicht:"), 0, 0)
        self.view_combo = QComboBox()
        self.view_combo.addItem("Von oben (0°)", 0)
        self.view_combo.addItem("Leicht geneigt (15°)", 15)
        self.view_combo.addItem("Isometrisch (30°)", 30)
        self.view_combo.addItem("Dramatisch (45°)", 45)
        self.view_combo.addItem("Fast seitlich (60°)", 60)
        self.view_combo.setCurrentIndex(2)
        self.view_combo.currentIndexChanged.connect(self._on_settings_changed)
        camera_layout.addWidget(self.view_combo, 0, 1)
        
        camera_layout.addWidget(QLabel("Winkel (°):"), 1, 0)
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 75)
        self.angle_slider.setValue(30)
        self.angle_slider.valueChanged.connect(self._on_angle_slider_changed)
        camera_layout.addWidget(self.angle_slider, 1, 1)
        self.angle_label = QLabel("30°")
        camera_layout.addWidget(self.angle_label, 1, 2)
        
        # Live-Update Checkbox
        self.live_update = QCheckBox("Live-Update")
        self.live_update.setChecked(True)
        camera_layout.addWidget(self.live_update, 2, 0, 1, 2)
        
        settings_layout.addWidget(camera_group)
        
        # --- Regen ---
        rain_group = QGroupBox("Regen")
        rain_layout = QGridLayout(rain_group)
        
        rain_layout.addWidget(QLabel("Intensität:"), 0, 0)
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(10, 300)
        self.intensity_slider.setValue(100)
        self.intensity_slider.valueChanged.connect(self._on_settings_changed)
        rain_layout.addWidget(self.intensity_slider, 0, 1)
        self.intensity_label = QLabel("1.0")
        rain_layout.addWidget(self.intensity_label, 0, 2)
        
        rain_layout.addWidget(QLabel("Wind:"), 1, 0)
        self.wind_slider = QSlider(Qt.Horizontal)
        self.wind_slider.setRange(-100, 100)
        self.wind_slider.setValue(0)
        self.wind_slider.valueChanged.connect(self._on_settings_changed)
        rain_layout.addWidget(self.wind_slider, 1, 1)
        
        rain_layout.addWidget(QLabel("Tropfengröße:"), 2, 0)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(5, 30)  # Viel kleinere Tropfen!
        self.size_slider.setValue(10)     # Standard: klein
        self.size_slider.valueChanged.connect(self._on_settings_changed)
        rain_layout.addWidget(self.size_slider, 2, 1)
        
        settings_layout.addWidget(rain_group)
        
        # --- Tropfen-Aussehen ---
        drop_group = QGroupBox("Tropfen-Aussehen (Glas-Effekt)")
        drop_layout = QGridLayout(drop_group)
        
        self.glass_check = QCheckBox("Glas-Effekt aktiviert")
        self.glass_check.setChecked(True)
        self.glass_check.stateChanged.connect(self._on_settings_changed)
        drop_layout.addWidget(self.glass_check, 0, 0, 1, 2)
        
        drop_layout.addWidget(QLabel("Refraktion:"), 1, 0)
        self.refraction_slider = QSlider(Qt.Horizontal)
        self.refraction_slider.setRange(0, 100)
        self.refraction_slider.setValue(30)
        self.refraction_slider.valueChanged.connect(self._on_settings_changed)
        drop_layout.addWidget(self.refraction_slider, 1, 1)
        
        drop_layout.addWidget(QLabel("Glanz:"), 2, 0)
        self.specular_slider = QSlider(Qt.Horizontal)
        self.specular_slider.setRange(0, 100)
        self.specular_slider.setValue(80)
        self.specular_slider.valueChanged.connect(self._on_settings_changed)
        drop_layout.addWidget(self.specular_slider, 2, 1)
        
        drop_layout.addWidget(QLabel("Bewegungsunschärfe:"), 3, 0)
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(50)
        self.blur_slider.valueChanged.connect(self._on_settings_changed)
        drop_layout.addWidget(self.blur_slider, 3, 1)
        
        drop_layout.addWidget(QLabel("Tropfenfarbe:"), 4, 0)
        self.drop_color = ColorButton(Color(0.7, 0.85, 1.0, 0.35))  # Transparenter!
        drop_layout.addWidget(self.drop_color, 4, 1)
        
        settings_layout.addWidget(drop_group)
        
        # --- Wasseroberfläche ---
        water_group = QGroupBox("Wasseroberfläche (Kollisionsebene)")
        water_layout = QGridLayout(water_group)
        
        self.water_check = QCheckBox("Wasseroberfläche aktiviert")
        self.water_check.setChecked(True)
        self.water_check.stateChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_check, 0, 0, 1, 2)
        
        # Position und Größe
        water_layout.addWidget(QLabel("Position X (%):"), 1, 0)
        self.water_x = QSlider(Qt.Horizontal)
        self.water_x.setRange(0, 80)
        self.water_x.setValue(0)
        self.water_x.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_x, 1, 1)
        
        water_layout.addWidget(QLabel("Position Y (%):"), 2, 0)
        self.water_level = QSlider(Qt.Horizontal)
        self.water_level.setRange(20, 100)
        self.water_level.setValue(75)
        self.water_level.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_level, 2, 1)
        
        water_layout.addWidget(QLabel("Breite (%):"), 3, 0)
        self.water_width = QSlider(Qt.Horizontal)
        self.water_width.setRange(20, 100)
        self.water_width.setValue(100)
        self.water_width.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_width, 3, 1)
        
        water_layout.addWidget(QLabel("Höhe (%):"), 4, 0)
        self.water_height = QSlider(Qt.Horizontal)
        self.water_height.setRange(5, 80)
        self.water_height.setValue(25)
        self.water_height.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_height, 4, 1)
        
        # Aussehen
        water_layout.addWidget(QLabel("--- Aussehen ---"), 5, 0, 1, 2)
        
        water_layout.addWidget(QLabel("Deckkraft (0=transparent):"), 6, 0)
        self.water_opacity = QSlider(Qt.Horizontal)
        self.water_opacity.setRange(0, 100)  # 0 = komplett transparent, 100 = solid
        self.water_opacity.setValue(40)
        self.water_opacity.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_opacity, 6, 1)
        
        self.water_glass = QCheckBox("Glas-Effekt (Reflexion)")
        self.water_glass.setChecked(True)
        self.water_glass.stateChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_glass, 7, 0, 1, 2)
        
        water_layout.addWidget(QLabel("Reflexion:"), 8, 0)
        self.water_reflection = QSlider(Qt.Horizontal)
        self.water_reflection.setRange(0, 100)
        self.water_reflection.setValue(50)
        self.water_reflection.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.water_reflection, 8, 1)
        
        # Ripples
        water_layout.addWidget(QLabel("--- Ripples ---"), 9, 0, 1, 2)
        
        self.splash_check = QCheckBox("Splash-Effekte")
        self.splash_check.setChecked(True)
        self.splash_check.stateChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.splash_check, 10, 0, 1, 2)
        
        water_layout.addWidget(QLabel("Ripple-Größe:"), 11, 0)
        self.ripple_size = QSlider(Qt.Horizontal)
        self.ripple_size.setRange(20, 150)
        self.ripple_size.setValue(60)
        self.ripple_size.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.ripple_size, 11, 1)
        
        water_layout.addWidget(QLabel("Ripple-Speed:"), 12, 0)
        self.ripple_speed = QSlider(Qt.Horizontal)
        self.ripple_speed.setRange(20, 200)
        self.ripple_speed.setValue(80)
        self.ripple_speed.valueChanged.connect(self._on_settings_changed)
        water_layout.addWidget(self.ripple_speed, 12, 1)
        
        water_layout.addWidget(QLabel("Wasser-Farbe:"), 13, 0)
        self.water_color = ColorButton(Color(0.2, 0.4, 0.6, 0.5))
        water_layout.addWidget(self.water_color, 13, 1)
        
        settings_layout.addWidget(water_group)
        
        settings_layout.addStretch()
        
        scroll.setWidget(settings_widget)
        left_layout.addWidget(scroll)
        
        # Anwenden-Button
        apply_btn = QPushButton("🔄 Einstellungen anwenden")
        apply_btn.clicked.connect(self._apply_settings)
        left_layout.addWidget(apply_btn)
        
        left_panel.setMaximumWidth(350)
        splitter.addWidget(left_panel)
        
        # === Mitte: Vorschau ===
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        
        self.preview = Preview2DWidget(800, 600)
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
        
        preview_layout.addLayout(controls)
        
        splitter.addWidget(preview_container)
        
        # === Rechte Seite: Export ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Canvas-Größe
        size_group = QGroupBox("Ausgabe-Größe")
        size_layout = QGridLayout(size_group)
        
        size_layout.addWidget(QLabel("Breite:"), 0, 0)
        self.out_width = QSpinBox()
        self.out_width.setRange(100, 3840)
        self.out_width.setValue(1920)
        size_layout.addWidget(self.out_width, 0, 1)
        
        size_layout.addWidget(QLabel("Höhe:"), 1, 0)
        self.out_height = QSpinBox()
        self.out_height.setRange(100, 2160)
        self.out_height.setValue(1080)
        size_layout.addWidget(self.out_height, 1, 1)
        
        right_layout.addWidget(size_group)
        
        # Export
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("WebM (+ Alpha)", ExportFormat.WEBM)
        self.format_combo.addItem("MP4 (Video)", ExportFormat.MP4)
        self.format_combo.addItem("GIF (Animiert)", ExportFormat.GIF)
        self.format_combo.addItem("APNG (+ Alpha)", ExportFormat.APNG)
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
        
        export_btn = QPushButton("📤 Exportieren...")
        export_btn.clicked.connect(self._export)
        export_btn.setMinimumHeight(40)
        export_layout.addWidget(export_btn)
        
        right_layout.addWidget(export_group)
        
        # Partikel-Typ
        type_group = QGroupBox("Partikel-Typ")
        type_layout = QVBoxLayout(type_group)
        
        self.particle_type_combo = QComboBox()
        self.particle_type_combo.addItem("🌧 Regen", "rain")
        self.particle_type_combo.addItem("❄ Schnee", "snow")
        self.particle_type_combo.addItem("🍂 Blätter", "leaves")
        self.particle_type_combo.addItem("💨 Staub", "dust")
        self.particle_type_combo.addItem("🌫 Nebel", "fog")
        self.particle_type_combo.addItem("🔥 Feuer", "fire")
        self.particle_type_combo.addItem("💨 Rauch", "smoke")
        self.particle_type_combo.addItem("✨ Funken", "sparks")
        self.particle_type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.particle_type_combo)
        
        right_layout.addWidget(type_group)
        
        # Wind-Einstellungen
        wind_group = QGroupBox("Wind")
        wind_layout = QGridLayout(wind_group)
        
        wind_layout.addWidget(QLabel("Richtung (°):"), 0, 0)
        self.wind_angle_slider = QSlider(Qt.Horizontal)
        self.wind_angle_slider.setRange(0, 360)
        self.wind_angle_slider.setValue(0)  # 0 = nach rechts
        self.wind_angle_slider.valueChanged.connect(self._on_wind_changed)
        wind_layout.addWidget(self.wind_angle_slider, 0, 1)
        self.wind_angle_label = QLabel("0° →")
        wind_layout.addWidget(self.wind_angle_label, 0, 2)
        
        wind_layout.addWidget(QLabel("Stärke:"), 1, 0)
        self.wind_strength_slider = QSlider(Qt.Horizontal)
        self.wind_strength_slider.setRange(0, 200)  # Erhöht für sichtbareren Effekt
        self.wind_strength_slider.setValue(30)      # Etwas mehr Standard-Wind
        self.wind_strength_slider.valueChanged.connect(self._on_wind_changed)
        wind_layout.addWidget(self.wind_strength_slider, 1, 1)
        self.wind_strength_label = QLabel("20")
        wind_layout.addWidget(self.wind_strength_label, 1, 2)
        
        right_layout.addWidget(wind_group)
        
        # Presets
        preset_group = QGroupBox("Schnell-Presets")
        preset_layout = QVBoxLayout(preset_group)
        
        # Regen-Presets
        rain_presets = [
            ("🌧 Leichter Regen", "rain", 0.5, 30, 10),
            ("🌧🌧 Normaler Regen", "rain", 1.0, 30, 20),
            ("⛈ Starkregen", "rain", 2.0, 45, 40),
        ]
        
        # Andere Presets
        other_presets = [
            ("❄ Leichter Schneefall", "snow", 0.5, 15, 15),
            ("❄❄ Schneesturm", "snow", 2.0, 45, 60),
            ("🍂 Herbstblätter", "leaves", 1.0, 30, 40),
            ("💨 Staubsturm", "dust", 2.0, 60, 80),
            ("🌫 Nebelschwaden", "fog", 1.0, 15, 10),
            ("🔥 Lagerfeuer", "fire", 1.0, 30, 10),
        ]
        
        for name, ptype, intensity, angle, wind in rain_presets + other_presets:
            btn = QPushButton(name)
            btn.clicked.connect(
                lambda checked, t=ptype, i=intensity, a=angle, w=wind: 
                    self._apply_full_preset(t, i, a, w)
            )
            preset_layout.addWidget(btn)
        
        right_layout.addWidget(preset_group)
        right_layout.addStretch()
        
        right_panel.setMaximumWidth(280)
        splitter.addWidget(right_panel)
        
        main_layout.addWidget(splitter)
        
        # Statusbar
        self.statusBar().showMessage("Bereit")
    
    def _setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("Datei")
        
        export_action = QAction("Exportieren...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Beenden", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
    
    def _on_angle_slider_changed(self, value):
        self.angle_label.setText(f"{value}°")
        # View-Combo aktualisieren
        self.view_combo.blockSignals(True)
        for i in range(self.view_combo.count()):
            if self.view_combo.itemData(i) == value:
                self.view_combo.setCurrentIndex(i)
                break
        self.view_combo.blockSignals(False)
        
        # Live-Update des Kamerawinkels
        if hasattr(self, 'live_update') and self.live_update.isChecked():
            self.preview.system.set_camera_angle(value)
            self.statusBar().showMessage(f"Kamera-Winkel: {value}°")
    
    def _on_settings_changed(self):
        self.intensity_label.setText(f"{self.intensity_slider.value() / 100:.1f}")
    
    def _on_type_changed(self, index):
        """Partikeltyp geändert"""
        ptype = self.particle_type_combo.currentData()
        
        # Wasseroberfläche nur bei Regen sinnvoll
        if ptype == "rain":
            self.water_check.setEnabled(True)
        else:
            self.water_check.setEnabled(True)  # Lassen wir aktiviert
        
        self.statusBar().showMessage(f"Partikeltyp: {self.particle_type_combo.currentText()}")
    
    def _on_wind_changed(self):
        """Wind-Einstellungen geändert"""
        angle = self.wind_angle_slider.value()
        strength = self.wind_strength_slider.value()
        
        # Richtungspfeil
        arrows = {0: "→", 45: "↘", 90: "↓", 135: "↙", 180: "←", 225: "↖", 270: "↑", 315: "↗"}
        nearest = min(arrows.keys(), key=lambda x: min(abs(x - angle), 360 - abs(x - angle)))
        self.wind_angle_label.setText(f"{angle}° {arrows.get(nearest, '')}")
        self.wind_strength_label.setText(str(strength))
        
        # Live-Update
        if hasattr(self, 'live_update') and self.live_update.isChecked():
            self.preview.system.set_global_wind(angle, strength)
    
    def _apply_settings(self):
        """Wende alle Einstellungen an"""
        self.preview.pause()
        
        # System neu erstellen
        w, h = self.preview.preview_width, self.preview.preview_height
        self.preview.system = ParticleSystem2D(w, h)
        
        # Kamera
        angle = self.angle_slider.value()
        self.preview.system.set_camera_angle(angle)
        
        # Wasseroberfläche
        if self.water_check.isChecked():
            # Berechne Bounds aus Prozentwerten
            water_x = w * self.water_x.value() / 100
            water_y = h * self.water_level.value() / 100
            water_width = w * self.water_width.value() / 100
            water_height = h * self.water_height.value() / 100
            
            self.preview.system.enable_water_surface(water_y)
            
            ws = self.preview.system.water_surface
            
            # Bounds setzen
            ws.set_bounds(water_x, water_y, water_width, water_height)
            
            # Aussehen - water_opacity steuert die Sichtbarkeit (0 = transparent)
            ws.water_opacity = self.water_opacity.value() / 100
            ws.glass_effect = self.water_glass.isChecked()
            ws.glass_reflection = self.water_reflection.value() / 100
            
            # Ripples
            ws.ripple_max_radius = self.ripple_size.value()
            ws.ripple_speed = self.ripple_speed.value()
            ws.splash_enabled = self.splash_check.isChecked()
            ws.water_color = self.water_color.get_color()
        
        # Tropfen-Aussehen
        appearance = self.preview.system.raindrop_appearance
        appearance.glass_enabled = self.glass_check.isChecked()
        appearance.refraction_strength = self.refraction_slider.value() / 100
        appearance.specular_strength = self.specular_slider.value() / 100
        appearance.motion_blur = self.blur_slider.value() / 100
        appearance.base_color = self.drop_color.get_color()
        
        # Partikeltyp und Emitter
        ptype = self.particle_type_combo.currentData() if hasattr(self, 'particle_type_combo') else "rain"
        intensity = self.intensity_slider.value() / 100
        wind_angle = self.wind_angle_slider.value() if hasattr(self, 'wind_angle_slider') else 0
        wind_strength = self.wind_strength_slider.value() if hasattr(self, 'wind_strength_slider') else 20
        
        self._add_emitter_by_type(ptype, intensity, wind_angle, wind_strength)
        
        self.preview.play()
        self.statusBar().showMessage("Einstellungen angewendet")
    
    def _add_emitter_by_type(self, ptype: str, intensity: float, 
                             wind_angle: float, wind_strength: float):
        """Füge Emitter basierend auf Typ hinzu"""
        system = self.preview.system
        w, h = self.preview.preview_width, self.preview.preview_height
        
        if ptype == "rain":
            emitter = system.add_rain_emitter(
                intensity=intensity,
                wind_angle=wind_angle,
                wind_strength=wind_strength
            )
            base_size = self.size_slider.value() / 10
            emitter.start_size = base_size
            emitter.size_variation = base_size * 0.4
        elif ptype == "snow":
            system.add_snow_emitter(intensity=intensity, wind_strength=wind_strength)
        elif ptype == "leaves":
            system.add_leaves_emitter(intensity=intensity, wind_strength=wind_strength)
        elif ptype == "dust":
            system.add_dust_emitter(intensity=intensity, wind_strength=wind_strength)
        elif ptype == "fog":
            system.add_fog_emitter(intensity=intensity)
        elif ptype == "fire":
            system.add_fire_emitter(w / 2, h * 0.7, intensity=intensity)
        elif ptype == "smoke":
            system.add_smoke_emitter(w / 2, h * 0.7, intensity=intensity)
        elif ptype == "sparks":
            system.add_sparks_emitter(w / 2, h * 0.7, intensity=intensity)
        
        # Globaler Wind
        if ptype not in ["fire", "smoke", "sparks"]:
            system.set_global_wind(wind_angle, wind_strength)
    
    def _apply_full_preset(self, ptype: str, intensity: float, angle: int, wind: float):
        """Wende volles Preset an"""
        # UI aktualisieren
        for i in range(self.particle_type_combo.count()):
            if self.particle_type_combo.itemData(i) == ptype:
                self.particle_type_combo.setCurrentIndex(i)
                break
        
        self.intensity_slider.setValue(int(intensity * 100))
        self.angle_slider.setValue(angle)
        self.wind_strength_slider.setValue(int(wind))
        
        # Wasseroberfläche nur bei Regen
        self.water_check.setChecked(ptype == "rain")
        
        self._apply_settings()
    
    def _apply_preset(self, intensity: float, angle: int, water: bool):
        """Wende Preset an"""
        self.intensity_slider.setValue(int(intensity * 100))
        self.angle_slider.setValue(angle)
        self.water_check.setChecked(water)
        self._apply_settings()
    
    def _toggle_play(self):
        if self.preview.playing:
            self.preview.pause()
            self.play_btn.setText("▶ Play")
        else:
            self.preview.play()
            self.play_btn.setText("⏸ Pause")
    
    def _reset(self):
        self.preview.reset()
    
    def _export(self):
        import shutil
        
        format_type = self.format_combo.currentData()
        
        # Warnung bei MP4/WebM wenn ffmpeg fehlt
        if format_type in (ExportFormat.MP4, ExportFormat.WEBM):
            ffmpeg_available = shutil.which("ffmpeg") is not None
            if not ffmpeg_available:
                reply = QMessageBox.warning(
                    self, "ffmpeg nicht gefunden",
                    "Für MP4/WebM Export wird ffmpeg benötigt, das nicht gefunden wurde.\n\n"
                    "Optionen:\n"
                    "• Installiere ffmpeg: https://ffmpeg.org/download.html\n"
                    "• Wähle GIF oder APNG Format (kein ffmpeg nötig)\n"
                    "• Wähle PNG-Sequenz für einzelne Frames\n\n"
                    "Trotzdem fortfahren? (Fallback auf GIF)",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
        
        extensions = {
            ExportFormat.MP4: "MP4 Video (*.mp4)",
            ExportFormat.WEBM: "WebM Video (*.webm)",
            ExportFormat.GIF: "Animiertes GIF (*.gif)",
            ExportFormat.APNG: "Animiertes PNG (*.png)",
            ExportFormat.PNG_SEQUENCE: "PNG-Sequenz (*.png)",
        }
        
        # Default-Dateiname basierend auf Format
        default_extensions = {
            ExportFormat.MP4: "regen_overlay.mp4",
            ExportFormat.WEBM: "regen_overlay.webm",
            ExportFormat.GIF: "regen_overlay.gif",
            ExportFormat.APNG: "regen_overlay.png",
            ExportFormat.PNG_SEQUENCE: "regen_overlay.png",
        }
        default_name = default_extensions.get(format_type, "regen_overlay.gif")
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportieren als...",
            default_name,
            extensions.get(format_type, "Alle Dateien (*)")
        )
        
        if not filename:
            return
        
        # Stelle sicher dass die Dateiendung zum Format passt
        expected_ext = {
            ExportFormat.MP4: ".mp4",
            ExportFormat.WEBM: ".webm",
            ExportFormat.GIF: ".gif",
            ExportFormat.APNG: ".png",
            ExportFormat.PNG_SEQUENCE: ".png",
        }.get(format_type, ".gif")
        
        if not filename.lower().endswith(expected_ext):
            filename = filename.rsplit(".", 1)[0] + expected_ext
        
        # System mit Ausgabe-Größe erstellen
        w, h = self.out_width.value(), self.out_height.value()
        export_system = ParticleSystem2D(w, h)
        export_system.set_camera_angle(self.angle_slider.value())
        
        # === WASSER-OBERFLÄCHE mit ALLEN Einstellungen ===
        if self.water_check.isChecked():
            # Berechne Bounds aus Prozentwerten (wie in _apply_settings)
            water_x = w * self.water_x.value() / 100
            water_y = h * self.water_level.value() / 100
            water_width = w * self.water_width.value() / 100
            water_height = h * self.water_height.value() / 100
            
            export_system.enable_water_surface(water_y)
            ws = export_system.water_surface
            
            # Bounds setzen
            ws.set_bounds(water_x, water_y, water_width, water_height)
            
            # Aussehen
            ws.water_opacity = self.water_opacity.value() / 100
            ws.glass_effect = self.water_glass.isChecked()
            ws.glass_reflection = self.water_reflection.value() / 100
            
            # Ripples
            ws.ripple_max_radius = self.ripple_size.value()
            ws.ripple_speed = self.ripple_speed.value()
            ws.splash_enabled = self.splash_check.isChecked()
            ws.water_color = self.water_color.get_color()
        
        # === TROPFEN-AUSSEHEN ===
        export_system.raindrop_appearance.glass_enabled = self.glass_check.isChecked()
        export_system.raindrop_appearance.refraction_strength = self.refraction_slider.value() / 100
        export_system.raindrop_appearance.specular_strength = self.specular_slider.value() / 100
        export_system.raindrop_appearance.motion_blur = self.blur_slider.value() / 100
        export_system.raindrop_appearance.base_color = self.drop_color.get_color()
        
        # === PARTIKEL-TYP und EMITTER ===
        ptype = self.particle_type_combo.currentData() if hasattr(self, 'particle_type_combo') else "rain"
        intensity = self.intensity_slider.value() / 100
        
        # Wind aus den Wind-Slidern (nicht aus dem alten wind_slider)
        wind_angle = self.wind_angle_slider.value() if hasattr(self, 'wind_angle_slider') else 0
        wind_strength = self.wind_strength_slider.value() if hasattr(self, 'wind_strength_slider') else 0
        
        # Emitter basierend auf Typ hinzufügen
        if ptype == "rain":
            emitter = export_system.add_rain_emitter(intensity=intensity)
            base_size = self.size_slider.value() / 10
            emitter.start_size = base_size
            emitter.size_variation = base_size * 0.4
        elif ptype == "snow":
            export_system.add_snow_emitter(intensity=intensity, wind_strength=wind_strength)
        elif ptype == "leaves":
            export_system.add_leaves_emitter(intensity=intensity, wind_strength=wind_strength)
        elif ptype == "dust":
            export_system.add_dust_emitter(intensity=intensity, wind_strength=wind_strength)
        elif ptype == "fog":
            export_system.add_fog_emitter(intensity=intensity)
        elif ptype == "fire":
            export_system.add_fire_emitter(w // 2, h - 50, intensity=intensity)
        elif ptype == "smoke":
            export_system.add_smoke_emitter(w // 2, h - 50, intensity=intensity)
        elif ptype == "sparks":
            export_system.add_sparks_emitter(w // 2, h - 50, intensity=intensity)
        else:
            # Fallback: Rain
            emitter = export_system.add_rain_emitter(intensity=intensity)
            emitter.start_size = self.size_slider.value() / 10
        
        # === GLOBALER WIND ===
        if wind_strength > 0:
            export_system.set_global_wind(wind_angle, wind_strength)
        
        # Progress
        progress = QProgressDialog("Exportiere...", "Abbrechen", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        # Export-Thread
        self.export_thread = Export2DThread(
            export_system, filename,
            self.duration_spin.value(),
            self.export_fps.value(),
            format_type
        )
        self.export_thread.progress.connect(
            lambda p, m: (progress.setValue(int(p * 100)), progress.setLabelText(m))
        )
        self.export_thread.finished.connect(
            lambda success, msg: self._export_finished(success, msg, progress)
        )
        
        self.export_thread.start()
    
    def _export_finished(self, success: bool, message: str, progress: QProgressDialog):
        progress.close()
        
        if success:
            QMessageBox.information(
                self, "Export abgeschlossen",
                f"Datei erfolgreich exportiert:\n{message}"
            )
        else:
            QMessageBox.warning(
                self, "Export fehlgeschlagen",
                f"Fehler beim Export:\n{message}"
            )


def launch_2d_editor():
    """Starte den 2D Partikel-Editor"""
    if not PYQT_AVAILABLE:
        print("Fehler: PyQt5 ist erforderlich!")
        return
    
    app = QApplication(sys.argv)
    
    # Dark Theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(30, 30, 32))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
    app.setPalette(palette)
    
    window = ParticleEditor2DWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    launch_2d_editor()
