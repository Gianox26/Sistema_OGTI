"""
Servicio de integración con Firecrawl y buscadores web para especificaciones técnicas.
Firecrawl es el motor principal (renderizado JS + extracción estructurada).
Sin API key, usa un fallback de mejor esfuerzo vía Bing que parsea tablas de specs.
"""
import os
import re
import base64
import logging
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY', '').strip()


def buscar_caracteristicas_web(marca: str, modelo: str) -> list:
    marca = (marca or '').strip()
    modelo = (modelo or '').strip()
    if not marca and not modelo:
        return []

    if FIRECRAWL_API_KEY:
        specs = _buscar_firecrawl(marca, modelo)
        if specs:
            return specs

    return _buscar_web_fallback(marca, modelo)


def _buscar_firecrawl(marca: str, modelo: str) -> list:
    query = f"{marca} {modelo} ficha tecnica especificaciones"
    try:
        resp = requests.post(
            "https://api.firecrawl.dev/v1/search",
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "limit": 5,
                "scrapeOptions": {"formats": ["markdown"]},
            },
            timeout=25,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('data', []):
                markdown = item.get('markdown', '') or ''
                specs = _extraer_specs_de_texto(markdown)
                if specs:
                    return specs
    except Exception as e:
        logger.warning(f"Error llamando a Firecrawl API: {e}")
    return []


def _buscar_web_fallback(marca: str, modelo: str) -> list:
    query = f"{marca} {modelo} ficha tecnica especificaciones caracteristicas"
    urls = _bing_urls(query)
    specs = []
    seen = set()
    for url in urls[:8]:
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=12,
            )
            if resp.status_code != 200:
                continue
            page_specs = _extraer_specs_estrictas(resp.text)
            for sp in page_specs:
                key = sp['nombre'].lower()
                if key not in seen and len(specs) < 25:
                    seen.add(key)
                    specs.append(sp)
            if len(specs) >= 8:
                break
        except Exception as e:
            logger.warning(f"Error scrapeando {url}: {e}")
    return specs


STRONG_KEYS = [
    'resolución', 'resolucion', 'velocidad', 'memoria', 'procesador', 'pantalla',
    'batería', 'bateria', 'dimensiones', 'peso', 'sistema operativo', 'capacidad',
    'almacenamiento', 'conectividad', 'puertos', 'puerto', 'cámara', 'camara',
    'garantía', 'garantia', 'escaneo', 'escane', 'impresión', 'impresion',
    'impresora', 'wi-fi', 'wifi', 'bluetooth', 'tinta', 'cartucho', 'toner',
    'voltaje', 'consumo', 'frecuencia', 'tecnología', 'tecnologia', 'interfaz',
    'alimentación', 'alimentacion', 'autonomía', 'autonomia', 'rango', 'alcance',
    'temperatura', 'humedad', 'rendimiento', 'formato', 'conexión', 'conexion',
    'protocolo', 'sensor', 'marca', 'modelo', 'color', 'tamaño', 'tamano',
    'pulgadas', 'escaner', 'escáner', 'dpi', 'ppm',
]
STRONG_RE = re.compile(r'\b(' + '|'.join(re.escape(k) for k in STRONG_KEYS) + r')\b', re.IGNORECASE)


def _es_label_spec_seguro(key: str) -> bool:
    return bool(STRONG_RE.search(key or ''))


def _extraer_specs_estrictas(html: str) -> list:
    specs = []
    seen = set()
    try:
        soup = BeautifulSoup(html, "html.parser")
        for table in soup.find_all("table"):
            ttext = table.get_text(" ", strip=True)
            if "v t e" in ttext:
                continue
            for tr in table.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if len(cells) < 2:
                    continue
                key = cells[0].get_text(" ", strip=True)
                val = cells[1].get_text(" ", strip=True)
                if not _es_label_spec_seguro(key):
                    continue
                if not val or len(val) > 90:
                    continue
                if not UNIT_PATTERN.search(val):
                    continue
                k = key.lower()
                if k not in seen:
                    seen.add(k)
                    specs.append({"nombre": key, "valor": val})
        if len(specs) < 4:
            texto = soup.get_text("\n", strip=True)
            for line in texto.splitlines():
                clean = re.sub(r'^[*\-•#\s]+', '', line).strip()
                if ':' in clean:
                    key, val = clean.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    if not _es_label_spec_seguro(key):
                        continue
                    if not val or len(val) > 90:
                        continue
                    if not UNIT_PATTERN.search(val):
                        continue
                    k = key.lower()
                    if k not in seen and len(specs) < 25:
                        seen.add(k)
                        specs.append({"nombre": key, "valor": val})
    except Exception:
        pass
    return specs


