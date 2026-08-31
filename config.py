import os

class Config:
    """Configuración central del Sistema OGTI."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'ogti-san-roman-juliaca-2026-dev')

    # PostgreSQL
    # Para conexión TCP con password: DB_HOST=localhost DB_PASSWORD=ogti2026
    # Para conexión por socket (peer): DB_HOST=/var/run/postgresql DB_PASSWORD=
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'sistema_ogti')
    DB_USER = os.environ.get('DB_USER', 'fulanito')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'ogti2026')

    # Rutas de plantillas .docx oficiales
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PLANTILLAS_DIR = os.path.join(BASE_DIR, 'plantillas_docx')
    DOCS_DIR = os.path.join(BASE_DIR, 'docs')

    # Plantillas específicas
    PLANTILLA_FICHA = os.path.join(PLANTILLAS_DIR, 'ficha_tecnica_tpl.docx')
    PLANTILLA_ET = os.path.join(PLANTILLAS_DIR, 'especificacion_tecnica_tpl.docx')

    # Formato institucional de la carta de almacén
    # Solo el número se ingresa; el año se toma del año fiscal de la ficha
    SUFIJO_CARTA = 'MPSR-J/OGA/OL/AC/WDB'
