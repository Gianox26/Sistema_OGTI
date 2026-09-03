"""
Sistema de Gestión de Especificaciones Técnicas y Fichas Técnicas
Municipalidad Provincial de San Román — Juliaca
Oficina General de Tecnologías de la Información (OGTI)

Entry point de la aplicación Flask.
"""
import os
from flask import Flask
from config import Config

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Importar blueprints
from routes.auth import auth_bp
from routes.catalogos import catalogos_bp
from routes.especificaciones import especificaciones_bp
from routes.fichas import fichas_bp
from routes.historial import historial_bp


def create_app():
    """Factory de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Clave secreta para sesiones
    app.secret_key = Config.SECRET_KEY

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogos_bp)
    app.register_blueprint(especificaciones_bp)
    app.register_blueprint(fichas_bp)
    app.register_blueprint(historial_bp)

    # Filtro Jinja2 para formateo de correlativos (mínimo 3 dígitos)
    from services.numeracion import formatear_correlativo
    @app.template_filter('correlativo')
    def filter_correlativo(numero, anio=None):
        if not numero:
            return '—'
        if anio:
            return formatear_correlativo(numero, anio)
        num_str = str(numero).strip()
        if num_str.isdigit():
            return num_str.zfill(3)
        return num_str

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000)
