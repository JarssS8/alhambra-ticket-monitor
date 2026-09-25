#!/usr/bin/env python3
"""
Monitor de precios - tickets.alhambra-patronato.es
- Descarga la web con Obscura (navegador headless en Rust; curl/requests reciben 403)
- Extrae el precio de cada producto (enlaces /producto/... "Comprar entradas | X€")
- Loguea TODOS los precios en cada ejecución
- Avisa por Discord mencionando al usuario SOLO si algún precio baja
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://tickets.alhambra-patronato.es/"
OBSCURA_BIN = os.getenv("OBSCURA_BIN", "./obscura")
STATE_FILE = Path(os.getenv("STATE_FILE", "state/prices.json"))
WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
USER_ID = os.getenv("DISCORD_USER_ID", "").strip()
TEST_DROP = os.getenv("TEST_DROP", "").lower() == "true"

PRICE_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*€")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


def fetch_html(retries: int = 4) -> str:
    """Obscura en modo stealth. La web a veces sirve un reto anti-bot;
    la cookie que deja se guarda en --storage-dir y el siguiente intento pasa."""
    storage = os.getenv("OBSCURA_STORAGE", "obscura-storage")
    out_file = Path("page.html")
    for attempt in range(1, retries + 1):
        out_file.unlink(missing_ok=True)
        try:
            proc = subprocess.run(
                [OBSCURA_BIN, "--stealth", "--storage-dir", storage, "fetch", URL,
                 "--dump", "html", "--wait", str(4 + 3 * attempt), "--timeout", "45",
                 "--quiet", "--output", str(out_file)],
                capture_output=True, text=True, timeout=120,
            )
            html = out_file.read_text(errors="ignore") if out_file.exists() else ""
            if "/producto/" in html:
                log(f"Página obtenida en el intento {attempt}")
                return html
            title = re.search(r"<title>(.*?)</title>", html, re.S)
            log(f"Intento {attempt}: sin productos ({len(html)} bytes, título: "
                f"{title.group(1).strip()[:60] if title else '-'}) {proc.stderr[-150:].strip()}")
        except subprocess.TimeoutExpired:
            log(f"Intento {attempt}: timeout")
        time.sleep(5 * attempt)
    raise RuntimeError("No se pudo obtener la página con productos tras varios intentos")


def pretty_name(slug: str) -> str:
    return slug.replace("-", " ").strip().capitalize()


def parse_prices(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    prices = {}
    for a in soup.find_all("a", href=True):
        m_slug = re.search(r"/producto/([^/?#]+)", a["href"])
        m_price = PRICE_RE.search(a.get_text(" ", strip=True))
        if m_slug and m_price:
            slug = m_slug.group(1)
            prices[slug] = {
                "name": pretty_name(slug),
                "price": float(m_price.group(1).replace(",", ".")),
                "url": a["href"],
            }
    return prices


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(prices: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(
        {"updated": datetime.now(timezone.utc).isoformat(), "prices": prices},
        indent=2, ensure_ascii=False))


def notify_discord(drops: list, test: bool) -> None:
    if not WEBHOOK:
        log("⚠️ DISCORD_WEBHOOK_URL no configurado, no se envía aviso")
        return
    mention = f"<@{USER_ID}> " if USER_ID else ""
    prefix = "🧪 [PRUEBA] " if test else ""
    fields = [{
        "name": d["name"],
        "value": f"~~{d['old']:.2f}€~~ → **{d['new']:.2f}€** (−{d['old'] - d['new']:.2f}€)\n[Comprar]({d['url']})",
        "inline": False,
    } for d in drops]
    payload = {
        "content": f"{mention}{prefix}💰 ¡Ha bajado el precio de {len(drops)} entrada(s) de la Alhambra!",
        "allowed_mentions": {"users": [USER_ID] if USER_ID else []},
        "embeds": [{
            "title": "Bajada de precio - Alhambra",
            "url": URL,
            "color": 0x2ECC71,
            "fields": fields[:25],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
    }
    r = requests.post(WEBHOOK, json=payload, timeout=10)
    if r.status_code in (200, 204):
        log("✅ Aviso enviado a Discord")
    else:
        log(f"❌ Discord respondió {r.status_code}: {r.text[:200]}")
        sys.exit(1)


def main() -> None:
    log(f"Consultando {URL} con Obscura...")
    current = parse_prices(fetch_html())
    if not current:
        log("❌ No se encontraron precios: la estructura de la web puede haber cambiado")
        sys.exit(1)

    previous = load_state().get("prices", {})
    if TEST_DROP:
        log("🧪 TEST_DROP activo: simulo que antes todo costaba 1€ más")
        previous = {k: {**v, "price": v["price"] + 1} for k, v in current.items()}

    log("=" * 60)
    log(f"📊 PRECIOS ACTUALES ({len(current)} productos):")
    drops = []
    for slug, info in sorted(current.items(), key=lambda kv: kv[1]["name"]):
        old = previous.get(slug, {}).get("price")
        tag = "(nuevo)" if old is None else ("= sin cambio" if old == info["price"]
              else f"{'⬇️ BAJA' if info['price'] < old else '⬆️ sube'} (antes {old:.2f}€)")
        log(f"  • {info['name']}: {info['price']:.2f}€  {tag}")
        if old is not None and info["price"] < old:
            drops.append({"name": info["name"], "old": old, "new": info["price"], "url": info["url"]})
    log("=" * 60)

    if drops:
        notify_discord(drops, TEST_DROP)
    else:
        log("Sin bajadas de precio → no se menciona en Discord")

    if not TEST_DROP:
        save_state(current)


if __name__ == "__main__":
    main()
