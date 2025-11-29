"""
Dynamic Lighting System für 2.5D VTT
Echtzeit-Beleuchtung mit Lichtquellen, Farbeffekten und Falloff
"""
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
import math
from typing import List, Tuple, Dict, Optional
import json
import numpy as np

# GPU Acceleration imports
try:
    import pyopencl as cl
    import pyopencl.array as cl_array
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️ PyOpenCL nicht verfügbar - GPU-Beschleunigung deaktiviert")

# Enable OpenCV OpenCL support
try:
    import cv2
    cv2.ocl.setUseOpenCL(True)
    if cv2.ocl.useOpenCL():
        print("✅ OpenCV OpenCL aktiviert")
    else:
        print("⚠️ OpenCV OpenCL nicht verfügbar")
except:
    pass

class GPUImage:
    """GPU-basierte Image-Klasse für vollständige GPU-Rendering-Pipeline"""
    
    def __init__(self, context, queue, width, height, channels=4):
        self.context = context
        self.queue = queue
        self.width = width
        self.height = height
        self.channels = channels
        
        # GPU Buffer für RGBA Daten
        self.gpu_buffer = cl_array.zeros(queue, (height, width, channels), dtype=np.float32)
        
    @classmethod
    def from_pil_image(cls, context, queue, pil_image):
        """Erstelle GPUImage aus PIL Image"""
        # Konvertiere PIL zu numpy array
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        np_array = np.array(pil_image, dtype=np.float32) / 255.0
        
        gpu_img = cls(context, queue, pil_image.width, pil_image.height, 4)
        gpu_img.gpu_buffer.set(np_array)
        
        return gpu_img
    
    def to_pil_image(self):
        """Konvertiere zurück zu PIL Image"""
        np_array = self.gpu_buffer.get()
        np_array = np.clip(np_array * 255, 0, 255).astype(np.uint8)
        
        if self.channels == 4:
            return Image.fromarray(np_array, mode='RGBA')
        elif self.channels == 3:
            return Image.fromarray(np_array, mode='RGB')
        else:
            return Image.fromarray(np_array[:, :, 0], mode='L')
    
    def copy(self):
        """Erstelle Kopie"""
        new_img = GPUImage(self.context, self.queue, self.width, self.height, self.channels)
        # GPU-to-GPU copy
        cl.enqueue_copy(self.queue, new_img.gpu_buffer.data, self.gpu_buffer.data)
        return new_img


