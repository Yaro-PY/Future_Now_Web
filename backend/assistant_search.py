"""Conversational, catalogue-grounded retrieval. No external model or stored chat."""
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator
from backend.web_schemas import Input, Filters
from backend.flow_catalog import CITIES, COUNTRIES, FORMATS, CRITERIA, AGES, DATES, label

Term=Annotated[str,StringConstraints(min_length=1,max_length=50)]

class SearchContext(Input):
    filters: Filters=Field(default_factory=Filters)
    terms: list[Term]=Field(default_factory=list,max_length=8)
    language: Literal['uk','ru','en']='uk'
    age_min: int|None=Field(default=None,ge=12,le=100)
    age_max: int|None=Field(default=None,ge=12,le=100)
    level: Literal['any','beginner','advanced']='any'
    certificate: bool=False
    self_paced: bool=False
    active: bool=False
    page: int=Field(default=1,ge=1,le=1000)

    @model_validator(mode='after')
    def age_range(self):
        if self.age_min is not None and self.age_max is not None and self.age_min>self.age_max:
            raise ValueError('Invalid age range')
        return self


def normalize(value):
    return re.sub(r'[^\w+#]+',' ',unicodedata.normalize('NFKC',value).casefold().replace('ё','е')).strip()


# Each group is an OR; separate requested groups must all match catalogue metadata.
SUBJECTS={
    'python':(r'\b(?:python|пайтон|питон|пітон)\w*',('python','пайтон','питон','пітон')),
    'javascript':(r'\b(?:javascript|джаваскрипт|жаваскрипт|js)\b',('javascript','джаваскрипт','жаваскрипт',' js ')),
    'java':(r'\bjava\b',(' java ','джава')),
    'web':(r'\b(?:web|веб|frontend|front end|фронтенд|html|css|react)\w*',('web','веб','frontend','front end','html','css','react')),
    'programming':(r'\b(?:програм\w*|прогром\w*|розроб\w*|разработ\w*|coding|programming|інформат\w*|информат\w*|айті|айти|it)\b',('програмув','программир','розроб','разработ','coding','programming','інформат','информат','web','веб','python','javascript')),
    'english':(r'\b(?:англі\w*|англи\w*|english|ielts|toefl)\b',('англі','англи','english','ielts','toefl')),
    'german':(r'\b(?:німець\w*|немец\w*|german|deutsch)\b',('німець','немец','german','deutsch')),
    'design':(r'\b(?:дизайн\w*|design\w*|figma|ux|ui)\b',('дизайн','design','figma',' ux ')),
    'business':(r'\b(?:бізнес\w*|бизнес\w*|business|підприєм\w*|предприним\w*)\b',('бізнес','бизнес','business','підприєм','предприним')),
    'marketing':(r'\b(?:маркет\w*|marketing|smm|реклам\w*)\b',('маркет','marketing','smm','реклам')),
    'photo':(r'\b(?:фото\w*|photo\w*)\b',('фото','photo')),
    'art':(r'\b(?:мистец\w*|искусств\w*|малю\w*|рисов\w*|art|drawing)\b',('мистец','искусств','малю','рисов',' art ','drawing')),
    'media':(r'\b(?:медіа\w*|медиа\w*|media|журналі\w*|журнали\w*|сторітел\w*|сторител\w*)\b',('медіа','медиа','media','журналі','журнали','сторітел','сторител')),
    'leadership':(r'\b(?:лідер\w*|лидер\w*|leadership|комуніка\w*|коммуника\w*)\b',('лідер','лидер','leadership','комуніка','коммуника')),
    'math':(r'\b(?:математ\w*|math\w*)\b',('математ','math')),
    'ecology':(r'\b(?:еколог\w*|эколог\w*|ecolog\w*|environment\w*)\b',('еколог','эколог','ecolog','environment')),
    'finance':(r'\b(?:фінанс\w*|финанс\w*|financ\w*|інвест\w*|инвест\w*)\b',('фінанс','финанс','financ','інвест','инвест')),
}
SUBJECT_LABELS={
    'python':('Python','Python','Python'), 'javascript':('JavaScript','JavaScript','JavaScript'),
    'java':('Java','Java','Java'), 'web':('Веброзробка','Веб-разработка','Web development'),
    'programming':('Програмування','Программирование','Programming'),
    'english':('Англійська','Английский','English'), 'german':('Німецька','Немецкий','German'),
    'design':('Дизайн','Дизайн','Design'), 'business':('Бізнес','Бизнес','Business'),
    'marketing':('Маркетинг','Маркетинг','Marketing'), 'photo':('Фотографія','Фотография','Photography'),
    'art':('Мистецтво','Искусство','Art'), 'media':('Медіа','Медиа','Media'),
    'leadership':('Лідерство','Лидерство','Leadership'), 'math':('Математика','Математика','Math'),
    'ecology':('Екологія','Экология','Ecology'), 'finance':('Фінанси','Финансы','Finance'),
}
TOPIC_FALLBACK={'business':'business','art':'art','media':'media','leadership':'leadership','ecology':'ecology'}
BEGINNER=('початк','начина','beginner','basic','основ','intro','вступ','з нуля','с нуля')
ADVANCED=('просунут','продвинут','advanced','поглиблен','углублен')
CITY_PATTERNS={'kyiv':r'ки[їе]в|kyiv|kiev','lviv':r'льв[іо]в|lviv','odesa':r'одес|odes[as]',
    'kharkiv':r'харк[іо]в|kharkiv','poltava':r'полтав|poltava','uzhhorod':r'ужгород|uzhhorod',
    'ivanofrankivsk':r'івано франків|ивано франков|ivano frank'}

