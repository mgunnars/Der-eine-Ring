"""
Überprüft den Inhalt der SVG-Datei
"""
import xml.etree.ElementTree as ET

svg_path = 'maps/beispiel_mittelerde.svg'

print("=" * 60)
print("SVG-INHALT ÜBERPRÜFUNG")
print("=" * 60)

try:
    root = ET.parse(svg_path).getroot()
    
    # SVG Dimensionen
    width = root.get('width')
    height = root.get('height')
    print(f"\n📐 SVG Dimensionen: {width} x {height}")
    
    # Bilder suchen
    namespaces = {
        'svg': 'http://www.w3.org/2000/svg',
        'xlink': 'http://www.w3.org/1999/xlink'
    }
    
    images = root.findall('.//{http://www.w3.org/2000/svg}image')
    print(f"\n🖼️ Gefundene Bilder: {len(images)}")
    
    if len(images) > 0:
        # Erstes Bild analysieren
        first_img = images[0]
        x = first_img.get('x')
        y = first_img.get('y')
        w = first_img.get('width')
        h = first_img.get('height')
        href = first_img.get('{http://www.w3.org/1999/xlink}href')
        
        print(f"\n📍 Erstes Bild:")
        print(f"   Position: ({x}, {y})")
        print(f"   Größe: {w} x {h}")
        
        if href:
            if href.startswith('data:image/'):
                # Base64 Bild
                header = href.split(',')[0]
                data_part = href.split(',')[1] if ',' in href else ''
                print(f"   Format: {header}")
                print(f"   Base64-Daten: {len(data_part)} Zeichen")
                print(f"   Vorschau: {data_part[:50]}...")
                
                # Teste Dekodierung
                try:
                    import base64
                    img_data = base64.b64decode(data_part[:100])  # Nur erste 100 zum Test
                    print(f"   ✅ Base64 dekodierbar")
                except Exception as e:
                    print(f"   ❌ Base64 Fehler: {e}")
            else:
                print(f"   href: {href}")
        else:
            print(f"   ⚠️ KEIN href Attribut gefunden!")
            print(f"   Verfügbare Attribute: {list(first_img.attrib.keys())}")
    else:
        print("\n⚠️ KEINE Bilder gefunden!")
        print("\nGruppen durchsuchen:")
        groups = root.findall('.//{http://www.w3.org/2000/svg}g')
        print(f"   Gefundene Gruppen: {len(groups)}")
        for i, g in enumerate(groups[:5]):
            gid = g.get('id')
            print(f"   Gruppe {i}: id={gid}")
    
    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n❌ Fehler: {e}")
    import traceback
    traceback.print_exc()
