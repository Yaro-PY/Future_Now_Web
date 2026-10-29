"""Persistent profiles, navigation, opportunities, bookmarks and notifications."""
import os
import asyncio
import hashlib
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import uuid4
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, JSON, ForeignKey, select, inspect, text, func, update, case
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from db_config import connection_settings

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./website.db')
connection_url, engine_options = connection_settings(DATABASE_URL, serverless=os.getenv('VERCEL') == '1')
engine = create_async_engine(connection_url, **engine_options)
Session = async_sessionmaker(engine, expire_on_commit=False)


def lock_key(name):
    return int.from_bytes(hashlib.blake2b(name.encode(), digest_size=8).digest(), 'big', signed=True)


@asynccontextmanager
async def distributed_lock(name):
    """Transaction-scoped lock, including when Neon uses transaction pooling."""
    if engine.dialect.name != 'postgresql':
        yield True
        return
    async with Session() as session:
        acquired = await session.scalar(text('SELECT pg_try_advisory_xact_lock(:key)'), {'key': lock_key(name)})
        try:
            yield acquired
        finally:
            await session.rollback()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def localnow():
    return datetime.now(ZoneInfo('Europe/Kyiv')).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default='')
    url: Mapped[str] = mapped_column(String(2000))
    source: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100), default='other')
    subjects: Mapped[list] = mapped_column(JSON, default=list)
    min_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    price_text: Mapped[str] = mapped_column(String(200), default='')
    format: Mapped[str] = mapped_column(String(50), default='unknown')
    city: Mapped[str] = mapped_column(String(200), default='')
    raw_text: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    country: Mapped[str] = mapped_column(String(50), default='ukraine')
    topics: Mapped[list] = mapped_column(JSON, default=list)
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    price_known: Mapped[bool] = mapped_column(Boolean, default=False)
    organizer: Mapped[str] = mapped_column(String(500), default='')
    participation_language: Mapped[str] = mapped_column(String(100), default='')
    requirements: Mapped[str] = mapped_column(Text, default='')
    is_self_paced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    admin_overrides: Mapped[dict] = mapped_column(JSON, default=dict)
    source_url: Mapped[str] = mapped_column(String(2000), default='')
    admin_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    admin_updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

class CatalogSource(Base):
    __tablename__ = 'catalog_sources'
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(40), default='')

class Submission(Base):
    __tablename__ = 'submissions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    review_note: Mapped[str] = mapped_column(String(500), default='')
    event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

class User(Base):
    """Original profile table retained for migration."""
    __tablename__ = 'users'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    subjects: Mapped[list] = mapped_column(JSON, default=list)
    time_pref: Mapped[str] = mapped_column(String(50), default='any')
    price_pref: Mapped[str] = mapped_column(String(50), default='any')
    format_pref: Mapped[str] = mapped_column(String(50), default='any')

class Account(Base):
    __tablename__ = 'accounts'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    language: Mapped[str] = mapped_column(String(2), default='uk')
    profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    search_defaults: Mapped[dict] = mapped_column(JSON, default=dict)
    notifications: Mapped[dict] = mapped_column(JSON, default=lambda: {'new': False, 'deadlines': False, 'expired': True})
    notification_since: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    flow: Mapped[dict] = mapped_column(JSON, default=lambda: {'screen': 'language', 'revision': 0, 'history': []})

class Credential(Base):
    """One shared bot/website login; the password itself is never stored."""
    __tablename__ = 'credentials'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('accounts.telegram_id'), unique=True)
    nickname: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class WebSession(Base):
    __tablename__ = 'web_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    credential_id: Mapped[str] = mapped_column(String(36), ForeignKey('credentials.id'), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

class AuthThrottle(Base):
    __tablename__ = 'auth_throttles'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=1)

class Saved(Base):
    __tablename__ = 'saved_events'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Receipt(Base):
    __tablename__ = 'notification_receipts'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(String(150), primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(20), default='new', index=True)
    review_note: Mapped[str] = mapped_column(Text, default='')
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)