HELP={
    'saved':(r'як.*(?:збер|обран)|как.*(?:сохран|избран)|how.*(?:sav|fav)', 'saved',
        ('Відкрий картку курсу й натисни сердечко. Потім знайдеш його в «Обране». Якщо курс завершиться, там буде видно його статус.',
         'Открой карточку курса и нажми сердечко. Потом найдёшь его в «Обране». Если курс завершится, там будет указан его статус.',
         'Open a course and select the heart. You can find it later in Saved, including its current availability.')),
    'proposal':(r'як.*(?:додат|пропоз|публік)|как.*(?:добав|предлож|публик)|how.*(?:suggest|add|publish)', 'suggest',
        ('Натисни «Запропонувати», заповни назву, опис, посилання та умови участі. Пропозиція з’явиться в каталозі після перевірки модератором.',
         'Нажми «Запропонувати», заполни название, описание, ссылку и условия участия. Предложение появится в каталоге после проверки модератором.',
         'Choose Suggest a listing and fill in the title, description, link and eligibility. A moderator reviews it before publication.')),
    'account':(r'(?:як|как|how).*(?:змінити пароль|сменить пароль|change.*password|профіл|профил|акаунт|аккаунт|account|profile|telegram|телеграм)', 'settings',
        ('Нік, ім’я та вік можна змінити у профілі. Пароль і двофакторний захист — у налаштуваннях. Для зв’язку з Telegram відкрий бота й виконай /login. Паролі та коди сюди не надсилай.',
         'Ник, имя и возраст меняются в профиле. Пароль и двухфакторная защита — в настройках. Для связи с Telegram открой бота и выполни /login. Пароли и коды сюда отправлять не нужно.',
         'Edit your nickname, name and age in Profile. Password and two-factor options are in Settings. To link Telegram, use /login in the bot. Do not send passwords or codes here.')),
    'notifications':(r'(?:як|как|how).*(?:сповіщ|уведом|notif)|(?:увімк|включ).*(?:сповіщ|уведом)', 'settings',
        ('У налаштуваннях можна ввімкнути повідомлення про нові можливості й дедлайни. Для повідомлень у Telegram потрібен прив’язаний бот.',
         'В настройках можно включить уведомления о новых возможностях и дедлайнах. Для сообщений в Telegram нужен привязанный бот.',
         'Settings lets you enable new-opportunity and deadline notifications. Telegram notifications require a linked bot.')),
}


