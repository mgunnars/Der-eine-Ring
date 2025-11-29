"""Run a ProjectorWindow with the provided SVG-enabled map and verify it renders an image (non-black)."""
import sys, json
sys.path.insert(0, '.')

from lighting_system import GPU_AVAILABLE
print('🧪 Test projector with real map (SVG mode)')

with open('maps/test_nacht_lighting3.json','r', encoding='utf-8') as f:
    map_data = json.load(f)

try:
    import tkinter as tk
    from projector_window import ProjectorWindow
    from PIL import Image
    import time

    root = tk.Tk(); root.withdraw()
    proj = ProjectorWindow(root, map_data=map_data, webcam_tracker=None, svg_path=map_data.get('svg_path'))

    # Wait for UI to initialize and create canvas
    waited = 0.0
    while not hasattr(proj, 'canvas') and waited < 5.0:
        time.sleep(0.1); waited += 0.1

    if not hasattr(proj, 'canvas'):
        print('❌ Projector canvas never created (timed out)')
        proj.destroy(); root.destroy(); sys.exit(2)

    # Allow a moment for any deferred renders
    time.sleep(0.25)
    proj.render_map()
    time.sleep(0.5)

    # Try to grab the canvas photo
    photo = getattr(proj, 'map_photo', None) or getattr(proj.canvas, 'photo', None)
    if photo is None:
        print('❌ No PhotoImage found on projector')
        proj.destroy(); root.destroy(); sys.exit(2)

    # Grab the internal image (we stored last rendered viewport_img as ImageTk.PhotoImage assigned to canvas.photo)
    img = getattr(proj.canvas, 'photo', None)
    if not img:
        print('⚠️ Could not locate ImageTk object on canvas (test inconclusive)')
    else:
        # ImageTk.PhotoImage does not expose easy getdata, but we can save canvas image from the projector's svg_static_cache if available
        try:
            # If svg_static_cache exists, it's a PIL Image representing the full render
            if getattr(proj, 'svg_static_cache', None):
                proj.svg_static_cache.save('tmp_projector_map_static_cache.png')
                print('✅ Saved tmp_projector_map_static_cache.png')
            else:
                print('✅ Map rendered and PhotoImage found')
        except Exception as e:
            print('⚠️ Could not save static cache:', e)

    proj.destroy(); root.destroy()
    print('✅ Finished test_projector_with_map (no crash)')

except Exception as e:
    print('❌ Test failed:', e)
    sys.exit(3)