class AdminAudit(Base):
    __tablename__ = 'admin_audit'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity: Mapped[str] = mapped_column(String(20), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    actor_id: Mapped[int] = mapped_column(BigInteger)
    changes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

@dataclass
class UserPreferences:
    age: int
    subjects: list[str]
    time_pref: str = 'any'
    price_pref: str = 'any'
    format_pref: str = 'any'

@dataclass
class EventData:
    external_id: str
    title: str
    description: str
    url: str
    source: str
    event_type: str
    subjects: list[str]
    min_age: Optional[int]
    max_age: Optional[int]
    start_at: Optional[datetime]
    deadline: Optional[datetime]
    is_free: bool
    price_text: str
    format: str
    city: str
    raw_text: str
    country: str = 'ukraine'
    topics: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    price_known: bool = False
    organizer: str = ''
    participation_language: str = ''
    requirements: str = ''
    is_self_paced: bool = False
    is_closed: bool = False
    verified_at: Optional[datetime] = None

def _migrate(conn):
    """Additive, repeatable migration of the original events table."""
    columns = {c['name'] for c in inspect(conn).get_columns('events')}
    additions = {
        'created_at': "TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:00'",
        'country': "VARCHAR(50) NOT NULL DEFAULT 'ukraine'",
        'topics': "JSON NOT NULL DEFAULT '[]'", 'criteria': "JSON NOT NULL DEFAULT '[]'",
        'price_known': 'BOOLEAN NOT NULL DEFAULT FALSE',
        'organizer': "VARCHAR(500) NOT NULL DEFAULT ''",
        'participation_language': "VARCHAR(100) NOT NULL DEFAULT ''",
        'requirements': "TEXT NOT NULL DEFAULT ''",
        'is_self_paced': 'BOOLEAN NOT NULL DEFAULT FALSE',
        'is_closed': 'BOOLEAN NOT NULL DEFAULT FALSE',
        'verified_at': 'TIMESTAMP',
        'revision': 'INTEGER NOT NULL DEFAULT 1',
        'admin_overrides': "JSON NOT NULL DEFAULT '{}'",
        'source_url': "VARCHAR(2000) NOT NULL DEFAULT ''",
        'admin_updated_at': 'TIMESTAMP', 'admin_updated_by': 'BIGINT'}
    for name, ddl in additions.items():
        if name not in columns:
            conn.execute(text(f'ALTER TABLE events ADD COLUMN {name} {ddl}'))
    if 'price_known' not in columns:
        conn.execute(text("UPDATE events SET price_known = TRUE WHERE price_text NOT IN ('', 'Не вказано', 'Ціна не вказана')"))
    report_columns = {c['name'] for c in inspect(conn).get_columns('reports')}
    for name, ddl in {'status': "VARCHAR(20) NOT NULL DEFAULT 'new'",
                      'review_note': "TEXT NOT NULL DEFAULT ''", 'reviewed_by': 'BIGINT',
                      'updated_at': "TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:00'",
                      'resolved_at': 'TIMESTAMP', 'revision': 'INTEGER NOT NULL DEFAULT 1'}.items():
        if name not in report_columns: conn.execute(text(f'ALTER TABLE reports ADD COLUMN {name} {ddl}'))
    if 'updated_at' not in report_columns:
        conn.execute(text('UPDATE reports SET updated_at = created_at'))
    if conn.dialect.name == 'postgresql':
        old_type = next(c['type'] for c in inspect(conn).get_columns('users') if c['name'] == 'telegram_id')
        if not isinstance(old_type, BigInteger):
            conn.execute(text('ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT'))

async def init_db():
    async with engine.begin() as conn:
        if engine.dialect.name == 'postgresql':
            await conn.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock_key('schema')})
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate)

async def close_db():
    await engine.dispose()

SUBJECT_TOPICS = {'informatics': 'it', 'economics': 'business', 'art': 'art',
                  'literature': 'culture', 'foreign': 'international', 'english': 'international'}

def topics_from_subjects(subjects):
    return sorted({SUBJECT_TOPICS.get(s, 'education') for s in subjects})

async def get_account(telegram_id):
    async with Session() as session:
        account = await session.get(Account, telegram_id)
        if account:
            return account
        account = Account(telegram_id=telegram_id)
        legacy = await session.get(User, telegram_id)
        if legacy and legacy.age:
            account.profile = {'age': legacy.age, 'country': 'ukraine', 'city': 'any',
                               'topics': topics_from_subjects(legacy.subjects or []),
                               'format': legacy.format_pref or 'any', 'criteria': []}
            account.flow = {'screen': 'menu', 'revision': 0, 'history': []}
        session.add(account)
        await session.commit()
        return account

