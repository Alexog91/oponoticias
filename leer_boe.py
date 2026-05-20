import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import json
import os
import time
from email.utils import parsedate_to_datetime
from datetime import datetime

# CONFIGURACIÓN
RSS_URL = "https://www.boe.es/rss/boe.php?s=2B"
TELEGRAM_TOKEN = "8803259416:AAFfXoRvMXIHemcIe6a5ey69TeR632-OZFI"
TELEGRAM_CHAT_ID = "-1003528545552"
SUPABASE_URL = "https://opnbxphxfclazxduhmkp.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wbmJ4cGh4ZmNsYXp4ZHVobWtwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwNDQwMzcsImV4cCI6MjA5NDYyMDAzN30.lcMQwdW2HTCeg2X6Qrl0uTmZA73Yr0KdGHf3y3fLMtM"


def leer_boe_rss():
    print("🔄 Leyendo RSS del BOE...")
    
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
                    print(f"📢 {titulo[:80]}...")
        
        return convocatorias
    
    except Exception as e:
        print(f"❌ Error al leer el RSS: {e}")
        return []


def extraer_cuerpo(titulo):
    """Extrae el tipo de puesto del título"""
    texto_busqueda = titulo.upper()
    
    if "POLIC" in texto_busqueda:
        return "👮 Policía"
    elif "ADMINIST" in texto_busqueda:
        return "📋 Administrativo"
    elif "SANITARI" in texto_busqueda or "ENFERM" in texto_busqueda or "MÉDIC" in texto_busqueda or "FISIOTER" in texto_busqueda:
        return "🏥 Sanitario"
    elif "JUSTICIA" in texto_busqueda or "JUZGADO" in texto_busqueda:
        return "⚖️ Justicia"
    elif "TÉCNIC" in texto_busqueda or "INGENIER" in texto_busqueda or "INFORMÁTIC" in texto_busqueda:
        return "🔧 Técnico"
    elif "HACIENDA" in texto_busqueda or "TESORERO" in texto_busqueda:
        return "💰 Hacienda"
    elif "JARDINERÍA" in texto_busqueda or "PEÓN" in texto_busqueda or "OPERARIO" in texto_busqueda:
        return "🚧 Servicios"
    elif "EDUCACIÓN" in texto_busqueda or "PROFESOR" in texto_busqueda or "DOCENTE" in texto_busqueda:
        return "📚 Educación"
    elif "BIBLIOTECA" in texto_busqueda:
        return "📖 Biblioteca"
    elif "FORESTAL" in texto_busqueda:
        return "🌲 Agente Forestal"
    elif "BOMBERO" in texto_busqueda:
        return "🚒 Bombero"
    elif "ARQUITECTO" in texto_busqueda:
        return "🏛️ Arquitecto"
    else:
        return "📄 Convocatoria"


def guardar_en_supabase(conv):
    """Guarda UNA convocatoria en Supabase. Retorna True si se guardó, False si ya existía."""
    data = {
        'fecha': conv['fecha'],
        'titulo': conv['titulo'],
        'enlace': conv['enlace'],
        'resumen': conv['resumen'],
        'cuerpo': conv.get('cuerpo', '📄 Convocatoria')
    }
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/convocatorias"
        headers = {
            'apikey': SUPABASE_API_KEY,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        response = urllib.request.urlopen(req, timeout=10)
        response.read()
        response.close()
        
        print(f"✓ Guardada en Supabase: {conv['titulo'][:60]}...")
        return True
    
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print(f"ℹ️  Ya existe: {conv['titulo'][:60]}...")
            return False
        else:
            print(f"❌ Error guardando en Supabase: {e}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def enviar_a_telegram(conv):
    """Envía mensaje formateado a Telegram"""
    
    # Convertir fecha a español
    try:
        fecha_obj = parsedate_to_datetime(conv['fecha'])
        meses = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        mes = meses[fecha_obj.month]
        fecha_spanish = f"{fecha_obj.day} de {mes} de {fecha_obj.year}"
    except:
        fecha_spanish = conv['fecha']
    
    titulo = conv['titulo']
    cuerpo = conv.get('cuerpo', '📄 Convocatoria')
    resumen = conv['resumen']
    
    if len(resumen) > 150:
        resumen = resumen[:150] + "..."
    
    mensaje = f"""🎯 <b>NUEVA CONVOCATORIA</b>

<b>{titulo[:100]}</b>

🏷️ <b>Tipo:</b> {cuerpo}
📅 <b>Fecha:</b> {fecha_spanish}

ℹ️ <b>Detalles:</b>
{resumen}

<a href="{conv['enlace']}">📄 Ver en BOE</a>

#oposiciones #empleo #BOE"""
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': mensaje,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode('utf-8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        response = urllib.request.urlopen(req, timeout=10)
        response.read()
        response.close()
        
        print(f"✅ Enviada a Telegram: {titulo[:50]}...")
    
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")


if __name__ == "__main__":
    convocatorias = leer_boe_rss()
    
    if convocatorias:
        nuevas = 0
        for conv in convocatorias:
            conv['cuerpo'] = extraer_cuerpo(conv['titulo'])
            
            # Solo enviar a Telegram si ES NUEVA (no existe en Supabase)
            if guardar_en_supabase(conv):
                enviar_a_telegram(conv)
                nuevas += 1
                time.sleep(2)
        
        print(f"\n✅ Procesadas {len(convocatorias)} convocatorias. Nuevas: {nuevas}")
    else:
        print("\n❌ No se encontraron convocatorias")
