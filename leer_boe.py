import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import json
import os
import time
import re
from email.utils import parsedate_to_datetime
from datetime import datetime

# CONFIGURACIÓN - Desde GitHub Secrets
RSS_URL = "https://www.boe.es/rss/boe.php?s=2B"
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_API_KEY = os.environ["SUPABASE_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


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
                
                # Limpiar resumen de metadata técnica
                resumen = re.sub(r'[-–]\s*Referencia:.*', '', resumen)
                resumen = re.sub(r'[-–]\s*KBytes:.*', '', resumen)
                resumen = re.sub(r'KBytes:.*', '', resumen)
                resumen = resumen.strip()
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


def generar_resumen_con_claude(titulo, resumen):
    """Usa Claude API para generar un resumen inteligente"""
    
    try:
        prompt = f"""Analiza esta convocatoria del BOE y extrae la información clave.

Título: {titulo}
Descripción: {resumen}

RESPONDE SOLO con una línea en MAYÚSCULAS con este formato exacto:
[NÚMERO] PLAZAS - [PUESTO ESPECÍFICO] - [LUGAR]

IMPORTANTE: Busca SIEMPRE el puesto ESPECÍFICO, nunca genérico.

Ejemplos de puestos ESPECÍFICOS (NO genéricos):
- POLICÍA LOCAL (NO "Policía")
- ENFERMERO (NO "Sanitario")
- INSPECTOR DE HACIENDA (NO "Hacienda")
- TÉCNICO DE HACIENDA
- AGENTE DE HACIENDA
- JUEZ (NO "Justicia")
- FISCAL
- LETRADO DE LA ADMINISTRACIÓN DE JUSTICIA
- GESTOR PROCESAL
- AUXILIAR JUDICIAL
- PROFESOR DE EDUCACIÓN FÍSICA (NO "Profesor")
- TÉCNICO INFORMÁTICO (NO "Técnico")
- INGENIERO TÉCNICO
- BOMBERO
- JARDINERO
- PEÓN DE SERVICIOS
- ADMINISTRATIVO
- SECRETARIO DE AYUNTAMIENTO

Estrategia:
1. Lee el título completo buscando palabras específicas
2. Si dice "Resolución de X de Y, del Ayuntamiento de Z", busca después qué puesto es
3. Extrae el puesto más específico posible del texto
4. Si encuentras "Inspector", "Técnico", "Agente", "Gestor", "Letrado", "Auxiliar" + categoría, úsalo
5. NUNCA pongas términos genéricos como "Justicia", "Hacienda", "Sanitario", "Funcionario"

Ejemplos correctos:
2 PLAZAS - POLICÍA LOCAL - CÁDIZ
1 PLAZA - INSPECTOR DE HACIENDA - MADRID
3 PLAZAS - LETRADO DE LA ADMINISTRACIÓN DE JUSTICIA - BARCELONA
1 PLAZA - ENFERMERO - VALENCIA
1 PLAZA - PROFESOR DE EDUCACIÓN FÍSICA - SEVILLA

Si NO encuentras un puesto específico, busca cualquier palabra del texto que indique el cargo.
Si realmente no hay nada, pon: 1 PLAZA - PERSONAL - [LUGAR]"""
        
        # Llamar a Claude API
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        response = urllib.request.urlopen(req, timeout=10)
        response_data = json.loads(response.read().decode('utf-8'))
        response.close()
        
        # Extraer el texto de la respuesta
        resumen_generado = response_data['content'][0]['text'].strip()
        print(f"✨ Claude generó: {resumen_generado}")
        return resumen_generado
    
    except Exception as e:
        print(f"⚠️  Error con Claude: {e}. Usando resumen por defecto.")
        return "Convocatoria disponible"


def extraer_cuerpo(titulo):
    """Extrae el tipo de puesto del título"""
    texto_busqueda = titulo.upper()
    
    if "POLIC" in texto_busqueda:
        return "👮 Policía"
    elif "ADMINIST" in texto_busqueda:
        return "📋 Administrativo"
    elif "SANITARI" in texto_busqueda or "ENFERM" in texto_busqueda or "MÉDIC" in texto_busqueda:
        return "🏥 Sanitario"
    elif "JUSTICIA" in texto_busqueda or "JUZGADO" in texto_busqueda:
        return "⚖️ Justicia"
    elif "TÉCNIC" in texto_busqueda or "INGENIER" in texto_busqueda:
        return "🔧 Técnico"
    elif "HACIENDA" in texto_busqueda or "TESORERO" in texto_busqueda:
        return "💰 Hacienda"
    elif "EDUCACIÓN" in texto_busqueda or "PROFESOR" in texto_busqueda:
        return "📚 Educación"
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
    """Envía mensaje formateado a Telegram con diseño Opción 3"""
    
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
    
    # Extraer información del detalles_ia
    detalles_ia = conv.get('resumen_ia', 'Convocatoria disponible')
    
    # Parsear: "X PLAZAS - PUESTO - UBICACIÓN"
    partes = detalles_ia.split(' - ')
    plazas = partes[0].strip() if len(partes) > 0 else "N/A"
    puesto = partes[1].strip() if len(partes) > 1 else "Convocatoria"
    ubicacion = partes[2].strip() if len(partes) > 2 else "España"
    
    # Extraer resumen del título (primeros 90 caracteres o hasta primer verbo)
    titulo_corto = conv['titulo'][:90]
    
    # Construir mensaje con diseño Opción 3
    mensaje = f"""╔═══════════════════════════════════╗
║ 🎯 NUEVA CONVOCATORIA             ║
╚═══════════════════════════════════╝

📰 {titulo_corto}

┌─────────────────────────────────────┐
│ 📍 {puesto}
│
│ 🔢 Plazas: {plazas}
│ 📍 Ubicación: {ubicacion}
│ 📅 Publicado: {fecha_spanish}
└─────────────────────────────────────┘

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
        
        print(f"✅ Enviada a Telegram: {titulo_corto}...")
    
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")


if __name__ == "__main__":
    convocatorias = leer_boe_rss()
    
    if convocatorias:
        nuevas = 0
        for conv in convocatorias:
            conv['cuerpo'] = extraer_cuerpo(conv['titulo'])
            
            # Generar resumen inteligente con Claude
            print(f"\n🤖 Analizando: {conv['titulo'][:60]}...")
            conv['resumen_ia'] = generar_resumen_con_claude(conv['titulo'], conv['resumen'])
            
            # Solo enviar a Telegram si ES NUEVA (no existe en Supabase)
            if guardar_en_supabase(conv):
                enviar_a_telegram(conv)
                nuevas += 1
                time.sleep(2)
        
        print(f"\n✅ Procesadas {len(convocatorias)} convocatorias. Nuevas: {nuevas}")
    else:
        print("\n❌ No se encontraron convocatorias")
