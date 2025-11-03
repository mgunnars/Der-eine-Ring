"""
Demo: Interaktive SVG mit echten Vektoren

Zeigt die Vorteile von Vektor-SVGs:
- Farben ändern per CSS
- Animationen
- Zoom ohne Qualitätsverlust
"""

from svg_texture_vectorizer import SVGTextureVectorizer
import xml.etree.ElementTree as ET


def create_interactive_demo():
    """Erstellt eine interaktive Demo-SVG"""
    print("🎨 Erstelle interaktive Vektor-Demo...")
    
    vectorizer = SVGTextureVectorizer()
    
    # Haupt-SVG
    svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': '800',
        'height': '600',
        'viewBox': '0 0 800 600'
    })
    
    # CSS für Interaktivität
    style = ET.SubElement(svg, 'style')
    style.text = """
        /* Hover-Effekte für Tiles */
        .tile:hover {
            transform: scale(1.05);
            filter: brightness(1.2);
            cursor: pointer;
        }
        
        /* Animation für Wasser */
        @keyframes water-flow {
            0% { opacity: 0.8; }
            50% { opacity: 1.0; }
            100% { opacity: 0.8; }
        }
        
        #water-tile {
            animation: water-flow 3s ease-in-out infinite;
        }
        
        /* Farb-Themen (umschaltbar via JavaScript) */
        .theme-dark {
            filter: brightness(0.7) contrast(1.2);
        }
        
        .theme-bright {
            filter: brightness(1.3) saturate(1.5);
        }
        
        /* Tile-Stil */
        .tile {
            transition: all 0.3s ease;
        }
    """
    
    # Titel
    title = ET.SubElement(svg, 'text', {
        'x': '400',
        'y': '40',
        'text-anchor': 'middle',
        'font-size': '24',
        'font-weight': 'bold',
        'fill': '#ffffff',
        'stroke': '#000000',
        'stroke-width': '2'
    })
    title.text = "Interaktive Vektor-Demo (Hover über Tiles!)"
    
    # 2x2 Grid
    materials = ['grass', 'water', 'forest', 'village']
    tile_size = 200
    
    for i, material in enumerate(materials):
        col = i % 2
        row = i // 2
        x = 200 + col * tile_size
        y = 100 + row * tile_size
        
        # Gruppe für Tile
        tile_group = ET.SubElement(svg, 'g', {
            'class': 'tile',
            'id': f'{material}-tile',
            'transform': f'translate({x},{y})'
        })
        
        # Vektor-Textur
        texture = vectorizer.create_vector_texture(material, tile_size)
        tile_group.append(texture)
        
        # Label
        label = ET.SubElement(svg, 'text', {
            'x': str(x + tile_size // 2),
            'y': str(y + tile_size + 20),
            'text-anchor': 'middle',
            'font-size': '14',
            'fill': '#ffffff',
            'stroke': '#000000',
            'stroke-width': '1'
        })
        label.text = material.upper()
    
    # Anleitung
    instructions = [
        "✓ Zoom hinein (Ctrl+Scrollrad) - Bleibt scharf!",
        "✓ Hover über Tiles für Effekt",
        "✓ Editierbar in Inkscape/Illustrator",
        "✓ Farben änderbar via CSS"
    ]
    
    for i, instruction in enumerate(instructions):
        inst_text = ET.SubElement(svg, 'text', {
            'x': '400',
            'y': str(550 + i * 15),
            'text-anchor': 'middle',
            'font-size': '12',
            'fill': '#cccccc'
        })
        inst_text.text = instruction
    
    # SVG speichern
    tree = ET.ElementTree(svg)
    output_path = 'demo_interactive_vectors.svg'
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    print(f"✅ Demo erstellt: {output_path}")
    print()
    print("Öffne in einem Browser und:")
    print("  1. Hover über die Tiles")
    print("  2. Zoom hinein (Ctrl + Mausrad)")
    print("  3. Öffne in Inkscape und bearbeite!")


if __name__ == '__main__':
    create_interactive_demo()