async def save_account(account):
    async with Session() as session:
        state = inspect(account)
        if state.transient:
            await session.merge(account)
        else:
            # A bot response must not overwrite settings just saved by the website.
            changes = {column.key: getattr(account, column.key)
                       for column in Account.__table__.columns
                       if column.key != 'telegram_id' and state.attrs[column.key].history.has_changes()}
            if changes:
                await session.execute(update(Account).where(Account.telegram_id == account.telegram_id).values(**changes))
        await session.commit()

def insert_for(table):
    return (pg_insert if engine.dialect.name == 'postgresql' else sqlite_insert)(table)

async def upsert_events(events):
    from links import canonical_url
    async with Session() as session:
        existing = {}
        for row in (await session.scalars(select(Event).order_by(Event.id))).all():
            existing.setdefault(canonical_url(row.url), row.external_id)
            if row.source_url: existing.setdefault(canonical_url(row.source_url), row.external_id)
        seen = set()
        count = 0
        for data in events:
            values = {key: getattr(data, key) for key in data.__dataclass_fields__}
            values['url'] = canonical_url(values['url'])
            if values['url'] in seen: continue
            seen.add(values['url'])
            values['external_id'] = existing.get(values['url'], values['external_id'])
            values['updated_at'] = utcnow()
            values['source_url'] = values['url']
            stmt = insert_for(Event).values(**values)
            # Decide against the CURRENT stored flags in SQL, so a concurrent admin
            # edit cannot be overwritten by a previously fetched source snapshot.
            updates = {key: case((Event.admin_overrides[key].as_boolean() == True, getattr(Event,key)),
                                else_=getattr(stmt.excluded,key))
                       if key not in ('external_id','updated_at','source_url','verified_at') else value
                       for key,value in values.items()}
            updates['revision'] = Event.revision + 1
            await session.execute(stmt.on_conflict_do_update(index_elements=['external_id'], set_=updates))
            count += 1
        await session.commit()
    return count

async def get_event(event_id):
    async with Session() as session:
        return await session.get(Event, event_id)

LEGACY_TYPES = {'Конкурс': 'contest', 'Олімпіада': 'contest', 'Турнір': 'contest',
                'Хакатон': 'hackathon', 'Курс': 'course', 'Вебінар': 'course', 'Лекція': 'course',
                'Освітній табір': 'program', 'Освітня програма': 'program', 'Інше': 'other'}

def event_status(event, now=None):
    if event.is_closed: return 'expired'
    now = now or localnow()
    for value in (event.deadline, None if event.is_self_paced else event.start_at):
        if value and (value.date() < now.date() or ((value.hour or value.minute) and value < now)):
            return 'expired'
    if event.is_self_paced and not event.deadline: return 'self_paced'
    return 'open' if event.deadline or event.start_at else 'check_source'

def matches(event, prefs, now=None):
    now = now or localnow()
    if event_status(event, now) == 'expired': return False
    kind = LEGACY_TYPES.get(event.event_type, event.event_type)
    requested = prefs.get('type', 'any')
    if requested != 'any':
        if requested == 'ukrainian':
            if event.country != 'ukraine': return False
        elif requested == 'international':
            if event.country not in ('international', 'europe', 'other') and kind != requested: return False
        elif kind != requested: return False
    age = prefs.get('age', 'any')
    if str(age) != 'any':
        if str(age) == '18+': low, high = 18, 100
        elif '-' in str(age): low, high = map(int, str(age).split('-'))
        else: low = high = int(age)
        if event.min_age is None and event.max_age is None: return False
        if event.max_age is not None and event.max_age < low: return False
        if event.min_age is not None and event.min_age > high: return False
    wanted = set(prefs.get('topics', []))
    topics = set(event.topics or topics_from_subjects(event.subjects or []))
    if wanted and not wanted.intersection(topics): return False
    country = prefs.get('country', 'any')
    if country == 'online':
        if event.format not in ('online', 'hybrid'): return False
    elif country != 'any' and event.country != country: return False
    city = prefs.get('city', 'any')
    if country == 'ukraine' and city != 'any' and event.city != city:
        # Nationwide online courses have no physical city; explicit local restrictions still apply.
        if not (event.format == 'online' and not event.city): return False
    fmt = prefs.get('format', 'any')
    if fmt != 'any' and event.format != fmt: return False
    criteria = set(prefs.get('criteria', []))
    available = set(event.criteria or [])
    if event.price_known: available.add('free' if event.is_free else 'paid')
    if not criteria.issubset(available): return False
    date_filter = prefs.get('date', 'any')
    if date_filter != 'any':
        when = event.deadline or event.start_at
        if not when: return False
        if date_filter == 'nearest' and not (now.date() <= when.date() <= (now + timedelta(days=7)).date()): return False
        if date_filter == 'month' and (when.year, when.month) != (now.year, now.month): return False
        if date_filter == 'next_month':
            month = now.replace(day=28) + timedelta(days=4)
            if (when.year, when.month) != (month.year, month.month): return False
    return True

