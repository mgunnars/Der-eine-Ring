"""
Test that ProjectorWindow reuses the same GPURenderer as its internal lighting engine.
This test requires a display (Tkinter) and PyOpenCL — will skip gracefully otherwise.
"""
import sys
sys.path.insert(0, '.')

import time
from lighting_system import GPU_AVAILABLE

print('🧪 Test ProjectorWindow reusing GPURenderer')
if not GPU_AVAILABLE:
    print('⚠️ PyOpenCL not available — skipping projector GPU test')
    sys.exit(0)

try:
    import tkinter as tk
    from projector_window import ProjectorWindow

    root = tk.Tk()
    root.withdraw()  # hide main window

    proj = ProjectorWindow(root, map_data={'width':10, 'height':10})

    # Wait briefly for initialization
    time.sleep(0.5)

    le = getattr(proj, 'lighting_engine', None)
    pr = getattr(proj, 'gpu_renderer', None)

    if not le:
        print('❌ Projector did not create lighting_engine')
        proj.destroy(); root.destroy(); sys.exit(2)

    if not le.gpu_renderer:
        print('⚠️ lighting_engine.gpu_renderer not present')

    print('lighting_engine.gpu_renderer:', id(getattr(le, 'gpu_renderer', None)))
    print('projector.gpu_renderer:', id(pr))

    if getattr(le, 'gpu_renderer', None) is pr and pr is not None:
        print('✅ GPURenderer is shared between lighting_engine and projector')
        success = True
    else:
        print('❌ GPURenderer is NOT shared')
        success = False

    proj.destroy()
    root.destroy()

    if not success:
        sys.exit(3)

except Exception as e:
    print('❌ Test failed:', e)
    sys.exit(4)