class GPURenderer:
    """Vollständige GPU-basierte Rendering-Engine"""
    
    def __init__(self):
        if not GPU_AVAILABLE:
            raise RuntimeError("GPU nicht verfügbar")
            
        # OpenCL Setup - Automatische GPU-Auswahl ohne Benutzer-Interaktion
        try:
            # Hole verfügbare Platformen
            platforms = cl.get_platforms()
            if not platforms:
                raise RuntimeError("Keine OpenCL-Platformen gefunden")
            
            # Wähle erste Platform (normalerweise AMD, NVIDIA oder Intel)
            platform = platforms[0]
            
            # Hole GPU-Devices von dieser Platform
            gpu_devices = [device for device in platform.get_devices() 
                          if device.type == cl.device_type.GPU]
            
            if not gpu_devices:
                # Fallback: Verwende alle verfügbaren Devices
                gpu_devices = platform.get_devices()
                if not gpu_devices:
                    raise RuntimeError("Keine OpenCL-Devices gefunden")
            
            # Wähle erstes verfügbares Device
            self.device = gpu_devices[0]
            
            # Erstelle Context und Queue
            self.context = cl.Context([self.device])
            self.queue = cl.CommandQueue(self.context)
            
            print(f"🎮 GPU-Renderer initialisiert: {self.device.name}")
            print(f"   Platform: {platform.name}")
            print(f"   Speicher: {self.device.global_mem_size // (1024**3)}GB GDDR")
            
        except Exception as e:
            print(f"⚠️ Automatische GPU-Initialisierung fehlgeschlagen: {e}")
            # Fallback zur interaktiven Methode
            print("🔄 Fallback zur interaktiven GPU-Auswahl...")
            self.context = cl.create_some_context()
            self.queue = cl.CommandQueue(self.context)
            self.device = self.context.devices[0]
            print(f"🎮 GPU-Renderer initialisiert (Fallback): {self.device.name}")
        
        # OpenCL Programme kompilieren
        self._compile_kernels()
        
        # GPU Buffer Cache für Performance
        self.buffer_cache = {}
        
    def _compile_kernels(self):
        """Kompiliere alle OpenCL-Kernel"""
        
        # Kernel für Lichtberechnung
        light_kernel = """
        __kernel void compute_light_mask(
            __global float4 *light_mask,
            const int width,
            const int height,
            const float cx,
            const float cy,
            const float radius_px,
            const float falloff_exponent,
            const float core_brightness,
            const float current_intensity,
            const float noise_strength,
            __global float *noise_map
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            float dx = x - cx;
            float dy = y - cy;
            float dist = sqrt(dx * dx + dy * dy);
            
            int idx = y * width + x;
            
            // Smooth falloff without hard cutoff
            // Allow light to fade gradually beyond the nominal radius
            float extended_radius = radius_px * 3.0f; // Allow falloff up to 3x radius for very smooth edges
            
            if (dist > extended_radius) {
                light_mask[idx] = (float4)(0.0f, 0.0f, 0.0f, 0.0f);
                return;
            }
            
            // Smooth normalized distance with soft clamping
            float normalized_dist = min(dist / radius_px, 2.0f); // Allow up to 2x radius for smooth falloff
            
            // Enhanced smooth falloff: combine inverse square with gaussian for smoother edges
            float inv_square = 1.0f / (1.0f + pow(normalized_dist, falloff_exponent));
            float gaussian = exp(-pow(normalized_dist * 1.5f, 2.0f)); // Softer gaussian for smoother edges
            
            // Blend the two falloff functions for smoother transition (more gaussian for realistic falloff)
            float falloff = inv_square * 0.4f + gaussian * 0.6f;
            
            // For distances beyond the nominal radius, apply additional fade
            if (dist > radius_px) {
                float beyond_radius_factor = (extended_radius - dist) / (extended_radius - radius_px);
                beyond_radius_factor = max(beyond_radius_factor, 0.0f);
                // Exponential fade for very smooth edge
                falloff *= exp(-pow(1.0f - beyond_radius_factor, 2.0f) * 3.0f);
            }
            
            // Kern-Bereich (inner 10%) gets brightness boost
            if (dist < radius_px * 0.1f) {
                falloff = min(1.0f, falloff * core_brightness);
            }
            
            // Noise for organic variation
            float noise_val = noise_map[idx];
            falloff = falloff * (1.0f + noise_val * noise_strength);
            
            float intensity = falloff * current_intensity;
            
            // Ensure minimum visibility for smooth blending
            intensity = max(intensity, 0.001f);
            
            // Basis-Farben (werden später überschrieben für spezielle Lichttypen)
            light_mask[idx] = (float4)(intensity, intensity, intensity, intensity);
        }
        
        __kernel void add_ambient_light(
            __global float4 *image,
            const int width,
            const int height,
            const float ambient_r,
            const float ambient_g,
            const float ambient_b,
            const float ambient_a
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            int idx = y * width + x;
            float4 pixel = image[idx];
            
            // Add ambient light
            pixel.x = max(pixel.x, ambient_r);
            pixel.y = max(pixel.y, ambient_g);
            pixel.z = max(pixel.z, ambient_b);
            pixel.w = max(pixel.w, ambient_a);
            
            image[idx] = pixel;
        }
        
        __kernel void multiply_blend(
            __global float4 *result,
            __global float4 *base,
            __global float4 *overlay,
            const int width,
            const int height
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            int idx = y * width + x;
            float4 base_pixel = base[idx];
            float4 overlay_pixel = overlay[idx];
            
            // Multiply blend: result = base * overlay
            result[idx] = (float4)(
                base_pixel.x * overlay_pixel.x,
                base_pixel.y * overlay_pixel.y,
                base_pixel.z * overlay_pixel.z,
                base_pixel.w * overlay_pixel.w
            );
        }
        
        __kernel void alpha_composite(
            __global float4 *result,
            __global float4 *base,
            __global float4 *overlay,
            const int width,
            const int height
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            int idx = y * width + x;
            float4 base_pixel = base[idx];
            float4 overlay_pixel = overlay[idx];
            
            // Alpha compositing
            float alpha = overlay_pixel.w;
            float inv_alpha = 1.0f - alpha;
            
            result[idx] = (float4)(
                base_pixel.x * inv_alpha + overlay_pixel.x * alpha,
                base_pixel.y * inv_alpha + overlay_pixel.y * alpha,
                base_pixel.z * inv_alpha + overlay_pixel.z * alpha,
                base_pixel.w * inv_alpha + overlay_pixel.w * alpha
            );
        }
        
        __kernel void gaussian_blur_3x3(
            __global float4 *output,
            __global float4 *input,
            const int width,
            const int height
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            // 3x3 Gaussian kernel
            float gauss_kernel[9] = {
                0.0625f, 0.125f, 0.0625f,
                0.125f,  0.25f,  0.125f,
                0.0625f, 0.125f, 0.0625f
            };
            
            float4 sum = (float4)(0.0f, 0.0f, 0.0f, 0.0f);
            
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int sx = clamp(x + kx, 0, width - 1);
                    int sy = clamp(y + ky, 0, height - 1);
                    int kidx = (ky + 1) * 3 + (kx + 1);
                    
                    sum += input[sy * width + sx] * gauss_kernel[kidx];
                }
            }
            
            output[y * width + x] = sum;
        }
        
        __kernel void generate_grass_texture(
            __global float4 *output,
            const int width,
            const int height,
            const int frame
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            int idx = y * width + x;
            
            // Perlin-like noise for organic variation
            float noise = sin(x * 0.1f) * cos(y * 0.1f) * 10.0f;
            noise += sin(x * 0.05f + y * 0.07f) * 5.0f;
            
            // Add some randomness
            float random_val = sin(x * 123.456f + y * 789.012f + frame * 0.1f) * 2.5f;
            noise += random_val;
            
            float variation = noise / 255.0f;
            
            // Base grass color with variation
            float r = clamp(126.0f/255.0f + variation * 0.1f, 110.0f/255.0f, 140.0f/255.0f);
            float g = clamp(179.0f/255.0f + variation * 0.15f, 165.0f/255.0f, 190.0f/255.0f);
            float b = clamp(86.0f/255.0f + variation * 0.1f, 75.0f/255.0f, 95.0f/255.0f);
            
            output[idx] = (float4)(r, g, b, 1.0f);
        }
        
        __kernel void generate_water_texture(
            __global float4 *output,
            const int width,
            const int height,
            const int frame,
            const int direction
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= width || y >= height) return;
            
            int idx = y * width + x;
            
            // Flow direction
            float dx = (direction == 0 || direction == 6 || direction == 7) ? 1.0f : 
                      (direction == 2 || direction == 3 || direction == 4) ? -1.0f : 0.0f;
            float dy = (direction == 2 || direction == 3 || direction == 4) ? 1.0f :
                      (direction == 6 || direction == 7) ? -1.0f : 0.0f;
            
            // Normalize diagonal directions
            if (dx != 0.0f && dy != 0.0f) {
                dx *= 0.707f; // 1/sqrt(2)
                dy *= 0.707f;
            }
            
            // Flow animation
            float flow_speed = frame * 0.4f;
            float pos_x = x + flow_speed * dx;
            float pos_y = y + flow_speed * dy;
            
            // Wave frequencies for realistic water
            float wave1 = sin(pos_x * 0.05f) * 8.0f;
            float wave2 = sin(pos_x * 0.037f + pos_y * 0.03f) * 5.0f;
            float cross_wave = sin(x * 0.042f) * 2.0f + sin(y * 0.042f) * 2.0f;
            
            float brightness = (wave1 + wave2 + cross_wave) / 255.0f;
            
            // Water color with wave-based variation
            float r = clamp(65.0f/255.0f + brightness * 0.15f, 50.0f/255.0f, 80.0f/255.0f);
            float g = clamp(155.0f/255.0f + brightness * 0.2f, 135.0f/255.0f, 170.0f/255.0f);
            float b = clamp(230.0f/255.0f + brightness * 0.15f, 205.0f/255.0f, 235.0f/255.0f);
            
            output[idx] = (float4)(r, g, b, 1.0f);
        }
        """
        
        self.program = cl.Program(self.context, light_kernel).build()
        print("✅ GPU-Kernel kompiliert")
    
    def create_gpu_image(self, width, height, channels=4):
        """Erstelle GPUImage"""
        return GPUImage(self.context, self.queue, width, height, channels)
    
    def compute_light_mask_gpu(self, width, height, light, time_offset):
        """Berechne Lichtmaske vollständig auf GPU"""
        
        # GPU Buffer für Lichtmaske
        light_mask = cl_array.zeros(self.queue, (height, width, 4), dtype=np.float32)
        
        # Parameter berechnen
        cx = light.x * 32 + 16  # Annahme: 32px per tile
        cy = light.y * 32 + 16
        radius_px = light.radius * 32
        current_intensity = light.get_current_intensity(time_offset)
        
        # Noise Map generieren (auf GPU)
        noise_map = cl_array.to_device(self.queue, 
            np.random.randn(height, width).astype(np.float32) * 0.1)
        
        # Kernel ausführen
        self.program.compute_light_mask(
            self.queue, (width, height), None,
            light_mask.data,
            np.int32(width), np.int32(height),
            np.float32(cx), np.float32(cy), np.float32(radius_px),
            np.float32(light.falloff_exponent), np.float32(light.core_brightness),
            np.float32(current_intensity), np.float32(0.12),
            noise_map.data
        )
        
        # GPUImage zurückgeben
        gpu_img = GPUImage(self.context, self.queue, width, height, 4)
        gpu_img.gpu_buffer = light_mask
        
        return gpu_img
    
    def add_ambient_light_gpu(self, gpu_image, ambient_r, ambient_g, ambient_b, ambient_a):
        """Füge Ambient Light auf GPU hinzu"""
        
        self.program.add_ambient_light(
            self.queue, (gpu_image.width, gpu_image.height), None,
            gpu_image.gpu_buffer.data,
            np.int32(gpu_image.width), np.int32(gpu_image.height),
            np.float32(ambient_r), np.float32(ambient_g), 
            np.float32(ambient_b), np.float32(ambient_a)
        )
        
        return gpu_image
    
    def multiply_blend_gpu(self, base_image, overlay_image):
        """Multiply-Blend vollständig auf GPU"""
        
        result = GPUImage(self.context, self.queue, base_image.width, base_image.height, 4)
        
        self.program.multiply_blend(
            self.queue, (base_image.width, base_image.height), None,
            result.gpu_buffer.data,
            base_image.gpu_buffer.data,
            overlay_image.gpu_buffer.data,
            np.int32(base_image.width), np.int32(base_image.height)
        )
        
        return result
    
    def alpha_composite_gpu(self, base_image, overlay_image):
        """Alpha-Compositing auf GPU"""
        
        result = GPUImage(self.context, self.queue, base_image.width, base_image.height, 4)
        
        self.program.alpha_composite(
            self.queue, (base_image.width, base_image.height), None,
            result.gpu_buffer.data,
            base_image.gpu_buffer.data,
            overlay_image.gpu_buffer.data,
            np.int32(base_image.width), np.int32(base_image.height)
        )
        
        return result
    
    def gaussian_blur_gpu(self, gpu_image, radius=1):
        """Gaussian Blur auf GPU"""
        
        # Für größere Radien mehrmals anwenden
        for _ in range(radius):
            temp_buffer = cl_array.zeros_like(gpu_image.gpu_buffer)
            
            self.program.gaussian_blur_3x3(
                self.queue, (gpu_image.width, gpu_image.height), None,
                temp_buffer.data,
                gpu_image.gpu_buffer.data,
                np.int32(gpu_image.width), np.int32(gpu_image.height)
            )
            
            gpu_image.gpu_buffer = temp_buffer
        
        return gpu_image
    
    def generate_grass_texture_gpu(self, width, height, frame=0):
        """Generiert Gras-Textur auf GPU"""
        
        gpu_texture = GPUImage(self.context, self.queue, width, height, 4)
        
        self.program.generate_grass_texture(
            self.queue, (width, height), None,
            gpu_texture.gpu_buffer.data,
            np.int32(width), np.int32(height),
            np.int32(frame)
        )
        
        return gpu_texture
    
    def generate_water_texture_gpu(self, width, height, frame=0, direction=0):
        """Generiert Wasser-Textur auf GPU"""
        
        gpu_texture = GPUImage(self.context, self.queue, width, height, 4)
        
        self.program.generate_water_texture(
            self.queue, (width, height), None,
            gpu_texture.gpu_buffer.data,
            np.int32(width), np.int32(height),
            np.int32(frame), np.int32(direction)
        )
        
        return gpu_texture

