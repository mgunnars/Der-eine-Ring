"""Sanity test: use ProjectorWindow.gpu_composite_rendering to composite a map + lighting overlay in multiply and alpha modes."""
import sys
sys.path.insert(0, '.')

from lighting_system import GPU_AVAILABLE
print('🧪 Test projector GPU visual')
if not GPU_AVAILABLE:
    print('⚠️ PyOpenCL not available — skipping')
    sys.exit(0)

try:
    from projector_window import ProjectorWindow
    import tkinter as tk
    from PIL import Image, ImageDraw
    import numpy as np
    import time

    root = tk.Tk(); root.withdraw()
    proj = ProjectorWindow(root, map_data={'width':8,'height':8})
    # create a simple map image (checkerboard) and lighting overlay (dark polygon with alpha)
    map_img = Image.new('RGBA', (256,256), (180,180,220,255))
    draw = ImageDraw.Draw(map_img)
    for y in range(8):
        for x in range(8):
            if (x+y) % 2 == 0:
                draw.rectangle((x*32,y*32,(x+1)*32,(y+1)*32), fill=(200,200,240,255))
            else:
                draw.rectangle((x*32,y*32,(x+1)*32,(y+1)*32), fill=(120,140,180,255))

    # lighting overlay: multiply factors (darker) and alpha in a central polygon
    lighting = Image.new('RGBA', (256,256), (255,255,255,0))
    draw_l = ImageDraw.Draw(lighting)
    # dark multiply factor -> multiply RGB by 0.4 (int ~102)
    mul = Image.new('RGB', (256,256), (102,102,102))
    alpha = Image.new('L', (256,256), 0)
    draw_alpha = ImageDraw.Draw(alpha)
    draw_alpha.ellipse((64,64,192,192), fill=255)
    lighting = Image.merge('RGBA', [mul.split()[0], mul.split()[1], mul.split()[2], alpha])

    # Try multiply mode
    out_m = proj.gpu_composite_rendering(map_img, lighting, fog_enabled=False, fog_data=None, mode='multiply')
    print('multiply ->', out_m.size, out_m.mode, 'nonzero:', sum(1 for p in out_m.getdata() if p != (0,0,0,0)))
    out_m.save('tmp_proj_gpu_multiply.png')

    # Try alpha mode (lighting semi-transparent light in center)
    light2 = Image.new('RGBA', (256,256), (0,0,0,0))
    ld = ImageDraw.Draw(light2)
    ld.ellipse((96,96,160,160), fill=(255,220,150,180))
    out_a = proj.gpu_composite_rendering(map_img, light2, fog_enabled=False, fog_data=None, mode='alpha')
    print('alpha ->', out_a.size, out_a.mode, 'nonzero:', sum(1 for p in out_a.getdata() if p != (0,0,0,0)))
    out_a.save('tmp_proj_gpu_alpha.png')

    proj.destroy(); root.destroy()
    print('✅ projector GPU visual tests complete - output saved to tmp_proj_gpu_multiply.png and tmp_proj_gpu_alpha.png')

except Exception as e:
    print('❌ Test failed:', e)
    sys.exit(2)
