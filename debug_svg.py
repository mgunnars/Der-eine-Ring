import xml.etree.ElementTree as ET

svg_path = 'maps/taverne_real_svg.svg'
tree = ET.parse(svg_path)
root = tree.getroot()

print(f"SVG Root: {root.tag}")
print(f"SVG Width: {root.get('width')}")
print(f"SVG Height: {root.get('height')}")

# Count elements
images = []
rects = []
paths = []
groups = []

for elem in root.iter():
    tag = elem.tag.split('}')[-1]
    if tag == 'image':
        images.append(elem)
    elif tag == 'rect':
        rects.append(elem)
    elif tag == 'path':
        paths.append(elem)
    elif tag == 'g':
        groups.append(elem)

print(f"\nElements found:")
print(f"  - <image> elements: {len(images)}")
print(f"  - <rect> elements: {len(rects)}")
print(f"  - <path> elements: {len(paths)}")
print(f"  - <g> (groups): {len(groups)}")

print(f"\nFirst 3 image elements:")
for img in images[:3]:
    x = img.get('x', 'N/A')
    y = img.get('y', 'N/A')
    w = img.get('width', 'N/A')
    h = img.get('height', 'N/A')
    elem_id = img.get('id', 'no-id')[:50]
    href = img.get('{http://www.w3.org/1999/xlink}href', img.get('href', ''))
    href_preview = href[:60] if href else 'N/A'
    print(f"  Image: x={x}, y={y}, w={w}, h={h}")
    print(f"    id={elem_id}")
    print(f"    href={href_preview}...")
