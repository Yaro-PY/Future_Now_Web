"""Administration regressions use isolated SQLite and a mocked link checker."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import select,func,text
from tests.test_api import APITests,opportunity,ADMIN,PASSWORD
import database as db
import web_auth as auth


class AdministrationTests(APITests):
    async def admin_login(self):
        await db.get_account(ADMIN)
        await db.save_profile(ADMIN,{'nickname':'admin_test','display_name':'Administrator','age':'18+',
            'country':'any','city':'any','format':'any','criteria':[]})
        await auth.set_bot_password_hash(ADMIN,await auth.hash_password(PASSWORD))
        response=await self.client.post('/api/v1/auth/login',json={'nickname':'admin_test','password':PASSWORD})
        self.assertEqual(response.status_code,200,response.text)
        self.csrf=response.json()['csrf_token']

    async def listing(self):
        await db.upsert_events([opportunity(1)])
        return (await self.client.get('/api/v1/admin/opportunities/1')).json()

    async def edit(self,row,**values):
        return await self.request('PATCH',f'/admin/opportunities/{row["id"]}',json={
            'expected_revision':row['revision'],'values':{**row['values'],**values}})

    async def test_admin_routes_require_role_and_csrf(self):
        for path in ('/admin/opportunities','/admin/opportunities/1','/admin/reports','/admin/opportunities/1/history'):
            self.assertEqual((await self.client.get('/api/v1'+path)).status_code,401)
        await self.register()
        for path in ('/admin/opportunities','/admin/opportunities/1','/admin/reports','/admin/opportunities/1/history'):
            self.assertEqual((await self.client.get('/api/v1'+path)).status_code,403)
        self.assertEqual((await self.request('PATCH','/admin/reports/1',json={'expected_revision':1,'status':'in_progress'})).status_code,403)
        await self.admin_login()
        row=await self.listing()
        response=await self.client.patch('/api/v1/admin/opportunities/1',json={'expected_revision':1,'values':row['values']})
        self.assertEqual(response.status_code,403)
        response=await self.client.patch('/api/v1/admin/reports/1',json={'expected_revision':1,'status':'in_progress'})
        self.assertEqual(response.status_code,403)

    async def test_edit_retains_identity_favorites_and_survives_source_refresh(self):
        await self.admin_login(); row=await self.listing(); await db.save_event(ADMIN,row['id'])
        changed=await self.edit(row,title='Administrator corrected title',is_closed=True,topics=['it'])
        self.assertEqual(changed.status_code,200,changed.text)
        self.assertEqual(changed.json()['revision'],2)
        self.assertEqual(changed.json()['status'],'expired')
        await db.upsert_events([opportunity(1,title='Upstream title',description='New upstream description',topics=['business'])])
        event=await db.get_event(row['id'])
        self.assertEqual(event.title,'Administrator corrected title')
        self.assertEqual(event.topics,['it'])
        self.assertEqual(event.description,'New upstream description')
        self.assertTrue(event.is_closed)
        self.assertTrue(await db.is_saved(ADMIN,row['id']))
        self.assertEqual(await db.search_events({}),[])
        history=(await self.client.get('/api/v1/admin/opportunities/1/history')).json()['items']
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['changes']['title']['before'],'Course 1')
        self.assertNotIn('actor_id',history[0])

    async def test_url_edit_keeps_original_source_identity_and_prevents_duplicates(self):
        await self.admin_login(); row=await self.listing()
        with patch('admin_catalog.check_link',AsyncMock(return_value=True)):
            response=await self.edit(row,url='https://example.org/corrected-course')
        self.assertEqual(response.status_code,200,response.text)
        await db.upsert_events([opportunity(3,url='https://example.org/course/1?utm_source=test',external_id='new-source-id')])
        async with db.Session() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(db.Event)),1)
        self.assertEqual((await db.get_event(1)).url,'https://example.org/corrected-course')
        await db.upsert_events([opportunity(2)])
        row=(await self.client.get('/api/v1/admin/opportunities/1')).json()
        with patch('admin_catalog.check_link',AsyncMock(return_value=True)):
            response=await self.edit(row,url='https://example.org/course/2')
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()['error']['code'],'duplicate_url')

    async def test_edits_reject_conflicts_invalid_values_and_unavailable_links(self):
        await self.admin_login(); row=await self.listing()
        self.assertEqual((await self.edit(row,title='Changed title')).status_code,200)
        response=await self.edit(row,title='Stale title')
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()['error']['code'],'edit_conflict')
        row=(await self.client.get('/api/v1/admin/opportunities/1')).json()
        for values in ({'min_age':80,'max_age':20},{'title':'   '},{'url':'http://127.0.0.1/private'},
                       {'event_type':'unknown-key'},{'source':'Forged source'},{'is_free':False,'criteria':['free']}):
            self.assertEqual((await self.edit(row,**values)).status_code,422,values)
        with patch('admin_catalog.check_link',AsyncMock(return_value=False)):
            self.assertEqual((await self.edit(row,url='https://example.org/unavailable')).status_code,409)
        self.assertEqual((await self.client.get('/api/v1/admin/opportunities/999')).status_code,404)

    async def test_source_refresh_conflicts_with_stale_editor_and_preserves_price_pair(self):
        await self.admin_login(); row=await self.listing()
        await db.upsert_events([opportunity(1)])
        self.assertEqual((await self.edit(row,title='Stale editor title')).status_code,409)
        row=(await self.client.get('/api/v1/admin/opportunities/1')).json()
        response=await self.edit(row,is_free=False,price_text='500 грн',min_age=18)
        self.assertEqual(response.status_code,200,response.text)
        await db.upsert_events([opportunity(1,price_known=False,is_free=True,max_age=16)])
        event=await db.get_event(1)
        self.assertFalse(event.is_free); self.assertTrue(event.price_known)
        self.assertEqual(event.price_text,'500 грн')
        self.assertEqual((event.min_age,event.max_age),(18,30))

    async def test_report_lifecycle_notes_conflicts_filters_and_privacy(self):
        await self.admin_login(); await self.listing()
        report_id=await db.add_report(ADMIN,1,'bad_info','Please correct the participation conditions.')
        response=await self.client.get('/api/v1/admin/reports?status=open')
        row=response.json()['items'][0]
        self.assertEqual(row['status'],'new'); self.assertEqual(row['event_title'],'Course 1')
        self.assertTrue(row['created_at'].endswith('Z'))
        self.assertNotIn('telegram_id',row)
        response=await self.request('PATCH',f'/admin/reports/{report_id}',json={'expected_revision':row['revision'],'status':'in_progress'})
        self.assertEqual(response.status_code,200,response.text)
        working=response.json()
        invalid=await self.request('PATCH',f'/admin/reports/{report_id}',json={'expected_revision':working['revision'],'status':'resolved','review_note':' '})
        self.assertEqual(invalid.status_code,422)
        resolved=await self.request('PATCH',f'/admin/reports/{report_id}',json={'expected_revision':working['revision'],'status':'resolved','review_note':'Corrected the listing conditions.'})
        self.assertEqual(resolved.status_code,200,resolved.text)
        self.assertIsNotNone(resolved.json()['resolved_at'])
        self.assertEqual((await self.client.get('/api/v1/admin/reports?status=open')).json()['total'],0)
        self.assertEqual((await self.client.get('/api/v1/admin/reports?status=resolved')).json()['total'],1)
        stale=await self.request('PATCH',f'/admin/reports/{report_id}',json={'expected_revision':working['revision'],'status':'dismissed','review_note':'Stale second decision.'})
        self.assertEqual(stale.status_code,409)
        reopened=await self.request('PATCH',f'/admin/reports/{report_id}',json={'expected_revision':resolved.json()['revision'],'status':'new','review_note':'Needs another review.'})
        self.assertEqual(reopened.status_code,200)
        self.assertIsNone(reopened.json()['resolved_at'])
        self.assertEqual(reopened.json()['created_at'],row['created_at'])
        async with db.Session() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(db.AdminAudit)),3)

    async def test_general_report_pagination_and_noop_review(self):
        await self.admin_login()
        for index in range(3): await db.add_report(ADMIN,None,'other',f'Service feedback {index}')
        response=await self.client.get('/api/v1/admin/reports?page=2&page_size=2')
        data=response.json(); self.assertEqual((data['total'],data['pages'],len(data['items'])),(3,2,1))
        row=data['items'][0]; self.assertIsNone(row['event_title'])
        result=await self.request('PATCH',f'/admin/reports/{row["id"]}',json={'expected_revision':row['revision'],'status':'new'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['revision'],row['revision'])
        self.assertEqual((await self.request('PATCH','/admin/reports/999',json={'expected_revision':1,'status':'new'})).status_code,404)
        self.assertEqual((await self.client.get('/api/v1/admin/reports?status=invalid')).status_code,422)

    async def test_published_search_and_status_pagination(self):
        await self.admin_login()
        await db.upsert_events([opportunity(1),opportunity(2,deadline=db.localnow()-timedelta(days=2)),opportunity(3,is_closed=True)])
        result=(await self.client.get('/api/v1/admin/opportunities?state=expired&page_size=1&page=2')).json()
        self.assertEqual((result['total'],result['pages'],len(result['items'])),(2,2,1))
        self.assertEqual((await self.client.get('/api/v1/admin/opportunities?q=Course%201')).json()['total'],1)
        self.assertEqual((await self.client.get('/api/v1/admin/opportunities?state=available')).json()['total'],1)

    async def test_old_reports_schema_migrates_without_losing_messages(self):
        async with db.engine.begin() as connection:
            await connection.execute(text('DROP TABLE reports'))
            await connection.execute(text('CREATE TABLE reports (id INTEGER PRIMARY KEY, telegram_id BIGINT NOT NULL, event_id INTEGER, category VARCHAR(50) NOT NULL, message TEXT NOT NULL, created_at TIMESTAMP NOT NULL)'))
            await connection.execute(text("INSERT INTO reports VALUES (1,123,NULL,'other','Original message','2026-10-01 12:00:00')"))
        await db.init_db(); await db.init_db()
        async with db.Session() as session:
            row=await session.get(db.Report,1)
            self.assertEqual((row.message,row.status,row.revision),('Original message','new',1))
            self.assertEqual(row.updated_at,row.created_at)


for _name in list(APITests.__dict__):
    if _name.startswith('test_'): setattr(AdministrationTests,_name,None)


def load_tests(loader, tests, pattern): return loader.loadTestsFromTestCase(AdministrationTests)
