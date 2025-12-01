"""
Video & Overlay Manager für "Der Eine Ring" VTT
================================================

Verwaltet MP4-Videos und animierte Overlays für:
- Video-basierte Karten (aus Unity/Blender gerendert)
- Wetter-Overlays (Regen, Schnee, Nebel)
- Effekt-Overlays (Partikel, Magie)
- Ambient-Overlays (Staub, Lichteffekte)

Benötigt: pip install opencv-python imageio

Autor: VTT Development Team
Version: 1.0.0
"""

import os
import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, ImageTk
import tkinter as tk

# Optional: OpenCV für bessere Video-Performance
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV nicht installiert. Video-Performance eingeschränkt.")
    print("   Installiere mit: pip install opencv-python")

# Optional: imageio als Fallback
try:
    import imageio
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False


class BlendMode(Enum):
    """Blend-Modi für Overlays"""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ADD = "add"
    SUBTRACT = "subtract"


@dataclass
class VideoSource:
    """Eine Video-Quelle"""
    id: str
    file_path: str
    width: int = 0
    height: int = 0
    fps: float = 30.0
    duration: float = 0.0
    total_frames: int = 0
    
    # Playback-Status
    is_loaded: bool = False
    is_playing: bool = False
    current_frame: int = 0
    loop: bool = True
    
    # Interne Referenzen
    _capture: any = None
    _reader: any = None
    _cached_frames: Dict[int, Image.Image] = field(default_factory=dict)
    _cache_size: int = 30  # Frames im Cache halten
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration": self.duration,
            "total_frames": self.total_frames,
            "loop": self.loop
        }


