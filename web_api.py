"""Versioned JSON API for Future Now's future frontend."""
import hmac
import math
import os
from dataclasses import dataclass
from datetime import timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import account_preferences as ui
import database as db
import web_auth as auth
import web_schemas as schema
from flow_catalog import CATALOGS, CRITERIA, FIELDS, TOPICS, TYPES, CITIES, COUNTRIES, FORMATS, label, tr
from identity import identity_complete, age_group
from links import check_link
from catalog_status import catalog_status

router = APIRouter(prefix='/api/v1', tags=['Website'])
SESSION_COOKIE = 'fn_session'
CSRF_COOKIE = 'fn_csrf'
COOKIE_PATH = '/api/v1'

MESSAGES = {
    'authentication_required': ('Увійдіть у свій акаунт.', 'Sign in to your account.'),
    'invalid_credentials': ('Неправильний логін або пароль.', 'Incorrect login or password.'),
    'nickname_taken': ('Нік уже зайнятий. Якщо це ваш профіль у боті, задайте пароль через /password і увійдіть.', 'Nickname is taken. For your existing bot profile, set a password with /password and sign in.'),
    'password_length': ('Пароль має містити 12–128 символів.', 'Use a password of 12–128 characters.'),
    'too_many_attempts': ('Забагато спроб. Спробуйте через 15 хвилин.', 'Too many attempts. Try again in 15 minutes.'),
    'csrf_failed': ('Оновіть сесію та повторіть дію.', 'Refresh your session and try again.'),
    'origin_forbidden': ('Цей сайт не має доступу до API.', 'This website is not allowed to access the API.'),
    'not_found': ('Запис не знайдено.', 'Record not found.'),
    'admin_required': ('Потрібні права адміністратора.', 'Administrator access required.'),
    'account_busy': ('Інша дія ще виконується. Спробуйте знову.', 'Another action is running. Try again.'),
    'invalid_request': ('Перевірте введені дані.', 'Check the submitted fields.'),
    'database_unavailable': ('База даних тимчасово недоступна.', 'The database is temporarily unavailable.'),
    'link_unavailable': ('Посилання зараз недоступне.', 'The link is currently unavailable.'),
    'opportunity_expired': ('Можливість завершена.', 'This opportunity has expired.'),
    'edit_conflict': ('Запис уже змінено. Оновіть його та повторіть редагування.', 'This record has changed. Reload it before editing again.'),
    'invalid_current_password': ('Неправильний поточний пароль.', 'Incorrect current password.'),
    'delete_confirmation': ('Для підтвердження введіть свій нік точно як у профілі.', 'Type your nickname exactly as shown in your profile to confirm.'),
    'proposal_not_pending': ('Пропозиція вже опрацьована або відкликана. Її не можна змінити.', 'This proposal has been reviewed or withdrawn and can no longer be changed.'),
    'duplicate_url': ('Оголошення з таким посиланням уже існує.', 'A listing with this URL already exists.'),
}


def request_language(request):
    selected = getattr(request.state, 'language', None) or request.query_params.get('lang')
    return selected if selected in ('uk', 'en') else ('en' if request.headers.get('Accept-Language', '').lower().startswith('en') else 'uk')


def error_body(code, language='uk'):
    if code in MESSAGES:
        message = MESSAGES[code][language == 'en']
    else:
        try: message = tr(code, language)
        except KeyError: message = MESSAGES['invalid_request'][language == 'en']
    return {'error': {'code': code, 'message': message}}


def fail(code, status=400):
    raise auth.AuthError(code, status)


def allowed_origins():
    default = '' if os.getenv('VERCEL') == '1' else 'http://localhost:5173,http://127.0.0.1:5173'
    result = []
    for value in os.getenv('WEB_ALLOWED_ORIGINS', default).split(','):
        value = value.strip().rstrip('/')
        if not value: continue
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('WEB_ALLOWED_ORIGINS must contain exact HTTP(S) origins')
        result.append(value)
    return result


def check_origin(request):
    origin = request.headers.get('Origin')
    if origin is None: return
    own = str(request.base_url).rstrip('/')
    configured = os.getenv('WEBHOOK_BASE_URL', '').rstrip('/')
    if origin not in {own, configured, *allowed_origins()}:
        fail('origin_forbidden', 403)


