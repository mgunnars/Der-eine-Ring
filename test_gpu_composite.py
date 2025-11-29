"""Test GPURenderer alpha_composite_gpu compositing."""
import sys
sys.path.insert(0, '.')

from lighting_system import GPU_AVAILABLE, GPURenderer
from PIL import Image, ImageDraw
import numpy as np

print('🧪 Test GPU compositing')
if not GPU_AVAILABLE:
    print('⚠️ PyOpenCL not available — skipping')
    sys.exit(0)

try:
    gr = GPURenderer()
    print('🎮 GPURenderer OK')

    map_img = Image.new('RGBA', (128, 128), (20, 100, 180, 255))
    light_img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(light_img)
    draw.ellipse((32, 32, 96, 96), fill=(255, 200, 150, 200))

    gpu_map = gr.create_gpu_image(128, 128, 4)
    gpu_map.gpu_buffer.set(np.array(map_img, dtype=np.float32) / 255.0)

    gpu_light = gr.create_gpu_image(128, 128, 4)
    gpu_light.gpu_buffer.set(np.array(light_img, dtype=np.float32) / 255.0)

    res = gr.alpha_composite_gpu(gpu_map, gpu_light)
    out = res.to_pil_image()
    print('Result image:', out.size, out.mode)
    out.save('tmp_gpu_composite_test.png')
    print('Saved tmp_gpu_composite_test.png')

except Exception as e:
    print('❌ GPU compositing failed:', e)
