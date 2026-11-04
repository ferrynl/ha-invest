"""Personal presentation preferences, isolated from portfolio data and backups."""
import json

MODULES = (
    ('currencies', 'full'), ('market', 'quarter'), ('cost', 'quarter'),
    ('gain', 'quarter'), ('income', 'quarter'), ('notice', 'full'),
    ('chart', 'full'), ('allocation', 'half'), ('movers', 'half'),
    ('holdings', 'full'),
)

CHARTS = frozenset(('value', 'area', 'columns', 'cost', 'invested', 'dividend',
                    'gain', 'return', 'income_value', 'value_invested'))


def chart_preference(data):
    chart = data.get('chart', 'value') if isinstance(data, dict) else 'value'
    if not isinstance(chart, str) or chart not in CHARTS:
        raise ValueError('Ongeldige dashboardindeling.')
    return chart


def defaults():
    return [{'id': key, 'enabled': True, 'width': width} for key, width in MODULES]


def validate(data):
    rows = data.get('modules') if isinstance(data, dict) else None
    known = dict(MODULES)
    if not isinstance(rows, list) or len(rows) > len(known):
        raise ValueError('Ongeldige dashboardindeling.')
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'enabled', 'width'}:
            raise ValueError('Ongeldige dashboardindeling.')
        key = row['id']
        if not isinstance(key, str) or key not in known or key in seen or type(row['enabled']) is not bool or row['width'] not in ('quarter', 'half', 'full'):
            raise ValueError('Ongeldige dashboardindeling.')
        seen.add(key)
        result.append(dict(row))
    return result + [row for row in defaults() if row['id'] not in seen]


def preference_key(user, profile):
    if profile not in ('personal', 'demo'):
        raise ValueError('Ongeldig profiel.')
    owner = user['id'] if user['id'] is not None else 'ha'
    return f'dashboard_layout:v1:{owner}:{profile}'


def read(store, user, profile):
    key = preference_key(user, profile)
    with store.read() as db:
        row = db.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
    try:
        data = json.loads(row[0]) if row else {'modules': defaults()}
        modules = validate(data)
        chart = chart_preference(data)
    except (ValueError, TypeError):
        modules, chart = defaults(), 'value'
    return {'modules': modules, 'chart': chart}


def save(store, user, profile, data):
    key = preference_key(user, profile)
    modules = validate(data)
    with store.connect() as db:
        chart = chart_preference(data)
        if 'chart' not in data:
            row = db.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
            if row:
                try:
                    chart = chart_preference(json.loads(row[0]))
                except (ValueError, TypeError):
                    pass
        result = {'modules': modules, 'chart': chart}
        db.execute('INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(result)))
    return result
