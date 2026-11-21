"""Weekend guards use the listing's local calendar, independently of host time."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MARKET_ZONES = {
    'AMSTERDAM': 'Europe/Amsterdam', 'BRUSSELS': 'Europe/Brussels',
    'DUBLIN': 'Europe/Dublin', 'MADRID': 'Europe/Madrid',
    'XETRA': 'Europe/Berlin', 'FRANKFURT': 'Europe/Berlin',
    'PARIS': 'Europe/Paris', 'MILAN': 'Europe/Rome',
    'LONDON': 'Europe/London', 'SWISS': 'Europe/Zurich',
    'NASDAQ': 'America/New_York', 'NYSE': 'America/New_York',
    'NYSEARCA': 'America/New_York', 'AMEX': 'America/New_York',
    'OTC': 'America/New_York', 'TOKYO': 'Asia/Tokyo',
    'TORONTO': 'America/Toronto', 'ASX': 'Australia/Sydney',
    'HONG KONG': 'Asia/Hong_Kong', 'COPENHAGEN': 'Europe/Copenhagen',
    'STOCKHOLM': 'Europe/Stockholm',
}


def market_weekend(exchange, moment=None):
    moment = moment or datetime.now(timezone.utc)
    try:
        zone = ZoneInfo(MARKET_ZONES.get(exchange, 'UTC'))
    except ZoneInfoNotFoundError:
        zone = timezone.utc
    return moment.astimezone(zone).weekday() >= 5
