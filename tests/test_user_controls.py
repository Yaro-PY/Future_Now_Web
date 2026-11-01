"""Author ownership, review races, reauthentication and shared-account erasure."""
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import select, func, text
from tests.test_api import APITests, PASSWORD, ADMIN, opportunity
import database as db
import web_auth as auth


def proposal(url='https://example.org/author-proposal'):
    return {'title':'A useful educational opportunity', 'description':'A detailed description for a valid educational opportunity submitted for review.',
            'url':url,'event_type':'course','country':'ukraine','city':'kyiv','format':'online',
            'is_free':True,'criteria':['free'], 'deadline':(db.localnow()+timedelta(days=20)).isoformat()}


class UserControlsTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = APITests.asyncSetUp
    asyncTearDown = APITests.asyncTearDown
    register = APITests.register
    request = APITests.request

    async def create(self, url='https://example.org/author-proposal'):
        response=await self.request('POST','/me/proposals',json=proposal(url))
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    async def test_author_can_edit_and_withdraw_but_not_publish(self):
        await self.register(); row=await self.create()
        response=await self.request('PATCH',f"/me/proposals/{row['id']}",json={'expected_revision':1,
            'values':{**row['payload'],'title':'Corrected course title','url':'https://example.org/updated-url?utm_source=test','source':'forged'}})
        self.assertEqual(response.status_code,200,response.text)
        changed=response.json(); self.assertEqual(changed['revision'],2)
        self.assertEqual(changed['status'],'pending')
        self.assertEqual(changed['created_at'],row['created_at'])
        self.assertEqual(changed['payload']['url'],'https://example.org/updated-url')
        self.assertNotEqual(changed['payload']['source'],'forged')
        self.assertEqual(await db.search_events({}),[])
        response=await self.request('POST',f"/me/proposals/{row['id']}/withdraw",json={'expected_revision':2})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'withdrawn')
        self.assertEqual(response.json()['revision'],3)
        self.assertEqual(await db.list_submissions(),[])
        self.assertEqual(await db.moderate_submission(row['id'],ADMIN,'approved'),'moderation_changed')
        self.assertEqual((await self.request('PATCH',f"/me/proposals/{row['id']}",json={'expected_revision':3,'values':row['payload']})).status_code,409)
        history=(await self.client.get('/api/v1/me/proposals')).json()['items']
        self.assertEqual(history[0]['status'],'withdrawn')
        # Withdrawal cannot reset creation time or bypass the global duplicate check.
        response=await self.request('POST','/me/proposals',json=proposal('https://example.org/updated-url'))
        self.assertEqual(response.status_code,409)

    async def test_other_users_cannot_read_edit_or_withdraw_a_proposal(self):
        await self.register(); row=await self.create()
        await self.register('another_user')
        path=f"/me/proposals/{row['id']}"
        self.assertEqual((await self.client.get('/api/v1'+path)).status_code,404)
        for method,suffix,body in [('PATCH','',{'expected_revision':1,'values':row['payload']}),('POST','/withdraw',{'expected_revision':1})]:
            response=await self.request(method,path+suffix,json=body)
            self.assertEqual(response.status_code,404,response.text)
        self.assertEqual((await db.get_submission(row['id'])).revision,1)

    async def test_csrf_validation_duplicates_and_stale_edits(self):
        await self.register(); row=await self.create(); path=f"/me/proposals/{row['id']}"
        self.assertEqual((await self.client.patch('/api/v1'+path,json={'expected_revision':1,'values':row['payload']})).status_code,403)
        self.assertEqual((await self.client.post('/api/v1'+path+'/withdraw',json={'expected_revision':1})).status_code,403)
        await db.upsert_events([opportunity(1)])
        for values in ({'url':'https://example.org/course/1'}, {'url':'http://127.0.0.1/private'},
                       {'deadline':'2000-01-01T00:00:00'}, {'title':'short'}):
            response=await self.request('PATCH',path,json={'expected_revision':1,'values':{**row['payload'],**values}})
            self.assertIn(response.status_code,(409,422),response.text)
        self.assertEqual((await self.request('PATCH',path,json={'expected_revision':1,'values':row['payload']})).status_code,200)
        for method,suffix,body in [('PATCH','',{'expected_revision':1,'values':row['payload']}),('POST','/withdraw',{'expected_revision':1})]:
            response=await self.request(method,path+suffix,json=body)
            self.assertEqual(response.status_code,409)
            self.assertEqual(response.json()['error']['code'],'edit_conflict')

    async def test_moderator_snapshot_cannot_approve_changed_or_withdrawn_proposal(self):
        await self.register(); row=await self.create()
        async with db.Session() as session:
            account=await session.scalar(select(db.Account))
            owner=account.telegram_id
        self.assertIsNone(await db.change_own_submission(row['id'],owner,1,{**row['payload'],'title':'Changed after admin opened it'}))
        self.assertEqual(await db.moderate_submission(row['id'],ADMIN,'approved',expected_revision=1),'edit_conflict')
        self.assertEqual(await db.search_events({}),[])
        self.assertEqual(await db.moderate_submission(row['id'],ADMIN,'approved',expected_revision=2),'moderation_done')
        self.assertEqual(len(await db.search_events({})),1)
        self.assertEqual(await db.change_own_submission(row['id'],owner,3),'proposal_not_pending')

    async def test_author_change_during_admin_link_check_cancels_approval(self):
        await self.register(); row=await self.create()
        async with db.Session() as session: owner=(await session.scalar(select(db.Account))).telegram_id
        await db.get_account(ADMIN)
        await db.save_profile(ADMIN,{'nickname':'admin_controls','display_name':'Admin','age':'18+'})
        await auth.set_bot_password_hash(ADMIN,await auth.hash_password(PASSWORD))
        login=await self.client.post('/api/v1/auth/login',json={'nickname':'admin_controls','password':PASSWORD})
        self.csrf=login.json()['csrf_token']
        async def racing_check(url):
            self.assertIsNone(await db.change_own_submission(row['id'],owner,1))
            return True
        with patch('web_api.check_link',racing_check):
            response=await self.request('POST',f"/admin/proposals/{row['id']}/decision",json={'decision':'approved','expected_revision':1})
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(await db.search_events({}),[])
        self.assertEqual((await db.get_submission(row['id'])).status,'withdrawn')

    async def test_deletion_requires_password_exact_nickname_and_csrf(self):
        await self.register()
        body={'password':PASSWORD,'confirmation':'website_user'}
        self.assertEqual((await self.client.request('DELETE','/api/v1/me',json=body)).status_code,403)
        response=await self.request('DELETE','/me',json={**body,'password':'wrong-password'})
        self.assertEqual(response.status_code,403,response.text)
        self.assertEqual((await self.client.get('/api/v1/me')).status_code,200)
        self.assertEqual((await self.request('DELETE','/me',json={**body,'confirmation':'someone_else'})).status_code,422)
        self.assertEqual((await self.request('DELETE','/me',json=body)).status_code,204)
        self.assertEqual((await self.client.get('/api/v1/auth/session')).status_code,401)
        response=await self.client.post('/api/v1/auth/login',json={'nickname':'website_user','password':PASSWORD})
        self.assertEqual(response.status_code,401)
        self.assertEqual((await self.register()).status_code,201)

    async def test_erasure_revokes_every_session_removes_private_data_and_preserves_catalog(self):
        await db.get_account(ADMIN)
        await db.save_profile(ADMIN,{'nickname':'bot_delete','display_name':'Delete User','age':'18+'})
        await auth.set_bot_password_hash(ADMIN,await auth.hash_password(PASSWORD))
        response=await self.client.post('/api/v1/auth/login',json={'nickname':'bot_delete','password':PASSWORD})
        self.csrf=response.json()['csrf_token']
        other=httpx.AsyncClient(transport=httpx.ASGITransport(app=__import__('main').app),base_url='https://example.org')
        try:
            await other.post('/api/v1/auth/login',json={'nickname':'bot_delete','password':PASSWORD})
            await db.upsert_events([opportunity(1)])
            await db.save_event(ADMIN,1); await db.toggle_subscription(ADMIN,1)
            await db.add_report(ADMIN,1,'other','Personal report message')
            row=await self.create()
            self.assertEqual(await db.moderate_submission(row['id'],ADMIN,'approved'),'moderation_done')
            await db.get_account(42)
            async with db.Session() as session:
                session.add(db.User(telegram_id=ADMIN,age=18))
                session.add(db.Receipt(telegram_id=ADMIN,key='test-notification'))
                session.add(db.Submission(telegram_id=42,fingerprint='other',payload=proposal('https://example.org/other'),status='rejected',reviewed_by=ADMIN))
                session.add(db.AdminAudit(entity='event',entity_id=1,actor_id=ADMIN,changes={'title':{'before':'Before','after':'After'}}))
                await session.commit()
            self.assertEqual((await self.request('DELETE','/me',json={'password':PASSWORD,'confirmation':'bot_delete'})).status_code,204)
            self.assertEqual((await other.get('/api/v1/me')).status_code,401)
            async with db.Session() as session:
                for model in (db.Account,db.User,db.Saved,db.Subscription,db.Receipt,db.Report,db.Submission):
                    self.assertEqual(await session.scalar(select(func.count()).select_from(model).where(model.telegram_id==ADMIN)),0,model.__name__)
                self.assertEqual(await session.scalar(select(func.count()).select_from(db.Credential)),0)
                self.assertEqual(await session.scalar(select(func.count()).select_from(db.WebSession)),0)
                self.assertEqual((await session.scalar(select(db.AdminAudit))).actor_id,0)
                self.assertIsNone((await session.scalar(select(db.Submission))).reviewed_by)
                self.assertEqual(await session.scalar(select(func.count()).select_from(db.Event)),2)
            fresh=await db.get_account(ADMIN)
            self.assertIsNone(fresh.profile)
        finally: await other.aclose()

    async def test_submission_migration_is_additive_and_repeatable(self):
        async with db.engine.begin() as conn:
            await conn.execute(text('ALTER TABLE submissions DROP COLUMN revision'))
            await conn.execute(text('ALTER TABLE submissions DROP COLUMN updated_at'))
            await conn.execute(text("INSERT INTO submissions (telegram_id,fingerprint,payload,status,created_at,review_note) VALUES (42,'old','{}','pending','2025-01-02','')"))
        await db.init_db(); await db.init_db()
        row=await db.get_submission(1)
        self.assertEqual(row.revision,1)
        self.assertEqual(row.updated_at,row.created_at)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(UserControlsTests)
