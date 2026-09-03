"""
Servicio de búsqueda y extracción de especificaciones técnicas.

Arquitectura de 3 niveles:
  1. Crawl4AI (open source, sin Docker) → obtiene HTML limpio de la web
  2. Ollama (modelo local) → extrae y redacta las características en JSON profesional
  3. Fallback web → scraping Bing + regex cuando Crawl4AI u Ollama no están disponibles

Nota sobre Corrección 4 (redacción profesional):
  Cuando Ollama está activo, el prompt pide explícitamente que los valores
  estén redactados en lenguaje formal y profesional.
  Cuando Ollama no está activo, se aplica _redaccion_basica() como limpieza.
"""
import os
import re
import json
import logging
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ============================================================
# Configuración
# ============================================================

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
CRAWL4AI_AVAILABLE = False

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    pass


# ============================================================
# Función principal (llamada desde el endpoint Cache-Aside)
# ============================================================

def buscar_caracteristicas_web(marca: str, modelo: str) -> list:
    """
    Busca especificaciones técnicas en la web.
    Orden: 1) Crawl4AI + Ollama, 2) Fallback web scraping, 3) lista vacía.
    Nunca bloquea el flujo — devuelve lista vacía si todo falla.
    """
    marca = (marca or '').strip()
    modelo = (modelo or '').strip()
    if not marca and not modelo:
        return []

    # Nivel 1: Crawl4AI + Ollama (mejor calidad)
    if CRAWL4AI_AVAILABLE:
        try:
            specs = _buscar_crawl4ai_ollama(marca, modelo)
            if specs:
                return specs
        except Exception as e:
            logger.warning(f"Crawl4AI falló: {e}")

    # Nivel 2: Fallback web scraping (Bing + regex)
    try:
        specs = _buscar_web_fallback(marca, modelo)
        if specs:
            return _redaccion_basica(specs)
    except Exception as e:
        logger.warning(f"Fallback web falló: {e}")

    # Nivel 3: Lista vacía — el operador usará el botón de búsqueda manual
    return []


# ============================================================
# Nivel 1: Crawl4AI + Ollama
# ============================================================

def _run_async(coro):
    """Ejecuta una corrutina de forma segura dentro de hilos de Flask."""
    import asyncio
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _buscar_crawl4ai_ollama(marca: str, modelo: str) -> list:
    """Usa Crawl4AI para obtener HTML y Ollama para extraer specs en JSON profesional."""
    query_str = f"{marca} {modelo} especificaciones técnicas ficha técnica"
    urls = _bing_urls(query_str)

    if not urls:
        return []

    # Crawlear las primeras 3 URLs de forma segura en el hilo de Flask
    try:
        contenido = _run_async(_crawl_urls(urls[:3]))
    except Exception as e:
        logger.warning(f"Error ejecutando crawl async: {e}")
        contenido = ""

    if not contenido:
        return []

    # Intentar extraer con Ollama primero
    if _ollama_disponible():
        specs = _extraer_con_ollama(marca, modelo, contenido)
        if specs:
            return specs

    # Si Ollama no está, extraer con regex
    return _extraer_specs_de_texto(contenido)


async def _crawl_urls(urls: list) -> str:
    """Crawlea URLs con Crawl4AI y devuelve el contenido concatenado."""
    contenido_total = ""
    try:
        async with AsyncWebCrawler() as crawler:
            for url in urls:
                try:
                    result = await crawler.arun(url=url)
                    if result and result.markdown:
                        contenido_total += result.markdown[:5000] + "\n\n"
                        if len(contenido_total) > 10000:
                            break
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"Error en Crawl4AI: {e}")
    return contenido_total


# ============================================================
# Ollama: extracción + redacción profesional (Corrección 4)
# ============================================================

def _ollama_disponible() -> bool:
    """Verifica si Ollama está corriendo."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def _extraer_con_ollama(marca: str, modelo: str, texto: str) -> list:
    """
    Usa Ollama para extraer características de texto web y redactarlas
    en formato profesional (Corrección 4).
    """
    prompt = f"""Analiza el siguiente texto de especificaciones técnicas sobre el producto "{marca} {modelo}" y extrae sus características reales.