def client_bucket(request, nickname=''):
    # Do not accept arbitrary forwarded IP headers from callers.
    address = request.client.host if request.client else 'unknown'
    return auth.token_hash(address + ':' + nickname.strip().lower())


def session_days():
    return max(1, min(30, int(os.getenv('WEB_SESSION_DAYS', '7'))))


def set_cookies(response, request, raw, csrf):
    secure = os.getenv('WEB_COOKIE_SECURE', 'true' if os.getenv('VERCEL') == '1' or request.url.scheme == 'https' else 'false').lower() == 'true'
    same_site = os.getenv('WEB_COOKIE_SAMESITE', 'lax')
    if same_site not in ('lax', 'strict', 'none') or (same_site == 'none' and not secure):
        raise ValueError('Cross-site cookies require WEB_COOKIE_SECURE=true')
    for name, value in ((SESSION_COOKIE, raw), (CSRF_COOKIE, csrf)):
        response.set_cookie(name, value, max_age=session_days() * 86400, httponly=True,
                            secure=secure, samesite=same_site, path=COOKIE_PATH)


def clear_cookies(response):
    for name in (SESSION_COOKIE, CSRF_COOKIE): response.delete_cookie(name, path=COOKIE_PATH)


@dataclass
class Principal:
    session: db.WebSession
    credential: db.Credential
    account: db.Account


async def optional_user(request: Request):
    row = await auth.session_account(request.cookies.get(SESSION_COOKIE))
    if not row: return None
    result = Principal(*row)
    request.state.language = result.account.language
    return result


async def current_user(user: Principal | None = Depends(optional_user)):
    if user is None: fail('authentication_required', 401)
    return user


async def changing_user(request: Request, csrf_header: str | None = Header(None, alias='X-CSRF-Token'),
                        user: Principal = Depends(current_user)):
    check_origin(request)
    csrf = csrf_header or ''
    cookie = request.cookies.get(CSRF_COOKIE, '')
    if not csrf or not hmac.compare_digest(csrf, cookie) or not hmac.compare_digest(auth.token_hash(csrf), user.session.csrf_hash):
        fail('csrf_failed', 403)
    async with db.distributed_lock(f'user:{user.account.telegram_id}') as acquired:
        if not acquired: fail('account_busy', 409)
        # A reset/deletion may have completed while this request waited for the lock.
        fresh = await optional_user(request)
        if fresh is None: fail('authentication_required', 401)
        yield fresh


def effective_filters(account):
    prefs = ui.defaults(account, 'search')
    values = {key: prefs.get(key, 'any') for key in ('type', 'age', 'country', 'city', 'format', 'date')}
    for key in values:
        if values[key] not in CATALOGS[key]: values[key] = 'any'
    values['criteria'] = sorted({key for key in prefs.get('criteria', []) if key in CRITERIA})
    if 'free' in values['criteria'] and 'paid' in values['criteria']: values['criteria'].remove('paid')
    return schema.Filters.model_validate(values)


def user_out(account):
    profile = account.profile or {}
    visible = {key: profile[key] for key in ('nickname', 'display_name', 'public_id', 'profile_updated_at', 'age', 'country', 'city', 'format', 'criteria') if key in profile}
    try:
        visible['age'] = age_group(profile.get('age'))
        profile_complete = identity_complete(profile)
    except ValueError:
        profile_complete = False
    # A completed Telegram profile already supplies usable search preferences.
    # New website registrations still complete their initial filter step.
    needs_filters = not bool(account.search_defaults) and not (account.telegram_id > 0 and profile_complete)
    return schema.UserOut(public_id=profile.get('public_id'), nickname=profile.get('nickname'),
        display_name=profile.get('display_name'), language=account.language,
        role='admin' if db.admin_user(account.telegram_id) else 'user', telegram_linked=account.telegram_id > 0,
        profile=visible or None, filters=effective_filters(account),
        notifications=schema.Notifications.model_validate(account.notifications),
        onboarding_required=not profile_complete,
        filters_setup_required=needs_filters)


