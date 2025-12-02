"""
Video-Export für Partikel-Animationen
Unterstützt MP4, GIF, WebM und PNG-Sequenzen
"""

import os
import sys
import subprocess
import tempfile
import shutil
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from particle_system import ParticleCanvas, ParticleEmitter, ParticleType
from particle_renderer import AdvancedParticleRenderer


class ExportFormat(Enum):
    """Unterstützte Export-Formate"""
    MP4 = "mp4"
    GIF = "gif"
    WEBM = "webm"
    PNG_SEQUENCE = "png"
    APNG = "apng"


@dataclass
class ExportSettings:
    """Export-Einstellungen"""
    format: ExportFormat = ExportFormat.MP4
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 5.0
    
    # Video-Qualität
    quality: int = 85  # 0-100
    bitrate: str = "5M"
    
    # GIF-spezifisch
    gif_colors: int = 256
    gif_dither: bool = True
    gif_loop: int = 0  # 0 = unendlich
    
    # Transparenz
    transparent_background: bool = True
    background_color: Tuple[int, int, int, int] = (0, 0, 0, 0)
    
    # Performance
    use_ffmpeg: bool = True  # Falls verfügbar
    
    @property
    def total_frames(self) -> int:
        return int(self.fps * self.duration)


class ParticleExporter:
    """
    Exportiert Partikel-Animationen in verschiedene Formate
    """
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.progress_callback: Optional[Callable[[float, str], None]] = None
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Suche nach ffmpeg"""
        # Prüfe PATH
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                return "ffmpeg"
        except FileNotFoundError:
            pass
        
        # Windows-spezifische Pfade
        if sys.platform == "win32":
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    def _report_progress(self, progress: float, message: str = ""):
        """Melde Fortschritt"""
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    def export(self, canvas: ParticleCanvas, 
               output_path: str,
               settings: ExportSettings) -> bool:
        """
        Exportiere Partikel-Animation
        
        Args:
            canvas: ParticleCanvas mit Emittern
            output_path: Ausgabepfad
            settings: Export-Einstellungen
            
        Returns:
            True bei Erfolg
        """
        self._report_progress(0, "Starte Export...")
        
        # Renderer erstellen
        renderer = AdvancedParticleRenderer(settings.width, settings.height)
        
        # Frames generieren
        frames = self._generate_frames(canvas, renderer, settings)
        
        if not frames:
            return False
        
        self._report_progress(0.5, "Frames generiert, exportiere...")
        
        # Format-spezifischer Export
        if settings.format == ExportFormat.MP4:
            success = self._export_mp4(frames, output_path, settings)
        elif settings.format == ExportFormat.GIF:
            success = self._export_gif(frames, output_path, settings)
        elif settings.format == ExportFormat.WEBM:
            success = self._export_webm(frames, output_path, settings)
        elif settings.format == ExportFormat.PNG_SEQUENCE:
            success = self._export_png_sequence(frames, output_path, settings)
        elif settings.format == ExportFormat.APNG:
            success = self._export_apng(frames, output_path, settings)
        else:
            success = False
        
        self._report_progress(1.0, "Export abgeschlossen" if success else "Export fehlgeschlagen")
        return success
    
    def _generate_frames(self, canvas: ParticleCanvas,
                         renderer: AdvancedParticleRenderer,
                         settings: ExportSettings) -> List[np.ndarray]:
        """Generiere alle Frames"""
        frames = []
        dt = 1.0 / settings.fps
        total_frames = settings.total_frames
        
        # Reset Canvas
        for emitter in canvas.emitters:
            emitter.clear()
        
        previous_frame = None
        
        for i in range(total_frames):
            # Update
            canvas.update(dt)
            
            # Render
            frame = renderer.render(canvas, 
                background_alpha=0 if settings.transparent_background else 1.0
            )
            
            # Post-Effects
            if canvas.glow_strength > 0 or canvas.motion_blur > 0:
                frame = renderer.apply_post_effects(
                    frame,
                    glow_strength=canvas.glow_strength,
                    glow_radius=canvas.glow_radius,
                    motion_blur=canvas.motion_blur,
                    previous_frame=previous_frame
                )
            
            frames.append(frame)
            previous_frame = frame.copy()
            
            # Fortschritt
            progress = (i + 1) / total_frames * 0.5
            self._report_progress(progress, f"Frame {i+1}/{total_frames}")
        
        return frames
    
    def _export_mp4(self, frames: List[np.ndarray], 
                    output_path: str, 
                    settings: ExportSettings) -> bool:
        """Exportiere als MP4 (mit ffmpeg)"""
        if not self.ffmpeg_path:
            print("Warnung: ffmpeg nicht gefunden, verwende GIF-Export")
            return self._export_gif(frames, output_path.replace('.mp4', '.gif'), settings)
        
        # Temporäres Verzeichnis für Frames
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Frames als PNG speichern
            for i, frame in enumerate(frames):
                img = Image.fromarray(frame, 'RGBA')
                # Für MP4 mit Alpha: Auf schwarzem Hintergrund compositen
                if not settings.transparent_background:
                    bg = Image.new('RGBA', (settings.width, settings.height), 
                                   settings.background_color)
                    img = Image.alpha_composite(bg, img)
                img = img.convert('RGB')
                img.save(os.path.join(temp_dir, f"frame_{i:05d}.png"))
                
                progress = 0.5 + (i + 1) / len(frames) * 0.3
                self._report_progress(progress, f"Speichere Frame {i+1}/{len(frames)}")
            
            # ffmpeg ausführen
            cmd = [
                self.ffmpeg_path,
                "-y",  # Überschreiben
                "-framerate", str(settings.fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", str(int(51 - settings.quality * 0.51)),  # 0-51, niedriger = besser
                "-pix_fmt", "yuv420p",
                "-b:v", settings.bitrate,
                output_path
            ]
            
            self._report_progress(0.85, "Encodiere Video...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ffmpeg Fehler: {result.stderr}")
                return False
            
            return True
            
        finally:
            # Aufräumen
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _export_webm(self, frames: List[np.ndarray],
                     output_path: str,
                     settings: ExportSettings) -> bool:
        """Exportiere als WebM (mit Transparenz-Unterstützung)"""
        if not self.ffmpeg_path:
            print("Warnung: ffmpeg nicht gefunden")
            return False
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Frames als PNG speichern (mit Alpha)
            for i, frame in enumerate(frames):
                img = Image.fromarray(frame, 'RGBA')
                img.save(os.path.join(temp_dir, f"frame_{i:05d}.png"))
                
                progress = 0.5 + (i + 1) / len(frames) * 0.3
                self._report_progress(progress, f"Speichere Frame {i+1}/{len(frames)}")
            
            # ffmpeg für WebM mit Alpha
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-framerate", str(settings.fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",  # Alpha-Kanal
                "-b:v", settings.bitrate,
                "-auto-alt-ref", "0",
                output_path
            ]
            
            self._report_progress(0.85, "Encodiere WebM...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ffmpeg Fehler: {result.stderr}")
                return False
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _export_gif(self, frames: List[np.ndarray],
                    output_path: str,
                    settings: ExportSettings) -> bool:
        """Exportiere als GIF"""
        if not PIL_AVAILABLE:
            print("Fehler: PIL nicht verfügbar")
            return False
        
        # Frames zu PIL Images konvertieren
        pil_frames = []
        
        for i, frame in enumerate(frames):
            img = Image.fromarray(frame, 'RGBA')
            
            # Für GIF: Transparenz als Palette-Index
            if settings.transparent_background:
                # Quantisieren mit Transparenz
                img = img.convert('P', palette=Image.ADAPTIVE, colors=settings.gif_colors - 1)
                # Transparenz-Index setzen
                img.info['transparency'] = 0
            else:
                # Auf Hintergrund compositen
                bg = Image.new('RGBA', (settings.width, settings.height),
                               settings.background_color)
                img = Image.alpha_composite(bg, img)
                img = img.convert('P', palette=Image.ADAPTIVE, colors=settings.gif_colors)
            
            pil_frames.append(img)
            
            progress = 0.5 + (i + 1) / len(frames) * 0.4
            self._report_progress(progress, f"Konvertiere Frame {i+1}/{len(frames)}")
        
        # Als GIF speichern
        self._report_progress(0.95, "Speichere GIF...")
        
        frame_duration = int(1000 / settings.fps)  # ms
        
        pil_frames[0].save(
            output_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=frame_duration,
            loop=settings.gif_loop,
            disposal=2  # Für Transparenz wichtig
        )
        
        return True
    
    def _export_apng(self, frames: List[np.ndarray],
                     output_path: str,
                     settings: ExportSettings) -> bool:
        """Exportiere als APNG (animiertes PNG mit voller Transparenz)"""
        if not PIL_AVAILABLE:
            print("Fehler: PIL nicht verfügbar")
            return False
        
        pil_frames = []
        
        for i, frame in enumerate(frames):
            img = Image.fromarray(frame, 'RGBA')
            pil_frames.append(img)
            
            progress = 0.5 + (i + 1) / len(frames) * 0.4
            self._report_progress(progress, f"Konvertiere Frame {i+1}/{len(frames)}")
        
        self._report_progress(0.95, "Speichere APNG...")
        
        frame_duration = int(1000 / settings.fps)
        
        pil_frames[0].save(
            output_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=frame_duration,
            loop=settings.gif_loop
        )
        
        return True
    
    def _export_png_sequence(self, frames: List[np.ndarray],
                             output_path: str,
                             settings: ExportSettings) -> bool:
        """Exportiere als PNG-Sequenz"""
        if not PIL_AVAILABLE:
            print("Fehler: PIL nicht verfügbar")
            return False
        
        # Verzeichnis erstellen
        output_dir = os.path.splitext(output_path)[0]
        os.makedirs(output_dir, exist_ok=True)
        
        for i, frame in enumerate(frames):
            img = Image.fromarray(frame, 'RGBA')
            frame_path = os.path.join(output_dir, f"frame_{i:05d}.png")
            img.save(frame_path)
            
            progress = 0.5 + (i + 1) / len(frames) * 0.5
            self._report_progress(progress, f"Speichere Frame {i+1}/{len(frames)}")
        
        return True
    
    def export_preview(self, canvas: ParticleCanvas,
                       output_path: str,
                       width: int = 400,
                       height: int = 300,
                       duration: float = 2.0,
                       fps: int = 15) -> bool:
        """
        Schnelle Vorschau-Export (niedrigere Qualität)
        """
        settings = ExportSettings(
            format=ExportFormat.GIF,
            width=width,
            height=height,
            fps=fps,
            duration=duration,
            gif_colors=64,
            quality=50
        )
        
        return self.export(canvas, output_path, settings)


def create_rain_overlay(output_path: str, 
                        width: int = 1920, height: int = 1080,
                        duration: float = 5.0,
                        intensity: float = 1.0,
                        format: ExportFormat = ExportFormat.WEBM) -> bool:
    """
    Erstelle Regen-Overlay
    
    Args:
        output_path: Ausgabepfad
        width, height: Größe
        duration: Dauer in Sekunden
        intensity: Intensität (0.1 - 2.0)
        format: Export-Format
    """
    from particle_system import (
        ParticleCanvas, ParticleEmitter, ParticleType,
        RectEmitter, Vector3, CollisionPlane
    )
    
    canvas = ParticleCanvas(width, height)
    emitter = ParticleEmitter(ParticleType.RAIN)
    
    # Emitter über der gesamten Breite
    emitter.shape = RectEmitter(
        position=Vector3(width/2, -50, 0),
        width=width + 200,
        height=20
    )
    
    # Intensität anpassen
    emitter.emission_rate = int(500 * intensity)
    
    # Boden-Kollision
    emitter.collision_planes = [
        CollisionPlane(position=Vector3(0, height + 10, 0))
    ]
    
    canvas.add_emitter(emitter)
    
    # Export
    exporter = ParticleExporter()
    settings = ExportSettings(
        format=format,
        width=width,
        height=height,
        fps=30,
        duration=duration,
        transparent_background=True
    )
    
    return exporter.export(canvas, output_path, settings)


def create_snow_overlay(output_path: str,
                        width: int = 1920, height: int = 1080,
                        duration: float = 10.0,
                        intensity: float = 1.0,
                        format: ExportFormat = ExportFormat.WEBM) -> bool:
    """Erstelle Schnee-Overlay"""
    from particle_system import (
        ParticleCanvas, ParticleEmitter, ParticleType,
        RectEmitter, Vector3
    )
    
    canvas = ParticleCanvas(width, height)
    emitter = ParticleEmitter(ParticleType.SNOW)
    
    emitter.shape = RectEmitter(
        position=Vector3(width/2, -50, 0),
        width=width + 300,
        height=20
    )
    
    emitter.emission_rate = int(100 * intensity)
    
    canvas.add_emitter(emitter)
    
    exporter = ParticleExporter()
    settings = ExportSettings(
        format=format,
        width=width,
        height=height,
        fps=30,
        duration=duration,
        transparent_background=True
    )
    
    return exporter.export(canvas, output_path, settings)


def create_fire_overlay(output_path: str,
                        width: int = 400, height: int = 400,
                        duration: float = 5.0,
                        format: ExportFormat = ExportFormat.WEBM) -> bool:
    """Erstelle Feuer-Overlay"""
    from particle_system import (
        ParticleCanvas, ParticleEmitter, ParticleType,
        CircleEmitter, Vector3
    )
    
    canvas = ParticleCanvas(width, height)
    
    # Feuer
    fire = ParticleEmitter(ParticleType.FIRE)
    fire.shape = CircleEmitter(
        position=Vector3(width/2, height - 50, 0),
        radius=30
    )
    canvas.add_emitter(fire)
    
    # Funken
    sparks = ParticleEmitter(ParticleType.SPARK)
    sparks.shape = CircleEmitter(
        position=Vector3(width/2, height - 70, 0),
        radius=20
    )
    sparks.emission_rate = 10
    canvas.add_emitter(sparks)
    
    # Rauch
    smoke = ParticleEmitter(ParticleType.SMOKE)
    smoke.shape = CircleEmitter(
        position=Vector3(width/2, height - 100, 0),
        radius=15
    )
    smoke.emission_rate = 5
    canvas.add_emitter(smoke)
    
    canvas.glow_strength = 0.3
    canvas.glow_radius = 15
    
    exporter = ParticleExporter()
    settings = ExportSettings(
        format=format,
        width=width,
        height=height,
        fps=30,
        duration=duration,
        transparent_background=True
    )
    
    return exporter.export(canvas, output_path, settings)


def create_magic_overlay(output_path: str,
                         width: int = 400, height: int = 400,
                         duration: float = 5.0,
                         color: Tuple[float, float, float] = (0.5, 0.3, 1.0),
                         format: ExportFormat = ExportFormat.WEBM) -> bool:
    """Erstelle magisches Partikel-Overlay"""
    from particle_system import (
        ParticleCanvas, ParticleEmitter, ParticleType,
        CircleEmitter, Vector3, Color, VortexForce
    )
    
    canvas = ParticleCanvas(width, height)
    emitter = ParticleEmitter(ParticleType.MAGIC)
    
    emitter.shape = CircleEmitter(
        position=Vector3(width/2, height/2, 0),
        radius=30
    )
    
    # Benutzerdefinierte Farbe
    emitter.start_color = Color(color[0], color[1], color[2], 1.0)
    emitter.end_color = Color(color[0] + 0.3, color[1] + 0.2, color[2], 0.0)
    
    # Wirbel hinzufügen
    emitter.forces.append(
        VortexForce(
            position=Vector3(width/2, height/2, 0),
            strength=80,
            radius=150,
            inward_strength=20
        )
    )
    
    canvas.add_emitter(emitter)
    canvas.glow_strength = 0.5
    canvas.glow_radius = 20
    
    exporter = ParticleExporter()
    settings = ExportSettings(
        format=format,
        width=width,
        height=height,
        fps=30,
        duration=duration,
        transparent_background=True
    )
    
    return exporter.export(canvas, output_path, settings)


if __name__ == "__main__":
    print("Partikel-Exporter Test")
    print("=" * 40)
    
    exporter = ParticleExporter()
    print(f"ffmpeg gefunden: {exporter.ffmpeg_path or 'Nein'}")
    
    # Test-Export
    def progress_callback(progress: float, message: str):
        bar_length = 30
        filled = int(bar_length * progress)
        bar = "=" * filled + "-" * (bar_length - filled)
        print(f"\r[{bar}] {progress*100:.1f}% - {message}", end="")
    
    exporter.progress_callback = progress_callback
    
    print("\n\nErstelle Regen-Overlay (Preview)...")
    from particle_system import ParticleCanvas, ParticleEmitter, ParticleType, RectEmitter, Vector3
    
    canvas = ParticleCanvas(400, 300)
    emitter = ParticleEmitter(ParticleType.RAIN)
    emitter.shape = RectEmitter(position=Vector3(200, -20, 0), width=450, height=10)
    canvas.add_emitter(emitter)
    
    settings = ExportSettings(
        format=ExportFormat.GIF,
        width=400,
        height=300,
        fps=15,
        duration=2.0,
        gif_colors=64
    )
    
    success = exporter.export(canvas, "test_rain.gif", settings)
    print(f"\n\nErfolg: {success}")
