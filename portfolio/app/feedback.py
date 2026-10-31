"""Public GitHub issues; never send credentials or portfolio context."""
import json
import time
from threading import RLock
from urllib.request import Request, urlopen
from persistent_cache import cached_json

REPOSITORY = 'https://github.com/ferrynl/ha-invest'
API = 'https://api.github.com/repos/ferrynl/ha-invest/issues?state=all&sort=updated&direction=desc&per_page=100'
_lock = RLock()
_retry_after = 0

def overview(store):
    def load():
        global _retry_after
        with _lock:
            if time.monotonic() < _retry_after:
                raise ValueError('GitHub is tijdelijk niet beschikbaar. Probeer het later opnieuw.')
            try:
                request = Request(API, headers={'Accept':'application/vnd.github+json','User-Agent':'Home-Invest-feedback'})
                with urlopen(request, timeout=10) as response:
                    raw = response.read(2000001)
                if len(raw) > 2000000: raise ValueError('response_too_large')
                rows = json.loads(raw)
                if not isinstance(rows, list): raise ValueError('invalid_response')
                issues = []
                for row in rows:
                    if not isinstance(row, dict) or 'pull_request' in row: continue
                    number = row.get('number')
                    if type(number) is not int or number < 1: continue
                    labels = {str(label.get('name','')).lower() for label in row.get('labels',[]) if isinstance(label,dict)}
                    title = str(row.get('title',''))[:300]
                    kind = 'bug' if 'bug' in labels or title.lower().startswith('[bug]') else 'wish' if labels & {'enhancement','feature','wish','wens'} or title.lower().startswith('[wens]') else 'other'
                    issues.append({'number':number,'title':title,'kind':kind,'state':'closed' if row.get('state')=='closed' else 'open','url':f'{REPOSITORY}/issues/{number}'})
                from datetime import datetime, timezone
                return {'issues':issues,'checked_at':datetime.now(timezone.utc).isoformat(),'limited':len(rows)==100}
            except Exception:
                _retry_after = time.monotonic() + 60
                raise ValueError('GitHub is tijdelijk niet beschikbaar. Probeer het later opnieuw.') from None
    return {**cached_json(store,'feedback','github-issues',600,load),'repository':REPOSITORY}
