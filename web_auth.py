"""Shared bot/site credentials and revocable, database-backed browser sessions."""
import asyncio
import hashlib
import hmac
import secrets
import threading
from contextlib import AsyncExitStack
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
from sqlalchemy import case, delete, func, select, text, update
from sqlalchemy.exc import IntegrityError

import database as db
from identity import identity_complete, normalize_name, normalize_nickname

PASSWORDS = PasswordHash.recommended()
PASSWORD_SLOTS = threading.BoundedSemaphore(2)
# A public dummy hash makes unknown-login and wrong-password verification comparable.
DUMMY_HASH = '$argon2id$v=19$m=65536,t=3,p=4$wagCPXjifgvUFBzq4hqe3w$CYaIb8sB+wtD+Vu/P4uod1+Qof8h+1g7bbDlBID48Rc'


class AuthError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def valid_password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        raise AuthError('password_length', 422)
    try: value.encode('utf-8')
    except UnicodeError: raise AuthError('invalid_request', 422) from None


async def hash_password(value):
    valid_password(value)
    def work():
        with PASSWORD_SLOTS: return PASSWORDS.hash(value)
    return await asyncio.to_thread(work)


async def verify_password(value, encoded):
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        return False
    try:
        def work():
            with PASSWORD_SLOTS: return PASSWORDS.verify(value, encoded)
        return await asyncio.to_thread(work)
    except (ValueError, TypeError, UnicodeError, PwdlibError):
        return False


async def reserve_attempt(bucket, limit=10):
    """Atomic fixed-window limiter shared by serverless instances."""
    now = db.utcnow()
    cutoff = now - timedelta(minutes=15)
    table = db.AuthThrottle
    async with db.Session() as session:
        stmt = db.insert_for(table).values(key=token_hash(bucket), window_start=now, attempts=1)
        stmt = stmt.on_conflict_do_update(index_elements=['key'], set_={
            'window_start': case((table.window_start < cutoff, now), else_=table.window_start),
            'attempts': case((table.window_start < cutoff, 1), else_=table.attempts + 1),
        }).returning(table.attempts)
        count = await session.scalar(stmt)
        await session.commit()
    if count > limit:
        raise AuthError('too_many_attempts', 429)


async def has_password(account_id):
    async with db.Session() as session:
        return await session.scalar(select(db.Credential.id).where(db.Credential.account_id == account_id)) is not None


async def _claim_lock(session):
    if db.engine.dialect.name == 'postgresql':
        await session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': db.lock_key('profile-claims')})


async def set_bot_password_hash(account_id, encoded):
    """Only the private-chat handler may call this after Telegram verified its sender."""
    if account_id <= 0 or not encoded.startswith('$argon2id$'):
        raise AuthError('profile_required', 409)
    async with db._profile_write_lock:
        async with db.Session() as session:
            await _claim_lock(session)
            account = await session.get(db.Account, account_id)
            credential = await session.scalar(select(db.Credential).where(db.Credential.account_id == account_id))
            if not account or (not credential and not identity_complete(account.profile)):
                raise AuthError('profile_required', 409)
            nickname = credential.nickname if credential else normalize_nickname(account.profile['nickname'])
            claimed = await session.scalar(select(db.Credential.id).where(db.Credential.nickname == nickname,
                                                                          db.Credential.account_id != account_id))
            if claimed: raise AuthError('nickname_taken', 409)
            if credential:
                credential.nickname = nickname
                credential.password_hash = encoded
                await session.execute(delete(db.WebSession).where(db.WebSession.credential_id == credential.id))
            else:
                session.add(db.Credential(account_id=account_id, nickname=nickname, password_hash=encoded))
            await session.commit()


async def authenticate(nickname, password, bucket):
    await reserve_attempt('login:' + bucket)
    try:
        nickname = normalize_nickname(nickname)
    except ValueError:
        nickname = ''
    async with db.Session() as session:
        credential = await session.scalar(select(db.Credential).where(db.Credential.nickname == nickname))
    valid = await verify_password(password, credential.password_hash if credential else DUMMY_HASH)
    if not credential or not valid:
        raise AuthError('invalid_credentials', 401)
    return credential