async def login_response(credential, request, response):
    raw, csrf = await auth.issue_session(credential, session_days())
    set_cookies(response, request, raw, csrf)
    account = await db.get_account(credential.account_id)
    request.state.language = account.language
    return schema.SessionOut(user=user_out(account), csrf_token=csrf)


@router.post('/auth/register', response_model=schema.SessionOut, status_code=201, tags=['Authentication'])
async def register(body: schema.Register, request: Request, response: Response):
    check_origin(request)
    credential = await auth.register(body.nickname, body.display_name, body.password.get_secret_value(), body.language, client_bucket(request))
    return await login_response(credential, request, response)


@router.post('/auth/login', response_model=schema.SessionOut, tags=['Authentication'])
async def login(body: schema.Login, request: Request, response: Response):
    check_origin(request)
    await auth.reserve_attempt('login-ip:' + client_bucket(request), 60)
    credential = await auth.authenticate(body.nickname, body.password.get_secret_value(), client_bucket(request, body.nickname))
    return await login_response(credential, request, response)


@router.get('/auth/session', response_model=schema.SessionOut, tags=['Authentication'])
async def session(request: Request, user: Principal = Depends(current_user)):
    csrf = request.cookies.get(CSRF_COOKIE, '')
    if not csrf or not hmac.compare_digest(auth.token_hash(csrf), user.session.csrf_hash): fail('csrf_failed', 403)
    return schema.SessionOut(user=user_out(user.account), csrf_token=csrf)


@router.post('/auth/logout', status_code=204, tags=['Authentication'])
async def logout(request: Request, user: Principal = Depends(changing_user)):
    await auth.logout(request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=204)
    clear_cookies(response)
    return response


@router.post('/auth/password', tags=['Authentication'])
async def password(body: schema.PasswordChange, request: Request, response: Response, user: Principal = Depends(changing_user)):
    await auth.reserve_attempt('password:' + user.credential.id)
    await auth.change_password(user.credential.id, body.current_password.get_secret_value(), body.new_password.get_secret_value())
    clear_cookies(response)
    return {'ok': True, 'reauthentication_required': True}


@router.delete('/me', status_code=204, tags=['Authentication'])
async def delete_me(body: schema.AccountDelete, user: Principal = Depends(changing_user)):
    await auth.reserve_attempt('delete-account:' + user.credential.id, 5)
    try:
        await auth.delete_website_account(user.credential.id, body.password.get_secret_value(), body.confirmation)
    except auth.AuthError as error:
        if error.code == 'invalid_credentials': fail('invalid_current_password', 403)
        raise
    response = Response(status_code=204)
    clear_cookies(response)
    return response


@router.get('/bootstrap')
async def bootstrap(lang: schema.Language = 'uk', user: Principal | None = Depends(optional_user)):
    language = user.account.language if user else lang
    catalogs = {key: [{'value': value, 'label': label(options, value, language)} for value in options]
                for key, options in CATALOGS.items() if key != 'topics'}
    catalogs['tags'] = [{'value': value, 'label': label(TOPICS, value, language)} for value in TOPICS]
    menu = [{'id': key, 'label': tr(title, language)} for key, title in (
        ('search', 'search'), ('favorites', 'saved'), ('suggest', 'proposal'),
        ('my_proposals', 'my_proposals'), ('profile', 'profile'), ('settings', 'settings'), ('about', 'about'))]
    if user and db.admin_user(user.account.telegram_id): menu.append({'id': 'moderation', 'label': tr('moderation', language)})
    return {'app': 'Future Now', 'api_version': 'v1', 'language': language,
            'languages': [{'value': 'uk', 'label': 'Українська'}, {'value': 'en', 'label': 'English'}],
            'authenticated': user is not None, 'user': user_out(user.account) if user else None,
            'onboarding_steps': ['profile', 'filters'],
            'menu': menu,
            'fields': {key: label(FIELDS, key, language) for key in FIELDS},
            'profile_age_groups': [entry for entry in catalogs['age'] if entry['value'] != 'any'],
            'catalogs': catalogs, 'about': tr('about_text', language), 'help': tr('help_text', language),
            'password_min_length': 12, 'password_max_length': 128, 'catalog': await catalog_status()}


