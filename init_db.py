"""
Script de inicialización de la base de datos.
Crea las tablas, inserta datos iniciales y el usuario administrador.

Uso:
    python3 init_db.py
"""
import os
import sys

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
from config import Config


def init_database():
    """Crea la base de datos y ejecuta el esquema SQL."""
    import psycopg2

    # Intentar crear la base de datos (conectar a 'postgres' primero)
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname='postgres',
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Verificar si la BD ya existe
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (Config.DB_NAME,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE {Config.DB_NAME}')
            print(f'✅ Base de datos "{Config.DB_NAME}" creada')
        else:
            print(f'ℹ️  Base de datos "{Config.DB_NAME}" ya existe')

        cur.close()
        conn.close()
    except Exception as e:
        print(f'⚠️  No se pudo crear la BD automáticamente: {e}')
        print(f'   Créela manualmente: CREATE DATABASE {Config.DB_NAME};')

    # Conectar a la BD del sistema y ejecutar el esquema
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
        )

        schema_path = os.path.join(os.path.dirname(__file__), 'sql', 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        cur = conn.cursor()
        cur.execute(schema_sql)
        conn.commit()
        print('✅ Esquema de tablas creado correctamente')

        # Crear usuario administrador si no existe
        cur.execute("SELECT id FROM usuarios WHERE username = 'admin'")
        if not cur.fetchone():
            password_hash = generate_password_hash('ogti2026', method='pbkdf2:sha256')
            cur.execute(
                """
                INSERT INTO usuarios (username, password_hash, nombre_completo, cargo, rol)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('admin', password_hash, 'Administrador OGTI', 'Jefe de OGTI', 'JEFE_OGTI')
            )
            conn.commit()
            print('✅ Usuario administrador creado:')
            print('   Usuario: admin')
            print('   Contraseña: ogti2026')
            print('   Rol: JEFE_OGTI')
        else:
            print('ℹ️  Usuario admin ya existe')

        # Crear un usuario operador de ejemplo
        cur.execute("SELECT id FROM usuarios WHERE username = 'operador'")
        if not cur.fetchone():
            password_hash = generate_password_hash('ogti2026', method='pbkdf2:sha256')
            cur.execute(
                """
                INSERT INTO usuarios (username, password_hash, nombre_completo, cargo, rol)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('operador', password_hash, 'Técnico OGTI', 'Practicante', 'OPERADOR')
            )
            conn.commit()
            print('✅ Usuario operador creado:')
            print('   Usuario: operador')
            print('   Contraseña: ogti2026')
            print('   Rol: OPERADOR')
        else:
            print('ℹ️  Usuario operador ya existe')

        # Insertar dependencias iniciales
        dependencias = [
            ('Oficina General de Tecnologías de la Información', 'Palacio Municipal', 'Piso 3'),
            ('Gerencia Municipal', 'Palacio Municipal', 'Piso 2'),
            ('Sub Gerencia de Logística', 'Palacio Municipal', 'Piso 1'),
            ('Sub Gerencia de Patrimonio', 'Palacio Municipal', 'Piso 1'),
            ('Gerencia de Administración y Finanzas', 'Palacio Municipal', 'Piso 2'),
        ]
        for nombre, edificio, pabellon in dependencias:
            cur.execute("SELECT id FROM dependencias WHERE nombre = %s", (nombre,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO dependencias (nombre, edificio, pabellon) VALUES (%s, %s, %s)",
                    (nombre, edificio, pabellon)
                )
        conn.commit()
        print('✅ Dependencias iniciales insertadas')

        cur.close()
        conn.close()
        print('')
        print('=' * 50)
        print('🏛️  Sistema OGTI inicializado correctamente')
        print('   Ejecute: python3 app.py')
        print('   Acceda a: http://localhost:5000')
        print('=' * 50)

    except Exception as e:
        print(f'❌ Error al inicializar: {e}')
        raise


if __name__ == '__main__':
    init_database()
