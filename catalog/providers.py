import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from database import EventData, localnow, utcnow
from links import canonical_url
from scraper import clean, collect_all_events, detect_age, detect_price, detect_subjects, parse_dates, TOPIC_WORDS

HEADERS = {'User-Agent':'FutureNow/1.0 (educational opportunities catalog)'}
TIMEOUT = (4, 10)
logger = logging.getLogger(__name__)


@dataclass
class SourceResult:
    key: str
    name: str
    url: str
    events: list = field(default_factory=list)
    failures: int = 0
    error_code: str = ''

    @property
    def status(self):
        return 'failed' if not self.events else 'partial' if self.failures else 'ok'


def fetch(url, hosts, *, json_data=False):
    if urlsplit(url).hostname not in hosts: raise ValueError('Unexpected source host')
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    if urlsplit(response.url).hostname not in hosts: raise ValueError('Unexpected redirect host')
    if len(response.content) > 3_000_000: raise ValueError('Source response is too large')
    return (response.json() if json_data else BeautifulSoup(response.content, 'html.parser')), response.url


def content_text(soup):
    # Exclude related-course cards, navigation and scripts from date/price detection.
    copy = BeautifulSoup(str(soup), 'html.parser')
    for node in copy.select('script,style,nav,header,footer'): node.decompose()
    body = copy.select_one('main') or copy.select_one('article') or copy.body or copy
    text = body.get_text(' ', strip=True)
    for marker in ('Нові курси', 'Схожі курси', 'Інші освітні серіали', 'Рекомендуємо також'):
        text = text.split(marker, 1)[0]
    return clean(text)


def meta(soup, name):
    node = soup.find('meta', attrs={'property':name}) or soup.find('meta', attrs={'name':name})
    return clean(node.get('content','')) if node else ''


def course_event(soup, url, source, *, api_record=None, free_hint=False):
    record = api_record or {}
    raw = content_text(soup)
    heading = soup.find('h1')
    title = clean(heading.get_text(' ',strip=True)) if heading else meta(soup,'og:title').split('|')[0].strip()
    title = title or clean(record.get('name',''))
    if not title or len(raw) < 80: raise ValueError('Course detail has no usable content')
    description = meta(soup,'description') or meta(soup,'og:description') or clean(record.get('short_description',''))
    if not description:
        paragraphs = [clean(p.get_text(' ',strip=True)) for p in soup.select('main p, article p')]
        description = next((p for p in paragraphs if len(p) > 55), title)
    low = raw.lower()
    if source == 'Prometheus' and not record and not re.search(r'програма курсу|записатис[ья] на курс|записатися на курс',low):
        raise ValueError('Not an individual course')
    if source == 'Дія.Освіта' and not re.fullmatch(r'/courses/[a-z0-9-]+/?',urlsplit(url).path):
        raise ValueError('Not an individual series')
    rolling = bool(re.search(r'доступ(?:но|ний|ність)?\s+постійно|доступ\s+постійно|навчання в будь-який час|self.paced',low+' '+str(record.get('start_display','')).lower()))
    # Diia's series consist of recorded episodes started by the learner; no cohort date is invented.
    if source == 'Дія.Освіта': rolling = 'розпочати' in low and 'сері' in low
    start, deadline = (None,None) if rolling else parse_dates(raw)
    if rolling:
        # Explicit enrollment deadlines still take precedence over self-paced delivery.
        _, deadline = parse_dates(raw)
    if not rolling:
        def api_date(value):
            try:
                date = datetime.fromisoformat(value.replace('Z','+00:00'))
                return date.astimezone(ZoneInfo('Europe/Kyiv')).replace(tzinfo=None) if date.tzinfo else date
            except (AttributeError,ValueError): return None
        start = start or api_date(record.get('start'))
        deadline = deadline or api_date(record.get('enrollment_end'))
    summary = raw.split('Про курс',1)[0][:1400]
    is_free, price_text = detect_price(summary)
    if free_hint: is_free,price_text = True,'Безкоштовно'
    age_min,age_max = detect_age(raw)
    if re.search(r'без вікових обмежень|вік не має значення|незалежно[^.]{0,70}віку',low): age_min,age_max = 0,None
    subjects = detect_subjects(raw)
    topics = [key for key, words in TOPIC_WORDS.items() if any(re.search(word,low) for word in words)] or ['education']
    language_section = re.search(r'(?:мова курсу|доступні мови|мова навчання)\s*:?\s*(.{0,100})',low)
    languages = [label for word,label in [('україн','Українська'),('англій','English'),('росій','Російська')]
                 if language_section and word in language_section.group(1)]
    url = canonical_url(url)
    return EventData(external_id=hashlib.sha256(url.encode()).hexdigest(),title=title[:500],
        description=description[:900],url=url,source=source,event_type='course',subjects=subjects,
        min_age=age_min,max_age=age_max,start_at=start,deadline=deadline,is_free=is_free,
        price_text=price_text,format='online',city='',raw_text=raw[:15000],country='ukraine',
        topics=topics,criteria=['certificate'] if 'сертифікат' in low else [],price_known=price_text!='Не вказано',
        organizer=clean(record.get('org') or source)[:500],participation_language=' / '.join(languages),
        is_self_paced=rolling,verified_at=utcnow())


