#!/bin/bash
# ============================================================
# Script de configuración de PostgreSQL para el Sistema OGTI
# Ejecutar con: sudo bash setup_postgres.sh
# ============================================================

set -e

echo "🏛️  Configurando PostgreSQL para el Sistema OGTI..."
echo ""

# 1. Crear rol de base de datos para el usuario fulanito
echo "1. Creando rol de base de datos..."
sudo -u postgres psql -c "DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'fulanito') THEN
        CREATE ROLE fulanito WITH LOGIN CREATEDB PASSWORD 'ogti2026';
        RAISE NOTICE 'Rol fulanito creado exitosamente';
    ELSE
        ALTER ROLE fulanito WITH LOGIN CREATEDB PASSWORD 'ogti2026';
        RAISE NOTICE 'Rol fulanito ya existía, actualizado';
    END IF;
END
\$\$;"

# 2. Crear la base de datos
echo "2. Creando base de datos sistema_ogti..."
sudo -u postgres psql -c "
    SELECT 'exists' FROM pg_database WHERE datname = 'sistema_ogti';
" | grep -q exists && echo "   Base de datos ya existe" || {
    sudo -u postgres createdb -O fulanito sistema_ogti
    echo "   Base de datos creada"
}

# 3. Ejecutar el esquema SQL
echo "3. Ejecutando esquema de tablas..."
PGPASSWORD=ogti2026 psql -h localhost -U fulanito -d sistema_ogti -f sql/schema.sql
echo "   Esquema ejecutado"

# 4. Ejecutar el script de inicialización Python
echo "4. Creando usuarios y datos iniciales..."
export DB_HOST=localhost
export DB_USER=fulanito
export DB_PASSWORD=ogti2026
export DB_NAME=sistema_ogti
python3 init_db.py

echo ""
echo "============================================"
echo "✅ PostgreSQL configurado correctamente"
echo "   Base de datos: sistema_ogti"
echo "   Usuario BD: fulanito / ogti2026"
echo ""
echo "   Para iniciar el sistema:"
echo "   export DB_PASSWORD=ogti2026"
echo "   python3 app.py"
echo "============================================"
