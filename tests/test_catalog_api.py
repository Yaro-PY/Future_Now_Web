from datetime import datetime, timedelta
from tests.test_api import APITests, opportunity
import database as db


class CatalogAPITests(APITests):
    async def test_source_status_authentication_and_public_bootstrap_summary(self):
        self.assertEqual((await self.client.get('/api/v1/catalog/status')).status_code,401)
        self.assertEqual((await self.client.get('/api/v1/bootstrap')).json()['catalog']['status'],'never')
        await self.register()
        now = db.utcnow()
        async with db.Session() as session:
            session.add(db.CatalogSource(key='prometheus',name='Prometheus',url='https://prometheus.org.ua/',
                last_attempt_at=now,last_success_at=now,status='ok',fetched=4,error_code=''))
            await session.commit()
        result = await self.client.get('/api/v1/catalog/status')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['status'],'ok')
        self.assertTrue(result.json()['last_checked_at'].endswith('Z'))
        self.assertEqual(result.json()['sources'][0]['count'],4)
        self.assertNotIn('error_code',result.json()['sources'][0])

    async def test_self_paced_course_and_provenance_are_available_in_the_api(self):
        await self.register()
        await db.upsert_events([opportunity(1,start_at=datetime(2018,1,1),deadline=None,is_self_paced=True,verified_at=db.utcnow())])
        result = await self.request('POST','/opportunities/search',json={'filters':{'type':'course'}})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['total'],1)
        item = result.json()['items'][0]
        self.assertEqual(item['status'],'self_paced')
        self.assertTrue(item['is_self_paced'])
        self.assertTrue(item['verified_at'].endswith('Z'))
        self.assertIsNotNone(item['registration_url'])

    async def test_explicit_deadline_expires_a_self_paced_saved_course(self):
        await self.register()
        await db.upsert_events([opportunity(1,is_self_paced=True,deadline=db.localnow()-timedelta(days=1))])
        async with db.Session() as session:
            event = await session.get(db.Event,1)
        self.assertEqual((await self.request('PUT','/me/favorites/'+str(event.id))).status_code,200)
        self.assertEqual((await self.request('POST','/opportunities/search',json={})).json()['total'],0)
        item = (await self.client.get('/api/v1/me/favorites')).json()['items'][0]
        self.assertEqual(item['status'],'expired')
        self.assertIsNone(item['registration_url'])


for _name in list(APITests.__dict__):
    if _name.startswith('test_'): setattr(CatalogAPITests,_name,None)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(CatalogAPITests)