async def register(nickname, display_name, password, language, bucket):
    await reserve_attempt('register:' + bucket, 5)
    nickname, display_name = normalize_nickname(nickname), normalize_name(display_name)
    encoded = await hash_password(password)
    async with db._profile_write_lock:
        async with db.Session() as session:
            await _claim_lock(session)
            taken = await session.scalar(select(db.Account.telegram_id).where(
                func.lower(db.Account.profile['nickname'].as_string()) == nickname))
            claimed = await session.scalar(select(db.Credential.id).where(db.Credential.nickname == nickname))
            if taken is not None or claimed:
                # Existing bot identities must set their password in their own private chat.
                raise AuthError('nickname_taken', 409)
            account_id = -(secrets.randbits(62) + 1)
            account = db.Account(telegram_id=account_id, language=language, profile={
                'nickname': nickname, 'display_name': display_name, 'public_id': str(uuid4()),
                'age': 'any', 'country': 'any', 'city': 'any', 'format': 'any', 'criteria': [],
                'profile_updated_at': db.utcnow().isoformat() + 'Z',
            })
            session.add(account)
            await session.flush()
            credential = db.Credential(account_id=account_id, nickname=nickname, password_hash=encoded)
            session.add(credential)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise AuthError('nickname_taken', 409) from None
            return credential


async def issue_session(verified, days=7):
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    async with db.Session() as session:
        credential = await session.scalar(select(db.Credential).where(db.Credential.id == verified.id).with_for_update())
        if not credential or not hmac.compare_digest(credential.password_hash, verified.password_hash):
            raise AuthError('invalid_credentials', 401)
        now = db.utcnow()
        await session.execute(delete(db.WebSession).where(db.WebSession.expires_at <= now))
        await session.execute(delete(db.AuthThrottle).where(db.AuthThrottle.window_start < now - timedelta(days=1)))
        session.add(db.WebSession(token_hash=token_hash(raw), credential_id=credential.id,
                                 csrf_hash=token_hash(csrf), expires_at=now + timedelta(days=days)))
        await session.commit()
    return raw, csrf


async def session_account(raw):
    if not raw or len(raw) > 128: return None
    async with db.Session() as session:
        row = (await session.execute(select(db.WebSession, db.Credential, db.Account)
               .join(db.Credential, db.Credential.id == db.WebSession.credential_id)
               .join(db.Account, db.Account.telegram_id == db.Credential.account_id)
               .where(db.WebSession.token_hash == token_hash(raw), db.WebSession.expires_at > db.utcnow()))).first()
        return row


async def logout(raw):
    if not raw: return
    async with db.Session() as session:
        await session.execute(delete(db.WebSession).where(db.WebSession.token_hash == token_hash(raw)))
        await session.commit()


async def change_password(credential_id, old_password, new_password):
    async with db.Session() as session:
        credential = await session.get(db.Credential, credential_id)
    if not credential or not await verify_password(old_password, credential.password_hash):
        raise AuthError('invalid_credentials', 401)
    encoded = await hash_password(new_password)
    async with db.Session() as session:
        current = await session.scalar(select(db.Credential).where(db.Credential.id == credential_id).with_for_update())
        if not current or current.password_hash != credential.password_hash:
            raise AuthError('invalid_credentials', 401)
        current.password_hash = encoded
        await session.execute(delete(db.WebSession).where(db.WebSession.credential_id == credential_id))
        await session.commit()


async def delete_website_account(credential_id, password, confirmation):
    """Reauthenticate before erasing the one shared bot/site account."""
    async with db.Session() as session:
        credential = await session.get(db.Credential, credential_id)
    if not credential or not await verify_password(password, credential.password_hash):
        raise AuthError('invalid_credentials', 401)
    if confirmation.strip() != credential.nickname:
        raise AuthError('delete_confirmation', 422)
    await _erase_account(credential.account_id, credential)


async def delete_bot_account(account_id, confirmation):
    """Private-chat caller must use the Telegram-verified sender ID, never an input ID."""
    if account_id <= 0: raise AuthError('invalid_request', 422)
    async with db.Session() as session:
        account = await session.get(db.Account, account_id)
    if not account: raise AuthError('authentication_required', 401)
    nickname = (account.profile or {}).get('nickname') or 'DELETE'
    if confirmation.strip() != nickname:
        raise AuthError('delete_confirmation', 422)
    await _erase_account(account_id)