class VideoPlayer:
    """
    Video-Player für einzelne Videos
    Unterstützt MP4, AVI, WebM etc.
    """
    
    def __init__(self, file_path: str, loop: bool = True):
        self.file_path = file_path
        self.loop = loop
        
        self.width = 0
        self.height = 0
        self.fps = 30.0
        self.total_frames = 0
        self.current_frame = 0
        
        self.is_loaded = False
        self.is_playing = False
        
        self._capture = None
        self._reader = None
        self._frame_cache: Dict[int, Image.Image] = {}
        self._cache_enabled = True
        self._max_cache_frames = 60
        
        # Callbacks
        self.on_frame: Optional[Callable[[Image.Image], None]] = None
        self.on_loop: Optional[Callable[[], None]] = None
        self.on_end: Optional[Callable[[], None]] = None
        
        # Threading
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._load_video()
    
    def _load_video(self):
        """Lädt Video-Metadaten"""
        if not os.path.exists(self.file_path):
            print(f"⚠️ Video nicht gefunden: {self.file_path}")
            return
        
        if CV2_AVAILABLE:
            self._load_with_cv2()
        elif IMAGEIO_AVAILABLE:
            self._load_with_imageio()
        else:
            print("❌ Kein Video-Backend verfügbar!")
            return
    
    def _load_with_cv2(self):
        """Lädt Video mit OpenCV"""
        self._capture = cv2.VideoCapture(self.file_path)
        
        if not self._capture.isOpened():
            print(f"❌ Konnte Video nicht öffnen: {self.file_path}")
            return
        
        self.width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self._capture.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.is_loaded = True
        print(f"✅ Video geladen: {self.width}x{self.height} @ {self.fps}fps, {self.total_frames} Frames")
    
    def _load_with_imageio(self):
        """Lädt Video mit imageio"""
        try:
            self._reader = imageio.get_reader(self.file_path)
            meta = self._reader.get_meta_data()
            
            self.width = meta.get('size', (0, 0))[0]
            self.height = meta.get('size', (0, 0))[1]
            self.fps = meta.get('fps', 30.0)
            self.total_frames = meta.get('nframes', 0) or self._reader.count_frames()
            
            self.is_loaded = True
            print(f"✅ Video geladen (imageio): {self.width}x{self.height} @ {self.fps}fps")
        except Exception as e:
            print(f"❌ Video-Ladefehler: {e}")
    
    def get_frame(self, frame_number: int = -1) -> Optional[Image.Image]:
        """Holt einen spezifischen Frame"""
        if not self.is_loaded:
            return None
        
        if frame_number < 0:
            frame_number = self.current_frame
        
        # Cache prüfen
        if frame_number in self._frame_cache:
            return self._frame_cache[frame_number]
        
        # Frame laden
        frame = self._read_frame(frame_number)
        
        if frame and self._cache_enabled:
            # In Cache speichern (älteste entfernen wenn voll)
            if len(self._frame_cache) >= self._max_cache_frames:
                oldest = min(self._frame_cache.keys())
                del self._frame_cache[oldest]
            self._frame_cache[frame_number] = frame
        
        return frame
    
    def _read_frame(self, frame_number: int) -> Optional[Image.Image]:
        """Liest einen Frame direkt"""
        if CV2_AVAILABLE and self._capture:
            return self._read_frame_cv2(frame_number)
        elif IMAGEIO_AVAILABLE and self._reader:
            return self._read_frame_imageio(frame_number)
        return None
    
    def _read_frame_cv2(self, frame_number: int) -> Optional[Image.Image]:
        """Liest Frame mit OpenCV"""
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self._capture.read()
        
        if not ret:
            return None
        
        # BGR zu RGB konvertieren
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    
    def _read_frame_imageio(self, frame_number: int) -> Optional[Image.Image]:
        """Liest Frame mit imageio"""
        try:
            frame_number = min(frame_number, self.total_frames - 1)
            frame = self._reader.get_data(frame_number)
            return Image.fromarray(frame)
        except Exception as e:
            return None
    
    def next_frame(self) -> Optional[Image.Image]:
        """Geht zum nächsten Frame"""
        self.current_frame += 1
        
        if self.current_frame >= self.total_frames:
            if self.loop:
                self.current_frame = 0
                if self.on_loop:
                    self.on_loop()
            else:
                self.current_frame = self.total_frames - 1
                self.is_playing = False
                if self.on_end:
                    self.on_end()
        
        return self.get_frame()
    
    def play(self):
        """Startet die Video-Wiedergabe in separatem Thread"""
        if self.is_playing:
            return
        
        self.is_playing = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()
    
    def pause(self):
        """Pausiert die Wiedergabe"""
        self.is_playing = False
    
    def stop(self):
        """Stoppt die Wiedergabe"""
        self.is_playing = False
        self._stop_event.set()
        self.current_frame = 0
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
    
    def seek(self, frame_number: int):
        """Springt zu einem bestimmten Frame"""
        self.current_frame = max(0, min(frame_number, self.total_frames - 1))
    
    def seek_percent(self, percent: float):
        """Springt zu einer Prozent-Position"""
        frame = int((percent / 100.0) * self.total_frames)
        self.seek(frame)
    
    def _playback_loop(self):
        """Wiedergabe-Schleife im Hintergrund-Thread"""
        frame_duration = 1.0 / self.fps
        
        while self.is_playing and not self._stop_event.is_set():
            start_time = time.time()
            
            frame = self.next_frame()
            
            if frame and self.on_frame:
                self.on_frame(frame)
            
            # FPS einhalten
            elapsed = time.time() - start_time
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def resize(self, width: int, height: int):
        """Setzt neue Zielgröße für Frames"""
        # Cache leeren bei Größenänderung
        self._frame_cache.clear()
    
    def close(self):
        """Gibt Ressourcen frei"""
        self.stop()
        
        if self._capture:
            self._capture.release()
            self._capture = None
        
        if self._reader:
            self._reader.close()
            self._reader = None
        
        self._frame_cache.clear()