REGLAS OBLIGATORIAS:
1. Devuelve ÚNICAMENTE un arreglo JSON válido, sin ningún texto antes ni después.
2. Cada elemento debe tener las llaves "nombre" y "valor".
3. Redacta los valores en español formal, profesional y completo (ej: "Resolución de 4800 x 1200 dpi", "Capacidad de 250 hojas", "Conectividad Wi-Fi Direct y Ethernet").
4. EXTRAE SOLAMENTE datos que pertenezcan EXPLICITAMENTE al producto "{marca} {modelo}".
5. NO agregues ni inventes componentes de laptop/computadora (como Procesador Intel, Memoria RAM DDR5, Tarjeta de Video) a menos que el producto sea efectivamente una computadora.
6. IGNORA cualquier referencia a imágenes, URLs de imágenes o rutas de archivos de imagen.
7. Máximo 10 características principales.

Ejemplo de estructura esperada:
[
  {{"nombre": "Resolución de Impresión", "valor": "4800 x 1200 dpi de alta definición"}},
  {{"nombre": "Velocidad de Impresión", "valor": "Hasta 33 páginas por minuto en negro"}}
]

TEXTO DE LA PÁGINA WEB:
{texto[:4000]}

JSON ARRAY:"""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=45
        )
        if resp.status_code == 200:
            respuesta = resp.json().get('response', '')
            # Extraer JSON del texto de respuesta
            match = re.search(r'\[[\s\S]*?\]', respuesta)
            if match:
                specs = json.loads(match.group())
                if isinstance(specs, list) and len(specs) > 0:
                    # Validar estructura
                    return [
                        {'nombre': s.get('nombre', ''), 'valor': s.get('valor', '')}
                        for s in specs
                        if s.get('nombre') and s.get('valor')
                    ][:15]
    except Exception as e:
        logger.warning(f"Error en Ollama: {e}")
    return []


# ============================================================
# Nivel 2: Fallback web scraping (sin Crawl4AI)
# ============================================================

def _buscar_web_fallback(marca: str, modelo: str) -> list:
    """Scraping directo de Bing + páginas de resultados."""
    query_str = f"{marca} {modelo} ficha tecnica especificaciones"
    urls = _bing_urls(query_str)
    specs = []
    seen = set()

    for url in urls[:5]:
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            page_specs = _extraer_specs_de_html(resp.text)
            for sp in page_specs:
                key = sp['nombre'].lower()
                if key not in seen and len(specs) < 15:
                    seen.add(key)
                    specs.append(sp)
            if len(specs) >= 8:
                break
        except Exception:
            continue
    return specs


# ============================================================
# Buscador de URLs específicas (DuckDuckGo + Bing)
# ============================================================

def _bing_urls(query_str: str) -> list:
    """Obtiene URLs específicas de fichas técnicas ignorando portadas raíz genericas."""
    import base64
    from urllib.parse import unquote, urlparse

    urls = []
    seen = set()

    # 1. DuckDuckGo HTML (Devuelve páginas de productos muy precisas)
    try:
        resp = requests.post(
            'https://html.duckduckgo.com/html/',
            data={'q': query_str},
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'},
            timeout=8
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', class_='result__url'):
                href = a.get('href', '').strip()
                if 'uddg=' in href:
                    m = re.search(r'uddg=([^&]+)', href)
                    if m:
                        href = unquote(m.group(1))
                if href.startswith('http'):
                    parsed = urlparse(href)
                    # Excluir portadas sin ruta interna (ej: https://epson.com.do/) y PDFs directos
                    if parsed.path and parsed.path != '/' and not href.lower().endswith('.pdf'):
                        if href not in seen:
                            seen.add(href)
                            urls.append(href)
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")

    # 2. Bing Search (Respaldo)
    try:
        resp = requests.get(
            "https://www.bing.com/search",
            params={"q": query_str},
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=8,
        )
        if resp.status_code == 200:
            for match in re.finditer(r'href="https?://[^"]+u=a1([^&"]+)', resp.text):
                s = match.group(1)
                s += "=" * (-len(s) % 4)
                try:
                    decoded = base64.urlsafe_b64decode(s).decode("utf-8", "ignore")
                    if decoded.startswith("http"):
                        parsed = urlparse(decoded)
                        if parsed.path and parsed.path != '/' and not decoded.lower().endswith('.pdf'):
                            if decoded not in seen:
                                seen.add(decoded)
                                urls.append(decoded)
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"Bing search error: {e}")

    return urls[:6]


# ============================================================
# Extractores de texto
# ============================================================

SPEC_KEYWORDS = [
    'resolución', 'resolucion', 'velocidad', 'memoria', 'procesador', 'pantalla',
    'batería', 'bateria', 'dimensiones', 'peso', 'sistema operativo', 'capacidad',
    'almacenamiento', 'conectividad', 'puertos', 'puerto', 'cámara', 'camara',
    'garantía', 'garantia', 'escaneo', 'impresión', 'impresion',
    'wifi', 'wi-fi', 'bluetooth', 'tinta', 'cartucho', 'toner',
    'voltaje', 'consumo', 'frecuencia', 'tecnología', 'tecnologia', 'interfaz',
    'alimentación', 'alimentacion', 'autonomía', 'autonomia', 'rango',
    'temperatura', 'rendimiento', 'formato', 'conexión', 'conexion',
    'sensor', 'marca', 'modelo', 'color', 'tamaño', 'tamano', 'pulgadas',
    'escáner', 'escaner', 'dpi', 'ppm', 'ram', 'disco', 'ssd', 'hdd',
]

UNIT_PATTERN = re.compile(
    r'(\d+\s*(x|\*|×)\s*\d+|\b\d+(\.\d+)?\s*'
    r'(dpi|ppm|ghz|mhz|hz|gb|mb|tb|mp|kg|g|cm|mm|pulg|inch|mah|db|mbps|gbps|w|v|a)\b)',
    re.IGNORECASE,
)


def _es_label_spec(key: str) -> bool:
    kl = (key or '').lower()
    return any(kw in kl for kw in SPEC_KEYWORDS)


def _extraer_specs_de_html(html: str) -> list:
    """Extrae specs de HTML buscando tablas y listas clave:valor."""
    specs = []
    seen = set()

    # Limpiar HTML
    clean = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
    clean = re.sub(r'<style.*?>.*?</style>', '', clean, flags=re.DOTALL)

    # Buscar tablas con specs
    for match in re.finditer(r'<tr[^>]*>(.*?)</tr>', clean, re.DOTALL):
        row = match.group(1)
        cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL)
        if len(cells) >= 2:
            key = re.sub(r'<[^>]+>', '', cells[0]).strip()
            val = re.sub(r'<[^>]+>', '', cells[1]).strip()
            if _es_label_spec(key) and val and len(val) <= 100:
                k = key.lower()
                if k not in seen:
                    seen.add(k)
                    specs.append({'nombre': key, 'valor': val})

    # Buscar listas con dos puntos
    text = re.sub(r'<[^>]+>', '\n', clean)
    for line in text.splitlines():
        line = line.strip()
        if ':' in line and len(line) < 150:
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if _es_label_spec(key) and val and len(val) <= 100:
                k = key.lower()
                if k not in seen and len(specs) < 15:
                    seen.add(k)
                    specs.append({'nombre': key, 'valor': val})

    return specs


def _extraer_specs_de_texto(text: str) -> list:
    """Extrae specs de texto markdown o plano."""
    specs = []
    seen = set()

    for line in text.splitlines():
        clean = re.sub(r'^[*\-•#\s]+', '', line).strip()
        # Tablas markdown
        if '|' in clean:
            parts = [p.strip() for p in clean.split('|') if p.strip()]
            if len(parts) >= 2:
                key, val = parts[0], parts[1]
                if _es_label_spec(key) and len(val) <= 100:
                    k = key.lower()
                    if k not in seen:
                        seen.add(k)
                        specs.append({'nombre': key, 'valor': val})
            continue
        # Listas clave:valor
        if ':' in clean:
            key, val = clean.split(':', 1)
            key, val = key.strip(), val.strip()
            if _es_label_spec(key) and val and len(val) <= 100:
                k = key.lower()
                if k not in seen and len(specs) < 15:
                    seen.add(k)
                    specs.append({'nombre': key, 'valor': val})

    return specs


# ============================================================
# Corrección 4: Redacción profesional básica (sin Ollama)
# ============================================================

def _redaccion_basica(specs: list) -> list:
    """
    Limpieza y capitalización profesional cuando Ollama no está disponible.
    Convierte 'ram 16gb ddr4' → 'RAM de 16 GB DDR4'.
    """
    result = []
    for sp in specs:
        nombre = sp.get('nombre', '').strip()
        valor = sp.get('valor', '').strip()

        # Capitalizar nombre
        nombre = nombre.title() if nombre.islower() else nombre

        # Limpiar valor: espaciar unidades pegadas (16GB → 16 GB)
        valor = re.sub(r'(\d)(GB|MB|TB|GHz|MHz|Hz|DPI|PPM|MP)', r'\1 \2', valor, flags=re.IGNORECASE)
        # Capitalizar primera letra si todo está en minúsculas
        if valor and valor[0].islower():
            valor = valor[0].upper() + valor[1:]

        result.append({'nombre': nombre, 'valor': valor})
    return result
