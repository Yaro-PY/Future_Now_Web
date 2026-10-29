"""MAN source adapter. Unknown fields remain unknown instead of inventing eligibility."""
import hashlib
import logging
import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit
import requests
from bs4 import BeautifulSoup
from database import EventData, localnow, topics_from_subjects
from flow_catalog import CITIES

logger = logging.getLogger(__name__)
HEADERS = {'User-Agent': 'UserFlow/2.0 (educational opportunities aggregator)'}
TIMEOUT = 12
SOURCE_URLS = ['https://man.gov.ua/', 'https://man.gov.ua/contests', 'https://man.gov.ua/all-ukrainian-olympiads']
SUBJECT_WORDS = {
    'math': ['математ', 'алгебр', 'геометр'],
    'informatics': ['інформат', 'програмув', r'\bit\b', 'python', 'кодинг', 'хакатон', 'hackathon'],
    'physics': ['фізик'], 'chemistry': ['хім'], 'biology': ['біолог', 'генетик'],
    'geography': ['географ'], 'history': ['істор'], 'ukrainian': ['українськ.{0,5} мов'],
    'literature': ['літератур'], 'english': ['англійськ'], 'foreign': ['іноземн'],
    'astronomy': ['астроном', 'косміч'], 'engineering': ['інженер', 'робототех'],
    'economics': ['економ', 'бізнес', 'стартап'], 'law': ['правознав', 'юридич'],
    'art': ['мистецтв', 'дизайн'], 'stem': ['stem', 'науков', 'дослід']}
TOPIC_WORDS = {
    'it': ['інформат', 'програмув', r'\bit\b', 'python', 'hackathon', 'хакатон'],
    'business': ['бізнес', 'підприєм', 'стартап'], 'leadership': ['лідер'],
    'art': ['мистецтв', 'дизайн', 'творч'], 'media': ['медіа', 'журналіст'],
    'education': ['навчан', 'освіт', 'математ', 'фізик', 'хім', 'біолог', 'науков'],
    'volunteer': ['волонтер'], 'ecology': ['еколог', 'довкіл'],
    'sport': ['спорт'], 'culture': ['культур'], 'international': ['міжнародн', 'дипломат']}
MONTHS = dict(zip(['січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
                  'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'], range(1, 13)))

def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()

def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.content, 'html.parser')

def detect_subjects(text):
    return [key for key, words in SUBJECT_WORDS.items() if any(re.search(word, text.lower()) for word in words)]

def detect_type(text):
    for pattern, key in [('хакатон|hackathon', 'hackathon'), ('стажув|internship', 'internship'),
                         ('волонтер|volunteer', 'volunteer'), ('грант|grant', 'grant'),
                         ('обмін|exchange', 'exchange'), ('конкурс|олімпіад|турнір', 'contest'),
                         ('курс|вебінар|лекці', 'course'), ('програм|табір', 'program')]:
        if re.search(pattern, text.lower()): return key
    return 'other'

def detect_age(text):
    low = text.lower()
    ranges = []
    for match in re.finditer(r'(?:від\s*)?(\d{1,2})\s*(?:[–-]|до)\s*(\d{1,2})\s*(?:рок|years)', low):
        a, b = map(int, match.groups())
        if 5 <= a <= b <= 100: ranges.append((a, b))
    if ranges: return min(a for a, b in ranges), max(b for a, b in ranges)
    single = re.search(r'(?:від|старше)\s*(\d{1,2})\s*рок|\b(\d{1,2})\s*\+', low)
    if single: return int(single.group(1) or single.group(2)), None
    return None, None

def detect_price(text):
    low = text.lower()
    free = bool(re.search(r'безкоштов|безплат|участь без оплати|\bfree\b', low))
    amount = re.search(r'\b(\d[\d ]{0,8})\s*(грн|₴|uah|eur|usd|€|\$)', low)
    paid = amount or re.search(r'платна участь|платний|вартість участі', low)
    if amount and int(amount.group(1).replace(' ', '')) == 0: return True, 'Безкоштовно'
    if paid: return False, clean(amount.group(0)) if amount else 'Платно'
    if free: return True, 'Безкоштовно'
    return False, 'Не вказано'

def detect_format(text):
    low = text.lower()
    online = bool(re.search(r'онлайн|online|дистанційн', low))
    offline = bool(re.search(r'офлайн|\bочно\b|адреса:', low))
    if online and offline: return 'hybrid'
    if online: return 'online'
    if offline: return 'offline'
    return 'unknown'