class OverlayRenderer:
    """
    Rendert mehrere Overlays übereinander
    mit verschiedenen Blend-Modi
    """
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Aktive Overlays (sortiert nach z_index)
        self.overlays: Dict[str, dict] = {}  # id -> {player, opacity, blend_mode, z_index, position}
    
    def add_overlay(self, overlay_id: str, file_path: str,
                   opacity: float = 1.0,
                   blend_mode: BlendMode = BlendMode.NORMAL,
                   z_index: int = 100,
                   position: Tuple[int, int] = (0, 0),
                   loop: bool = True):
        """Fügt ein neues Overlay hinzu"""
        player = VideoPlayer(file_path, loop=loop)
        
        self.overlays[overlay_id] = {
            "player": player,
            "opacity": opacity,
            "blend_mode": blend_mode,
            "z_index": z_index,
            "position": position,
            "visible": True
        }
        
        # Automatisch starten
        player.play()
        print(f"🎬 Overlay hinzugefügt: {overlay_id} (z={z_index})")
    
    def remove_overlay(self, overlay_id: str):
        """Entfernt ein Overlay"""
        if overlay_id in self.overlays:
            self.overlays[overlay_id]["player"].close()
            del self.overlays[overlay_id]
            print(f"🎬 Overlay entfernt: {overlay_id}")
    
    def set_visibility(self, overlay_id: str, visible: bool):
        """Setzt Sichtbarkeit eines Overlays"""
        if overlay_id in self.overlays:
            self.overlays[overlay_id]["visible"] = visible
    
    def set_opacity(self, overlay_id: str, opacity: float):
        """Setzt Deckkraft eines Overlays"""
        if overlay_id in self.overlays:
            self.overlays[overlay_id]["opacity"] = max(0.0, min(1.0, opacity))
    
    def composite(self, base_image: Image.Image) -> Image.Image:
        """
        Kombiniert alle sichtbaren Overlays auf das Basis-Bild
        """
        result = base_image.convert('RGBA')
        
        # Nach z_index sortieren
        sorted_overlays = sorted(
            [(oid, data) for oid, data in self.overlays.items() if data["visible"]],
            key=lambda x: x[1]["z_index"]
        )
        
        for overlay_id, data in sorted_overlays:
            player: VideoPlayer = data["player"]
            frame = player.get_frame()
            
            if not frame:
                continue
            
            # Frame auf Overlay-Größe skalieren falls nötig
            if frame.size != (self.width, self.height):
                frame = frame.resize((self.width, self.height), Image.LANCZOS)
            
            # Zu RGBA konvertieren
            if frame.mode != 'RGBA':
                frame = frame.convert('RGBA')
            
            # Opacity anwenden
            opacity = data["opacity"]
            if opacity < 1.0:
                # Alpha-Kanal anpassen
                r, g, b, a = frame.split()
                a = a.point(lambda x: int(x * opacity))
                frame = Image.merge('RGBA', (r, g, b, a))
            
            # Blend-Modus anwenden
            result = self._blend(result, frame, data["blend_mode"], data["position"])
        
        return result
    
    def _blend(self, base: Image.Image, overlay: Image.Image, 
               mode: BlendMode, position: Tuple[int, int]) -> Image.Image:
        """Wendet einen Blend-Modus an"""
        
        # Position berücksichtigen
        x, y = position
        
        if mode == BlendMode.NORMAL:
            # Standard Alpha-Compositing
            if x == 0 and y == 0 and overlay.size == base.size:
                return Image.alpha_composite(base, overlay)
            else:
                result = base.copy()
                result.paste(overlay, position, overlay)
                return result
        
        elif mode == BlendMode.MULTIPLY:
            # Multiply: Verdunkelt
            from PIL import ImageChops
            base_rgb = base.convert('RGB')
            overlay_rgb = overlay.convert('RGB')
            blended = ImageChops.multiply(base_rgb, overlay_rgb)
            # Mit Alpha kombinieren
            result = blended.convert('RGBA')
            result.putalpha(base.split()[3])
            return result
        
        elif mode == BlendMode.SCREEN:
            # Screen: Aufhellen
            from PIL import ImageChops
            base_rgb = base.convert('RGB')
            overlay_rgb = overlay.convert('RGB')
            blended = ImageChops.screen(base_rgb, overlay_rgb)
            result = blended.convert('RGBA')
            result.putalpha(base.split()[3])
            return result
        
        elif mode == BlendMode.ADD:
            # Add: Additiv (für Glühen, Feuer)
            from PIL import ImageChops
            base_rgb = base.convert('RGB')
            overlay_rgb = overlay.convert('RGB')
            blended = ImageChops.add(base_rgb, overlay_rgb)
            result = blended.convert('RGBA')
            result.putalpha(base.split()[3])
            return result
        
        # Fallback
        return Image.alpha_composite(base, overlay)
    
    def update(self):
        """Update-Tick für alle Overlays (nächster Frame)"""
        for overlay_id, data in self.overlays.items():
            if data["visible"]:
                data["player"].next_frame()
    
    def close_all(self):
        """Schließt alle Overlays"""
        for overlay_id in list(self.overlays.keys()):
            self.remove_overlay(overlay_id)


