#!/usr/bin/env python3
"""
Script de prueba para verificar que el monitor funciona correctamente
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_imports():
    """Verifica que las dependencias estén instaladas"""
    print("📦 Verificando dependencias...")
    try:
        import requests
        print("  ✅ requests")
        import bs4
        print("  ✅ beautifulsoup4")
        from dotenv import load_dotenv
        print("  ✅ python-dotenv")
        return True
    except ImportError as e:
        print(f"  ❌ {e}")
        print("\n   Instala las dependencias con: pip install -r requirements.txt")
        return False

def test_env_file():
    """Verifica que el archivo .env existe"""
    print("\n📋 Verificando archivo .env...")
    if Path('.env').exists():
        print("  ✅ Archivo .env encontrado")
        return True
    else:
        print("  ❌ Archivo .env no encontrado")
        print("\n   Crea uno con: cp .env.example .env")
        return False

def test_config():
    """Verifica la configuración de notificaciones"""
    print("\n⚙️  Verificando configuración...")
    
    channels = {
        'Telegram': ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'),
        'Discord': ('DISCORD_WEBHOOK_URL',),
        'Email': ('SMTP_SERVER', 'SMTP_SENDER', 'SMTP_PASSWORD', 'EMAIL_RECIPIENT')
    }
    
    configured = []
    
    for name, vars in channels.items():
        if all(os.getenv(var) for var in vars):
            print(f"  ✅ {name} configurado")
            configured.append(name)
        else:
            print(f"  ⚠️  {name} no configurado")
    
    if not configured:
        print("\n  ⚠️  ADVERTENCIA: Sin canales de notificación configurados")
        print("  El monitor funcionará pero solo mostrará en consola")
    
    return len(configured) > 0

def test_web_connection():
    """Verifica que se puede conectar a la web de la Alhambra"""
    print("\n🌐 Verificando conexión a la Alhambra...")
    try:
        import requests
        response = requests.get(
            'https://tickets.alhambra-patronato.es/',
            timeout=5,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200:
            print(f"  ✅ Conexión exitosa (status: {response.status_code})")
            return True
        else:
            print(f"  ❌ Error de conexión (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_monitor_import():
    """Verifica que el monitor se puede importar sin errores"""
    print("\n🤖 Verificando monitor...")
    try:
        from monitor import AlhambraMonitor
        print("  ✅ Monitor importado correctamente")
        return True
    except Exception as e:
        print(f"  ❌ Error al importar monitor: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("🎫 PRUEBA DEL MONITOR DE LA ALHAMBRA")
    print("="*60 + "\n")
    
    results = []
    
    results.append(("Dependencias", test_imports()))
    results.append(("Archivo .env", test_env_file()))
    results.append(("Configuración", test_config()))
    results.append(("Conexión web", test_web_connection()))
    results.append(("Monitor", test_monitor_import()))
    
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        symbol = "✅" if result else "❌"
        print(f"{symbol} {name}")
    
    print("="*60)
    print(f"\nResultado: {passed}/{total} pruebas pasadas\n")
    
    if passed == total:
        print("✨ ¡Todo listo! Ejecuta: python monitor.py")
    elif passed >= total - 1:
        print("⚠️  Casi listo. Revisa los errores arriba.")
    else:
        print("❌ Hay problemas. Revisa los errores arriba.")
        sys.exit(1)

if __name__ == '__main__':
    main()
