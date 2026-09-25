#!/usr/bin/env python3
"""
Alhambra Ticket Monitor - Monitorea disponibilidad de entradas en tiempo real
Notifica por Telegram, Discord o email cuando hay disponibilidad
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Selenium para navegador real (evitar WAF/403)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('alhambra_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TicketInfo:
    """Estructura para guardar información de entradas"""
    timestamp: str
    ticket_type: str
    available: bool
    price: Optional[str] = None
    price_float: Optional[float] = None  # Para comparar cambios
    url: str = "https://tickets.alhambra-patronato.es/"


class AlhambraMonitor:
    """Monitor de disponibilidad de entradas de la Alhambra"""
    
    def __init__(self):
        self.base_url = "https://tickets.alhambra-patronato.es/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.history_file = Path('alhambra_history.json')
        self.last_notification = {}
        
        # Configurar notificaciones
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'sender': os.getenv('SMTP_SENDER'),
            'password': os.getenv('SMTP_PASSWORD'),
            'recipient': os.getenv('EMAIL_RECIPIENT')
        }
        
        logger.info("Monitor inicializado")
    
    def check_availability(self) -> List[TicketInfo]:
        """Verifica disponibilidad de entradas usando Selenium (evita WAF/403)"""
        tickets = []
        driver = None
        
        try:
            logger.info(f"Abriendo navegador Chrome para {self.base_url}...")
            
            # Configurar opciones de Chrome
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Modo headless (sin ventana)
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Crear driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # Cargar página
            logger.info("Cargando página...")
            driver.get(self.base_url)
            
            # Esperar a que cargue contenido (max 10 segundos)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: len(d.page_source) > 500
                )
                logger.info("✅ Página cargada correctamente")
            except:
                logger.warning("⚠️ Timeout esperando contenido, continuando...")
            
            # Obtener HTML después de que JavaScript se ejecute
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Buscar botones de compra
            buy_buttons = soup.find_all('button', {'class': ['buy', 'comprar', 'add-to-cart']})
            
            logger.info(f"Botones encontrados: {len(buy_buttons)}")
            
            # Si hay botones de compra, las entradas están disponibles
            if buy_buttons:
                for btn in buy_buttons:
                    ticket_type = self._extract_ticket_type(btn)
                    price_str, price_float = self._extract_price(btn)
                    
                    tickets.append(TicketInfo(
                        timestamp=datetime.now().isoformat(),
                        ticket_type=ticket_type,
                        available=True,
                        price=price_str,
                        price_float=price_float
                    ))
            
            # Fallback: buscar texto "sold out" o "agotado"
            page_text = soup.get_text().lower()
            if 'agotado' in page_text or 'sold out' in page_text:
                if not tickets:
                    tickets.append(TicketInfo(
                        timestamp=datetime.now().isoformat(),
                        ticket_type='General',
                        available=False
                    ))
            
            # Si no encuentra nada, buscar precios con €
            if not tickets:
                prices = soup.find_all(string=lambda x: '€' in str(x) if x else False)
                if prices:
                    logger.info(f"Precios encontrados en la página: {len(prices)}")
                    tickets.append(TicketInfo(
                        timestamp=datetime.now().isoformat(),
                        ticket_type='General',
                        available=True,
                        price=str(prices[0]).strip() if prices else None
                    ))
                else:
                    logger.warning("⚠️ No se encontraron precios en la página")
                    tickets.append(TicketInfo(
                        timestamp=datetime.now().isoformat(),
                        ticket_type='General',
                        available=True
                    ))
            
            logger.info(f"✅ Verificación realizada: {len(tickets)} tipos de entrada encontrados")
            
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            return []
        finally:
            # Cerrar el navegador
            if driver:
                try:
                    driver.quit()
                    logger.info("Navegador cerrado")
                except:
                    pass
        
        return tickets
    
    def _extract_ticket_type(self, element) -> str:
        """Extrae el tipo de entrada del elemento HTML"""
        text = element.get_text().strip()
        if 'noche' in text.lower() or 'night' in text.lower():
            return 'Nocturna'
        elif 'dobla' in text.lower():
            return 'Dobla de Oro'
        return 'General'
    
    def _extract_price(self, element) -> tuple[Optional[str], Optional[float]]:
        """Extrae el precio del elemento HTML (retorna string y float)"""
        parent = element.find_parent(['div', 'article', 'section'])
        if parent:
            price_text = parent.find(string=lambda x: '€' in str(x) if x else False)
            if price_text:
                price_str = str(price_text).strip()
                try:
                    # Extrae el número del formato "15.00€" o "15€"
                    import re
                    match = re.search(r'(\d+[.,]\d+|\d+)', price_str)
                    if match:
                        price_float = float(match.group(1).replace(',', '.'))
                        return price_str, price_float
                except (ValueError, AttributeError):
                    pass
                return price_str, None
        return None, None
    
    def get_price_changes(self, tickets: List[TicketInfo]) -> Dict[str, dict]:
        """Detecta qué precios bajaron comparando con el historial"""
        changes = {}
        
        if not self.history_file.exists():
            return changes
        
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return changes
        
        # Agrupar último precio por tipo de entrada
        last_prices = {}
        for h in reversed(history):  # Desde más reciente
            ticket_type = h.get('ticket_type')
            price_float = h.get('price_float')
            
            if ticket_type and price_float and ticket_type not in last_prices:
                last_prices[ticket_type] = price_float
        
        # Comparar con los nuevos precios
        for ticket in tickets:
            if ticket.available and ticket.price_float:
                old_price = last_prices.get(ticket.ticket_type)
                
                if old_price and ticket.price_float < old_price:
                    # El precio bajó
                    change_percent = ((old_price - ticket.price_float) / old_price) * 100
                    changes[ticket.ticket_type] = {
                        'old_price': old_price,
                        'new_price': ticket.price_float,
                        'change_percent': change_percent,
                        'price_str': ticket.price
                    }
                    logger.info(f"💰 PRECIO BAJÓ: {ticket.ticket_type} de {old_price}€ a {ticket.price_float}€ ({change_percent:.1f}%)")
        
        return changes
    
    def save_history(self, tickets: List[TicketInfo]):
        """Guarda el historial de búsquedas"""
        history = []
        
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                history = []
        
        history.extend([asdict(t) for t in tickets])
        
        # Guardar solo los últimos 7 días
        cutoff_time = time.time() - (7 * 86400)
        history = [
            h for h in history 
            if datetime.fromisoformat(h['timestamp']).timestamp() > cutoff_time
        ]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def notify(self, tickets: List[TicketInfo], price_changes: Dict = None):
        """Envía notificaciones por todos los canales disponibles"""
        available_tickets = [t for t in tickets if t.available]
        
        # Mostrar todos los precios en logs
        logger.info("=" * 60)
        logger.info("📊 PRECIOS ACTUALES:")
        for ticket in available_tickets:
            precio_info = f"{ticket.price}" if ticket.price else "N/A"
            logger.info(f"  • {ticket.ticket_type}: {precio_info}")
        logger.info("=" * 60)
        
        if not available_tickets:
            logger.info("Sin entradas disponibles en este momento")
            return
        
        # Detectar cambios de precio
        if price_changes is None:
            price_changes = self.get_price_changes(available_tickets)
        
        # Solo notificar si hay cambios de precio O es la primera notificación
        if not price_changes:
            logger.debug("Sin cambios de precio, saltando notificación")
            return
        
        message = self._build_message(available_tickets, price_changes)
        
        if self.telegram_token and self.telegram_chat_id:
            self._notify_telegram(message)
        
        if self.discord_webhook:
            self._notify_discord(message, available_tickets, price_changes)
        
        if all(self.smtp_config.values()):
            self._notify_email(message, available_tickets, price_changes)
        
        if not (self.telegram_token or self.discord_webhook or self.smtp_config['server']):
            logger.warning("⚠️  PRECIOS BAJARON, pero sin canales de notificación configurados")
            print("\n" + "="*60)
            print("💰 ¡PRECIOS BAJARON!")
            print("="*60)
            print(message)
            print("="*60 + "\n")
    
    def _build_message(self, tickets: List[TicketInfo], price_changes: Dict = None) -> str:
        """Construye el mensaje de notificación"""
        message = "💰 ¡PRECIOS BAJARON EN LA ALHAMBRA!\n\n"
        
        for ticket in tickets:
            message += f"📅 {ticket.ticket_type}\n"
            if ticket.price:
                message += f"💵 Precio actual: {ticket.price}\n"
                
                # Mostrar cambio de precio si existe
                if price_changes and ticket.ticket_type in price_changes:
                    change = price_changes[ticket.ticket_type]
                    message += f"⬇️  Anterior: {change['old_price']:.2f}€\n"
                    message += f"📊 Descuento: {change['change_percent']:.1f}%\n"
            
            message += f"🔗 {ticket.url}\n\n"
        
        message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message
    
    def _notify_telegram(self, message: str):
        """Envía notificación por Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ Notificación Telegram enviada")
            else:
                logger.error(f"❌ Error Telegram: {response.text}")
        except Exception as e:
            logger.error(f"❌ Error enviando Telegram: {e}")
    
    def _notify_discord(self, message: str, tickets: List[TicketInfo], price_changes: Dict = None):
        """Envía notificación por Discord con mención al usuario"""
        try:
            # User ID de Discord a mencionar
            discord_user_id = os.getenv('DISCORD_USER_ID', '156445717068644352')
            mention = f"<@{discord_user_id}>"
            
            # Construir campos con cambios de precio
            fields = []
            
            for ticket in tickets:
                field_value = f"Precio: {ticket.price or 'N/A'}\n"
                
                if price_changes and ticket.ticket_type in price_changes:
                    change = price_changes[ticket.ticket_type]
                    field_value += f"Anterior: {change['old_price']:.2f}€\n"
                    field_value += f"Descuento: ⬇️ {change['change_percent']:.1f}%"
                
                fields.append({
                    "name": f"📅 {ticket.ticket_type}",
                    "value": field_value,
                    "inline": True
                })
            
            fields.append({
                "name": "Enlace",
                "value": f"[Comprar entradas]({tickets[0].url})",
                "inline": False
            })
            
            embeds = [{
                "title": "💰 ¡PRECIOS BAJARON EN LA ALHAMBRA!",
                "description": mention,
                "color": 0xFFD700,  # Oro
                "fields": fields,
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "Monitor Alhambra"}
            }]
            
            payload = {"embeds": embeds}
            response = requests.post(self.discord_webhook, json=payload, timeout=5)
            
            if response.status_code == 204:
                logger.info(f"✅ Notificación Discord enviada mencionando usuario {discord_user_id}")
            else:
                logger.error(f"❌ Error Discord: {response.text}")
        except Exception as e:
            logger.error(f"❌ Error enviando Discord: {e}")
    
    def _notify_email(self, message: str, tickets: List[TicketInfo], price_changes: Dict = None):
        """Envía notificación por email"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "💰 Precios bajaron en la Alhambra"
            msg['From'] = self.smtp_config['sender']
            msg['To'] = self.smtp_config['recipient']
            
            # Construir tabla HTML con precios
            price_rows = ""
            for ticket in tickets:
                change_info = ""
                if price_changes and ticket.ticket_type in price_changes:
                    change = price_changes[ticket.ticket_type]
                    change_info = f"""
                    <tr style="background-color: #fff3cd;">
                        <td>Anterior:</td>
                        <td>{change['old_price']:.2f}€</td>
                    </tr>
                    <tr style="background-color: #fff3cd;">
                        <td>Descuento:</td>
                        <td>⬇️ {change['change_percent']:.1f}%</td>
                    </tr>
                    """
                
                price_rows += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;"><strong>{ticket.ticket_type}</strong></td>
                    <td style="padding: 8px;">{ticket.price or 'N/A'}</td>
                </tr>
                {change_info}
                """
            
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2 style="color: #ff9800;">💰 ¡Precios bajaron en la Alhambra!</h2>
                    <table style="border-collapse: collapse; width: 100%;">
                        <tr style="background-color: #f0f0f0;">
                            <th style="padding: 8px; text-align: left;">Tipo</th>
                            <th style="padding: 8px; text-align: left;">Precio</th>
                        </tr>
                        {price_rows}
                    </table>
                    <p><strong>Compra aquí:</strong> <a href="{tickets[0].url}">{tickets[0].url}</a></p>
                    <p><small>Detectado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
                </body>
            </html>
            """
            
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['sender'], self.smtp_config['password'])
                server.send_message(msg)
            
            logger.info("✅ Notificación email enviada")
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
    
    def run(self, interval: int = 300, max_iterations: Optional[int] = None):
        """Ejecuta el monitor continuamente"""
        logger.info(f"Iniciando monitor (intervalo: {interval}s)")
        logger.info(f"🔗 Discord webhook configurado: {bool(self.discord_webhook)}")
        logger.info(f"📊 Detectando cambios de precio y notificando en Discord...")
        iteration = 0
        
        try:
            while True:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"Verificación #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*60}")
                
                tickets = self.check_availability()
                
                if tickets:
                    # Detectar cambios de precio
                    price_changes = self.get_price_changes(tickets)
                    
                    # Guardar historial
                    self.save_history(tickets)
                    
                    # Notificar solo si hay cambios de precio
                    if price_changes:
                        self.notify(tickets, price_changes)
                    else:
                        # Mostrar precios en logs aunque no haya cambios
                        available_tickets = [t for t in tickets if t.available]
                        if available_tickets:
                            logger.info("📊 Precios sin cambios (no hay mención):")
                            for ticket in available_tickets:
                                logger.info(f"  • {ticket.ticket_type}: {ticket.price or 'N/A'}")
                else:
                    logger.warning("⚠️  No se pudo conectar o las entradas no están disponibles")
                
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Alcanzado límite de {max_iterations} iteraciones")
                    break
                
                logger.info(f"⏱️  Próxima verificación en {interval}s ({interval//60}m)")
                time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("⛔ Monitor detenido por el usuario")
        except Exception as e:
            logger.error(f"Error fatal: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Punto de entrada principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor de entradas de la Alhambra de Granada'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Intervalo de verificación en segundos (default: 300)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Verificar solo una vez y salir'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Verificar configuración y salir'
    )
    
    args = parser.parse_args()
    
    monitor = AlhambraMonitor()
    
    if args.check:
        print("\n" + "="*60)
        print("VERIFICACIÓN DE CONFIGURACIÓN")
        print("="*60)
        print(f"✅ Telegram: {'Configurado' if monitor.telegram_token else '❌ No configurado'}")
        print(f"✅ Discord: {'Configurado' if monitor.discord_webhook else '❌ No configurado'}")
        print(f"✅ Email: {'Configurado' if monitor.smtp_config['server'] else '❌ No configurado'}")
        print("="*60 + "\n")
        return
    
    if args.once:
        tickets = monitor.check_availability()
        print(json.dumps([asdict(t) for t in tickets], indent=2, ensure_ascii=False))
    else:
        monitor.run(interval=args.interval)


if __name__ == '__main__':
    main()
