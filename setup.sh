#!/bin/bash

echo "🎫 Alhambra Ticket Monitor - Setup"
echo "=================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo primero:"
    echo "   https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Crear venv
echo "📦 Creando entorno virtual..."
python3 -m venv venv

# Activar venv
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -q -r requirements.txt

# Copiar .env
if [ ! -f .env ]; then
    echo "📋 Creando archivo .env..."
    cp .env.example .env
    echo "   Edita .env con tus credenciales"
else
    echo "✅ .env ya existe"
fi

echo ""
echo "=================================="
echo "✅ Instalación completada"
echo "=================================="
echo ""
echo "Próximos pasos:"
echo "1. Edita .env con tus credenciales (Telegram, Discord, email)"
echo "2. Ejecuta: python monitor.py --check"
echo "3. Inicia el monitor: python monitor.py"
echo ""
