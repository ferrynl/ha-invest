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


def automatic_window(moment=None):
    """The installation owner requested Dutch weekdays, 08:00 up to 22:00."""
    moment = moment or datetime.now(timezone.utc)
    local = moment.astimezone(ZoneInfo('Europe/Amsterdam'))
    return local.weekday() < 5 and 8 <= local.hour < 22


def claim_refresh(store, interval, key='personal'):
    """Persist the automatic round budget before I/O, also across restarts."""
    import time
    if not automatic_window():
        return False
    stamp = time.time()
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute(
            "SELECT expires_at FROM api_cache WHERE namespace='automatic-market' AND cache_key=?",
            (key,),
        ).fetchone()
        if previous and previous[0] > stamp:
            return False
        db.execute(
            'INSERT OR REPLACE INTO api_cache VALUES(?,?,?,?,?)',
            ('automatic-market', key, '{}', stamp, stamp + max(900, interval)),
        )
    return True
