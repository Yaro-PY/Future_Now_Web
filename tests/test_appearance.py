from tests.test_api import APITests
import database as db

class AppearanceTests(APITests):
    async def test_defaults_and_all_colors_survive_session_resume(self):
        await self.register()
        self.assertEqual((await self.client.get('/api/v1/me')).json()['appearance'],{'accent':'blue','spider_enabled':True})
        for color in ['lemon','orange','red','green','blue']:
            response=await self.request('PATCH','/me/settings',json={'appearance':{'accent':color,'spider_enabled':False}})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['appearance'],{'accent':color,'spider_enabled':False})
            resumed=(await self.client.get('/api/v1/auth/session')).json()
            self.assertEqual(resumed['user']['appearance'],response.json()['appearance'])

    async def test_notifications_profile_and_partial_changes_preserve_appearance(self):
        await self.register()
        await self.request('PATCH','/me/settings',json={'appearance':{'accent':'green','spider_enabled':False}})
        result=await self.request('PATCH','/me/settings',json={'notifications':{'new':True,'deadlines':True,'expired':False},'language':'en'})
        self.assertEqual(result.status_code,200,result.text)
        result=await self.request('PUT','/me/profile',json={'nickname':'website_user','display_name':'User Name','age':'14-17','country':'any','city':'any','format':'any','criteria':[]})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['appearance'],{'accent':'green','spider_enabled':False})
        result=await self.request('PATCH','/me/settings',json={'appearance':{'spider_enabled':True}})
        self.assertEqual(result.json()['appearance'],{'accent':'green','spider_enabled':True})
        self.assertEqual(result.json()['notifications'],{'new':True,'deadlines':True,'expired':False})

    async def test_settings_require_auth_csrf_and_validate_color(self):
        self.assertEqual((await self.request('PATCH','/me/settings',json={'appearance':{'accent':'red'}})).status_code,401)
        await self.register()
        self.assertEqual((await self.client.patch('/api/v1/me/settings',json={'appearance':{'accent':'red'}})).status_code,403)
        for values in ({'accent':'purple'},{'accent':'red','unknown':True}):
            self.assertEqual((await self.request('PATCH','/me/settings',json={'appearance':values})).status_code,422)

    async def test_user_preferences_are_isolated(self):
        await self.register()
        await self.request('PATCH','/me/settings',json={'appearance':{'accent':'lemon','spider_enabled':False}})
        await self.register('second_user')
        self.assertEqual((await self.client.get('/api/v1/me')).json()['appearance'],{'accent':'blue','spider_enabled':True})

for name in list(APITests.__dict__):
    if name.startswith('test_'):setattr(AppearanceTests,name,None)
def load_tests(loader,tests,pattern):return loader.loadTestsFromTestCase(AppearanceTests)
