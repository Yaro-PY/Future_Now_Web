"""Shared MFA: encrypted TOTP, private Telegram codes, browser-bound challenges."""
import base64
import hashlib
import hmac
import io
import os
import re
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, select, update
from sqlalchemy.orm.attributes import set_committed_value

import database as db
import web_auth as auth

TTL = 300
MAX_ATTEMPTS = 5


def cipher():
    try:
        return Fernet(os.environ.get('AUTH_ENCRYPTION_KEY', '').encode())
    except (ValueError, TypeError):
        raise auth.AuthError('two_factor_unavailable', 503) from None


def configured():
    try: cipher(); return True
    except auth.AuthError: return False


def decrypt(value):
    try: return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, UnicodeError):
        raise auth.AuthError('two_factor_unavailable', 503) from None


def digest(label, value):
    cipher()
    key = base64.urlsafe_b64decode(os.environ['AUTH_ENCRYPTION_KEY'])
    return hmac.new(key, (label + ':' + value).encode(), hashlib.sha256).hexdigest()


def methods(state):
    result = []
    if state and state.totp_secret: result.append('totp')
    if state and state.telegram_enabled: result.append('telegram')
    if state and state.recovery_hashes: result.append('recovery')
    return result


def enabled(state):
    return bool(state and (state.totp_secret or state.telegram_enabled))


@dataclass(frozen=True)
class FactorProof:
    credential_id: str
    revision: int
    credential_digest: str


async def require_factor(session, credential, proof=None):
    state = await session.scalar(select(db.TwoFactor).where(db.TwoFactor.credential_id == credential.id).with_for_update())
    if enabled(state):
        if not isinstance(proof, FactorProof) or (proof.credential_id, proof.revision, proof.credential_digest) != (
                credential.id, state.revision, auth.token_hash(credential.password_hash)):
            raise auth.AuthError('two_factor_required', 403)


async def status(credential_id, account_id):
    async with db.Session() as session:
        state = await session.get(db.TwoFactor, credential_id)
        return {'configured': configured(), 'totp_enabled': bool(state and state.totp_secret),
                'telegram_enabled': bool(state and state.telegram_enabled), 'telegram_available': account_id > 0,
                'recovery_codes_remaining': len(state.recovery_hashes or []) if state else 0}


async def _locked(session, credential_id):
    credential = await session.scalar(select(db.Credential).where(db.Credential.id == credential_id).with_for_update())
    if not credential: raise auth.AuthError('authentication_required', 401)
    state = await session.scalar(select(db.TwoFactor).where(db.TwoFactor.credential_id == credential_id).with_for_update())
    if not state:
        state = db.TwoFactor(credential_id=credential_id)
        session.add(state)
        await session.flush()
    return credential, state


def _challenge_out(token, state, purpose):
    available = methods(state)
    return {'challenge_token': token, 'methods': available or ['none'], 'expires_in': TTL,
            'telegram_url': 'https://t.me/FutureNowAssistantBot?start=2fa_' + token
                            if 'telegram' in available or purpose == 'telegram_enroll' else None}


async def _new(session, credential, state, binding, purpose):
    cipher()
    token = secrets.token_urlsafe(32)
    await session.execute(delete(db.AuthChallenge).where(db.AuthChallenge.expires_at < db.utcnow()))
    session.add(db.AuthChallenge(token_hash=auth.token_hash(token), credential_id=credential.id,
        binding_hash=binding, purpose=purpose, credential_digest=auth.token_hash(credential.password_hash),
        factor_revision=state.revision, expires_at=db.utcnow() + timedelta(seconds=TTL)))
    return _challenge_out(token, state, purpose)


async def begin_login(verified, binding):
    async with db.Session() as session:
        credential, state = await _locked(session, verified.id)
        if credential.password_hash != verified.password_hash: raise auth.AuthError('invalid_credentials', 401)
        if not enabled(state): return None
        result = await _new(session, credential, state, binding, 'login')
        await session.commit()
        return {'two_factor_required': True, **result}


