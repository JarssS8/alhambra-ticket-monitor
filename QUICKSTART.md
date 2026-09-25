# ⚡ Inicio Rápido (5 minutos)

## Opción 1: Línea de comandos (más fácil para probar)

```bash
# Descargar/clonar el proyecto
git clone https://github.com/tu_usuario/alhambra-ticket-monitor.git
cd alhambra-ticket-monitor

# Instalar
./setup.sh

# Editar credenciales (opcional)
nano .env

# ¡Ejecutar!
source venv/bin/activate
python monitor.py
```

## Opción 2: Docker (si tienes Docker)

```bash
# Descargar el proyecto
git clone https://github.com/tu_usuario/alhambra-ticket-monitor.git
cd alhambra-ticket-monitor

# Editar .env
cp .env.example .env
nano .env

# Ejecutar con Docker
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## Opción 3: GitHub Actions (completamente automático)

1. Haz **fork** del proyecto en GitHub
2. Ve a **Settings → Secrets and variables → Actions**
3. Agrega secretos (igual que las variables en `.env`):
   - `TELEGRAM_BOT_TOKEN` (opcional)
   - `TELEGRAM_CHAT_ID` (opcional)
   - `DISCORD_WEBHOOK_URL` (opcional)
   - etc.
4. ¡Listo! Se ejecutará automáticamente cada 5 minutos

## Configuración por servicio (elige uno)

### 🔔 Telegram (recomendado - más rápido)

1. Abre Telegram y busca `@BotFather`
2. Envía `/newbot`
3. Sigue las instrucciones y copia el TOKEN
4. Busca `@userinfobot` y anota tu ID
5. En `.env`:
```env
TELEGRAM_BOT_TOKEN=TU_TOKEN_AQUI
TELEGRAM_CHAT_ID=TU_ID_AQUI
```

### 🎮 Discord

1. Clic derecho en tu servidor → Webhooks → New Webhook
2. Copia la URL
3. En `.env`:
```env
DISCORD_WEBHOOK_URL=LA_URL_AQUI
```

### 📧 Gmail

1. Activa 2FA en tu cuenta Google
2. Genera [App Password](https://myaccount.google.com/apppasswords)
3. En `.env`:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_SENDER=tu_email@gmail.com
SMTP_PASSWORD=TU_APP_PASSWORD_16_CARACTERES
EMAIL_RECIPIENT=tu_email@gmail.com
```

## Verificar que funciona

```bash
# Prueba rápida (verifica una sola vez)
python monitor.py --once

# Verifica la configuración
python monitor.py --check

# Ejecuta pruebas
python test.py
```

## Monitor continuo

```bash
# Ejecutar hasta que lo detengas (Ctrl+C)
python monitor.py

# Con intervalo personalizado (ej: 2 minutos)
python monitor.py --interval 120
```

## 🔗 Dónde poner esto para monitoreo 24/7

Si quieres que se ejecute sin que tu ordenador esté encendido:

- **GitHub Actions** (gratis, incluido en el proyecto)
- **Heroku** (free tier requiere tarjeta, pero muy fácil)
- **AWS Lambda** (gratis primer año)
- **VPS** (5€/mes en Linode, DigitalOcean, etc.)

## 📞 Ayuda

```bash
# Ver todas las opciones
python monitor.py --help

# Ver logs
tail -f alhambra_monitor.log

# Ejecutar pruebas
python test.py
```

## ❌ Si algo no funciona

1. Ejecuta `python test.py` para diagnósticos
2. Revisa `alhambra_monitor.log`
3. Verifica que `.env` está completo
4. Instala dependencias: `pip install -r requirements.txt`

---

¿Preguntas? Abre un **issue** en GitHub 🐛
