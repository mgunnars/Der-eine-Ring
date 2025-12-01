#!/usr/bin/env python3
"""Test GPU acceleration for lighting system"""

from lighting_system import GPUAcceleratedLightingEngine, LightingEngine, GPU_AVAILABLE, LightSource
import time

print("=" * 60)
print("GPU ACCELERATION TEST")
print("=" * 60)

print(f"\n1. GPU verfügbar (PyOpenCL): {GPU_AVAILABLE}")

print("\n2. Teste GPUAcceleratedLightingEngine...")
try:
    engine = GPUAcceleratedLightingEngine()
    print(f"   ✅ Engine erstellt")
    print(f"   - GPU Renderer: {engine.gpu_renderer is not None}")
    print(f"   - GPU Context: {getattr(engine, 'gpu_context', None) is not None}")
    
    if engine.gpu_renderer:
        print("\n3. GPU-Renderer aktiv! Benchmark...")
        
        # Füge mehrere Test-Lichter hinzu für realistischen Test
        for i in range(10):
            light = LightSource(x=5+i*3, y=5+i*2, radius=4, 
                              color=(255, 200, 100), intensity=0.8)
            engine.add_light(light)
        
        print(f"   Anzahl Lichter: {len(engine.lights)}")
        
        # Größeres Rendering für realistischen GPU-Vorteil
        test_width, test_height = 1920, 1080
        tile_size = 32
        
        # Warmup GPU (erste Ausführung ist langsamer)
        _ = engine.render_lighting_gpu(test_width, test_height, tile_size)
        
        # GPU Benchmark
        iterations = 5
        gpu_times = []
        for _ in range(iterations):
            start = time.time()
            result = engine.render_lighting_gpu(test_width, test_height, tile_size)
            gpu_times.append(time.time() - start)
        
        gpu_avg = sum(gpu_times) / len(gpu_times)
        print(f"\n   📊 GPU-Rendering ({iterations} iterations):")
        print(f"      Durchschnitt: {gpu_avg*1000:.2f}ms")
        print(f"      Min/Max: {min(gpu_times)*1000:.2f}ms / {max(gpu_times)*1000:.2f}ms")
        print(f"      Ergebnis: {result.size if result else 'None'}")
        
        # CPU Benchmark zum Vergleich
        cpu_engine = LightingEngine()
        for light in engine.lights:
            cpu_engine.add_light(light)
        
        cpu_times = []
        for _ in range(iterations):
            start = time.time()
            cpu_result = cpu_engine.render_lighting(test_width, test_height, tile_size)
            cpu_times.append(time.time() - start)
        
        cpu_avg = sum(cpu_times) / len(cpu_times)
        print(f"\n   📊 CPU-Rendering ({iterations} iterations):")
        print(f"      Durchschnitt: {cpu_avg*1000:.2f}ms")
        print(f"      Min/Max: {min(cpu_times)*1000:.2f}ms / {max(cpu_times)*1000:.2f}ms")
        
        speedup = cpu_avg / gpu_avg
        print(f"\n   🚀 GPU Speedup: {speedup:.2f}x")
        if speedup > 1:
            print(f"   ✅ GPU ist {speedup:.1f}x schneller!")
        else:
            print(f"   ⚠️ GPU ist {1/speedup:.1f}x langsamer (Overhead bei kleinen Szenen)")
        
    else:
        print("\n⚠️ GPU-Renderer nicht aktiv - CPU Fallback wird verwendet")
        
except Exception as e:
    print(f"   ❌ Fehler: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