class VideoMapRenderer:
    """
    Rendert eine Video-basierte Karte (MP4 aus Unity/Blender)
    mit optionalen Overlays
    """
    
    def __init__(self):
        self.current_video: Optional[VideoPlayer] = None
        self.overlay_renderer: Optional[OverlayRenderer] = None
        
        self.width = 0
        self.height = 0
        
        # Callbacks
        self.on_frame_ready: Optional[Callable[[Image.Image], None]] = None
        
        # Threading
        self._render_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_rendering = False
    
    def load_video_map(self, video_path: str):
        """Lädt eine Video-Map"""
        if self.current_video:
            self.current_video.close()
        
        self.current_video = VideoPlayer(video_path, loop=True)
        
        if self.current_video.is_loaded:
            self.width = self.current_video.width
            self.height = self.current_video.height
            
            # Overlay-Renderer erstellen/aktualisieren
            self.overlay_renderer = OverlayRenderer(self.width, self.height)
            
            print(f"🗺️ Video-Map geladen: {video_path}")
            print(f"   Größe: {self.width}x{self.height}")
    
    def add_weather_overlay(self, weather_type: str, video_path: str):
        """Fügt ein Wetter-Overlay hinzu"""
        if not self.overlay_renderer:
            return
        
        overlay_id = f"weather_{weather_type}"
        
        # Altes Wetter-Overlay entfernen
        for oid in list(self.overlay_renderer.overlays.keys()):
            if oid.startswith("weather_"):
                self.overlay_renderer.remove_overlay(oid)
        
        # Neues Overlay hinzufügen
        self.overlay_renderer.add_overlay(
            overlay_id,
            video_path,
            opacity=0.6,
            blend_mode=BlendMode.SCREEN,  # Für Regen/Schnee gut
            z_index=200
        )
    
    def add_effect_overlay(self, effect_id: str, video_path: str,
                          opacity: float = 1.0,
                          blend_mode: BlendMode = BlendMode.NORMAL):
        """Fügt ein Effekt-Overlay hinzu"""
        if not self.overlay_renderer:
            return
        
        self.overlay_renderer.add_overlay(
            effect_id,
            video_path,
            opacity=opacity,
            blend_mode=blend_mode,
            z_index=150
        )
    
    def remove_overlay(self, overlay_id: str):
        """Entfernt ein Overlay"""
        if self.overlay_renderer:
            self.overlay_renderer.remove_overlay(overlay_id)
    
    def render_frame(self) -> Optional[Image.Image]:
        """Rendert einen Frame mit allen Overlays"""
        if not self.current_video or not self.current_video.is_loaded:
            return None
        
        # Basis-Frame holen
        base_frame = self.current_video.get_frame()
        if not base_frame:
            return None
        
        # Overlays anwenden
        if self.overlay_renderer:
            result = self.overlay_renderer.composite(base_frame)
        else:
            result = base_frame
        
        return result
    
    def start_playback(self, fps: float = 30.0):
        """Startet kontinuierliche Wiedergabe"""
        if self._is_rendering:
            return
        
        self._is_rendering = True
        self._stop_event.clear()
        
        if self.current_video:
            self.current_video.play()
        
        self._render_thread = threading.Thread(target=self._render_loop, args=(fps,), daemon=True)
        self._render_thread.start()
    
    def stop_playback(self):
        """Stoppt die Wiedergabe"""
        self._is_rendering = False
        self._stop_event.set()
        
        if self.current_video:
            self.current_video.pause()
        
        if self._render_thread:
            self._render_thread.join(timeout=1.0)
            self._render_thread = None
    
    def _render_loop(self, fps: float):
        """Render-Schleife"""
        frame_duration = 1.0 / fps
        
        while self._is_rendering and not self._stop_event.is_set():
            start_time = time.time()
            
            # Frame rendern
            frame = self.render_frame()
            
            if frame and self.on_frame_ready:
                self.on_frame_ready(frame)
            
            # Overlays updaten
            if self.overlay_renderer:
                self.overlay_renderer.update()
            
            # Video-Frame weiterspulen
            if self.current_video:
                self.current_video.next_frame()
            
            # FPS einhalten
            elapsed = time.time() - start_time
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def close(self):
        """Gibt alle Ressourcen frei"""
        self.stop_playback()
        
        if self.current_video:
            self.current_video.close()
            self.current_video = None
        
        if self.overlay_renderer:
            self.overlay_renderer.close_all()
            self.overlay_renderer = None


