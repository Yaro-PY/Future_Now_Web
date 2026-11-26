"""Public listing visibility, stable deep links, metadata and private-action boundaries."""
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from unittest.mock import AsyncMock,patch

from backend import database as db
from tests.test_api import APITests,opportunity
from backend.opportunity_cover_assignments import OPPORTUNITY_COVER_NAMES
from backend.opportunity_pages import opportunity_path


class PublicOpportunityTests(APITests):
    async def seed(self):
        await db.upsert_events([
            opportunity(1,title='Python з нуля: основи',description='Програма для початківців. Практика та основи Python.'),
            opportunity(2,title='Завершений курс',deadline=db.localnow()-timedelta(days=2)),
        ])

    async def test_guest_detail_and_expired_page_are_public_without_account_data(self):
        await self.seed()
        response=await self.client.get('/api/v1/opportunities/1',headers={'Accept-Language':'en'})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(data['page_url'],'/opportunities/1/python-z-nulya-osnovy')
        self.assertEqual(data['event_type_label'],'Courses')
        self.assertFalse(data['saved']);self.assertFalse(data['subscribed'])
        self.assertNotIn('telegram_id',data);self.assertNotIn('nickname',data)
        self.assertEqual(response.headers['cache-control'],'no-store')
        expired=(await self.client.get('/api/v1/opportunities/2')).json()
        self.assertEqual(expired['status'],'expired')
        self.assertIsNone(expired['registration_url'])
        self.assertEqual((await self.client.get(expired['page_url'])).status_code,200)

    async def test_private_actions_still_require_session_and_csrf(self):
        await self.seed()
        for method,path,values in [('PUT','/me/favorites/1',{}),('PUT','/me/subscriptions/1',{'enabled':True}),
            ('POST','/me/reports',{'event_id':1,'category':'other','message':'A test report'})]:
            self.assertEqual((await self.request(method,path,json=values)).status_code,401)
        await self.register()
        self.assertEqual((await self.client.put('/api/v1/me/favorites/1')).status_code,403)
        await self.request('PUT','/me/favorites/1')
        self.assertTrue((await self.client.get('/api/v1/opportunities/1')).json()['saved'])
        await self.client.post('/api/v1/auth/logout',headers={'X-CSRF-Token':self.csrf})
        self.assertFalse((await self.client.get('/api/v1/opportunities/1')).json()['saved'])

    async def test_direct_pages_have_metadata_and_keep_application_headers(self):
        await self.seed()
        page=await self.client.get('/opportunities/1/python-z-nulya-osnovy')
        self.assertEqual(page.status_code,200,page.text)
        self.assertIn('<title>Python з нуля: основи — Future Now</title>',page.text)
        self.assertIn('property="og:title"',page.text)
        self.assertIn('https://example.org/opportunities/1/python-z-nulya-osnovy',page.text)
        detail = (await self.client.get('/api/v1/opportunities/1')).json()
        other = (await self.client.get('/api/v1/opportunities/2')).json()
        first_asset = detail['default_cover_url']
        second_asset = other['default_cover_url']
        self.assertTrue(first_asset.startswith('/assets/images/courses/code-'))
        self.assertTrue(second_asset.startswith('/assets/images/courses/study-'))
        for asset in (first_asset, second_asset):
            image = await self.client.get(asset)
            self.assertEqual(image.status_code, 200, asset)
            self.assertEqual(image.headers['content-type'], 'image/jpeg')
        self.assertIn(f'property="og:image" content="https://example.org{first_asset}"', page.text)
        self.assertIn('frame-ancestors',page.headers['content-security-policy'])
        self.assertIn('/assets/react/bundles/',page.text)
        self.assertEqual(page.headers['cache-control'],'no-cache')

    async def test_individual_opportunity_covers_are_unique_and_follow_listing_identity(self):
        self.assertTrue(OPPORTUNITY_COVER_NAMES)
        folder = Path(__file__).resolve().parents[1] / 'static' / 'images'
        hashes = {sha256((folder / f'{asset}.jpg').read_bytes()).digest()
                  for asset in OPPORTUNITY_COVER_NAMES.values()}
        self.assertEqual(len(hashes), len(OPPORTUNITY_COVER_NAMES))

        identity, asset = next((key, asset) for key, asset in OPPORTUNITY_COVER_NAMES.items()
                               if asset.startswith('opportunities/'))
        event = opportunity(1, external_id=identity, event_type='contest')
        await db.upsert_events([event])
        cover = f'/assets/images/{asset}.jpg'
        for title in ('Course before source refresh', 'New course title from source'):
            event.title = title
            await db.upsert_events([event])
            listing = (await self.client.get('/api/v1/opportunities/1')).json()
            self.assertEqual(listing['default_cover_url'], cover)
            page = await self.client.get(listing['page_url'])
            self.assertIn(f'property="og:image" content="https://example.org{cover}"', page.text)

    async def test_old_slugs_resolve_by_id_after_title_change(self):
        await self.seed()
        for path in ('/opportunities/1','/opportunities/1/old-course-name'):
            response=await self.client.get(path)
            self.assertEqual(response.status_code,308)
            self.assertEqual(response.headers['location'],'/opportunities/1/python-z-nulya-osnovy')
        await db.upsert_events([opportunity(1,title='Python: оновлена назва')])
        response=await self.client.get('/opportunities/1/python-z-nulya-osnovy')
        self.assertEqual(response.status_code,308)
        self.assertEqual(response.headers['location'],'/opportunities/1/python-onovlena-nazva')

    async def test_missing_pages_are_404_and_api_and_assets_are_not_rewritten(self):
        await self.seed()
        for path in ('/opportunities/999/missing','/api/v1/opportunities/999','/opportunities/not-an-id','/opportunities/999999999999999999999/large','/api/v1/opportunities/999999999999999999999',
            '/api/v1/not-a-route','/assets/%2e%2e/database.py'):
            self.assertEqual((await self.client.get(path)).status_code,404,path)
        missing=await self.client.get('/opportunities/999/missing')
        self.assertIn('text/html',missing.headers['content-type'])
        self.assertEqual(missing.headers['x-robots-tag'],'noindex')

    async def test_metadata_escapes_untrusted_listing_text(self):
        await db.upsert_events([opportunity(1,title='"><script>alert(1)</script>',description='"><img src=x onerror=alert(1)>')])
        event=await db.get_event(1)
        response=await self.client.get(opportunity_path(event))
        self.assertEqual(response.status_code,200)
        self.assertNotIn('<script>alert(1)</script>',response.text)
        self.assertNotIn('<img src=x',response.text)
        self.assertIn('&lt;script&gt;',response.text)
        self.assertIn('&lt;img',response.text)

    async def test_public_registration_checks_closed_status_and_source_link(self):
        await self.seed()
        with patch('backend.web_api.check_link',new=AsyncMock(return_value=True)):
            response=await self.client.get('/api/v1/opportunities/1/registration')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['url'],'https://example.org/course/1')
            self.assertEqual((await self.client.get('/api/v1/opportunities/2/registration')).status_code,409)
        with patch('backend.web_api.check_link',new=AsyncMock(return_value=False)):
            self.assertEqual((await self.client.get('/api/v1/opportunities/1/registration')).status_code,503)

    async def test_public_pages_fail_closed_when_service_is_not_ready(self):
        import main
        main.app.state.ready=False
        self.assertEqual((await self.client.get('/opportunities/1/python')).status_code,503)


for name in list(APITests.__dict__):
    if name.startswith('test_'):setattr(PublicOpportunityTests,name,None)

def load_tests(loader,tests,pattern):return loader.loadTestsFromTestCase(PublicOpportunityTests)
