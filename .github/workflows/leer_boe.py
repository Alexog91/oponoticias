import urllib.request
import xml.etree.ElementTree as ET
import csv
from datetime import datetime

RSS_URL = "https://www.boe.es/rss/boe.php?s=2B"

def leer_boe_rss():
    print("🔄 Leyendo RSS del BOE...")
    print(f"URL: {RSS_URL}\n")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    req = urllib.request.Request(RSS_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        print(f"✓ Se encontraron {len(items)} publicaciones del BOE hoy\n")
        
        convocatorias = []
        
        for item in items:
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubDate_elem = item.find('pubDate')
            description_elem = item.find('description')
            
            if title_elem is not None:
                titulo = title_elem.text or 'Sin título'
                enlace = link_elem.text if link_elem is not None else 'Sin enlace'
                fecha = pubDate_elem.text if pubDate_elem is not None else 'Sin fecha'
                resumen = description_elem.text if description_elem is not None else 'Sin descripción'
                resumen = resumen[:200] if resumen else 'Sin descripción'
                
                palabras_clave = ['oposición', 'oposiciones', 'selectivo', 'convocatoria', 'plazas']
                es_oposicion = any(palabra in titulo.lower() for palabra in palabras_clave)
                
                if es_oposicion:
                    convocatoria = {
                        'fecha': fecha,
                        'titulo': titulo,
                        'enlace': enlace,
                        'resumen': resumen
                    }
                    convocatorias.append(convocatoria)
                    
                    print(f"📢 {titulo}")
                    print(f"   📅 {fecha}")
                    print(f"   🔗 {enlace}")
                    print(f"   📝 {resumen}...\n")
        
        return convocatorias
    
    except Exception as e:
        print(f"❌ Error al leer el RSS: {e}")
        return []

def guardar_en_csv(convocatorias, nombre_archivo='convocatorias.csv'):
    if not convocatorias:
        print("⚠️  No hay convocatorias para guardar.")
        return
    
    with open(nombre_archivo, 'w', newline='', encoding='utf-8') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=['fecha', 'titulo', 'enlace', 'resumen'])
        writer.writeheader()
        writer.writerows(convocatorias)
    
    print(f"✓ Se guardaron {len(convocatorias)} convocatorias en '{nombre_archivo}'")

if __name__ == "__main__":
    convocatorias = leer_boe_rss()
    
    if convocatorias:
        guardar_en_csv(convocatorias)
        print(f"\n✅ Total de convocatorias encontradas: {len(convocatorias)}")
    else:
        print("\n❌ No se encontraron convocatorias de oposiciones hoy.")
