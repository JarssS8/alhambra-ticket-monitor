# Alhambra price monitor

Revisa cada 5 minutos (GitHub Actions) los precios de https://tickets.alhambra-patronato.es/
y avisa por Discord, mencionando al usuario, **solo si algún precio baja**.

- La web está protegida por un reto proof-of-work de TransparentEdge; `monitor.py` lo resuelve
  (SHA-256) y usa [Obscura](https://github.com/h4ckf0r0day/obscura) como respaldo.
- Todos los precios se muestran en los logs de cada ejecución.
- El último precio conocido se guarda en la rama `state` (`prices.json`).

## Secrets
`DISCORD_WEBHOOK_URL`, `DISCORD_USER_ID`

## Probar el aviso
Actions → *Alhambra price monitor* → Run workflow → marcar **test_drop**.

## Local
```bash
pip install -r requirements.txt
DISCORD_WEBHOOK_URL=... DISCORD_USER_ID=... STATE_FILE=state/prices.json python monitor.py
```
