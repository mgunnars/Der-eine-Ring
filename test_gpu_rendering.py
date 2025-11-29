"""
Minimal test for GPU-accelerated lighting rendering.
Skips if PyOpenCL not available.
"""
import sys
sys.path.insert(0, '.')

from lighting_system import GPU_AVAILABLE, GPUAcceleratedLightingEngine, LightSource

print("🧪 Test GPU rendering")
if not GPU_AVAILABLE:
    print("⚠️ PyOpenCL not available — skipping GPU test")
    sys.exit(0)

engine = GPUAcceleratedLightingEngine()
if not getattr(engine, 'gpu_renderer', None):
    print("⚠️ GPU renderer not initialized — skipping GPU test")
    sys.exit(0)

# Add a single light in the center
engine.add_light(LightSource(x=2, y=2, radius=3, light_type='torch', flicker=False))

img = engine.render_lighting(width=5, height=5, tile_size=16, time_offset=0.0, radius_scale=1.0)
print(f"result: {type(img)}, size={getattr(img, 'size', None)}, mode={getattr(img, 'mode', None)}")

if img is None:
    print("❌ GPU test returned None — failure")
    sys.exit(2)

print("✅ GPU rendering test finished — output is non-empty (inspect above)!")