async def authorize(credential_id, password, binding):
    await auth.reserve_attempt('mfa-manage:' + credential_id)
    async with db.Session() as session:
        credential = await session.get(db.Credential, credential_id)
    if not credential or not await auth.verify_password(password, credential.password_hash):
        raise auth.AuthError('invalid_current_password', 403)
    async with db.Session() as session:
        current, state = await _locked(session, credential_id)
        if current.password_hash != credential.password_hash: raise auth.AuthError('invalid_current_password', 403)
        result = await _new(session, current, state, binding, 'manage')
        await session.commit()
        return result


def _step(secret, code):
    if not re.fullmatch(r'[0-9]{6}', code): return None
    counter = int(time.time()) // 30
    otp = pyotp.TOTP(secret)
    for step in (counter, counter - 1, counter + 1):
        if hmac.compare_digest(otp.generate_otp(step), code): return step
    return None


async def _verify(session, credential, state, challenge, method, code):
    if method == 'totp' and state.totp_secret:
        step = _step(decrypt(state.totp_secret), code)
        if step is None: raise auth.AuthError('invalid_two_factor_code', 422)
        result = await session.execute(update(db.TwoFactor).where(db.TwoFactor.credential_id == credential.id,
            db.TwoFactor.last_totp_step < step).values(last_totp_step=step).execution_options(synchronize_session=False))
        if result.rowcount != 1: raise auth.AuthError('two_factor_code_used', 422)
        set_committed_value(state, 'last_totp_step', step)
    elif method == 'telegram' and (state.telegram_enabled or challenge.purpose == 'telegram_enroll'):
        if not re.fullmatch(r'[0-9]{6}', code) or not challenge.telegram_code_hash or not hmac.compare_digest(
                digest('telegram:' + challenge.token_hash, code), challenge.telegram_code_hash):
            raise auth.AuthError('invalid_two_factor_code', 422)
    elif method == 'recovery' and enabled(state):
        normalized = re.sub(r'[\s-]', '', code).upper()
        if not re.fullmatch(r'[A-F0-9]{10}', normalized):
            raise auth.AuthError('invalid_two_factor_code', 422)
        code_hash = digest('recovery:' + credential.id, normalized)
        hashes = list(state.recovery_hashes or [])
        if code_hash not in hashes:
            raise auth.AuthError('invalid_two_factor_code', 422)
        hashes.remove(code_hash)
        result = await session.execute(update(db.TwoFactor).where(db.TwoFactor.credential_id == credential.id,
            db.TwoFactor.revision == state.revision).values(recovery_hashes=hashes, revision=state.revision + 1)
            .execution_options(synchronize_session=False))
        if result.rowcount != 1: raise auth.AuthError('challenge_expired', 409)
        set_committed_value(state, 'recovery_hashes', hashes)
        set_committed_value(state, 'revision', state.revision + 1)
    elif method == 'none' and not enabled(state) and challenge.purpose == 'manage':
        pass
    else: raise auth.AuthError('invalid_two_factor_code', 422)


