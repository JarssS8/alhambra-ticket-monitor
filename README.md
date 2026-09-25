# 🎫 Alhambra Ticket Monitor

Monitor automatizado para detectar disponibilidad de entradas a la Alhambra de Granada y notificar en tiempo real por Telegram, Discord o email.

## ¿Cómo funciona?

1. **Monitorea** la web oficial `https://tickets.alhambra-patronato.es/` a intervalos regulares
2. **Detecta** cuando hay entradas disponibles
3. **Notifica** automáticamente por tus canales preferidos (Telegram, Discord, email)
4. **Registra** el historial de búsquedas en `alhambra_history.json`

## 🚀 Instalación rápida

### Requisitos
- Python 3.8+
- Git (opcional, para clonar el repo)

### Pasos

```bash
# 1. Clonar o descargar el proyecto
git clone https://github.com/TU_USUARIO/alhambra-ticket-monitor.git
cd alhambra-ticket-monitor

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar el archivo de configuración
cp .env.example .env

# 5. Editar .env con tus credenciales (ver sección Configuración más abajo)
nano .env

# 6. ¡Ejecutar!
python monitor.py
```

## ⚙️ Configuración

### Sin notificaciones (solo línea de comandos)
```bash
python monitor.py --once
```

### Con notificaciones automáticas

#### 1️⃣ **Telegram** (recomendado - más fácil)

1. Abre [@BotFather](https://t.me/BotFather) en Telegram
2. Escribe `/newbot` y sigue las instrucciones
3. Copia el token que recibes
4. Abre [@userinfobot](https://t.me/userinfobot) y anota tu `user_id`
5. Edita `.env`:
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=1234567890
```

#### 2️⃣ **Discord**

1. Ve a un servidor donde tengas permisos
2. Settings → Webhooks → New Webhook
3. Copia la URL del webhook
4. Edita `.env`:
```env
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/123456789/abcdefg
```

#### 3️⃣ **Email (Gmail)**

1. Activa 2FA en tu cuenta Google
2. Ve a [App Passwords](https://myaccount.google.com/apppasswords)
3. Crea una contraseña de app y cópiala
4. Edita `.env`:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_SENDER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password_16_caracteres
EMAIL_RECIPIENT=tu_email@gmail.com
```

## 💻 Uso

### Verificación única
```bash
python monitor.py --once
```

### Monitor continuo (intervalo 5 minutos)
```bash
python monitor.py
```

### Monitor con intervalo personalizado (ej: cada 2 minutos)
```bash
python monitor.py --interval 120
```

### Verificar configuración
```bash
python monitor.py --check
```

## 🐳 Usando Docker

```bash
# Construir imagen
docker build -t alhambra-monitor .

# Ejecutar contenedor
docker run -d --name alhambra --env-file .env alhambra-monitor

# Ver logs
docker logs -f alhambra

# Detener
docker stop alhambra
```

## 📋 GitHub Actions (Despliegue automático)

Si subes a GitHub, el monitor se ejecutará automáticamente cada 5 minutos:

1. Sube tu `.env` como secretos en GitHub (Settings → Secrets and variables → Actions)
2. El workflow `.github/workflows/monitor.yml` se ejecutará automáticamente

## 📊 Historial

El historial se guarda en `alhambra_history.json` con formato:
```json
[
  {
    "timestamp": "2024-09-25T14:30:45.123456",
    "ticket_type": "General",
    "available": true,
    "price": "15.00€",
    "url": "https://tickets.alhambra-patronato.es/"
  }
]
```

## 🔍 Logs

Los logs se guardan en `alhambra_monitor.log` y se muestran en consola.

## 📝 Notas

- El monitor evita spam: solo notifica nuevamente si pasaron 6 horas desde la última notificación del mismo tipo
- Se conservan los últimos 7 días de historial
- Recomendado: ejecutar en servidor (AWS, Heroku, VPS) para monitoreo 24/7
- La estructura de la web oficial puede cambiar; el script usa búsqueda genérica de botones de compra

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip install -r requirements.txt
```

### "Error 403" al conectar
Puede ser anti-bot. El script usa User-Agent falso, pero si sigue fallando:
- Espera más entre intentos (aumenta `CHECK_INTERVAL`)
- Usa un proxy VPN

### Notificaciones no llegan
Ejecuta para verificar credenciales:
```bash
python monitor.py --check
```

## 📄 Licencia

MIT - Úsalo libremente

## ✨ Contribuciones

¿Mejoras? Envía un PR. El código es limpio y fácil de extender.

---

**Hecho para no perderse ni una entrada** 🎫✨
