#!/usr/bin/env python3
"""
Monitor de precios - tickets.alhambra-patronato.es
- Descarga la web con requests resolviendo el reto anti-bot de TransparentEdge
  (proof-of-work SHA-256); Obscura como respaldo
- Extrae el precio de cada producto (enlaces /producto/... "Comprar entradas | X€")
- Loguea TODOS los precios en cada ejecución
- Avisa por Discord mencionando al usuario SOLO si algún precio baja
"""
import hashlib
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


CHALLENGE_RE = re.compile(r'"([0-9a-f]{64})~([0-9a-f]+)~(\d+)~(\d+)"')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def solve_challenge(html: str):
    """Reto proof-of-work de TransparentEdge: nonce tal que
    sha256(f"{seed}:{ts}~{nonce}") empiece por `difficulty`. Cookie TEDGEUA = f"{ts}~{nonce}"."""
    m = CHALLENGE_RE.search(html)
    if not m:
        return None
    seed, difficulty, ts, _ttl = m.groups()
    prefix = f"{seed}:{ts}~"
    nonce = 0
    while not hashlib.sha256(f"{prefix}{nonce}".encode()).hexdigest().startswith(difficulty):
        nonce += 1
    return f"{ts}~{nonce}"


def fetch_with_requests(retries: int = 3) -> str:
    session = requests.Session()
    session.headers.update(HEADERS)
    for attempt in range(1, retries + 1):
        r = session.get(URL, timeout=20)
        if "/producto/" in r.text:
            log(f"Página obtenida (requests, intento {attempt}, HTTP {r.status_code})")
            return r.text
        cookie = solve_challenge(r.text)
        if not cookie:
            log(f"requests intento {attempt}: HTTP {r.status_code} sin reto reconocible")
            time.sleep(3)
            continue
        log(f"requests intento {attempt}: reto anti-bot resuelto (TEDGEUA={cookie})")
        domain = "tickets.alhambra-patronato.es"
        session.cookies.set("TEDGEUA", cookie, domain=domain, path="/")
        session.cookies.set("TEDGEUAS", cookie, domain=domain, path="/")
        time.sleep(1)
    return ""


def fetch_with_obscura() -> str:
    out_file = Path("page.html")
    out_file.unlink(missing_ok=True)
    subprocess.run(
        [OBSCURA_BIN, "--stealth", "fetch", URL, "--dump", "html", "--wait", "10",
         "--quiet", "--output", str(out_file)],
        capture_output=True, text=True, timeout=120,
    )
    html = out_file.read_text(errors="ignore") if out_file.exists() else ""
    if "/producto/" in html:
        log("Página obtenida (Obscura)")
    return html


def fetch_html() -> str:
    try:
        html = fetch_with_requests()
        if html:
            return html
    except requests.RequestException as e:
        log(f"requests falló: {e}")
    if Path(OBSCURA_BIN).exists():
        log("Probando respaldo con Obscura...")
        html = fetch_with_obscura()
        if "/producto/" in html:
            return html
    raise RuntimeError("No se pudo obtener la página con productos")


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
    log(f"Consultando {URL} ...")
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
