"""
Servicio de integración con Firecrawl y Extractor Web para especificaciones técnicas.
Sigue el patrón Cache-Aside para autocompletar modelos no registrados.
"""
import os
import re
import logging
import requests

logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY', '')

def buscar_caracteristicas_web(marca: str, modelo: str) -> list:
    """
    Busca especificaciones técnicas en la web usando Firecrawl API.
    Si no hay API key o la llamada falla, utiliza un extractor web de respaldo.
    Retorna una lista de dicts: [{'nombre': '...', 'valor': '...'}]
    """
    marca_clean = marca.strip()
    modelo_clean = modelo.strip()
    query_str = f"{marca_clean} {modelo_clean} especificaciones tecnicas datasheet"

    api_key = os.environ.get('FIRECRAWL_API_KEY', '').strip()

    if api_key:
        try:
            url = "https://api.firecrawl.dev/v1/search"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query_str,
                "limit": 3,
                "scrapeOptions": {
                    "formats": ["markdown"]
                }
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', [])
                for item in items:
                    markdown = item.get('markdown', '')
                    specs = _extraer_specs_de_markdown(markdown)
                    if specs:
                        return specs
        except Exception as e:
            logger.warning(f"Error llamando a Firecrawl API: {e}")

    # Fallback si no hay API Key o falla Firecrawl
    return _buscar_fallback_duckduckgo(marca_clean, modelo_clean)


def _extraer_specs_de_markdown(text: str) -> list:
    """Extrae pares clave-valor de texto markdown o HTML."""
    if not text:
        return []

    specs = []
    seen = set()

    # Patrón 1: Tablas Markdown | Campo | Valor |
    for line in text.splitlines():
        if '|' in line:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                col1, col2 = parts[0], parts[1]
                if col1.lower() in ['característica', 'campo', 'especificación', 'propiedad', 'item', '---']:
                    continue
                if len(col1) < 40 and len(col2) < 120 and col1.lower() not in seen:
                    seen.add(col1.lower())
                    specs.append({'nombre': col1, 'valor': col2})

    # Patrón 2: Listas con dos puntos - Procesador: Intel i7
    if len(specs) < 3:
        lines = text.splitlines()
        for line in lines:
            line_clean = re.sub(r'^[*\-#\s]+', '', line).strip()
            if ':' in line_clean:
                parts = line_clean.split(':', 1)
                k = parts[0].strip()
                v = parts[1].strip()
                if 2 <= len(k) <= 35 and 1 <= len(v) <= 100 and k.lower() not in seen:
                    if not any(stop in k.lower() for stop in ['http', 'www', 'copyright', 'derechos', 'cookie', 'login']):
                        seen.add(k.lower())
                        specs.append({'nombre': k, 'valor': v})

    return specs[:15]


def _buscar_fallback_duckduckgo(marca: str, modelo: str) -> list:
    """
    Extractor de respaldo mediante DuckDuckGo HTML cuando no hay API Key de Firecrawl.
    """
    try:
        query_encoded = requests.utils.quote(f"{marca} {modelo} especificaciones técnicas")
        url = f"https://html.duckduckgo.com/html/?q={query_encoded}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            text = resp.text
            # Limpiar HTML básico
            clean_text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
            clean_text = re.sub(r'<style.*?>.*?</style>', '', clean_text, flags=re.DOTALL)
            clean_text = re.sub(r'<[^>]+>', '\n', clean_text)
            specs = _extraer_specs_de_markdown(clean_text)
            if specs:
                return specs
    except Exception as e:
        logger.warning(f"Error en fallback DuckDuckGo: {e}")

    # Fallback genérico estructurado si no se logra conexion externa
    return [
        {"nombre": "Marca", "valor": marca},
        {"nombre": "Modelo", "valor": modelo},
        {"nombre": "Estado", "valor": "Pendiente de verificación física"},
    ]