@router.get('/catalog/status', tags=['Catalog'])
async def source_health(user: Principal = Depends(current_user)):
    return await catalog_status()


@router.get('/me', response_model=schema.UserOut)
async def me(user: Principal = Depends(current_user)):
    return user_out(user.account)


@router.put('/me/profile', response_model=schema.UserOut)
async def profile(body: schema.Profile, user: Principal = Depends(changing_user)):
    _, error = await db.save_profile(user.account.telegram_id, body.model_dump())
    if error: fail(error, 409 if error == 'nickname_taken' else 422)
    return user_out(await db.get_account(user.account.telegram_id))


@router.get('/me/filters', response_model=schema.Filters)
async def filters(user: Principal = Depends(current_user)):
    return effective_filters(user.account)


async def save_filters(account, values):
    account.search_defaults = values
    await db.save_account(account)


@router.put('/me/filters', response_model=schema.Filters)
async def update_filters(body: schema.Filters, user: Principal = Depends(changing_user)):
    await save_filters(user.account, body.model_dump())
    return body


@router.patch('/me/settings', response_model=schema.UserOut)
async def settings(body: schema.Settings, request: Request, user: Principal = Depends(changing_user)):
    account = user.account
    if body.language is not None: account.language = body.language
    if body.notifications is not None:
        prefs = body.notifications.model_dump()
        if prefs['new'] and not account.notifications.get('new'): account.notification_since = db.utcnow()
        account.notifications = prefs
    await db.save_account(account)
    request.state.language = account.language
    return user_out(account)


async def event_flags(account_id):
    if account_id is None: return set(), set()
    async with db.Session() as session:
        saved = set((await session.scalars(select(db.Saved.event_id).where(db.Saved.telegram_id == account_id))).all())
        subscribed = set((await session.scalars(select(db.Subscription.event_id).where(db.Subscription.telegram_id == account_id))).all())
        return saved, subscribed


def event_out(event, language, saved, subscribed):
    kind = db.LEGACY_TYPES.get(event.event_type, event.event_type)
    if kind not in TYPES: kind = 'other'
    topics = event.topics or db.topics_from_subjects(event.subjects or [])
    url = event.url if ui.safe_url(event.url) else None
    status = db.event_status(event)
    return schema.EventOut(id=event.id, title=event.title, description=event.description,
        source=event.source, url=url, registration_url=url if status != 'expired' else None,
        event_type=kind, event_type_label=label(TYPES, kind, language), topics=topics,
        tags=[{'value': key, 'label': label(TOPICS, key, language)} for key in topics],
        country=event.country, country_label=label(COUNTRIES, event.country, language),
        city=event.city, city_label=label(CITIES, event.city, language) if event.city else tr('unknown', language),
        format=event.format, format_label=label(FORMATS, event.format, language) if event.format in FORMATS else tr('unknown', language),
        min_age=event.min_age, max_age=event.max_age, start_at=event.start_at, deadline=event.deadline,
        is_self_paced=event.is_self_paced, verified_at=event.verified_at.replace(tzinfo=timezone.utc) if event.verified_at else None,
        status=status, price={'known': event.price_known, 'is_free': event.is_free if event.price_known else None,
                              'text': event.price_text if event.price_known else tr('unknown', language)},
        criteria=event.criteria or [], organizer=event.organizer or event.source,
        participation_language=event.participation_language, requirements=event.requirements,
        saved=event.id in saved, subscribed=event.id in subscribed)


async def page_events(events, page, page_size, language, account_id=None, applied=None):
    saved, subscribed = await event_flags(account_id)
    return schema.EventPage(items=[event_out(event, language, saved, subscribed) for event in events[(page - 1) * page_size:page * page_size]],
                            total=len(events), page=page, page_size=page_size,
                            pages=max(1, math.ceil(len(events) / page_size)), filters=applied)


@router.post('/opportunities/search', response_model=schema.EventPage)
async def search(body: schema.Search, user: Principal = Depends(changing_user)):
    applied = body.filters or effective_filters(user.account)
    events = await db.search_events(applied.model_dump())
    query = body.query.strip().casefold()
    if query: events = [event for event in events if query in (event.title + ' ' + event.description).casefold()]
    await save_filters(user.account, applied.model_dump())
    return await page_events(events, body.page, body.page_size, user.account.language, user.account.telegram_id, applied)