class LightSource:
    """Einzelne Lichtquelle mit physikalischen Eigenschaften"""
    def __init__(self, x: int, y: int, radius: int = 5, 
                 color: Tuple[int, int, int] = (255, 255, 200),
                 intensity: float = 1.0,
                 flicker: bool = False,
                 light_type: str = "point"):
        """
        Args:
            x, y: Position in Tiles
            radius: Leuchtradius in Tiles
            color: RGB Farbe des Lichts (255,255,200 = warmes Licht)
            intensity: Helligkeit 0.0-1.0
            flicker: Ob Licht flackert (Fackel-Effekt)
            light_type: "point", "torch", "candle", "window", "magic", "fire", "campfire"
        """
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity
        self.flicker = flicker
        self.light_type = light_type
        self.flicker_offset = 0.0
        
        # Physikalische Parameter basierend auf Lichtquelle-Typ
        self._setup_light_physics()
    
    def _setup_light_physics(self):
        """Konfiguriere physikalische Parameter basierend auf Lichttyp"""
        # Standard-Werte
        self.falloff_exponent = 2.0  # Inverse-square-law
        self.core_brightness = 1.2   # Kern-Helligkeit (kann >1 sein für bloom)
        self.flicker_frequency = 0.0
        self.flicker_amplitude = 0.0
        self.flicker_chaos = 0.0     # Zufälligkeit
        
        # Typ-spezifische Parameter
        if self.light_type in ["torch", "fire", "campfire"]:
            # Fackel/Feuer: Realistischeres Flackern, langsamer und weniger chaotisch
            self.falloff_exponent = 2.5  # Stärker abfallend
            self.core_brightness = 1.5
            self.flicker_frequency = 4.5  # Realistisch: 3-5 Hz
            self.flicker_amplitude = 0.13  # Weniger Schwankung
            self.flicker_chaos = 0.18
            
        elif self.light_type == "candle":
            # Kerze: Sanftes, langsames Flackern
            self.falloff_exponent = 2.2
            self.core_brightness = 1.3
            self.flicker_frequency = 2.2   # Sehr langsam
            self.flicker_amplitude = 0.09
            self.flicker_chaos = 0.08
            
        elif self.light_type == "magic":
            # Magie: Pulsierend, konstante Wellen
            self.falloff_exponent = 1.8  # Sanfter Falloff
            self.core_brightness = 1.6   # Sehr hell
            self.flicker_frequency = 4.0   # Langsames Pulsieren
            self.flicker_amplitude = 0.20
            self.flicker_chaos = 0.05    # Wenig Chaos
            
        elif self.light_type == "window":
            # Fenster/Tageslicht: Fast konstant
            self.falloff_exponent = 1.5  # Sehr sanft
            self.core_brightness = 1.0
            self.flicker_frequency = 1.0   # Minimales Flackern (Wind)
            self.flicker_amplitude = 0.05
            self.flicker_chaos = 0.02
            
        elif self.light_type == "moonlight":
            # Mondlicht: Komplett konstant
            self.falloff_exponent = 1.2  # Sehr weich
            self.core_brightness = 0.8
            self.flicker_frequency = 0.0
            self.flicker_amplitude = 0.0
            self.flicker_chaos = 0.0
            
        else:  # "point" oder andere
            # Standard Lichtquelle
            self.falloff_exponent = 2.0
            self.core_brightness = 1.2
            self.flicker_frequency = 0.0
            self.flicker_amplitude = 0.0
            self.flicker_chaos = 0.0
        
    def get_current_intensity(self, time_offset: float = 0.0) -> float:
        """Berechne aktuelle Intensität mit physikalisch korrektem Flackern"""
        if not self.flicker or self.flicker_frequency == 0.0:
            return self.intensity
        
        import random
        
        # Basis-Welle (Hauptfrequenz)
        # time_offset ist in Sekunden, flicker_frequency in Hz
        main_wave = math.sin(time_offset * self.flicker_frequency * math.pi * 2)
        
        # Harmonische (höhere Frequenzen für Detailreichtum)
        harmonic1 = math.sin(time_offset * self.flicker_frequency * 2.3 * math.pi * 2) * 0.3
        harmonic2 = math.sin(time_offset * self.flicker_frequency * 3.7 * math.pi * 2) * 0.15
        
        # Perlin-artiges Chaos (langsame Drift)
        slow_drift = math.sin(time_offset * 0.5 * math.pi * 2) * 0.1
        
        # Zufälliges Rauschen (Chaos)
        chaos = random.uniform(-1, 1) * self.flicker_chaos
        
        # Kombiniere alle Komponenten
        combined_flicker = (
            main_wave * 0.5 +
            harmonic1 * 0.3 +
            harmonic2 * 0.15 +
            slow_drift * 0.05 +
            chaos
        )
        
        # Skaliere mit Amplitude
        flicker_amount = combined_flicker * self.flicker_amplitude
        
        # Spezielle Effekte für bestimmte Lichttypen
        if self.light_type in ["torch", "fire", "campfire"]:
            # Gelegentliche "Aussetzer" (Feuer sackt kurz ab)
            if random.random() < 0.03:  # 3% Chance pro Frame
                flicker_amount -= random.uniform(0.2, 0.4)
            
            # Extra "Funken" (kurze helle Spitzen)
            if random.random() < 0.02:  # 2% Chance
                flicker_amount += random.uniform(0.3, 0.5)
        
        # Finale Intensität berechnen
        final_intensity = self.intensity + flicker_amount
        
        # Clamp auf sinnvolle Werte (verschiedene Minima je nach Typ)
        if self.light_type in ["torch", "fire", "campfire"]:
            min_intensity = 0.25  # Feuer kann sehr dunkel werden
        elif self.light_type == "candle":
            min_intensity = 0.60  # Kerzen bleiben relativ stabil
        else:
            min_intensity = 0.40
        
        return max(min_intensity, min(1.5, final_intensity))  # Erlaubt kurze Überhellung
        
    def get_light_at_position(self, px: int, py: int, time_offset: float = 0.0) -> Tuple[int, int, int, int]:
        """
        Berechne Lichtfarbe an Position mit physikalisch korrektem Falloff
        Returns: (R, G, B, A) mit Alpha als Intensität
        """
        import random
        
        # Distanz zur Lichtquelle (in Tiles)
        dx = px - self.x
        dy = py - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Extended radius for smooth falloff (allow light to fade up to 1.5x radius)
        extended_radius = self.radius * 1.5
        
        # Hard cutoff at extended radius for performance
        if distance > extended_radius:
            return (0, 0, 0, 0)
        
        # Smooth normalized distance (clamped to prevent issues)
        normalized_distance = min(distance / self.radius, 1.0)
        
        # Enhanced smooth falloff: combine inverse square with gaussian for smoother edges
        inv_square = 1.0 / (1.0 + normalized_distance ** self.falloff_exponent)
        gaussian = math.exp(-(normalized_distance * 2.0) ** 2)
        
        # Blend the two falloff functions for smoother transition
        falloff = inv_square * 0.7 + gaussian * 0.3
        
        # For distances beyond the nominal radius, apply additional fade
        if distance > self.radius:
            beyond_radius_factor = (extended_radius - distance) / (extended_radius - self.radius)
            beyond_radius_factor = max(beyond_radius_factor, 0.0)
            # Exponential fade for very smooth edge
            falloff *= math.exp(-pow(1.0 - beyond_radius_factor, 2.0) * 3.0)
        
        # Kern-Bereich (inner 10%) gets brightness boost
        if distance < self.radius * 0.1:
            falloff = min(1.0, falloff * self.core_brightness)
        
        # Aktuelle Intensität (mit Flackern)
        current_intensity = self.get_current_intensity(time_offset)
        
        # Finale Intensität
        final_intensity = falloff * current_intensity
        
        # Ensure minimum visibility for smooth blending
        final_intensity = max(final_intensity, 0.001)
        
        # DYNAMISCHER FARB-SHIFT basierend auf Lichttyp und Distanz
        base_color = self.color
        
        if self.light_type in ["torch", "fire", "campfire"]:
            # Feuer: Realistischer Farbverlauf (Weiß→Gelb→Orange→Rot)
            # Physik: Heißer Kern (weiß), kühlere Außenbereiche (rot)
            
            # Zeit-basierter Farbshift (Flackern der Farbe)
            color_wave = math.sin(time_offset * 4.0 + distance * 1.2) * 0.08
            
            # Distanz-basierte Farbtemperatur
            dist_factor = normalized_distance
            
            if dist_factor < 0.15:  # Kern: Weißglühend
                r = int(min(255, 255 * (1.0 + color_wave)))
                g = int(min(255, 245 * (1.0 + color_wave)))
                b = int(min(255, 220 * (1.0 + color_wave * 0.5)))
            elif dist_factor < 0.40:  # Innen: Helles Gelb-Orange
                r = int(min(255, 255 * (1.0 + color_wave * 0.5)))
                g = int(min(255, 200 * (1.0 + color_wave * 0.3)))
                b = int(min(255, 80 * (1.0 - color_wave * 0.5)))
            elif dist_factor < 0.70:  # Mitte: Orange
                r = int(min(255, 255 * (0.95 + color_wave * 0.2)))
                g = int(min(255, 140 * (1.0 + color_wave * 0.2)))
                b = int(40)
            else:  # Außen: Dunkelrot
                r = int(180 * (1.0 + color_wave * 0.2))
                g = int(60 * (1.0 - dist_factor * 0.3))
                b = int(20)
            
            # Zufällige Funken (nur im inneren Bereich)
            if random.random() < 0.015 and dist_factor < 0.5:
                spark_boost = random.uniform(50, 120)
                r = min(255, r + int(spark_boost))
                g = min(255, g + int(spark_boost * 0.6))
        
        elif self.light_type == "candle":
            # Kerze: Sanftes warmes Gelb mit subtilen Variationen
            warmth_wave = math.sin(time_offset * 2.5) * 0.06
            r = int(min(255, base_color[0] * (1.0 + warmth_wave)))
            g = int(min(255, base_color[1] * (1.0 + warmth_wave * 0.8)))
            b = int(min(255, base_color[2] * (1.0 - warmth_wave * 0.2)))
        
        elif self.light_type == "magic":
            # Magie: Pulsierender Farbshift mit Regenbogen-Effekt
            hue_time = time_offset * 2.0
            r = int(min(255, base_color[0] * (1.0 + math.sin(hue_time) * 0.3)))
            g = int(min(255, base_color[1] * (1.0 + math.sin(hue_time + 2.1) * 0.3)))
            b = int(min(255, base_color[2] * (1.0 + math.sin(hue_time + 4.2) * 0.3)))
        
        elif self.light_type == "window":
            # Tageslicht: Leicht bläulicher Shift
            r = int(base_color[0] * 0.95)
            g = int(base_color[1])
            b = int(min(255, base_color[2] * 1.05))
        
        else:
            # Standard: Direkte Farbe
            r = int(base_color[0])
            g = int(base_color[1])
            b = int(base_color[2])
        
        # Intensität anwenden
        r = int(r * final_intensity)
        g = int(g * final_intensity)
        b = int(b * final_intensity)
        
        a = int(255 * final_intensity)
        
        return (r, g, b, a)
        
    def to_dict(self) -> Dict:
        """Export als Dictionary"""
        return {
            "x": self.x,
            "y": self.y,
            "radius": self.radius,
            "color": self.color,
            "intensity": self.intensity,
            "flicker": self.flicker,
            "light_type": self.light_type
        }
        
    @staticmethod
    def from_dict(data: Dict) -> 'LightSource':
        """Import aus Dictionary"""
        return LightSource(
            x=data["x"],
            y=data["y"],
            radius=data.get("radius", 5),
            color=tuple(data.get("color", [255, 255, 200])),
            intensity=data.get("intensity", 1.0),
            flicker=data.get("flicker", False),
            light_type=data.get("light_type", "point")
        )