def details(result, candidates, hosts, limit, workers, parser):
    def one(item):
        try:
            soup, final_url = fetch(item[0],hosts)
            return parser(soup,final_url,item)
        except (requests.RequestException,ValueError,TypeError,KeyError): return None
    with ThreadPoolExecutor(max_workers=max(1,min(workers,4))) as pool:
        for event in pool.map(one,candidates[:limit]):
            if event is None: result.failures += 1
            else: result.events.append(event)
    if result.failures: result.error_code = 'detail_unavailable'
    return result


def prometheus(limit=12, workers=2):
    result = SourceResult('prometheus','Prometheus','https://prometheus.org.ua/courses-catalog/')
    hosts = {'prometheus.org.ua','www.prometheus.org.ua','courses.prometheus.org.ua'}
    # Reviewed discovery seeds are refreshed from the live official page on every run.
    candidates = {
        'https://prometheus.org.ua/prometheus-free/web-ui-development-basics/':({},False),
        'https://prometheus.org.ua/prometheus-free/linux-basics/':({},False),
    }
    try:
        soup,_ = fetch('https://prometheus.org.ua/',hosts)
        for link in soup.select('a[href]'):
            if clean(link.get_text(' ',strip=True)).lower() in {'дізнатися більше','детальніше','докладніше','learn more'}: continue
            url = urljoin('https://prometheus.org.ua/',link['href'])
            path = urlsplit(url).path
            if urlsplit(url).hostname not in hosts or not (path.startswith('/prometheus-free/') or path.startswith('/course/')): continue
            hint = bool(re.search(r'безплатно|безкоштовно',link.get_text(' ',strip=True).lower()))
            candidates.setdefault(url,({},hint))
    except (requests.RequestException,ValueError): result.failures += 1
    try:
        payload,_ = fetch(f'https://courses.prometheus.org.ua/api/courses/v1/courses/?page_size={limit}',hosts,json_data=True)
        for row in payload.get('results',[]):
            if row.get('hidden') or row.get('invitation_only') or not row.get('id'): continue
            url = 'https://prometheus.org.ua/course/' + row['id']
            candidates.setdefault(url,(row,False))
    except (requests.RequestException,ValueError,TypeError): result.failures += 1
    return details(result,[(url,*value) for url,value in candidates.items()],hosts,limit,workers,
                   lambda soup,url,item:course_event(soup,url,result.name,api_record=item[1],free_hint=item[2]))


def diia(limit=12, workers=2):
    result = SourceResult('diia','Дія.Освіта','https://osvita.diia.gov.ua/courses')
    hosts = {'osvita.diia.gov.ua'}
    soup,_ = fetch(result.url,hosts)
    candidates = {}
    for link in soup.select('a[href]'):
        url = urljoin(result.url,link['href'])
        if urlsplit(url).hostname in hosts and re.fullmatch(r'/courses/[a-z0-9-]+/?',urlsplit(url).path): candidates.setdefault(url,True)
    return details(result,[(url,) for url in candidates],hosts,limit,workers,
                   lambda soup,url,item:course_event(soup,url,result.name))


def man(limit=12, workers=2):
    result = SourceResult('man','МАН України','https://man.gov.ua/')
    result.events = collect_all_events(workers=workers,limit=limit)
    for event in result.events: event.verified_at = utcnow()
    return result


PROVIDERS = {'man':man,'prometheus':prometheus,'diia':diia}


def collect(keys, limit=12, workers=2):
    outcomes = []
    for key in keys:
        try:
            result = PROVIDERS[key](limit=limit,workers=workers)
            if not result.events: result.error_code = 'empty_response'
        except (requests.RequestException,ValueError,TypeError,KeyError):
            names = {'man':('МАН України','https://man.gov.ua/'),'prometheus':('Prometheus','https://prometheus.org.ua/courses-catalog/'),'diia':('Дія.Освіта','https://osvita.diia.gov.ua/courses')}
            result = SourceResult(key,*names[key],error_code='source_unavailable')
        outcomes.append(result)
    return outcomes