def _bing_urls(query: str) -> list:
    try:
        resp = requests.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=12,
        )
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        urls = []
        for a in soup.select("li.b_algo h2 a"):
            href = a.get("href", "")
            decoded = _decodificar_url_bing(href)
            if decoded and decoded.startswith("http"):
                urls.append(decoded)
        return urls
    except Exception as e:
        logger.warning(f"Error buscando en Bing: {e}")
        return []


def _decodificar_url_bing(href: str):
    m = re.search(r"u=a1([^&]+)", href or "")
    if not m:
        return None
    s = m.group(1)
    s += "=" * (-len(s) % 4)
    try:
        return base64.urlsafe_b64decode(s).decode("utf-8", "ignore")
    except Exception:
        return None


def _extraer_specs_de_texto(text: str, seen: set = None) -> list:
    if not text:
        return []
    if seen is None:
        seen = set()
    specs = []
    for line in text.splitlines():
        clean = re.sub(r'^[*\-•#\s]+', '', line).strip()
        if '|' in clean:
            parts = [p.strip() for p in clean.split('|') if p.strip()]
            if len(parts) >= 2:
                key, val = parts[0], parts[1]
                if key.lower() in ('especificación', 'campo', 'caracteristica', 'item', '---'):
                    continue
                if len(val) > 120:
                    continue
                if _key_es_spec(key) or _val_es_spec(val):
                    k = key.lower()
                    if k not in seen and len(specs) < 25:
                        seen.add(k)
                        specs.append({"nombre": key, "valor": val})
            continue
        if ':' in clean:
            key, val = clean.split(':', 1)
            key = key.strip()
            val = val.strip()
            if len(val) > 80:
                continue
            if not UNIT_PATTERN.search(val):
                continue
            if _es_spec_valida(key, val):
                k = key.lower()
                if k not in seen:
                    seen.add(k)
                    specs.append({"nombre": key, "valor": val})
    return specs


SPEC_KEYWORDS = [
    'resoluci', 'velocidad', 'conectividad', 'memoria', 'procesador', 'pantalla',
    'bater', 'dimension', 'peso', 'sistema operativo', 'capacidad',
    'puerto', 'wi-fi', 'wifi', 'bluetooth', 'garant', 'escane', 'impres',
    'pulgada', 'almacenamiento', 'camara', 'cámara', 'camera', 'sensor',
    'tamano', 'tamaño', 'voltaje', 'amperaje', 'consumo', 'potencia',
    'frecuencia', 'tecnolog', 'compatible', 'driver', 'interface', 'interfaz',
    'marca', 'modelo', 'color', 'material', 'duracion', 'autonom',
    'conexion', 'conexión', 'alimentacion', 'alimentación', 'protocolo',
    'formato', 'soporte', 'rango', 'alcance', 'temperatura', 'humedad',
    'escaneo', 'impresion', 'impresión', 'rendimiento', 'cartucho', 'toner',
    'tinta', 'resolución',
]

UNIT_PATTERN = re.compile(
    r'(\d+\s*(x|\*|×)\s*\d+|\b\d+(\.\d+)?\s*(dpi|ppm|ghz|mhz|hz|gb|mb|tb|mp|kg|g|cm|mm|'
    r'pulg|inch|mah|db|mbps|gbps|lpi|bit)\b)',
    re.IGNORECASE,
)


def _key_es_spec(key: str) -> bool:
    kl = (key or '').lower()
    return any(kw in kl for kw in SPEC_KEYWORDS)


def _val_es_spec(val: str) -> bool:
    return bool(UNIT_PATTERN.search(val or ''))


def _es_spec_valida(key: str, val: str) -> bool:
    if not key or not val:
        return False
    if not (2 <= len(key) <= 45):
        return False
    if not (1 <= len(val) <= 120):
        return False
    if len(key.split()) > 8:
        return False
    if any(stop in key.lower() for stop in ['http', 'www', 'cookie', 'login', 'copyright', 'derechos', 'privacidad']):
        return False
    if key.lower() in ['característica', 'campo', 'especificación', 'propiedad', 'item', '---', 'nombre', 'valor']:
        return False
    return _key_es_spec(key) or _val_es_spec(val)
