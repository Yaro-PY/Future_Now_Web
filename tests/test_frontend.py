"""Verify the delivered frontend is served by the same standalone API."""
import re

from tests.test_api import APITests


class FrontendTests(APITests):
    async def test_home_and_assets_work_before_authentication(self):
        response = await self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.headers['content-type'])
        self.assertIn('Future Now', response.text)
        bundles = re.findall(r'(?:src|href)="(/assets/react/bundles/[^\"]+\.(?:js|css))"', response.text)
        self.assertTrue(any(path.endswith('.js') for path in bundles))
        self.assertTrue(any(path.endswith('.css') for path in bundles))
        self.assertIn('frame-ancestors', response.headers['content-security-policy'])
        assets = [(path, 'javascript' if path.endswith('.js') else 'text/css') for path in bundles]
        assets += [('/assets/images/earthrise.jpg', 'image/jpeg'), ('/favicon.ico', 'image/svg+xml')]
        for path, content_type in assets:
            result = await self.client.get(path)
            self.assertEqual(result.status_code, 200, path)
            self.assertIn(content_type, result.headers['content-type'])

    async def test_frontend_does_not_replace_api_or_allow_path_traversal(self):
        self.assertEqual((await self.client.get('/api/v1/me')).status_code, 401)
        self.assertEqual((await self.client.get('/assets/%2e%2e/database.py')).status_code, 404)
        response = await self.client.get('/openapi.json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('/api/v1/auth/login', response.json()['paths'])


for _name in list(APITests.__dict__):
    if _name.startswith('test_'): setattr(FrontendTests, _name, None)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(FrontendTests)