def detect_language(text,fallback):
    if re.search('[іїєґ]',text): return 'uk'
    if re.search('[ыэъё]',text) or re.search(r'\b(?:привет|найди|покажи|мне|нужен|нужны|бесплат\w*|курсы|как|где|какой|какие|сохран\w*|спасибо)\b',text): return 'ru'
    if re.search(r'\b(?:hello|hi|find|show|courses|thanks|please|only|free)\b',text): return 'en'
    return fallback


def choose(language,uk,ru,en): return {'uk':uk,'ru':ru,'en':en}[language]


def plan(message,previous):
    context=previous.model_copy(deep=True)
    text=normalize(message)
    context.language=detect_language(text,context.language)
    lang=context.language
    if re.fullmatch(r'(?:привіт|вітаю|доброго дня|привет|здравствуй\w*|добрый день|hello|hi|hey)[ !.]*',text):
        return 'greeting',context,None
    if re.fullmatch(r'(?:дякую|спасиб[оі]|thanks|thank you|дяки|ок|окей|okay|ok)[ !.]*',text):
        return 'thanks',context,None
    if re.search(r'^(?:як справи|как дела|how are you|хто ти|кто ты|who are you|що ти вмієш|что ты умеешь|what can you do)',text):
        return 'smalltalk',context,None
    for key,(pattern,route,answers) in HELP.items():
        if re.search(pattern,text): return 'help',context,{'message':answers[('uk','ru','en').index(lang)],'route':route}
    if re.search(r'нова?ий? пошук|новий пошук|новый поиск|спочатку|сначала|new search|start over|скин[ьу]|скинут|reset',text):
        context=SearchContext(language=lang,filters=Filters(type='course'))
        return 'clarify',context,None
    more=bool(re.fullmatch(r'(?:а\s+)?(?:ще|ще курси|покажи ще|показати ще|більше|еще|покажи еще|показать еще|больше|more|show more|next)',text))
    if more and context.active:
        context.page=min(1000,context.page+1)
        return 'search',context,None
    changed=False
    # An assistant course search is independent of the filters currently saved in the catalogue.
    context.filters.type='course'
    if re.search(r'будь який формат|любой формат|неваж\w* формат|any format',text): context.filters.format='any';changed=True
    elif re.search(r'гібрид|гибрид|змішан|смешан|hybrid',text): context.filters.format='hybrid';changed=True
    elif re.search(r'офлайн|очно|offline|in person|не онлайн|not online',text): context.filters.format='offline';changed=True
    elif re.search(r'онлайн|online|дистанц',text): context.filters.format='online';changed=True
    criteria=set(context.filters.criteria)
    if re.search(r'будь яка цін|любая цен|можна платн|можно платн|ц[іе]на не|неваж\w*.*оплат|any price|paid is fine',text):
        criteria.discard('free');criteria.discard('paid');changed=True
    elif re.search(r'\b(?:безкоштов\w*|безплат\w*|безоплат\w*|бесплат\w*|неплат\w*|free|no cost)\b',text):
        criteria.discard('paid');criteria.add('free');changed=True
    elif re.search(r'\b(?:платн\w*|paid)\b',text):
        criteria.discard('free');criteria.add('paid');changed=True
    context.filters.criteria=sorted(criteria)
    for city,pattern in CITY_PATTERNS.items():
        if re.search(pattern,text): context.filters.country='ukraine';context.filters.city=city;changed=True;break
    else:
        if re.search(r'будь яка країн|любой стран|любая стран|без.*країн|без.*стран|any country|any location|весь світ|весь мир',text):
            context.filters.country='any';context.filters.city='any';changed=True
        elif re.search(r'україн|украин|ukrain',text): context.filters.country='ukraine';context.filters.city='any';changed=True
        elif re.search(r'європ|европ|europ',text): context.filters.country='europe';context.filters.city='any';changed=True
    if re.search(r'будь який вік|любого возраста|любой возраст|без.*віков|без.*возраст|any age',text):
        context.filters.age='any';context.age_min=None;context.age_max=None;changed=True
    else:
        age_range=re.search(r'\b(\d{1,2})\s*(?:-|–|до|to)\s*(\d{1,3})\b',message.casefold())
        adult=re.search(r'\b18\s*\+',message)
        age=re.search(r'(?:мені|мне|вік|возраст|age|для|i am|i m)\s*(?:вже|уже)?\s*[:=]?\s*(\d{1,3})\b|\b(\d{1,3})\s*(?:рок|лет|рік|year)',text)
        if age_range or adult or age:
            low,high=(map(int,age_range.groups()) if age_range else (18,100) if adult else (int(age.group(1) or age.group(2)),)*2)
            if not 12<=low<=high<=100: return 'invalid_age',context,None
            context.filters.age='any';context.age_min=low;context.age_max=high;changed=True
    if re.search(r'наступн\w* місяц|следующ\w* месяц|next month',text): context.filters.date='next_month';changed=True
    elif re.search(r'цього місяц|эт\w* месяц|this month',text): context.filters.date='month';changed=True
    elif re.search(r'найближч\w*|ближайш\w*|цього тиж|эт\w* недел|next week|next 7 days',text): context.filters.date='nearest';changed=True
    if re.search(r'без дедлайн|без строк|у своєму темпі|в своем темпе|self paced',text): context.self_paced=True;context.filters.date='any';changed=True
    if re.search(r'початк|начина|beginner|з нуля|с нуля',text): context.level='beginner';changed=True
    elif re.search(r'просунут|продвинут|advanced',text): context.level='advanced';changed=True
    elif re.search(r'будь який рівень|любой уровень|any level',text): context.level='any';changed=True
    if re.search(r'сертифік|сертифик|certificate',text): context.certificate=True;changed=True
    found=[key for key,(pattern,_) in SUBJECTS.items() if re.search(pattern,text)]
    if len(found)>1 and 'programming' in found: found.remove('programming')
    if found:
        context.terms=found[:8];changed=True
    else:
        # Preserve a meaningful unrecognized subject instead of pretending to understand it.
        candidate=text
        candidate=re.sub(r'(?:мені|мне|для|вік|возраст|age|i am)\s*(?:вже|уже)?\s*\d{1,3}',' ',candidate)
        stop=r'\b(?:хочу|хот[еі]в\w*|хотел\w*|найди|знайди|знайти|покажи|показати|показать|найт\w*|порад\w*|посовет\w*|підбер\w*|подбер\w*|потріб\w*|нуж\w*|помо\w*|допомо\w*|курс\w*|вивч\w*|изуч\w*|навча\w*|учит\w*|навчи\w*|teach|learn|find|show|course\w*|please|want|need|help|me|a|an|the|some|only|i|to|for|with|in|of|and|or|а|і|та|по|з|с|на|у|в|для|тільки|только|будь|які|какие|ще|еще|далі|дальше|так|да|онлайн|online|офлайн|offline|безкоштов\w*|бесплат\w*|free|платн\w*|paid|рок\w*|лет|year\w*|формат\w*|вік|возраст|beginner|початк\w*|начина\w*|саме|именно|можна|можно|лише|это|це|it|мені|мне|є|есть|варіант\w*|вариант\w*|чи|ли|пожалуйста|ласка|привет|привіт|hello|hi)\b'
        candidate=re.sub(stop,' ',candidate)
        for pattern in CITY_PATTERNS.values(): candidate=re.sub(pattern+r'\w*',' ',candidate)
        candidate=re.sub(r'україн\w*|украин\w*|ukrain\w*|європ\w*|европ\w*|europ\w*|\d+',' ',candidate)
        words=[word for word in candidate.split() if len(word)>2][:5]
        modifiers=r'^(?:як|как|how|all|все|всі|усі|any|любо\w*|яки\w*|яка|без|не|not|no|self|paced|рів\w*|уров\w*|level|beginner\w*|сертиф\w*|certificate|дедлайн\w*|строк\w*|темп\w*|сво\w*|місяц\w*|месяц\w*|цього|эт\w*|next|this|month|week|найближч\w*|ближайш\w*|наступн\w*|следующ\w*|paid|fine|price|ц[іе]н\w*|віков\w*|возраст\w*|обмеж\w*|огранич\w*|оплат\w*|варт\w*|країн\w*|стран\w*|country|location|весь|світ|мир|початк\w*|начина\w*|просунут\w*|продвинут\w*|advanced|рок\w*|years?)$'
        words=[word for word in words if not re.fullmatch(modifiers,word)]
        if words:
            context.terms=words;changed=True
    all_courses=bool(re.search(r'всі курси|усі курси|все курсы|all courses',text))
    if all_courses: context.terms=[];context.level='any'
    if not changed and not context.active and not all_courses: return 'clarify',context,None
    context.active=True;context.page=1
    return 'search',SearchContext.model_validate(context.model_dump()),None


