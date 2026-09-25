# 🚀 Despliegue en servidor (Monitoreo 24/7)

Para que el monitor funcione sin necesidad de que tu ordenador esté encendido.

## Opción 1: GitHub Actions (GRATIS - Recomendado)

Ya está configurado. Solo necesitas:

1. Hacer **fork** del repo en GitHub
2. Ir a **Settings → Secrets and variables → Actions**
3. Agregar tus secretos (las variables de `.env`)
4. Activar Actions (si no está activado)
5. ¡Listo! Se ejecutará cada 5 minutos automáticamente

**Ventajas:**
- ✅ Completamente gratis
- ✅ Sin configuración de servidor
- ✅ Historial guardado en artifacts

**Limitaciones:**
- ~2000 minutos/mes gratuitos (suficiente para 5 minutos cada 5 min)
- El historial se borra después de 7 días

## Opción 2: Heroku (Aprox 5€/mes)

### Requisitos
- Cuenta en [Heroku](https://www.heroku.com)
- Git instalado localmente

### Pasos

```bash
# 1. Inicializar como repo de Heroku (si no lo es)
git init
git add .
git commit -m "Initial commit"

# 2. Crear app en Heroku
heroku login
heroku create nombre-de-tu-app

# 3. Agregar variables de entorno
heroku config:set TELEGRAM_BOT_TOKEN="tu_token"
heroku config:set TELEGRAM_CHAT_ID="tu_id"
# ... agregar el resto de variables

# 4. Ver la configuración
heroku config

# 5. Desplegar
git push heroku main

# 6. Ver logs en tiempo real
heroku logs -t
```

**Para que se ejecute cada X minutos (Procfile ya configurado):**

El archivo `Procfile` ya contiene:
```
release: python monitor.py --once
```

Para ejecutar periódicamente usa:
```bash
heroku addons:create scheduler:standard
heroku run python monitor.py --once  # Ejecuta manual
```

O mejor: usa Heroku Scheduler (addon gratuito):
```bash
# Dashboard → Resources → Add-ons → Heroku Scheduler
# Agregar tarea: python monitor.py --once
# Frecuencia: Every 10 minutes
```

## Opción 3: VPS (DigitalOcean, Linode, etc.)

Aprox 5-20€/mes según el proveedor

### En la VPS (Ubuntu/Debian)

```bash
# 1. SSH a tu VPS
ssh root@tu_servidor_ip

# 2. Actualizar
apt update && apt upgrade -y

# 3. Instalar Python y Git
apt install -y python3-pip python3-venv git

# 4. Clonar el proyecto
cd /opt
git clone https://github.com/tu_usuario/alhambra-ticket-monitor.git
cd alhambra-ticket-monitor

# 5. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Crear archivo .env
cp .env.example .env
nano .env  # Editar con tus credenciales

# 7. Crear servicio systemd
cat > /etc/systemd/system/alhambra-monitor.service << EOF
[Unit]
Description=Alhambra Ticket Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/alhambra-ticket-monitor
ExecStart=/opt/alhambra-ticket-monitor/venv/bin/python /opt/alhambra-ticket-monitor/monitor.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

# 8. Habilitar y iniciar el servicio
systemctl daemon-reload
systemctl enable alhambra-monitor
systemctl start alhambra-monitor

# 9. Ver estado
systemctl status alhambra-monitor

# 10. Ver logs
journalctl -u alhambra-monitor -f
```

## Opción 4: Docker (en VPS o local)

```bash
# En tu servidor (con Docker instalado)
docker run -d \
  --name alhambra-monitor \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN="tu_token" \
  -e TELEGRAM_CHAT_ID="tu_id" \
  -v alhambra-data:/app/data \
  tu_usuario/alhambra-monitor:latest
```

O con docker-compose:

```bash
cd /opt/alhambra-ticket-monitor
docker-compose up -d
docker-compose logs -f
```

## Opción 5: AWS Lambda (Gratis primer año)

Para ejecución programada sin servidor:

1. Crear función Lambda con Python 3.11
2. Copiar código de `monitor.py`
3. Configurar trigger CloudWatch Events (cada 5 minutos)
4. Agregar capas para dependencias (requests, bs4)
5. Variables de entorno para credenciales

[Guía detallada AWS](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)

## Comparación

| Opción | Costo | Configuración | Ventajas |
|--------|-------|---------------|----------|
| **GitHub Actions** | Gratis | ⭐ Muy fácil | Sin servidor, historial |
| **Heroku** | 5-50€ | ⭐⭐ Fácil | Fácil de manejar |
| **VPS** | 5-20€ | ⭐⭐⭐ Media | Control total, historial 24/7 |
| **Docker** | Varía | ⭐⭐ Media | Portable, escalable |
| **AWS Lambda** | Gratis* | ⭐⭐⭐⭐ Difícil | Pago por uso |

*AWS: gratis 1M solicitudes/mes

## Monitoreo del monitor

Para asegurarte que está funcionando:

```bash
# Ver últimas búsquedas
tail -f alhambra_monitor.log

# Verificar historial
cat alhambra_history.json | jq '.[-5:]'

# Ver si el proceso está corriendo
ps aux | grep monitor.py
```

## Troubleshooting despliegue

### "502 Bad Gateway" en Heroku
```bash
heroku logs --tail
# Revisa si hay errores de dependencias
```

### El servicio systemd no inicia
```bash
journalctl -xe  # Ver error específico
systemctl status alhambra-monitor
```

### GitHub Actions no ejecuta
1. Ve a Actions → Tu workflow
2. Revisa si pasó los últimos 5 minutos
3. Clica "Run workflow" manualmente para testear
4. Verifica que tienes secretos configurados

### No recibe notificaciones
```bash
# Ejecuta prueba
python test.py

# O manualmente:
python monitor.py --check
python monitor.py --once
```

## Mantenimiento

```bash
# Actualizar código
git pull origin main

# Si usas Heroku
git push heroku main

# Si usas systemd
systemctl restart alhambra-monitor

# Limpiar historial viejo (opcional)
rm alhambra_history.json
```

---

¡Elige la opción que mejor se adapte a ti! 🚀
