import urllib.request
import xml.etree.ElementTree as ET
import csv
import json
import os

RSS_URL = "https://www.boe.es/rss/boe.php?s=2B"
TELEGRAM_TOKEN = "8803259416:AAFfXoRvMXIHemcIe6a5ey69TeR632-OZFI"  # ← REEMPLAZA CON TU TOKEN
TELEGRAM_CHAT_ID = "-1003528545552"  # Tu ID del canal
CSV_FILE = "convocatorias.csv"
ENVIADAS_FILE = "convocatorias_enviadas.txt"  # Archivo para rastrear cuáles ya se enviaron

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

def guardar_en_csv(convocatorias, nombre_archivo=CSV_FILE):
    if not convocatorias:
        print("⚠️  No hay convocatorias para guardar.")
        return
    
    with open(nombre_archivo, 'w', newline='', encoding='utf-8') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=['fecha', 'titulo', 'enlace', 'resumen'])
        writer.writeheader()
        writer.writerows(convocatorias)
    
    print(f"✓ Se guardaron {len(convocatorias)} convocatorias en '{nombre_archivo}'")

def obtener_convocatorias_enviadas():
    """Lee qué convocatorias ya se han enviado a Telegram"""
    if os.path.exists(ENVIADAS_FILE):
        with open(ENVIADAS_FILE, 'r', encoding='utf-8') as f:
            return set(f.read().strip().split('\n'))
    return set()

def guardar_convocatoria_enviada(titulo):
    """Marca una convocatoria como enviada"""
    with open(ENVIADAS_FILE, 'a', encoding='utf-8') as f:
        f.write(titulo + '\n')

def enviar_a_telegram(convocatorias):
    """Envía las convocatorias nuevas a Telegram"""
    print("\n📤 Enviando a Telegram...\n")
    
    enviadas = obtener_convocatorias_enviadas()
    contador = 0
    
    for conv in convocatorias:
        if conv['titulo'] not in enviadas:
            mensaje = f"""
📌 NUEVA CONVOCATORIA

<b>{conv['titulo']}</b>

📅 {conv['fecha']}

📝 {conv['resumen']}

🔗 <a href="{conv['enlace']}">Ver en BOE</a>

#oposiciones #empleo #BOE
"""
            
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                data = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': mensaje,
                    'parse_mode': 'HTML'
                }
                
                req = urllib.request.Request(url, 
                    data=urllib.parse.urlencode(data).encode('utf-8'),
                    headers={'Content-Type': 'application/x-www-form-urlencoded'})
                
                response = urllib.request.urlopen(req, timeout=10)
                response.read()
                response.close()
                
                print(f"✓ Enviada: {conv['titulo'][:60]}...")
                guardar_convocatoria_enviada(conv['titulo'])
                contador += 1
            
            except Exception as e:
                print(f"❌ Error enviando a Telegram: {e}")
    
    if contador == 0:
        print("ℹ️  No hay convocatorias nuevas para enviar.")
    else:
        print(f"\n✅ Se enviaron {contador} convocatorias a Telegram")

if __name__ == "__main__":
    convocatorias = leer_boe_rss()
    
    if convocatorias:
        guardar_en_csv(convocatorias)
        enviar_a_telegram(convocatorias)
        print(f"\n✅ Total de convocatorias encontradas: {len(convocatorias)}")
    else:
        print("\n❌ No se encontraron convocatorias de oposiciones hoy.")
