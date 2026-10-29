"""Standalone website API tests: no bot checkout or aiogram required."""
import ast
import asyncio
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.update(DATABASE_URL='sqlite+aiosqlite:///:memory:', VERCEL='0', ADMIN_ID='7000000001')
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import database as db
import main
import web_auth as auth

PASSWORD = 'FutureNow-Website-Test-42'
ADMIN = 7000000001


def opportunity(index, **changes):
    values = dict(external_id=f'qa:{index}', title=f'Course {index}', description='Educational opportunity',
        url=f'https://example.org/course/{index}', source='QA', event_type='course', subjects=[],
        min_age=13, max_age=30, start_at=db.localnow() + timedelta(days=20),
        deadline=db.localnow() + timedelta(days=10), is_free=True, price_text='Free', price_known=True,
        format='online', city='kyiv', raw_text='', country='ukraine', topics=['education'], criteria=[])
    values.update(changes)
    return db.EventData(**values)


class APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        db._profile_write_lock = asyncio.Lock()
        db.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        db.Session = async_sessionmaker(db.engine, expire_on_commit=False)
        await db.init_db()
        main.app.state.ready = True
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='https://example.org')
        self.csrf = ''

    async def asyncTearDown(self):
        await self.client.aclose()
        main.app.state.ready = False
        await db.close_db()

    async def register(self, nickname='website_user'):
        response = await self.client.post('/api/v1/auth/register', json={
            'nickname': nickname, 'display_name': 'Website User', 'password': PASSWORD})
        self.assertEqual(response.status_code, 201, response.text)
        self.csrf = response.json()['csrf_token']
        return response

    async def request(self, method, path, **kwargs):
        return await self.client.request(method, '/api/v1' + path, headers={'X-CSRF-Token': self.csrf}, **kwargs)

    async def test_registration_onboarding_language_and_filters(self):
        response = await self.register()
        public_id = response.json()['user']['public_id']
        self.assertTrue(response.json()['user']['onboarding_required'])
        response = await self.request('PUT', '/me/profile', json={
            'nickname': 'new_login', 'display_name': 'Олена', 'age': '16-18',
            'country': 'ukraine', 'city': 'kyiv', 'format': 'online'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()['onboarding_required'])
        self.assertTrue(response.json()['filters_setup_required'])
        self.assertEqual(response.json()['public_id'], public_id)
        self.assertEqual((await self.request('PUT', '/me/filters', json={'country': 'europe'})).status_code, 200)
        response = await self.request('PATCH', '/me/settings', json={'language': 'en'})
        self.assertEqual(response.headers['Content-Language'], 'en')
        result = (await self.client.get('/api/v1/bootstrap')).json()
        self.assertEqual(result['app'], 'Future Now')
        self.assertEqual(result['language'], 'en')
        self.assertFalse(result['user']['filters_setup_required'])
        self.assertNotIn('aiogram', sys.modules)

    async def test_csrf_cookie_protection_and_generic_login_errors(self):
        await self.register()
        response = await self.client.put('/api/v1/me/filters', json={})
        self.assertEqual(response.status_code, 403)
        response = await self.client.put('/api/v1/me/filters', json={}, headers={
            'X-CSRF-Token': self.csrf, 'Origin': 'https://attacker.example'})
        self.assertEqual(response.status_code, 403)
        for cookie in self.client.cookies.jar:
            self.assertTrue(cookie.secure)
            self.assertIn('HttpOnly', cookie._rest)
        response = await self.client.post('/api/v1/auth/login', json={'nickname': 'unknown_user', 'password': PASSWORD})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(PASSWORD, response.text)
        response = await self.client.post('/api/v1/auth/register', json={'nickname': 'another', 'display_name': 'Name', 'password': 'short123'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('short123', response.text)

    async def test_bot_credential_contract_and_password_revocation(self):
        await db.get_account(ADMIN)
        _, error = await db.save_profile(ADMIN, {'nickname': 'bot_user', 'display_name': 'Bot User',
            'age': '16-18', 'country': 'ukraine', 'city': 'kyiv', 'format': 'online', 'criteria': []})
        self.assertIsNone(error)
        await auth.set_bot_password_hash(ADMIN, await auth.hash_password(PASSWORD))
        response = await self.client.post('/api/v1/auth/login', json={'nickname': 'BOT_USER', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        self.csrf = response.json()['csrf_token']
        self.assertTrue(response.json()['user']['telegram_linked'])
        self.assertEqual(response.json()['user']['role'], 'admin')
        self.assertNotIn('telegram_id', response.text)
        response = await self.request('POST', '/auth/password', json={'current_password': PASSWORD, 'new_password': PASSWORD + '-new'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await self.client.get('/api/v1/me')).status_code, 401)

    async def seed_bot_login(self):
        await db.get_account(ADMIN)
        await db.save_profile(ADMIN, {'nickname':'bot_existing','display_name':'Existing User',
            'age':'16-18','country':'ukraine','city':'kyiv','format':'online','criteria':['free']})
        await auth.set_bot_password_hash(ADMIN, await auth.hash_password(PASSWORD))

    async def bot_login(self):
        response = await self.client.post('/api/v1/auth/login',json={'nickname':'bot_existing','password':PASSWORD})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['user']

    async def test_bot_profile_without_search_history_skips_website_onboarding(self):
        await self.seed_bot_login()
        user = await self.bot_login()
        self.assertFalse(user['onboarding_required'])
        self.assertFalse(user['filters_setup_required'])
        self.assertEqual({key:user['filters'][key] for key in ('age','country','city','format','criteria')},
            {'age':'16-18','country':'ukraine','city':'kyiv','format':'online','criteria':['free']})
        self.assertEqual((await db.get_account(ADMIN)).search_defaults,{})
        resumed = (await self.client.get('/api/v1/auth/session')).json()['user']
        self.assertFalse(resumed['onboarding_required'])
        self.assertFalse(resumed['filters_setup_required'])

    async def test_legacy_bot_age_is_normalized_without_profile_rewrite(self):
        await self.seed_bot_login()
        for legacy,expected in ((17,'16-18'),('13-14','13-16'),('15-17','16-18')):
            account = await db.get_account(ADMIN)
            account.profile = {**account.profile,'age':legacy}
            await db.save_account(account)
            user = await self.bot_login()
            self.assertFalse(user['onboarding_required'])
            self.assertFalse(user['filters_setup_required'])
            self.assertEqual(user['profile']['age'],expected)
            self.assertEqual(user['filters']['age'],expected)
            self.assertEqual((await db.get_account(ADMIN)).profile['age'],legacy)

    async def test_incomplete_bot_profile_still_requires_onboarding(self):
        await self.seed_bot_login()
        account = await db.get_account(ADMIN)
        account.profile = {**account.profile,'age':'any'}
        await db.save_account(account)
        user = await self.bot_login()
        self.assertTrue(user['onboarding_required'])
        self.assertTrue(user['filters_setup_required'])

    async def test_search_and_expired_favorites(self):
        await self.register()
        await db.upsert_events([opportunity(1), opportunity(2),
            opportunity(3, deadline=db.localnow() - timedelta(days=1)), opportunity(4, price_known=False)])
        response = await self.request('POST', '/opportunities/search', json={'filters': {'criteria': ['free']}, 'page_size': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total'], 2)
        self.assertEqual(response.json()['pages'], 2)
        self.assertEqual((await self.client.get('/api/v1/me/filters')).json()['criteria'], ['free'])
        async with db.Session() as session:
            ended = await session.scalar(select(db.Event).where(db.Event.external_id == 'qa:3'))
        for _ in range(2):
            self.assertEqual((await self.request('PUT', f'/me/favorites/{ended.id}')).status_code, 200)
        item = (await self.client.get('/api/v1/me/favorites')).json()['items'][0]
        self.assertEqual(item['status'], 'expired')
        self.assertIsNone(item['registration_url'])

    async def test_proposals_are_private_and_require_moderation(self):
        await self.register()
        response = await self.request('POST', '/me/proposals', json={
            'title': 'Educational course', 'description': 'An educational course offered by a verified organizer for students.',
            'url': 'https://example.org/proposal?utm_source=qa', 'event_type': 'course'})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['status'], 'pending')
        self.assertNotIn('utm_', response.json()['payload']['url'])
        self.assertEqual(await db.search_events({}), [])
        self.assertEqual((await self.client.get('/api/v1/admin/proposals')).status_code, 403)
        self.assertEqual((await self.client.get('/api/v1/me/proposals')).json()['total'], 1)
        self.assertEqual(await db.pending_decisions(), [])

    async def test_login_rate_limit_and_missing_schema_health(self):
        for _ in range(10):
            response = await self.client.post('/api/v1/auth/login', json={'nickname': 'unknown', 'password': PASSWORD})
            self.assertEqual(response.status_code, 401)
        response = await self.client.post('/api/v1/auth/login', json={'nickname': 'unknown', 'password': PASSWORD})
        self.assertEqual(response.status_code, 429)
        self.assertEqual((await self.client.get('/health')).status_code, 200)
        async with db.engine.begin() as connection:
            await connection.run_sync(db.AuthThrottle.__table__.drop)
        self.assertEqual((await self.client.get('/health')).status_code, 503)

    async def test_cold_start_does_not_migrate_or_import_telegram(self):
        with patch('main.SERVERLESS', True), patch('main.serverless_configuration_error', return_value=''), \
             patch('database.init_db', AsyncMock()) as initialize:
            async with main.app.router.lifespan_context(main.app):
                self.assertEqual((await self.client.get('/health')).status_code, 200)
                initialize.assert_not_awaited()
                self.assertNotIn('aiogram', sys.modules)
        self.assertEqual((await self.client.get('/api/v1/bootstrap')).status_code, 503)

    async def test_shared_schema_contract_matches_bot(self):
        bot_file = Path(__file__).resolve().parents[2] / 'User-flow-main' / 'User-flow-main' / 'database.py'
        if not bot_file.exists(): self.skipTest('Bot checkout is not present')
        def models(filename):
            tree = ast.parse(filename.read_text(encoding='utf-8-sig'))
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.ClassDef)}
        self.assertEqual(models(Path(db.__file__)), models(bot_file))