async def _erase_account(account_id, verified=None):
    async with db._profile_write_lock:
        async with db.Session() as session:
            await _claim_lock(session)
            account = await session.scalar(select(db.Account).where(db.Account.telegram_id == account_id).with_for_update())
            credential = await session.scalar(select(db.Credential).where(db.Credential.account_id == account_id).with_for_update())
            if not account: raise AuthError('authentication_required', 401)
            if verified and (not credential or credential.id != verified.id or
                             not hmac.compare_digest(credential.password_hash, verified.password_hash) or
                             credential.nickname != verified.nickname):
                raise AuthError('invalid_credentials', 401)
            if credential:
                await session.execute(delete(db.WebSession).where(db.WebSession.credential_id == credential.id))
                await session.delete(credential)
                await session.flush()
            # Public listings survive; private drafts, proposals, reports and delivery data do not.
            for model in (db.Saved, db.Subscription, db.Receipt, db.Submission, db.Report, db.User):
                await session.execute(delete(model).where(model.telegram_id == account_id))
            await session.execute(update(db.Event).where(db.Event.admin_updated_by == account_id).values(admin_updated_by=None))
            await session.execute(update(db.Submission).where(db.Submission.reviewed_by == account_id).values(reviewed_by=None))
            await session.execute(update(db.Report).where(db.Report.reviewed_by == account_id).values(reviewed_by=None))
            await session.execute(update(db.AdminAudit).where(db.AdminAudit.actor_id == account_id).values(actor_id=0))
            await session.delete(account)
            await session.commit()


async def attach_website_account(verified, telegram_id, telegram_locked=False):
    """Link a website-first login to its first Telegram account without changing web sessions."""
    if verified.account_id == telegram_id: return await db.get_account(telegram_id)
    if verified.account_id > 0:
        raise AuthError('telegram_already_linked', 409)
    async with AsyncExitStack() as stack:
        for account_id in sorted((verified.account_id, telegram_id)):
            if telegram_locked and account_id == telegram_id: continue
            acquired = await stack.enter_async_context(db.distributed_lock(f'user:{account_id}'))
            if not acquired: raise AuthError('account_busy', 409)
        async with db._profile_write_lock:
            async with db.Session() as session:
                await _claim_lock(session)
                credential = await session.scalar(select(db.Credential).where(db.Credential.id == verified.id).with_for_update())
                if not credential or credential.password_hash != verified.password_hash:
                    raise AuthError('invalid_credentials', 401)
                if credential.account_id != verified.account_id:
                    raise AuthError('telegram_already_linked', 409)
                target_login = await session.scalar(select(db.Credential.id).where(db.Credential.account_id == telegram_id))
                if target_login: raise AuthError('telegram_already_linked', 409)
                source = await session.get(db.Account, credential.account_id)
                target = await session.get(db.Account, telegram_id)
                if not source or not target: raise AuthError('invalid_credentials', 401)
                for field in ('profile', 'language', 'search_defaults', 'notifications', 'notification_since'):
                    setattr(target, field, deepcopy(getattr(source, field)))
                target.flow = {'screen': 'menu', 'revision': target.flow.get('revision', 0), 'history': []}
                for model in (db.Saved, db.Subscription):
                    rows = list((await session.scalars(select(model).where(model.telegram_id == source.telegram_id))).all())
                    for row in rows:
                        await session.execute(db.insert_for(model).values(telegram_id=telegram_id, event_id=row.event_id).on_conflict_do_nothing())
                    await session.execute(delete(model).where(model.telegram_id == source.telegram_id))
                for model in (db.Submission, db.Report, db.Receipt):
                    if model is db.Receipt:
                        # Website-only accounts never generate Telegram delivery receipts.
                        await session.execute(delete(model).where(model.telegram_id == source.telegram_id))
                    else:
                        await session.execute(update(model).where(model.telegram_id == source.telegram_id).values(telegram_id=telegram_id))
                credential.account_id = telegram_id
                await session.flush()
                await session.delete(source)
                await session.commit()
    return await db.get_account(telegram_id)