async def search_events(prefs, now=None):
    async with Session() as session:
        events = list((await session.scalars(select(Event).order_by(Event.deadline.asc().nullslast(), Event.start_at.asc().nullslast(), Event.id))).all())
    return [event for event in events if matches(event, prefs, now)]

async def saved_events(telegram_id):
    async with Session() as session:
        return list((await session.scalars(select(Event).join(Saved, Event.id == Saved.event_id).where(Saved.telegram_id == telegram_id).order_by(Saved.created_at.desc(), Event.id))).all())

async def is_saved(telegram_id, event_id):
    async with Session() as session:
        return await session.get(Saved, (telegram_id, event_id)) is not None

async def save_event(telegram_id, event_id):
    async with Session() as session:
        if not await session.get(Event, event_id): return False
        result = await session.execute(insert_for(Saved).values(telegram_id=telegram_id, event_id=event_id).on_conflict_do_nothing())
        await session.commit()
        return result.rowcount > 0

async def remove_saved(telegram_id, event_id):
    async with Session() as session:
        obj = await session.get(Saved, (telegram_id, event_id))
        if obj: await session.delete(obj)
        await session.commit()

async def subscribed(telegram_id, event_id):
    async with Session() as session:
        return await session.get(Subscription, (telegram_id, event_id)) is not None

async def toggle_subscription(telegram_id, event_id):
    async with Session() as session:
        obj = await session.get(Subscription, (telegram_id, event_id))
        if obj:
            await session.delete(obj)
        else:
            if not await session.get(Event, event_id): return False
            session.add(Subscription(telegram_id=telegram_id, event_id=event_id))
        await session.commit()
        return obj is None

async def add_report(telegram_id, event_id, category, message):
    async with Session() as session:
        obj = Report(telegram_id=telegram_id, event_id=event_id, category=category, message=message)
        session.add(obj)
        await session.commit()
        return obj.id

async def pending_notifications(now=None):
    now = now or localnow()
    async with Session() as session:
        accounts = list((await session.scalars(select(Account))).all())
        events = list((await session.scalars(select(Event))).all())
        saved = set((await session.execute(select(Saved.telegram_id, Saved.event_id))).all())
        subs = set((await session.execute(select(Subscription.telegram_id, Subscription.event_id))).all())
        receipts = set((await session.execute(select(Receipt.telegram_id, Receipt.key))).all())
    out = []
    for account in accounts:
        if account.telegram_id <= 0: continue  # Website-only accounts have no Telegram delivery address.
        prefs = dict(account.profile or {})
        prefs.pop('topics', None)
        for event in events:
            if account.profile and account.notifications.get('new') and event.created_at > account.notification_since and matches(event, prefs, now):
                key = f'new:{event.id}'
                if (account.telegram_id, key) not in receipts: out.append((account, event, key, 'new_digest'))
            if account.notifications.get('expired', True) and (account.telegram_id, event.id) in saved and event_status(event, now) == 'expired':
                dated = event.deadline or event.start_at
                key = f'expired:{event.id}:{dated.isoformat()}'
                if (account.telegram_id, key) not in receipts: out.append((account, event, key, 'favorite_expired'))
            if account.notifications.get('deadlines') and event.deadline and event_status(event, now) != 'expired':
                if 0 <= (event.deadline.date() - now.date()).days <= 3 and ((account.telegram_id, event.id) in saved or (account.telegram_id, event.id) in subs):
                    key = f'deadline:{event.id}:{event.deadline.isoformat()}'
                    if (account.telegram_id, key) not in receipts: out.append((account, event, key, 'deadline_reminder'))
    return out