@router.get('/opportunities/{event_id}', response_model=schema.EventOut)
async def detail(event_id: int, user: Principal = Depends(current_user)):
    event = await db.get_event(event_id)
    if not event: fail('not_found', 404)
    saved, subscribed = await event_flags(user.account.telegram_id)
    return event_out(event, user.account.language, saved, subscribed)


@router.get('/opportunities/{event_id}/registration')
async def registration(event_id: int, user: Principal = Depends(current_user)):
    event = await db.get_event(event_id)
    if not event: fail('not_found', 404)
    if db.event_status(event) == 'expired': fail('opportunity_expired', 409)
    if not ui.safe_url(event.url) or not await check_link(event.url): fail('link_unavailable', 503)
    return {'url': event.url}


@router.get('/me/favorites', response_model=schema.EventPage)
async def favorites(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), user: Principal = Depends(current_user)):
    return await page_events(await db.saved_events(user.account.telegram_id), page, page_size,
                             user.account.language, user.account.telegram_id)


@router.put('/me/favorites/{event_id}')
async def save_favorite(event_id: int, user: Principal = Depends(changing_user)):
    if not await db.get_event(event_id): fail('not_found', 404)
    await db.save_event(user.account.telegram_id, event_id)
    return {'event_id': event_id, 'saved': True}


@router.delete('/me/favorites/{event_id}', status_code=204)
async def remove_favorite(event_id: int, user: Principal = Depends(changing_user)):
    await db.remove_saved(user.account.telegram_id, event_id)
    return Response(status_code=204)


@router.put('/me/subscriptions/{event_id}')
async def subscription(event_id: int, body: schema.Subscription, user: Principal = Depends(changing_user)):
    if not await db.get_event(event_id): fail('not_found', 404)
    if await db.subscribed(user.account.telegram_id, event_id) != body.enabled:
        await db.toggle_subscription(user.account.telegram_id, event_id)
    return {'event_id': event_id, 'subscribed': body.enabled,
            'telegram_delivery_available': user.account.telegram_id > 0,
            'deadline_notifications_enabled': user.account.notifications.get('deadlines', False)}


@router.post('/me/reports', status_code=201)
async def report(body: schema.Report, user: Principal = Depends(changing_user)):
    if body.event_id and not await db.get_event(body.event_id): fail('not_found', 404)
    report_id = await db.add_report(user.account.telegram_id, body.event_id, body.category, body.message)
    return {'id': report_id, 'ok': True}


def proposal_out(row):
    return schema.ProposalOut(id=row.id, revision=row.revision, updated_at=row.updated_at, payload=row.payload, status=row.status, created_at=row.created_at,
                              reviewed_at=row.reviewed_at, review_note=row.review_note, event_id=row.event_id)


@router.post('/me/proposals', response_model=schema.ProposalOut, status_code=201)
async def suggest(body: schema.Proposal, user: Principal = Depends(changing_user)):
    payload = body.model_dump(mode='json')
    payload['source'] = 'Пропозиція користувача / User suggestion'
    event = body.event()
    if db.event_status(db.Event(**event.__dict__)) == 'expired': fail('submission_expired', 422)
    submission_id, error = await db.submit_proposal(user.account.telegram_id, payload)
    if error: fail(error, 429 if error in ('proposal_limit', 'proposal_cooldown') else 409)
    return proposal_out(await db.get_submission(submission_id))


async def proposals_page(account_id, page, page_size):
    rows = await db.list_submissions(account_id)
    return {'items': [proposal_out(row) for row in rows[(page - 1) * page_size:page * page_size]],
            'total': len(rows), 'page': page, 'page_size': page_size, 'pages': max(1, math.ceil(len(rows) / page_size))}


@router.get('/me/proposals')
async def my_proposals(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), user: Principal = Depends(current_user)):
    return await proposals_page(user.account.telegram_id, page, page_size)