class VideoOverlayManager:
    """
    Zentrale Verwaltung aller Video-Assets
    """
    
    def __init__(self, assets_folder: str = "assets/videos"):
        self.assets_folder = assets_folder
        
        # Geladene Video-Quellen
        self.video_sources: Dict[str, VideoSource] = {}
        
        # Vordefinierte Overlays
        self.weather_overlays: Dict[str, str] = {}  # weather_type -> file_path
        self.effect_overlays: Dict[str, str] = {}   # effect_name -> file_path
        
        # Aktiver Renderer
        self.active_renderer: Optional[VideoMapRenderer] = None
        
        self._scan_assets()
    
    def _scan_assets(self):
        """Scannt Asset-Ordner nach Videos"""
        if not os.path.exists(self.assets_folder):
            os.makedirs(self.assets_folder, exist_ok=True)
            print(f"📁 Video-Asset-Ordner erstellt: {self.assets_folder}")
            return
        
        # Unterordner durchsuchen
        weather_folder = os.path.join(self.assets_folder, "weather")
        effects_folder = os.path.join(self.assets_folder, "effects")
        maps_folder = os.path.join(self.assets_folder, "maps")
        
        # Wetter-Overlays
        if os.path.exists(weather_folder):
            for filename in os.listdir(weather_folder):
                if filename.endswith(('.mp4', '.webm', '.avi')):
                    weather_type = os.path.splitext(filename)[0]
                    self.weather_overlays[weather_type] = os.path.join(weather_folder, filename)
                    print(f"  🌧️ Wetter-Overlay: {weather_type}")
        
        # Effekt-Overlays
        if os.path.exists(effects_folder):
            for filename in os.listdir(effects_folder):
                if filename.endswith(('.mp4', '.webm', '.avi')):
                    effect_name = os.path.splitext(filename)[0]
                    self.effect_overlays[effect_name] = os.path.join(effects_folder, filename)
                    print(f"  ✨ Effekt-Overlay: {effect_name}")
        
        # Video-Maps
        if os.path.exists(maps_folder):
            for filename in os.listdir(maps_folder):
                if filename.endswith(('.mp4', '.webm', '.avi')):
                    map_id = os.path.splitext(filename)[0]
                    self.video_sources[map_id] = VideoSource(
                        id=map_id,
                        file_path=os.path.join(maps_folder, filename)
                    )
                    print(f"  🗺️ Video-Map: {map_id}")
    
    def create_renderer(self) -> VideoMapRenderer:
        """Erstellt einen neuen Video-Renderer"""
        self.active_renderer = VideoMapRenderer()
        return self.active_renderer
    
    def load_map(self, map_id: str) -> bool:
        """Lädt eine Video-Map"""
        if map_id not in self.video_sources:
            print(f"⚠️ Video-Map nicht gefunden: {map_id}")
            return False
        
        if not self.active_renderer:
            self.create_renderer()
        
        source = self.video_sources[map_id]
        self.active_renderer.load_video_map(source.file_path)
        return True
    
    def set_weather(self, weather_type: str):
        """Setzt das Wetter (Overlay)"""
        if not self.active_renderer:
            return
        
        if weather_type in self.weather_overlays:
            self.active_renderer.add_weather_overlay(
                weather_type,
                self.weather_overlays[weather_type]
            )
        elif weather_type == "clear":
            # Kein Wetter-Overlay
            for oid in list(self.active_renderer.overlay_renderer.overlays.keys()):
                if oid.startswith("weather_"):
                    self.active_renderer.remove_overlay(oid)
    
    def add_effect(self, effect_name: str):
        """Fügt einen Effekt hinzu"""
        if not self.active_renderer:
            return
        
        if effect_name in self.effect_overlays:
            self.active_renderer.add_effect_overlay(
                f"effect_{effect_name}",
                self.effect_overlays[effect_name]
            )
    
    def remove_effect(self, effect_name: str):
        """Entfernt einen Effekt"""
        if self.active_renderer:
            self.active_renderer.remove_overlay(f"effect_{effect_name}")
    
    def get_available_weather(self) -> List[str]:
        """Gibt verfügbare Wetter-Typen zurück"""
        return list(self.weather_overlays.keys())
    
    def get_available_effects(self) -> List[str]:
        """Gibt verfügbare Effekte zurück"""
        return list(self.effect_overlays.keys())
    
    def get_available_maps(self) -> List[str]:
        """Gibt verfügbare Video-Maps zurück"""
        return list(self.video_sources.keys())


# ============================================================
# TKINTER WIDGET für Video-Anzeige
# ============================================================