class LightingEngine:
    """Verwaltet alle Lichtquellen und rendert Beleuchtung"""
    def _get_active_light_indices(self, max_lights: int, time_offset: float) -> list:
        """Gibt die Indizes der Lichtquellen zurück, die im aktuellen Frame gerendert werden sollen."""
        if not self.lights:
            return []
        # Zyklisch durch alle Lichter gehen
        frame = int(time_offset * 30)  # 30 FPS
        total = len(self.lights)
        start = (frame * max_lights) % total
        indices = [(start + i) % total for i in range(max_lights)]
        return indices

    def __init__(self):
        self.lights = []
        self.ambient_color = (30, 30, 40)  # Dunkles Blau für Nacht
        self.ambient_intensity = 0.2  # Basis-Helligkeit
        self.enabled = True
        self.time_offset = 0.0  # Für Animationen
        self.global_radius_scale = 1.0  # Manueller Radius-Multiplikator

        # Tag/Nacht-System
        self.lighting_mode = "night"  # "day", "night", "custom"
        self.darkness_opacity = 0.85  # Wie dunkel sind unbeleuchtete Bereiche (0=hell, 1=schwarz)
        self.darkness_feather = 20   # Feathering-Radius für weiche Kanten (Pixel)

        # Darkness-Polygone (für Tag-Modus: definiere Innenräume)
        self.darkness_polygons = []  # Liste von Polygon-Punkten [(x,y), ...]
        
        # GPU Texture Cache für häufig verwendete Texturen
        self.gpu_texture_cache = {}
        self.texture_generation_queue = []
        
    def add_light(self, light: LightSource):
        """Füge Lichtquelle hinzu"""
        self.lights.append(light)
        
    def remove_light(self, index: int):
        """Entferne Lichtquelle"""
        if 0 <= index < len(self.lights):
            del self.lights[index]
            
    def get_light_at(self, x: int, y: int, tolerance: int = 1) -> Optional[int]:
        """Finde Lichtquelle an Position (gibt Index zurück)"""
        for i, light in enumerate(self.lights):
            if abs(light.x - x) <= tolerance and abs(light.y - y) <= tolerance:
                return i
        return None
        
    def clear_lights(self):
        """Entferne alle Lichtquellen"""
        self.lights.clear()
        
    def render_lighting(self, width: int, height: int, tile_size: int, time_offset: float = 0.0, radius_scale: float = 1.0) -> Image.Image:
        """
        Rendere Beleuchtungs-Overlay mit farbigem Licht und Dunkelheit
        Args:
            time_offset: Zeit für Flicker-Animation
            radius_scale: Skalierungsfaktor für Lichtradien (abhängig von Tile-Größe)
        Returns: RGBA Image mit farbigem Licht und Schatten
        """
        self.time_offset = time_offset
        print(f"DEBUG: render_lighting darkness_polygons = {self.darkness_polygons}")
        

        # TILE-BASIERTES RENDERING: Nur sichtbarer Bereich
        # Hole sichtbare Tiles aus MapEditor (Standard: alles, aber kann optimiert werden)
        # WICHTIG: Im Tagesmodus mit Darkness-Polygonen MUSS die gesamte Karte gerendert werden!
        
        # Prüfe ob wir die gesamte Karte rendern müssen
        render_full_map = (self.lighting_mode == "day" and self.darkness_polygons) or not self.enabled
        
        if render_full_map:
            # Volle Karte rendern für korrekte Polygon-Anwendung oder wenn disabled
            img_width = width * tile_size
            img_height = height * tile_size
            offset_x = 0
            offset_y = 0
            min_x = 0
            max_x = width - 1
            min_y = 0
            max_y = height - 1
        else:
            # Nur Bereich um Lichtquellen (Performance-Optimierung)
            margin_tiles = 10
            min_x = min([l.x for l in self.lights]) if self.lights else 0
            max_x = max([l.x for l in self.lights]) if self.lights else width-1
            min_y = min([l.y for l in self.lights]) if self.lights else 0
            max_y = max([l.y for l in self.lights]) if self.lights else height-1
            min_x = max(0, min_x - margin_tiles)
            max_x = min(width-1, max_x + margin_tiles)
            min_y = max(0, min_y - margin_tiles)
            max_y = min(height-1, max_y + margin_tiles)

            # Bereich in Pixeln
            img_width = (max_x - min_x + 1) * tile_size
            img_height = (max_y - min_y + 1) * tile_size
            offset_x = min_x * tile_size
            offset_y = min_y * tile_size
        
        if not self.enabled:
            # Keine Beleuchtung aktiv
            if self.lighting_mode == "day":
                # Tagesszene ohne Lichter = normal sichtbar, aber mit Darkness-Polygonen wenn vorhanden
                if self.darkness_polygons:
                    # Erstelle multiply_layer für Darkness-Polygone ohne Lichter
                    img_width = width * tile_size
                    img_height = height * tile_size
                    
                    # Erstelle Shadow-Mask ohne Lichter
                    shadow_mask = Image.new('L', (img_width, img_height), 0)
                    draw = ImageDraw.Draw(shadow_mask)
                    
                    for polygon in self.darkness_polygons:
                        pixel_poly = [(int(x * width * tile_size), int(y * height * tile_size)) for x, y in polygon]
                        shadow_intensity = int(self.darkness_opacity * 255)
                        draw.polygon(pixel_poly, fill=shadow_intensity)
                    
                    if self.darkness_feather > 0:
                        shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=self.darkness_feather))
                    
                    # Erstelle multiply_mask
                    import numpy as np
                    shadow_array = np.array(shadow_mask, dtype=np.float32)
                    multiply_array = 255 - (shadow_array * (1.0 - self.ambient_intensity))
                    multiply_array = np.clip(multiply_array, int(self.ambient_intensity * 255), 255).astype(np.uint8)
                    multiply_mask = Image.fromarray(multiply_array)
                    
                    multiply_rgb = Image.merge('RGB', [multiply_mask, multiply_mask, multiply_mask])
                    
                    # Polygon-Alpha-Maske
                    polygon_alpha = Image.new('L', (img_width, img_height), 0)
                    draw_alpha = ImageDraw.Draw(polygon_alpha)
                    for polygon in self.darkness_polygons:
                        pixel_poly = [(int(x * width * tile_size), int(y * height * tile_size)) for x, y in polygon]
                        draw_alpha.polygon(pixel_poly, fill=255)
                    
                    multiply_layer = multiply_rgb.convert('RGBA')
                    multiply_layer.putalpha(polygon_alpha)
                    
                    # Kein Licht-Layer, nur multiply_layer
                    return multiply_layer
                else:
                    return Image.new('RGBA', (width * tile_size, height * tile_size), (255, 255, 255, 0))
            else:
                # Nachtszene ohne Lichter = ambient darkness
                img_width = width * tile_size
                img_height = height * tile_size
                ambient = int(self.ambient_intensity * 255)
                darkness = Image.new('RGB', (img_width, img_height), (ambient, ambient, ambient))
                return darkness.convert('RGBA')
        
        # Wenn enabled, aber keine Lichter, dann Tagesmodus mit Polygonen
        if not self.lights:
            if self.lighting_mode == "day" and self.darkness_polygons:
                # Gleicher Code wie oben
                img_width = width * tile_size
                img_height = height * tile_size
                
                shadow_mask = Image.new('L', (img_width, img_height), 0)
                draw = ImageDraw.Draw(shadow_mask)
                
                for polygon in self.darkness_polygons:
                    pixel_poly = [(int(x * width * tile_size), int(y * height * tile_size)) for x, y in polygon]
                    shadow_intensity = int(self.darkness_opacity * 255)
                    draw.polygon(pixel_poly, fill=shadow_intensity)
                
                if self.darkness_feather > 0:
                    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=self.darkness_feather))
                
                import numpy as np
                shadow_array = np.array(shadow_mask, dtype=np.float32)
                multiply_array = 255 - (shadow_array * (1.0 - self.ambient_intensity))
                multiply_array = np.clip(multiply_array, int(self.ambient_intensity * 255), 255).astype(np.uint8)
                multiply_mask = Image.fromarray(multiply_array)
                
                multiply_rgb = Image.merge('RGB', [multiply_mask, multiply_mask, multiply_mask])
                
                polygon_alpha = Image.new('L', (img_width, img_height), 0)
                draw_alpha = ImageDraw.Draw(polygon_alpha)
                for polygon in self.darkness_polygons:
                    pixel_poly = [(int(x * width * tile_size), int(y * height * tile_size)) for x, y in polygon]
                    draw_alpha.polygon(pixel_poly, fill=255)
                
                multiply_layer = multiply_rgb.convert('RGBA')
                multiply_layer.putalpha(polygon_alpha)
                
                return multiply_layer
            elif self.lighting_mode == "day":
                return Image.new('RGBA', (width * tile_size, height * tile_size), (255, 255, 255, 0))
            else:
                img_width = width * tile_size
                img_height = height * tile_size
                ambient = int(self.ambient_intensity * 255)
                darkness = Image.new('RGB', (img_width, img_height), (ambient, ambient, ambient))
                return darkness.convert('RGBA')
        


        # GPU-optimiertes Licht-Layer mit numpy und OpenCV (nur für sichtbaren Bereich)
        import numpy as np
        import cv2


        # Multi-Threading für Lichtquellen
        import concurrent.futures
        from noise import pnoise2


        def compute_light_mask(light):
            # Noch niedrigere Auflösung für schwache PCs
            scale_factor = 0.25
            small_height = int(img_height * scale_factor)
            small_width = int(img_width * scale_factor)

            cx = int((light.x - min_x) * tile_size * scale_factor + tile_size * scale_factor / 2)
            cy = int((light.y - min_y) * tile_size * scale_factor + tile_size * scale_factor / 2)
            final_radius_scale = radius_scale * self.global_radius_scale
            radius_px = int(light.radius * tile_size * final_radius_scale * scale_factor)
            current_intensity = light.get_current_intensity(time_offset)

            y_grid, x_grid = np.ogrid[:small_height, :small_width]
            dist_from_center = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
            
            # Extended radius for smooth falloff
            extended_radius_px = radius_px * 1.5
            mask = dist_from_center <= extended_radius_px  # Allow falloff beyond nominal radius
            
            dist_norm = np.clip(dist_from_center / radius_px, 0, 1)

            # Nur 1 Noise-Layer für Speed
            from noise import pnoise2
            noise_scale = 0.10
            noise_strength = 0.12
            nx = (x_grid - cx) * noise_scale
            ny = (y_grid - cy) * noise_scale
            nx_grid, ny_grid = np.meshgrid(nx, ny)
            noise_map = np.vectorize(pnoise2)(nx_grid, ny_grid, 1)

            # Enhanced smooth falloff: combine inverse square with gaussian
            inv_square = 1.0 / (1.0 + (dist_norm ** light.falloff_exponent) * 1.5)
            gaussian = np.exp(-(dist_norm ** 2) * 2.0)
            falloff = inv_square * 0.6 + gaussian * 0.4
            
            # For distances beyond the nominal radius, apply additional fade
            beyond_radius = dist_from_center > radius_px
            if np.any(beyond_radius):
                beyond_radius_factor = (extended_radius_px - dist_from_center) / (extended_radius_px - radius_px)
                beyond_radius_factor = np.maximum(beyond_radius_factor, 0.0)
                # Exponential fade for very smooth edge
                extra_fade = np.exp(-np.power(1.0 - beyond_radius_factor, 2.0) * 3.0)
                falloff = np.where(beyond_radius, falloff * extra_fade, falloff)
            
            falloff = falloff * (1.0 + noise_map * noise_strength)
            intensity = falloff * current_intensity * mask

            # Nur ein Blur-Pass
            import cv2
            intensity_blur = cv2.GaussianBlur(intensity.astype(np.float32), (7, 7), 0)

            if light.light_type in ["torch", "fire", "campfire"]:
                r = np.where(dist_norm < 0.15, 255,
                    np.where(dist_norm < 0.4, 255,
                        np.where(dist_norm < 0.7, 255 - dist_norm * 50, 200 - dist_norm * 50)))
                g = np.where(dist_norm < 0.15, 250,
                    np.where(dist_norm < 0.4, 220 - dist_norm * 100,
                        np.where(dist_norm < 0.7, 140 - dist_norm * 60, 80 - dist_norm * 40)))
                b = np.where(dist_norm < 0.15, 230,
                    np.where(dist_norm < 0.4, 150 - dist_norm * 200,
                        np.where(dist_norm < 0.7, 50 - dist_norm * 30, 20)))
            elif light.light_type == "candle":
                r = np.full_like(dist_norm, 255)
                g = 230 - dist_norm * 30
                b = 180 - dist_norm * 80
            elif light.light_type == "magic":
                hue_shift = math.sin(time_offset * 2.0) * 0.2
                r = (180 + hue_shift * 40) * (1.0 - dist_norm * 0.5)
                g = (120 + hue_shift * 30) * (1.0 - dist_norm * 0.5)
                b = (255 + hue_shift * 20) * (1.0 - dist_norm * 0.3)
            elif light.light_type == "window":
                r = 220 - dist_norm * 20
                g = 235 - dist_norm * 35
                b = np.full_like(dist_norm, 255)
            elif light.light_type == "moonlight":
                r = 180 - dist_norm * 60
                g = 200 - dist_norm * 50
                b = 235 - dist_norm * 35
            else:
                bright = 255 * (1.0 - dist_norm * 0.3)
                r = g = b = bright

            light_mask = np.zeros((small_height, small_width, 3), dtype=np.float32)
            light_mask[..., 0] = r * intensity_blur
            light_mask[..., 1] = g * intensity_blur
            light_mask[..., 2] = b * intensity_blur

            light_mask_up = cv2.resize(light_mask, (img_width, img_height), interpolation=cv2.INTER_CUBIC)
            return light_mask_up

        # Maximal 3 Lichtquellen pro Frame (wichtigste zuerst)
        # Alle Lichtquellen pro Frame, aber mit minimaler Auflösung/Effekten
        used_lights = self.lights

        light_layer_np = np.zeros((img_height, img_width, 3), dtype=np.float32)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(compute_light_mask, used_lights))
        for mask in results:
            light_layer_np += mask

        light_layer_np = np.clip(light_layer_np, 0, 255).astype(np.uint8)

        # REDUZIERTE BLUR-INTENSITÄT für Speed
        # Blur-Intensität aus maximalem Licht-Radius im Bereich
        if self.lights:
            max_radius = max([light.radius for light in self.lights])
        else:
            max_radius = 5
        blur_strength = max(int(tile_size * max_radius * 0.7), 7)
        light_layer_np = cv2.GaussianBlur(light_layer_np, (blur_strength|1, blur_strength|1), 0)
        light_layer_np = cv2.GaussianBlur(light_layer_np, (max(3, blur_strength//2)|1, max(3, blur_strength//2)|1), 0)

        light_layer = Image.fromarray(light_layer_np, mode='RGB')

        # Offset für Rückgabe (MapEditor muss Overlay an richtiger Stelle platzieren)
        self._render_offset = (offset_x, offset_y)
        

        # Addiere Ambient Light als numpy-Array für Performance
        if self.ambient_intensity > 0:
            ambient = int(self.ambient_intensity * 255)
            ambient_np = np.full((img_height, img_width, 3), ambient, dtype=np.uint8)
            light_layer_np = np.maximum(np.array(light_layer), ambient_np)
            light_layer = Image.fromarray(light_layer_np, mode='RGB')
        
        # TAG/NACHT-MODI: Unterschiedliche Rendering-Strategien
        if self.lighting_mode == "day":
            # ════════════════════════════════════════════════════════════
            # TAGESMODUS: Physikalisch korrekte Schatten & Beleuchtung
            # ════════════════════════════════════════════════════════════
            # Die Map-Texturen bleiben IMMER sichtbar!
            # Dunkelheit = multiplikative Verdunkelung (wie echte Schatten)
            # Licht = additive Aufhellung der dunklen Bereiche
            
            if not self.darkness_polygons:
                # KEINE Dunkel-Bereiche definiert = NUR Lichtquellen als Highlights
                # Komplett transparent, keine Dunkelheit!
                light_rgba = light_layer.convert('RGBA')
                # Mache Lichtquellen sichtbar aber nicht zu dominant
                alpha = light_layer.convert('L')
                # Reduziere Alpha für subtileren Effekt im Tag-Modus
                alpha = alpha.point(lambda p: int(p * 0.3))  # 30% Intensität
                light_rgba.putalpha(alpha)
                return light_rgba
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 1: Erstelle Shadow-Mask (Schatten-Intensität pro Pixel)
            # ════════════════════════════════════════════════════════════
            # Diese Maske definiert wo es dunkel ist (0=hell, 255=dunkel)
            shadow_mask = Image.new('L', (img_width, img_height), 0)  # 0 = keine Schatten
            draw = ImageDraw.Draw(shadow_mask)
            
            # Zeichne Dunkelheits-Polygone als Schatten-Bereiche
            for polygon in self.darkness_polygons:
                # Polygone sind in relativen Koordinaten (0-1) gespeichert, konvertiere zu Pixeln
                pixel_poly = [(int(x * width * tile_size), int(y * height * tile_size)) for x, y in polygon]
                print(f"DEBUG: polygon {polygon} -> pixel_poly {pixel_poly} (converted from relative to pixels)")
                # Basis-Schatten-Intensität (nie 100% schwarz wegen Ambient)
                # darkness_opacity = 0.85 → 85% dunkel → Pixel-Wert 217 (von 255)
                shadow_intensity = int(self.darkness_opacity * 255)
                draw.polygon(pixel_poly, fill=shadow_intensity)
            
            # ════════════════════════════════════════════════════════════
            # FEATHERING: Weiche Kanten durch Gaussian Blur
            # ════════════════════════════════════════════════════════════
            if self.darkness_feather > 0:
                shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=self.darkness_feather))
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 2: Licht reduziert Schatten (physikalisch korrekt)
            # ════════════════════════════════════════════════════════════
            # Konvertiere Licht zu Helligkeit (Grayscale)
            light_brightness = light_layer.convert('L')
            
            # Licht subtrahiert von Schatten: Wo Licht ist, weniger Schatten
            # ImageChops.subtract(a, b) = max(0, a - b)
            final_shadow_mask = ImageChops.subtract(shadow_mask, light_brightness)
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 3: Erstelle MULTIPLICATIVE Darkening Layer
            # ════════════════════════════════════════════════════════════
            # Dieser Layer wird MULTIPLIZIERT mit der Map (nicht darübergelegt!)
            # Wert 255 = 100% hell (keine Veränderung)
            # Wert 128 = 50% dunkel
            # Wert 0 = 100% dunkel (schwarz)
            
            # Invertiere Schatten-Maske: 0→255 (dunkel→hell), 255→0 (hell→dunkel)
            # Dann skalieren mit Ambient-Minimum (nie komplett schwarz)
            import numpy as np
            shadow_array = np.array(final_shadow_mask, dtype=np.float32)
            
            # Invertiere und normalisiere
            # shadow_mask: 0=kein Schatten, 255=maximaler Schatten
            # multiply_mask: 255=keine Verdunkelung, 0=maximale Verdunkelung
            # ABER: minimum = ambient_intensity (z.B. 0.2 = 20% Helligkeit minimum)
            ambient_min = int(self.ambient_intensity * 255)  # Minimale Helligkeit (Streulicht)
            
            # Formel: multiply = (255 - shadow) * (1 - ambient) + ambient * 255
            # Oder einfacher: multiply = 255 - (shadow * (1 - ambient))
            multiply_array = 255 - (shadow_array * (1.0 - self.ambient_intensity))
            multiply_array = np.clip(multiply_array, ambient_min, 255).astype(np.uint8)
            
            multiply_mask = Image.fromarray(multiply_array)
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 4: Erstelle RGBA Multiply-Layer
            # ════════════════════════════════════════════════════════════
            # Wir brauchen einen Layer der die Map MULTIPLIZIERT (verdunkelt)
            # Dies wird über den Blend-Modus "multiply" erreicht
            
            # PROBLEM: PIL alpha_composite unterstützt kein "multiply" direkt
            # LÖSUNG: Wir nutzen einen Trick mit ImageChops.multiply
            # Aber wir returnen einen Layer den der Projector anders verarbeiten muss!
            
            # Erstelle RGB Layer für Multiplikation (wird außerhalb angewandt)
            # Format: RGB-Werte = Multiplikations-Faktor (0=schwarz, 255=keine Änderung)
            multiply_layer = Image.merge('RGB', [multiply_mask, multiply_mask, multiply_mask])
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 5: Füge farbiges Licht additiv hinzu
            # ════════════════════════════════════════════════════════════
            # Das Licht wird NACH der Multiplikation additiv aufgehellt
            # Nur im Polygon-Bereich sichtbar (sonst würde es die ganze Map aufhellen)
            
            # Erstelle Polygon-Maske (wo sind die Darkness-Bereiche?)
            polygon_mask = Image.new('L', (img_width, img_height), 0)
            draw_poly = ImageDraw.Draw(polygon_mask)
            for polygon in self.darkness_polygons:
                pixel_poly = [(int(x - offset_x), int(y - offset_y)) for x, y in polygon]
                draw_poly.polygon(pixel_poly, fill=255)
            
            # Clamp Licht auf Polygon-Bereich
            light_rgba = light_layer.convert('RGBA')
            light_alpha_original = light_rgba.split()[3]
            
            # Kombiniere Original-Licht-Alpha mit Polygon-Maske
            light_alpha_clamped = ImageChops.multiply(
                light_alpha_original.convert('RGB'),
                Image.merge('RGB', [polygon_mask]*3)
            ).convert('L')
            
            light_rgba.putalpha(light_alpha_clamped)
            
            # ════════════════════════════════════════════════════════════
            # RETURN: Spezielles Format für Projector
            # ════════════════════════════════════════════════════════════
            # Wir returnen ein Dict mit beiden Layern:
            # - "multiply": RGB Layer zum Multiplizieren (Schatten)
            # - "add": RGBA Layer zum Addieren (Licht)
            # 
            # ABER: render_lighting() muss Image returnen, nicht Dict!
            # LÖSUNG: Wir encoden beide Infos in einem speziellen RGBA Image
            # 
            # ALTERNATIVE: Wir passen den Projector an um multiply korrekt zu handlen
            # Für jetzt: Return RGBA mit custom Handling im Projector
            
            # Erstelle finales RGBA Image:
            # - RGB Channels: Multiply-Faktor (wird für Multiplikation genutzt)
            # - Alpha Channel: Kodiert dass dies ein Multiply-Layer ist (255=multiply mode)
            
            # ABER das ist zu komplex. Bessere Lösung:
            # Return ein Layer der im Projector mit MULTIPLY statt ALPHA_COMPOSITE verarbeitet wird
            
            # EINFACHSTE LÖSUNG: Store Flag in LightingEngine und ändere Projector
            # Für jetzt: Composite multiply + light direkt hier
            
            # ════════════════════════════════════════════════════════════
            # FINALE COMPOSITING mit echtem MULTIPLY-BLEND
            # ════════════════════════════════════════════════════════════
            # PROBLEM: PIL alpha_composite kann kein Multiply!
            # LÖSUNG: Wir returnen ein spezielles Format, das der Projector
            #         mit ImageChops.multiply() verarbeiten kann
            
            # Erstelle einen RGBA Layer mit spezieller Bedeutung:
            # - RGB: Multiply-Faktoren (255 = keine Änderung, 0 = schwarz)
            # - Alpha: Wo der Effekt angewandt wird (Polygon-Bereiche)
            
            # SCHRITT 1: Erstelle Multiply-RGB Layer
            # multiply_mask enthält bereits die richtigen Werte (0-255)
            multiply_rgb = Image.merge('RGB', [multiply_mask, multiply_mask, multiply_mask])
            
            # SCHRITT 2: Erstelle Alpha-Maske (wo sind die Polygone?)
            polygon_alpha = Image.new('L', (img_width, img_height), 0)
            draw_alpha = ImageDraw.Draw(polygon_alpha)
            for polygon in self.darkness_polygons:
                pixel_poly = [(int(x * width * tile_size), int(y * height * tile_size)) for x, y in polygon]
                draw_alpha.polygon(pixel_poly, fill=255)
            
            # SCHRITT 3: Kombiniere zu RGBA
            # Dieser Layer enthält die Multiply-Faktoren und wird vom Projector
            # mit ImageChops.multiply() auf die Map angewandt
            multiply_layer = multiply_rgb.convert('RGBA')
            multiply_layer.putalpha(polygon_alpha)
            
            # RETURN: Multiply-Layer (Licht wird separat behandelt)
            return multiply_layer
            
        else:
            # NACHTMODUS: Nur additive Lichtquellen, KEIN Darkness-Overlay
            # Die Map bleibt sichtbar, nur Lichtquellen werden hinzugefügt
            light_rgba = light_layer.convert('RGBA')
            return light_rgba
    
    def update_animation(self, delta_time: float = 0.016):
        """
        Update Animation Timer (für Flicker)
        Args:
            delta_time: Zeit seit letztem Frame in Sekunden (default: ~60 FPS)
        """
        self.time_offset += delta_time
        
    def generate_gpu_texture(self, material_id, size=64, animation_frame=0, river_direction="right"):
        """
        GPU-beschleunigte Textur-Generierung
        Fallback auf CPU wenn GPU nicht verfügbar
        """
        cache_key = f"gpu_{material_id}_{size}_{animation_frame}_{river_direction}"
        
        # Cache prüfen
        if cache_key in self.gpu_texture_cache:
            return self.gpu_texture_cache[cache_key]
        
        # GPU-generierte Texturen
        gpu_textures = {
            "grass": lambda: self._generate_gpu_grass_texture(size, animation_frame),
            "water": lambda: self._generate_gpu_water_texture(size, animation_frame, river_direction),
        }
        
        if material_id in gpu_textures:
            try:
                gpu_texture = gpu_textures[material_id]()
                pil_image = gpu_texture.to_pil_image()
                
                # Cache speichern
                self.gpu_texture_cache[cache_key] = pil_image
                
                # Cache-Größe begrenzen
                if len(self.gpu_texture_cache) > 50:
                    oldest_key = next(iter(self.gpu_texture_cache))
                    del self.gpu_texture_cache[oldest_key]
                
                return pil_image
            except Exception as e:
                print(f"⚠️ GPU-Textur-Generierung fehlgeschlagen für {material_id}: {e}")
        
        # Fallback auf CPU
        return None
    
    def _generate_gpu_grass_texture(self, size, frame):
        """GPU-Gras-Textur"""
        if hasattr(self, 'gpu_renderer') and self.gpu_renderer:
            return self.gpu_renderer.generate_grass_texture_gpu(size, size, frame)
        raise RuntimeError("GPU Renderer nicht verfügbar")
    
    def _generate_gpu_water_texture(self, size, frame, direction):
        """GPU-Wasser-Textur"""
        if hasattr(self, 'gpu_renderer') and self.gpu_renderer:
            # Direction mapping
            direction_map = {
                "right": 0, "left": 2, "down": 4, "up": 6,
                "down-right": 3, "down-left": 5, "up-right": 7, "up-left": 1
            }
            dir_code = direction_map.get(direction, 0)
            return self.gpu_renderer.generate_water_texture_gpu(size, size, frame, dir_code)
        raise RuntimeError("GPU Renderer nicht verfügbar")
        
    def to_dict(self) -> Dict:
        """Export als Dictionary"""
        return {
            "lights": [light.to_dict() for light in self.lights],
            "ambient_color": self.ambient_color,
            "ambient_intensity": self.ambient_intensity,
            "enabled": self.enabled,
            "lighting_mode": self.lighting_mode,
            "darkness_opacity": self.darkness_opacity,
            "darkness_polygons": self.darkness_polygons
        }
        
    def from_dict(self, data: Dict):
        """Import aus Dictionary"""
        self.lights = [LightSource.from_dict(l) for l in data.get("lights", [])]
        self.ambient_color = tuple(data.get("ambient_color", [30, 30, 40]))
        self.ambient_intensity = data.get("ambient_intensity", 0.2)
        self.enabled = data.get("enabled", True)
        self.lighting_mode = data.get("lighting_mode", "night")
        self.darkness_opacity = data.get("darkness_opacity", 0.85)
        self.darkness_polygons = data.get("darkness_polygons", [])


class GPUAcceleratedLightingEngine(LightingEngine):
    """GPU-beschleunigte Version des LightingEngine mit OpenCL"""
    
    def __init__(self):
        super().__init__()
        self.gpu_renderer = None
        self._init_gpu()
    
    def _init_gpu(self):
        """Initialisiere GPU-Renderer"""
        if not GPU_AVAILABLE:
            print("⚠️ GPU nicht verfügbar - verwende CPU-Fallback")
            return
        
        try:
            self.gpu_renderer = GPURenderer()
            # Mirror key attributes so other code can access them consistently
            self.gpu_context = self.gpu_renderer.context
            self.gpu_queue = self.gpu_renderer.queue
            self.gpu_program = self.gpu_renderer.program
            print("✅ Vollständige GPU-Rendering-Pipeline initialisiert")
            
        except Exception as e:
            print(f"⚠️ GPU-Initialisierung fehlgeschlagen: {e}")
            self.gpu_renderer = None
    
    def render_lighting_gpu(self, width: int, height: int, tile_size: int, time_offset: float = 0.0, radius_scale: float = 1.0) -> Image.Image:
        """GPU-beschleunigte Licht-Rendering"""
        # Darkness polygons require CPU rendering for now
        if self.lighting_mode == "day" and self.darkness_polygons:
            print("🎯 GPU: Darkness polygons detected in day mode, using CPU fallback")
            return super().render_lighting(width, height, tile_size, time_offset, radius_scale)
        
        if not getattr(self, 'gpu_context', None) or not self.lights:
            # Fallback zur CPU-Version — call parent to avoid recursion
            print('⚠️ GPU render path not ready or no lights — use CPU fallback')
            return super().render_lighting(width, height, tile_size, time_offset, radius_scale)
        
        try:
            # Vereinfachte GPU-Version für Performance
            margin_tiles = 5
            if self.lights:
                min_x = min([l.x for l in self.lights]) - margin_tiles
                max_x = max([l.x for l in self.lights]) + margin_tiles
                min_y = min([l.y for l in self.lights]) - margin_tiles
                max_y = max([l.y for l in self.lights]) + margin_tiles
            else:
                min_x = max_x = min_y = max_y = 0
            
            img_width = max(1, (max_x - min_x + 1) * tile_size)
            img_height = max(1, (max_y - min_y + 1) * tile_size)
            
            # Guard: make sure gpu_renderer/program/queue exist and there are lights
            if not getattr(self, 'gpu_renderer', None) or not getattr(self, 'gpu_program', None):
                # Not properly initialized: fall back to CPU
                print('⚠️ GPU-Renderer intern nicht initialisiert — Fallback zu CPU')
                return super().render_lighting(width, height, tile_size, time_offset, radius_scale)

            # GPU Buffer für Gesamt-Lichtmaske (RGBA)
            final_mask = cl_array.zeros(self.gpu_queue, (img_height, img_width, 4), dtype=np.float32)
            print(f"🎯 GPU: render_lighting_gpu: creating final_mask {img_width}x{img_height}, lights={len(self.lights)}")
            
            # Für jedes Licht: GPU-Kernel ausführen
            for light in self.lights[:3]:  # Max 3 Lichter für Performance
                cx = (light.x - min_x) * tile_size + tile_size / 2
                cy = (light.y - min_y) * tile_size + tile_size / 2
                final_radius_scale = radius_scale * self.global_radius_scale
                radius_px = light.radius * tile_size * final_radius_scale
                current_intensity = light.get_current_intensity(time_offset)
                
                # Noise-Map generieren (einfache Version)
                noise_map = np.random.randn(img_height, img_width).astype(np.float32) * 0.1
                noise_gpu = cl_array.to_device(self.gpu_queue, noise_map)

                # Per-light temporary RGBA buffer
                light_mask = cl_array.zeros(self.gpu_queue, (img_height, img_width, 4), dtype=np.float32)

                # Kernel ausführen (compute_light_mask expects a float4 buffer)
                self.gpu_program.compute_light_mask(
                    self.gpu_queue, (img_width, img_height), None,
                    light_mask.data,
                    np.int32(img_width), np.int32(img_height),
                    np.float32(cx), np.float32(cy), np.float32(radius_px),
                    np.float32(light.falloff_exponent), np.float32(light.core_brightness),
                    np.float32(current_intensity), np.float32(0.12),
                    noise_gpu.data
                )

                # Akkumulieren (GPU-to-GPU Add)
                final_mask = final_mask + light_mask
                print(f"   ✔️ GPU: added light @ ({light.x},{light.y}), radius_px={radius_px}, intensity={current_intensity:.2f}")
            
            # Ergebnis zurück zur CPU holen (RGBA float32)
            rgba_np = final_mask.get()
            nonzero = np.count_nonzero(rgba_np)
            print(f"🎯 GPU: finished accumulation — buffer nonzero count: {nonzero}")
            # Falls kernel nur schrieb 1 channel intensity, expand it
            if rgba_np.ndim == 2:
                rgba_np = np.stack([rgba_np]*3 + [np.ones_like(rgba_np)], axis=2)

            # Clamp and convert to uint8
            rgba_array = np.clip(rgba_np * 255.0, 0, 255).astype(np.uint8)
            print(f"🎯 GPU: converted rgba_array -> shape {rgba_array.shape}, dtype {rgba_array.dtype}")
            
            # If we have alpha channel use RGBA, else convert to RGB
            if rgba_array.shape[2] == 4:
                light_image = Image.fromarray(rgba_array, mode='RGBA')
            else:
                light_image = Image.fromarray(rgba_array[:, :, :3], mode='RGB')
            
            # Blur für weiche Kanten (CPU, da GPU-Blur komplex wäre)
            from PIL import ImageFilter
            blur_radius = max(1, int(tile_size * 0.3))
            light_image = light_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
            # Ambient hinzufügen
            if self.ambient_intensity > 0:
                ambient = int(self.ambient_intensity * 255)
                # Create ambient image in the same mode as light_image so ImageChops works
                if light_image.mode == 'RGBA':
                    ambient_img = Image.new('RGBA', light_image.size, (ambient, ambient, ambient, 255))
                else:
                    ambient_img = Image.new('RGB', light_image.size, (ambient, ambient, ambient))
                # Ensure comparable modes
                if ambient_img.mode != light_image.mode:
                    ambient_img = ambient_img.convert(light_image.mode)
                light_image = ImageChops.lighter(light_image, ambient_img)
            
            return light_image.convert('RGBA')
            
        except Exception as e:
            print(f"⚠️ GPU-Rendering fehlgeschlagen, verwende CPU: {e}")
            return super().render_lighting(width, height, tile_size, time_offset, radius_scale)
    
    def render_lighting(self, width: int, height: int, tile_size: int, time_offset: float = 0.0, radius_scale: float = 1.0) -> Image.Image:
        """Override der CPU-Version für GPU-Beschleunigung"""
        return self.render_lighting_gpu(width, height, tile_size, time_offset, radius_scale)


# Preset Lichtquellen mit optimierten physikalischen Parametern
LIGHT_PRESETS = {
    "torch": {
        "radius": 7,  # Größerer Radius für Fackeln
        "color": (255, 180, 80),  # Wärmeres Orange
        "intensity": 1.0,  # Volle Intensität
        "flicker": True,
        "light_type": "torch"
    },
    "candle": {
        "radius": 4,  # Etwas größer für bessere Sichtbarkeit
        "color": (255, 230, 180),  # Weiches warmes Gelb
        "intensity": 0.8,
        "flicker": True,
        "light_type": "candle"
    },
    "fire": {
        "radius": 8,  # Großes Feuer
        "color": (255, 140, 40),  # Intensives Orange-Rot
        "intensity": 1.2,  # Sehr hell (erlaubt Überhellung)
        "flicker": True,
        "light_type": "fire"
    },
    "campfire": {
        "radius": 6,
        "color": (255, 160, 60),
        "intensity": 1.0,
        "flicker": True,
        "light_type": "campfire"
    },
    "window": {
        "radius": 10,  # Großer sanfter Bereich
        "color": (220, 235, 255),  # Tageslicht (leicht blau)
        "intensity": 0.7,
        "flicker": False,  # Kein Flackern bei Tageslicht
        "light_type": "window"
    },
    "magic": {
        "radius": 8,
        "color": (180, 120, 255),  # Lila/Violett für Magie
        "intensity": 1.1,
        "flicker": True,  # Pulsiert
        "light_type": "magic"
    },
    "moonlight": {
        "radius": 12,  # Sehr großer, sanfter Bereich
        "color": (180, 200, 235),  # Kühles Blau-Weiß
        "intensity": 0.5,
        "flicker": False,
        "light_type": "moonlight"
    },
    # Neue Presets
    "lantern": {
        "radius": 6,
        "color": (255, 200, 120),
        "intensity": 0.85,
        "flicker": True,
        "light_type": "torch"  # Verwendet Torch-Physik aber schwächer
    },
    "brazier": {
        "radius": 9,
        "color": (255, 150, 50),
        "intensity": 1.1,
        "flicker": True,
        "light_type": "fire"
    },
    "crystal": {
        "radius": 7,
        "color": (150, 200, 255),  # Kühles Blau
        "intensity": 0.9,
        "flicker": True,
        "light_type": "magic"
    }
}