@router.get('/me/proposals/{submission_id}', response_model=schema.ProposalOut)
async def my_proposal(submission_id: int, user: Principal = Depends(current_user)):
    row = await db.get_submission(submission_id)
    if not row or row.telegram_id != user.account.telegram_id: fail('not_found', 404)
    return proposal_out(row)


@router.patch('/me/proposals/{submission_id}', response_model=schema.ProposalOut)
async def edit_my_proposal(submission_id: int, body: schema.ProposalEdit, user: Principal = Depends(changing_user)):
    error = await db.change_own_submission(submission_id, user.account.telegram_id, body.expected_revision,
                                           body.values.model_dump(mode='json'))
    if error: fail(error, 404 if error == 'not_found' else 422 if error == 'submission_expired' else 409)
    return proposal_out(await db.get_submission(submission_id))


@router.post('/me/proposals/{submission_id}/withdraw', response_model=schema.ProposalOut)
async def withdraw_my_proposal(submission_id: int, body: schema.Revision, user: Principal = Depends(changing_user)):
    error = await db.change_own_submission(submission_id, user.account.telegram_id, body.expected_revision)
    if error: fail(error, 404 if error == 'not_found' else 409)
    return proposal_out(await db.get_submission(submission_id))


def require_admin(user):
    if not db.admin_user(user.account.telegram_id): fail('admin_required', 403)


@router.get('/admin/proposals', tags=['Moderation'])
async def moderation(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), user: Principal = Depends(current_user)):
    require_admin(user)
    return await proposals_page(None, page, page_size)


@router.patch('/admin/proposals/{submission_id}', response_model=schema.ProposalOut, tags=['Moderation'])
async def edit_proposal(submission_id: int, body: schema.AdminProposal, user: Principal = Depends(changing_user)):
    require_admin(user)
    if not await db.get_submission(submission_id): fail('not_found', 404)
    if not await db.edit_submission(submission_id, user.account.telegram_id, body.model_dump(mode='json', exclude={'expected_revision'}), expected_revision=body.expected_revision):
        fail('edit_conflict', 409)
    return proposal_out(await db.get_submission(submission_id))


@router.post('/admin/proposals/{submission_id}/decision', response_model=schema.ProposalOut, tags=['Moderation'])
async def decision(submission_id: int, body: schema.Decision, user: Principal = Depends(changing_user)):
    require_admin(user)
    row = await db.get_submission(submission_id)
    if not row: fail('not_found', 404)
    if body.decision == 'rejected' and not 5 <= len(body.reason.strip()) <= 500: fail('invalid_request', 422)
    if body.decision == 'approved' and not await check_link(row.payload['url']): fail('moderation_link', 409)
    result = await db.moderate_submission(submission_id, user.account.telegram_id, body.decision, body.reason,
                                           expected_revision=body.expected_revision if body.expected_revision is not None else row.revision)
    if result != 'moderation_done': fail(result, 409)
    return proposal_out(await db.get_submission(submission_id))


from admin_catalog import install as install_administration
install_administration(router,current_user=current_user,changing_user=changing_user,require_admin=require_admin,fail=fail)


def install(app: FastAPI):
    app.include_router(router)
    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(), allow_credentials=True,
                       allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
                       allow_headers=['Content-Type', 'X-CSRF-Token', 'Accept-Language'])

    @app.middleware('http')
    async def website_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith('/api/v1'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Content-Language'] = request_language(request)
        return response

    @app.exception_handler(auth.AuthError)
    async def auth_error(request, exc):
        headers = {'Retry-After': '900'} if exc.status == 429 else None
        return JSONResponse(error_body(exc.code, request_language(request)), status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        if not request.url.path.startswith('/api/v1'): return await request_validation_exception_handler(request, exc)
        body = error_body('invalid_request', request_language(request))
        # Never echo input values: a rejected field can contain a password.
        body['error']['fields'] = [{'location': list(item['loc']), 'type': item['type'], 'message': item['msg']}
                                   for item in exc.errors()]
        return JSONResponse(body, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request, exc):
        if not request.url.path.startswith('/api/v1'): raise exc
        return JSONResponse(error_body('database_unavailable', request_language(request)), status_code=503)