def parse_dates(text):
    """Classify dates by their nearest preceding label; retain explicitly supplied time."""
    low = text.lower()
    pattern = (r'(?P<iso>20\d{2}-\d{2}-\d{2})|'
               r'(?P<numeric>\b\d{1,2}[./]\d{1,2}[./]20\d{2}\b)|'
               r'(?P<words>\b\d{1,2}\s+(?:' + '|'.join(MONTHS) + r')(?:\s+20\d{2})?)')
    starts, deadlines = [], []
    for match in re.finditer(pattern, low):
        try:
            if match.group('iso'): date = datetime.strptime(match.group(), '%Y-%m-%d')
            elif match.group('numeric'):
                date = datetime.strptime(match.group().replace('/', '.'), '%d.%m.%Y')
            else:
                parts = match.group().split()
                if len(parts) != 3: continue  # Never roll an old undated announcement into the current year.
                date = datetime(int(parts[2]), MONTHS[parts[1]], int(parts[0]))
            clock = re.match(r'\s*(?:о|at|в)?\s*(\d{1,2}):(\d{2})', low[match.end():])
            if clock: date = date.replace(hour=int(clock.group(1)), minute=int(clock.group(2)))
        except ValueError:
            continue
        prefix = re.split(r'[!?;\n]|\.\s', low[:match.start()])[-1][-120:]
        tags = list(re.finditer(r'(?P<deadline>дедлайн|реєстрац\w*|заяв\w*|подач\w*|прийом\w*|deadline|apply|application|registration)|(?P<start>відбуд\w*|почат\w*|проведен\w*|подія|event|starts?)', prefix))
        if not tags: continue  # Publication dates, copyright dates and unrelated years are not event dates.
        is_deadline = bool(tags and tags[-1].group('deadline'))
        (deadlines if is_deadline else starts).append(date)
    return min(starts) if starts else None, min(deadlines) if deadlines else None

def make_event(title, description, url, source, raw):
    full = clean(raw or f'{title} {description}')
    min_age, max_age = detect_age(full)
    is_free, price_text = detect_price(full)
    start, deadline = parse_dates(full)
    subjects = detect_subjects(full)
    topics = [key for key, words in TOPIC_WORDS.items() if any(re.search(word, full.lower()) for word in words)]
    criteria = []
    for key, pattern in [('funded', r'фінансуван|funded'), ('travel', r'подорож|поїздк|обмін|travel|trip|exchange'),
                         ('housing', r'проживан.{0,20}(?:нада|покри|безкоштов)|accommodation.{0,20}(?:provided|covered)'),
                         ('meals', r'харчуван.{0,20}(?:нада|покри|безкоштов)|meals.{0,20}(?:provided|covered)'),
                         ('transport', r'проїзд.{0,20}(?:покри|відшкод)|transport.{0,20}covered'),
                         ('certificate', r'сертифікат|certificate')]:
        if re.search(pattern, full.lower()): criteria.append(key)
    city = next((key for key, names in CITIES.items() if key not in ('other', 'any') and names[0].lower() in full.lower()), '')
    return EventData(external_id=hashlib.sha256(url.encode()).hexdigest(), title=clean(title)[:500],
                     description=clean(description)[:5000], url=url, source=source, event_type=detect_type(title),
                     subjects=subjects, min_age=min_age, max_age=max_age, start_at=start, deadline=deadline,
                     is_free=is_free, price_text=price_text, format=detect_format(full), city=city, raw_text=full[:15000],
                     topics=topics or topics_from_subjects(subjects), criteria=criteria,
                     price_known=price_text != 'Не вказано', organizer='МАН України',
                     is_closed=bool(re.search(r'нагородили|підсумки|як це було|вітаємо перемож|відбувся|відбулася|завершився|оголошено переможців', title.lower())))

def page_text(soup):
    for node in soup.select('script, style, nav, header, footer'): node.decompose()
    content = soup.select_one('article') or soup.select_one('main') or soup.body or soup
    return clean(content.get_text(' ', strip=True))

def collect_all_events(workers=1, limit=None):
    candidates = {}
    for source in SOURCE_URLS:
        try:
            soup = fetch(source)
            for node in soup.select('a[href]'):
                title = clean(node.get_text(' ', strip=True))
                href = urljoin(source, node['href']).split('#')[0]
                parts = urlsplit(href)
                if parts.hostname != 'man.gov.ua' or len(title) < 8 or href.rstrip('/') in {s.rstrip('/') for s in SOURCE_URLS}: continue
                if re.search(r'конкурс|олімпіад|хакатон|програм|табір|курс|обмін|грант', title.lower()):
                    candidates.setdefault(href, title)
        except requests.RequestException:
            logger.warning('MAN listing unavailable: %s', source)
    limit = max(1, min(100, int(limit if limit is not None else os.getenv('SCRAPER_DETAIL_LIMIT', '40'))))
    def collect_detail(item):
        url, title = item
        try:
            soup = fetch(url)
            raw = page_text(soup)
            heading = soup.select_one('h1')
            if heading: title = clean(heading.get_text(' ', strip=True)) or title
            return make_event(title, raw[:5000], url, 'МАН України', raw)
        except requests.RequestException:
            logger.warning('MAN detail unavailable: %s', url)
    items = list(candidates.items())[:limit]
    if workers <= 1:
        return [event for item in items if (event := collect_detail(item)) is not None]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(workers, 4)) as executor:
        return [event for event in executor.map(collect_detail, items) if event is not None]