def rank(event,context):
    if context.age_min is not None:
        if event.min_age is None and event.max_age is None: return None
        if event.max_age is not None and event.max_age<context.age_min: return None
        if event.min_age is not None and event.min_age>(context.age_max or context.age_min): return None
    if context.self_paced and not event.is_self_paced: return None
    if context.certificate and 'certificate' not in (event.criteria or []): return None
    title=' '+normalize(event.title)+' '
    content=' '+normalize(' '.join(str(value or '') for value in (event.title,event.description,event.requirements,event.organizer)))+' '
    if context.level!='any' and not any(word in content for word in (BEGINNER if context.level=='beginner' else ADVANCED)): return None
    score=0
    for term in context.terms:
        alternatives=SUBJECTS[term][1] if term in SUBJECTS else (normalize(term),)
        matches=[word for word in alternatives if word in content]
        if not matches:
            if TOPIC_FALLBACK.get(term) in (event.topics or []): score+=1;continue
            return None
        score+=max(6 if word in title else 2 for word in matches)
    return score


def describe(context):
    lang=context.language;locale='en' if lang=='en' else 'uk'
    labels=[]
    if context.terms: labels.append(' / '.join(SUBJECT_LABELS.get(term,(term,term,term))[('uk','ru','en').index(lang)] for term in context.terms))
    if context.filters.format!='any': labels.append(label(FORMATS,context.filters.format,locale))
    for item in context.filters.criteria:
        labels.append({'free':'Бесплатно','paid':'Платные','funded':'С финансированием','travel':'Поездка'}.get(item,item) if lang=='ru' else label(CRITERIA,item,locale))
    if context.age_min is not None:
        labels.append(f'{context.age_min}+' if context.age_max==100 else str(context.age_min) if context.age_min==context.age_max else f'{context.age_min}–{context.age_max}')
    elif context.filters.age!='any': labels.append(label(AGES,context.filters.age,locale))
    if context.filters.country!='any': labels.append(label(COUNTRIES,context.filters.country,locale))
    if context.filters.country=='ukraine' and context.filters.city!='any': labels.append(label(CITIES,context.filters.city,locale))
    if context.level=='beginner': labels.append(choose(lang,'Для початківців','Для начинающих','Beginner'))
    if context.level=='advanced': labels.append(choose(lang,'Поглиблений рівень','Продвинутый уровень','Advanced'))
    if context.self_paced: labels.append(choose(lang,'У своєму темпі','В своём темпе','Self-paced'))
    if context.filters.date!='any': labels.append(label(DATES,context.filters.date,locale))
    if context.certificate: labels.append(choose(lang,'Із сертифікатом','С сертификатом','Certificate'))
    return labels