async def _consume(session, credential, state, token, binding, purpose, method, code):
    challenge = await session.scalar(select(db.AuthChallenge).where(db.AuthChallenge.token_hash == auth.token_hash(token)).with_for_update())
    if not challenge or challenge.credential_id != credential.id or challenge.purpose != purpose or challenge.consumed \
       or challenge.expires_at <= db.utcnow() or challenge.attempts >= MAX_ATTEMPTS \
       or not hmac.compare_digest(challenge.binding_hash, binding) \
       or challenge.credential_digest != auth.token_hash(credential.password_hash) or challenge.factor_revision != state.revision:
        raise auth.AuthError('challenge_expired', 409)
    try:
        await _verify(session, credential, state, challenge, method, code)
    except auth.AuthError as error:
        if error.code in ('invalid_two_factor_code', 'two_factor_code_used'):
            # Failed attempts must persist even when the API returns an error.
            await session.execute(update(db.AuthChallenge).where(db.AuthChallenge.token_hash == challenge.token_hash)
                .values(attempts=db.AuthChallenge.attempts + 1))
            await session.commit()
        raise
    result = await session.execute(update(db.AuthChallenge).where(db.AuthChallenge.token_hash == challenge.token_hash,
        db.AuthChallenge.consumed.is_(False)).values(consumed=True).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        await session.rollback()
        raise auth.AuthError('challenge_expired', 409)
    return FactorProof(credential.id, state.revision, auth.token_hash(credential.password_hash))


async def finish_login(token, binding, method, code):
    if not token or len(token) > 100: raise auth.AuthError('challenge_expired', 409)
    await auth.reserve_attempt('mfa-login:' + auth.token_hash(token), 10)
    async with db.Session() as session:
        challenge = await session.get(db.AuthChallenge, auth.token_hash(token))
        if not challenge: raise auth.AuthError('challenge_expired', 409)
        credential, state = await _locked(session, challenge.credential_id)
        proof = await _consume(session, credential, state, token, binding, 'login', method, code)
        await session.commit()
        return credential, proof


async def telegram_code(token, telegram_id):
    if not token or len(token) > 100: raise auth.AuthError('challenge_expired', 409)
    await auth.reserve_attempt('mfa-telegram:' + str(telegram_id), 20)
    async with db.Session() as session:
        challenge = await session.get(db.AuthChallenge, auth.token_hash(token))
        if not challenge: raise auth.AuthError('challenge_expired', 409)
        credential, state = await _locked(session, challenge.credential_id)
        challenge = await session.scalar(select(db.AuthChallenge).where(db.AuthChallenge.token_hash == challenge.token_hash).with_for_update())
        if credential.account_id != telegram_id or telegram_id <= 0:
            raise auth.AuthError('challenge_expired', 409)
        if challenge.purpose not in ('login', 'manage', 'telegram_enroll') or challenge.consumed \
           or challenge.expires_at <= db.utcnow() or challenge.attempts >= MAX_ATTEMPTS \
           or challenge.credential_digest != auth.token_hash(credential.password_hash) or challenge.factor_revision != state.revision \
           or (not state.telegram_enabled and challenge.purpose != 'telegram_enroll'):
            raise auth.AuthError('challenge_expired', 409)
        if challenge.sent_at and db.utcnow() - challenge.sent_at < timedelta(seconds=60):
            raise auth.AuthError('two_factor_cooldown', 429)
        code = f'{secrets.randbelow(1_000_000):06d}'
        challenge.telegram_code_hash = digest('telegram:' + challenge.token_hash, code)
        challenge.sent_at = db.utcnow()
        await session.commit()
        return code, credential.nickname, challenge.purpose


def _recovery_codes(credential, state):
    codes = [secrets.token_hex(5).upper() for _ in range(8)]
    state.recovery_hashes = [digest('recovery:' + credential.id, code) for code in codes]
    return [code[:5] + '-' + code[5:] for code in codes]


async def _revoke_other_sessions(session, credential_id, keep):
    await session.execute(delete(db.WebSession).where(db.WebSession.credential_id == credential_id,
                                                     db.WebSession.token_hash != keep))


async def manage(credential_id, binding, authorization, action):
    """Password-verified, single-use authorization before changing MFA settings."""
    async with db.Session() as session:
        credential, state = await _locked(session, credential_id)
        await _consume(session, credential, state, authorization['challenge_token'], binding,
                       'manage', authorization['method'], authorization['code'])
        result = {}
        if action == 'totp_setup':
            if state.totp_secret: raise auth.AuthError('two_factor_already_enabled', 409)
            secret, token = pyotp.random_base32(), secrets.token_urlsafe(32)
            state.pending_secret = cipher().encrypt(secret.encode()).decode()
            state.pending_token_hash, state.pending_session = auth.token_hash(token), binding
            state.pending_expires = db.utcnow() + timedelta(minutes=10)
            uri = pyotp.TOTP(secret).provisioning_uri(name=credential.nickname, issuer_name='Future Now')
            image = qrcode.make(uri)
            output = io.BytesIO(); image.save(output, format='PNG')
            result = {'setup_token': token, 'secret': secret, 'otpauth_uri': uri,
                      'qr_code': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}
        elif action == 'telegram_setup':
            if credential.account_id <= 0: raise auth.AuthError('telegram_link_required', 409)
            if state.telegram_enabled: raise auth.AuthError('two_factor_already_enabled', 409)
            result = await _new(session, credential, state, binding, 'telegram_enroll')
        elif action in ('totp_disable', 'telegram_disable'):
            if action == 'totp_disable':
                state.totp_secret = None
                state.pending_secret = state.pending_token_hash = state.pending_session = state.pending_expires = None
                state.last_totp_step = -1
            else: state.telegram_enabled = False
            state.revision += 1
            if not enabled(state): state.recovery_hashes = []
            await _revoke_other_sessions(session, credential.id, binding)
        elif action == 'recovery_codes':
            if not enabled(state): raise auth.AuthError('two_factor_required', 409)
            result['recovery_codes'] = _recovery_codes(credential, state)
            state.revision += 1
            await _revoke_other_sessions(session, credential.id, binding)
        else: raise ValueError('Unknown MFA action')
        await session.commit()
        return result


async def enable_totp(credential_id, binding, token, code):
    await auth.reserve_attempt('totp-enroll:' + credential_id, 10)
    async with db.Session() as session:
        credential, state = await _locked(session, credential_id)
        if state.totp_secret or not state.pending_secret or state.pending_expires <= db.utcnow() \
           or state.pending_token_hash != auth.token_hash(token) or state.pending_session != binding:
            raise auth.AuthError('challenge_expired', 409)
        step = _step(decrypt(state.pending_secret), code)
        if step is None: raise auth.AuthError('invalid_two_factor_code', 422)
        first = not enabled(state)
        state.totp_secret = state.pending_secret
        state.last_totp_step = step
        state.pending_secret = state.pending_token_hash = state.pending_session = state.pending_expires = None
        state.revision += 1
        codes = _recovery_codes(credential, state) if first else []
        await _revoke_other_sessions(session, credential.id, binding)
        await session.commit()
        return {'recovery_codes': codes}


async def enable_telegram(credential_id, binding, token, code):
    async with db.Session() as session:
        credential, state = await _locked(session, credential_id)
        if credential.account_id <= 0: raise auth.AuthError('telegram_link_required', 409)
        if state.telegram_enabled: raise auth.AuthError('two_factor_already_enabled', 409)
        await _consume(session, credential, state, token, binding, 'telegram_enroll', 'telegram', code)
        first = not enabled(state)
        state.telegram_enabled = True
        state.revision += 1
        codes = _recovery_codes(credential, state) if first else []
        await _revoke_other_sessions(session, credential.id, binding)
        await session.commit()
        return {'recovery_codes': codes}


async def verify_bot_link(verified, code):
    """Website-first accounts cannot bypass TOTP by linking an attacker's Telegram."""
    await auth.reserve_attempt('bot-mfa:' + verified.id, MAX_ATTEMPTS)
    async with db.Session() as session:
        credential, state = await _locked(session, verified.id)
        if credential.password_hash != verified.password_hash: raise auth.AuthError('invalid_credentials', 401)
        if not enabled(state): return FactorProof(credential.id, state.revision, auth.token_hash(credential.password_hash))
        # An unlinked website account can use its authenticator or a recovery code.
        challenge = db.AuthChallenge(purpose='bot_link')
        await _verify(session, credential, state, challenge, 'totp' if re.fullmatch(r'[0-9]{6}', code) else 'recovery', code)
        proof = FactorProof(credential.id, state.revision, auth.token_hash(credential.password_hash))
        await session.commit()
        return proof


async def invalidate_pending(session, credential_id):
    await session.execute(delete(db.AuthChallenge).where(db.AuthChallenge.credential_id == credential_id))
    await session.execute(update(db.TwoFactor).where(db.TwoFactor.credential_id == credential_id).values(
        pending_secret=None, pending_token_hash=None, pending_session=None, pending_expires=None))