async def mark_notification(telegram_id, key):
    async with Session() as session:
        await session.execute(insert_for(Receipt).values(telegram_id=telegram_id, key=key).on_conflict_do_nothing())
        await session.commit()

async def database_ready(require_schema=False):
    async with Session() as session:
        await session.execute(select(Account.telegram_id).limit(1) if require_schema else text('SELECT 1'))
        if require_schema:
            for column in (Credential.id, WebSession.token_hash, AuthThrottle.key, Event.is_self_paced, Event.is_closed, Event.verified_at, CatalogSource.key,
                           Event.revision, Event.admin_overrides, Event.source_url, Event.admin_updated_at, Event.admin_updated_by,
                           Report.status, Report.review_note, Report.reviewed_by, Report.updated_at, Report.resolved_at, Report.revision, AdminAudit.id):
                await session.execute(select(column).limit(1))


def admin_user(telegram_id):
    return telegram_id == int(os.getenv('ADMIN_ID', '0')) and telegram_id != 0

async def get_submission(submission_id):
    async with Session() as session:
        return await session.get(Submission, submission_id)

async def list_submissions(telegram_id=None):
    async with Session() as session:
        stmt = select(Submission).order_by(Submission.created_at.desc(), Submission.id.desc())
        if telegram_id is not None: stmt = stmt.where(Submission.telegram_id == telegram_id)
        else: stmt = stmt.where(Submission.status == 'pending')
        return list((await session.scalars(stmt)).all())

async def submit_proposal(telegram_id, payload):
    from hashlib import sha256
    from sqlalchemy.exc import IntegrityError
    from import_events import Opportunity
    from proposals import canonical_url
    if not int(os.getenv('ADMIN_ID', '0')): return None, 'proposal_unconfigured'
    validated = Opportunity.model_validate(payload).model_dump(mode='json')
    normalized = canonical_url(validated['url'])
    validated['url'] = normalized
    fingerprint = sha256(normalized.encode()).hexdigest()
    now = utcnow()
    async with Session() as session:
        # Locks serialise quota checks for this account on PostgreSQL.
        await session.scalar(select(Account).where(Account.telegram_id == telegram_id).with_for_update())
        pending = await session.scalar(select(func.count()).select_from(Submission).where(Submission.telegram_id == telegram_id, Submission.status == 'pending'))
        recent = await session.scalar(select(func.count()).select_from(Submission).where(Submission.telegram_id == telegram_id, Submission.created_at >= now - timedelta(days=1)))
        if pending >= 3 or recent >= 3: return None, 'proposal_limit'
        if await session.scalar(select(Submission.id).where(Submission.fingerprint == fingerprint)): return None, 'proposal_duplicate'
        for url in (await session.scalars(select(Event.url))).all():
            try:
                if canonical_url(url) == normalized: return None, 'proposal_duplicate'
            except ValueError:
                continue
        latest = await session.scalar(select(Submission.created_at).where(Submission.telegram_id == telegram_id).order_by(Submission.created_at.desc()).limit(1))
        if latest and now - latest < timedelta(minutes=10): return None, 'proposal_cooldown'
        obj = Submission(telegram_id=telegram_id, fingerprint=fingerprint, payload=validated, created_at=now)
        session.add(obj)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return None, 'proposal_duplicate'
        return obj.id, None

async def edit_submission(submission_id, actor, payload):
    from import_events import Opportunity
    from proposals import canonical_url
    if not admin_user(actor): raise PermissionError('Admin only')
    validated = Opportunity.model_validate(payload).model_dump(mode='json')
    async with Session() as session:
        obj = await session.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
        if not obj or obj.status != 'pending': return False
        # The original URL/fingerprint cannot be silently changed during review.
        if canonical_url(validated['url']) != canonical_url(obj.payload['url']): return False
        obj.payload = validated
        await session.commit()
        return True

