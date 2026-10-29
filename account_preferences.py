"""UI-independent profile/search defaults shared by bot and website."""
from copy import deepcopy
from urllib.parse import urlsplit

from flow_catalog import CRITERIA
from identity import age_group


def defaults(account, mode):
    prefs = {'type': 'any', 'topics': [], 'age': 'any', 'country': 'any',
             'city': 'any', 'format': 'any', 'date': 'any', 'criteria': []}
    prefs.update(deepcopy(account.profile or {}))
    if mode != 'profile': prefs.update(deepcopy(account.search_defaults or {}))
    prefs.pop('topics', None)
    if mode == 'profile':
        prefs.setdefault('nickname', '')
        prefs.setdefault('display_name', '')
    else:
        for key in ('nickname', 'display_name', 'public_id', 'profile_updated_at'):
            prefs.pop(key, None)
    if prefs.get('age') != 'any':
        try: prefs['age'] = age_group(prefs['age'])
        except ValueError: pass
    prefs['criteria'] = [key for key in prefs.get('criteria', []) if key in CRITERIA]
    return prefs


def safe_url(url):
    try:
        parsed = urlsplit(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False