class VideoCanvas(tk.Canvas):
    """
    Tkinter Canvas-Widget für Video-Wiedergabe
    """
    
    def __init__(self, parent, width: int = 800, height: int = 600, **kwargs):
        super().__init__(parent, width=width, height=height, bg="black", **kwargs)
        
        self.video_manager = VideoOverlayManager()
        self.renderer: Optional[VideoMapRenderer] = None
        
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._image_id: Optional[int] = None
        
        self._target_width = width
        self._target_height = height
        
        # FPS-Counter
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._current_fps = 0.0
    
    def load_video(self, video_path: str):
        """Lädt ein Video"""
        if self.renderer:
            self.renderer.close()
        
        self.renderer = self.video_manager.create_renderer()
        self.renderer.load_video_map(video_path)
        self.renderer.on_frame_ready = self._on_frame
    
    def play(self, fps: float = 30.0):
        """Startet die Wiedergabe"""
        if self.renderer:
            self.renderer.start_playback(fps)
    
    def stop(self):
        """Stoppt die Wiedergabe"""
        if self.renderer:
            self.renderer.stop_playback()
    
    def _on_frame(self, frame: Image.Image):
        """Callback für jeden Frame"""
        try:
            # Frame skalieren falls nötig
            if frame.size != (self._target_width, self._target_height):
                frame = frame.resize(
                    (self._target_width, self._target_height),
                    Image.LANCZOS
                )
            
            # Zu PhotoImage konvertieren
            self._photo = ImageTk.PhotoImage(frame)
            
            # Auf Canvas zeichnen
            if self._image_id:
                self.itemconfig(self._image_id, image=self._photo)
            else:
                self._image_id = self.create_image(
                    0, 0, image=self._photo, anchor=tk.NW
                )
            
            # FPS zählen
            self._frame_count += 1
            current_time = time.time()
            if current_time - self._last_fps_time >= 1.0:
                self._current_fps = self._frame_count / (current_time - self._last_fps_time)
                self._frame_count = 0
                self._last_fps_time = current_time
        except Exception as e:
            print(f"Frame-Fehler: {e}")
    
    def add_weather(self, weather_type: str):
        """Fügt Wetter-Overlay hinzu"""
        if self.renderer and self.video_manager:
            self.video_manager.set_weather(weather_type)
    
    def clear_weather(self):
        """Entfernt Wetter"""
        if self.video_manager:
            self.video_manager.set_weather("clear")
    
    def destroy(self):
        """Aufräumen"""
        if self.renderer:
            self.renderer.close()
        super().destroy()


# ============================================================
# PRESET WEATHER EFFECTS
# ============================================================

WEATHER_PRESETS = {
    "rain": {
        "opacity": 0.5,
        "blend_mode": BlendMode.SCREEN,
        "z_index": 200
    },
    "rain_heavy": {
        "opacity": 0.7,
        "blend_mode": BlendMode.SCREEN,
        "z_index": 200
    },
    "snow": {
        "opacity": 0.6,
        "blend_mode": BlendMode.SCREEN,
        "z_index": 200
    },
    "fog": {
        "opacity": 0.4,
        "blend_mode": BlendMode.NORMAL,
        "z_index": 180
    },
    "storm": {
        "opacity": 0.8,
        "blend_mode": BlendMode.MULTIPLY,
        "z_index": 210
    },
    "sandstorm": {
        "opacity": 0.6,
        "blend_mode": BlendMode.MULTIPLY,
        "z_index": 200
    }
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_dummy_weather_video(output_path: str, weather_type: str, 
                               width: int = 1920, height: int = 1080,
                               duration: int = 10, fps: int = 30):
    """
    Erstellt ein Dummy-Wetter-Video (für Tests)
    Benötigt: pip install opencv-python numpy
    """
    if not CV2_AVAILABLE:
        print("❌ OpenCV benötigt für Video-Erstellung!")
        return
    
    import numpy as np
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration * fps
    
    for i in range(total_frames):
        # Erstelle Frame je nach Wetter-Typ
        if weather_type == "rain":
            # Regen-Effekt: Zufällige Linien
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            for _ in range(100):
                x = np.random.randint(0, width)
                y1 = np.random.randint(0, height - 50)
                y2 = y1 + np.random.randint(20, 50)
                cv2.line(frame, (x, y1), (x + 2, y2), (150, 150, 180), 1)
        
        elif weather_type == "snow":
            # Schnee: Weiße Punkte
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            for _ in range(200):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                radius = np.random.randint(2, 5)
                cv2.circle(frame, (x, y), radius, (255, 255, 255), -1)
        
        elif weather_type == "fog":
            # Nebel: Grauer Gradient
            frame = np.ones((height, width, 3), dtype=np.uint8) * 100
            noise = np.random.randint(-20, 20, (height, width, 3), dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Dummy-Video erstellt: {output_path}")