async def moderate_submission(submission_id, actor, decision, reason=''):
    from import_events import Opportunity
    from proposals import canonical_url
    if not admin_user(actor): raise PermissionError('Admin only')
    if decision not in ('approved', 'rejected'): raise ValueError('Invalid decision')
    if decision == 'rejected' and not 5 <= len(reason.strip()) <= 500: raise ValueError('Rejection needs a reason')
    async with Session() as session:
        obj = await session.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
        if not obj or obj.status != 'pending': return 'moderation_changed'
        if decision == 'approved':
            data = Opportunity.model_validate(obj.payload).event()
            if event_status(Event(**{key: getattr(data, key) for key in data.__dataclass_fields__})) == 'expired': return 'submission_expired'
            for url in (await session.scalars(select(Event.url))).all():
                try:
                    if canonical_url(url) == canonical_url(data.url): return 'proposal_duplicate'
                except ValueError:
                    continue
            values = {key: getattr(data, key) for key in data.__dataclass_fields__}
            result = await session.execute(insert_for(Event).values(**values).on_conflict_do_nothing())
            if result.rowcount == 0: return 'proposal_duplicate'
            obj.event_id = await session.scalar(select(Event.id).where(Event.external_id == data.external_id))
        obj.status = decision
        obj.reviewed_by = actor
        obj.reviewed_at = utcnow()
        obj.review_note = reason.strip()
        await session.commit()
        return 'moderation_done'

async def pending_decisions():
    async with Session() as session:
        rows = list((await session.scalars(select(Submission).where(Submission.status.in_(['approved', 'rejected'])))).all())
        receipts = set((await session.execute(select(Receipt.telegram_id, Receipt.key))).all())
        out = []
        for row in rows:
            if row.telegram_id <= 0: continue
            key = f'submission:{row.id}:{row.status}'
            if (row.telegram_id, key) in receipts: continue
            account = await session.get(Account, row.telegram_id)
            if account: out.append((account, row, key))
        return out


# Profile fields remain in JSON; shared authentication is kept in credentials.
# SQLite uses the local lock; PostgreSQL additionally locks claims across instances.
_profile_write_lock = asyncio.Lock()

async def nickname_available(value, telegram_id):
    from identity import normalize_nickname
    nickname = normalize_nickname(value)
    async with Session() as session:
        taken = await session.scalar(select(Account.telegram_id).where(
            func.lower(Account.profile['nickname'].as_string()) == nickname,
            Account.telegram_id != telegram_id).limit(1))
        return taken is None

async def save_profile(telegram_id, draft):
    from identity import normalize_nickname, normalize_name, age_group
    try:
        nickname = normalize_nickname(draft.get('nickname', ''))
        name = normalize_name(draft.get('display_name', ''))
        age = age_group(draft.get('age'))
    except ValueError as exc:
        return None, str(exc)
    async with _profile_write_lock:
        async with Session() as session:
            if engine.dialect.name == 'postgresql':
                await session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock_key('profile-claims')})
            taken = await session.scalar(select(Account.telegram_id).where(
                func.lower(Account.profile['nickname'].as_string()) == nickname,
                Account.telegram_id != telegram_id).limit(1))
            if taken is not None:
                return None, 'nickname_taken'
            claimed = await session.scalar(select(Credential).where(Credential.nickname == nickname,
                                                                    Credential.account_id != telegram_id))
            if claimed: return None, 'nickname_taken'
            account = await session.get(Account, telegram_id)
            if not account: raise ValueError('Account missing')
            previous = account.profile or {}
            profile = {key: deepcopy(draft.get(key, [] if key == 'criteria' else 'any'))
                       for key in ('country', 'city', 'format', 'criteria')}
            profile.update(nickname=nickname, display_name=name, age=age,
                           public_id=previous.get('public_id') or str(uuid4()),
                           profile_updated_at=utcnow().isoformat() + 'Z')
            account.profile = profile
            credential = await session.scalar(select(Credential).where(Credential.account_id == telegram_id))
            if credential: credential.nickname = nickname
            await session.commit()
            return profile, None