def reply(kind,context,total=0,shown=0,extra=None):
    lang=context.language
    if kind=='help': return extra['message']
    if kind=='greeting': return choose(lang,'Привіт! Допоможу підібрати курс. Що хочеш вивчати? Можеш одразу додати: онлайн, безкоштовно та свій вік.','Привет! Помогу подобрать курс. Что хочешь изучать? Можешь сразу добавить: онлайн, бесплатно и свой возраст.','Hi! I can help you find a course. What would you like to learn? You can also mention online, free and your age.')
    if kind=='thanks': return choose(lang,'Будь ласка! Якщо хочеш, уточни тему чи умови — підберемо ще варіанти.','Пожалуйста! Если хочешь, уточни тему или условия — подберём ещё варианты.','You’re welcome! Tell me another topic or preference whenever you want to refine the search.')
    if kind=='smalltalk': return choose(lang,'Я помічник Future Now. Допомагаю знаходити курси в нашому каталозі та розбиратися із сайтом. Що хочеш вивчати?','Я помощник Future Now. Помогаю находить курсы в нашем каталоге и разбираться с сайтом. Что хочешь изучать?','I’m the Future Now assistant. I help you find courses in our catalogue and use the site. What would you like to learn?')
    if kind=='invalid_age': return choose(lang,'Можу шукати для віку від 12 до 100 років. Напиши, будь ласка, вік або діапазон, наприклад «мені 16».','Могу искать для возраста от 12 до 100 лет. Напиши возраст или диапазон, например «мне 16».','Please give an age from 12 to 100, or an age range, for example “I am 16”.')
    if kind=='clarify': return choose(lang,'Що тобі цікаво вивчати? Наприклад, програмування, англійську чи дизайн. Якщо тема неважлива, напиши «покажи всі курси».','Что тебе интересно изучать? Например, программирование, английский или дизайн. Если тема не важна, напиши «покажи все курсы».','What would you like to learn: programming, English, design, or something else? Say “show all courses” if you have no topic in mind.')
    if not total: return choose(lang,'За цими умовами поки нічого не знайшов у каталозі. Можемо змінити формат, вік або тему. Умови не розширюватиму без твого прохання.','По этим условиям пока ничего не нашёл в каталоге. Можно изменить формат, возраст или тему. Условия без твоей просьбы расширять не буду.','I couldn’t find a current listing matching these preferences. We can change the format, age or topic. I won’t loosen your preferences without asking.')
    if not shown: return choose(lang,'Це вже всі знайдені варіанти. Хочеш змінити тему або умови?','Это уже все найденные варианты. Хочешь изменить тему или условия?','That’s all the matching courses. Would you like to change the topic or preferences?')
    if context.page>1:
        return choose(lang,f'Ось наступні варіанти — {shown}. '+('Є ще результати нижче.' if context.page*3<total else 'Це останні курси за цими умовами.'),
            f'Вот следующие варианты — {shown}. '+('Ниже можно показать ещё.' if context.page*3<total else 'Это последние курсы по этим условиям.'),
            f'Here are {shown} more matches. '+('There are more below.' if context.page*3<total else 'These are the last matches for these preferences.'))
    return choose(lang,f'Знайшов відповідні курси — {total}. '+(f'Показую {shown}; решту можна відкрити кнопкою нижче.' if shown<total else 'Ось що є в каталозі зараз. Відкрий картку, щоб перевірити програму й умови участі.'),
        f'Нашёл подходящие курсы — {total}. '+(f'Показываю {shown}; остальные можно открыть кнопкой ниже.' if shown<total else 'Вот что есть в каталоге сейчас. Открой карточку, чтобы посмотреть программу и условия участия.'),
        f'I found {total} matching courses. '+(f'Here are {shown}; use the button below to see more.' if shown<total else 'Open a course to check its programme and eligibility.'))


def suggestions(context,kind,total):
    lang=context.language
    if kind in ('greeting','clarify','thanks','smalltalk'):
        return choose(lang,['Курси програмування','Безкоштовні онлайн-курси','Покажи всі курси'],['Курсы программирования','Бесплатные онлайн-курсы','Покажи все курсы'],['Programming courses','Free online courses','Show all courses'])
    if kind=='search' and not total:
        result=[]
        if context.age_min is not None or context.filters.age!='any': result.append(choose(lang,'Будь-який вік','Любой возраст','Any age'))
        if context.filters.format!='any': result.append(choose(lang,'Будь-який формат','Любой формат','Any format'))
        result.append(choose(lang,'Новий пошук','Новый поиск','New search'))
        return result
    return choose(lang,['Тільки онлайн','Лише безкоштовні','Новий пошук'],['Только онлайн','Только бесплатные','Новый поиск'],['Online only','Free only','New search'])
