"""MFA is enforced before sessions/linking; media remains private and bounded."""
import io
import os
import time
import unittest
from unittest.mock import patch

import httpx
import pyotp
from cryptography.fernet import Fernet
from PIL import Image
from sqlalchemy import select, func, delete

from tests.test_api import APITests, PASSWORD
import database as db
import web_auth as auth
import two_factor as mfa
import main


class SecurityTests(unittest.IsolatedAsyncioTestCase):
    register = APITests.register
    request = APITests.request

    async def asyncSetUp(self):
        self.key_patch = patch.dict(os.environ, {'AUTH_ENCRYPTION_KEY': Fernet.generate_key().decode()})
        self.key_patch.start()
        await APITests.asyncSetUp(self)

    async def asyncTearDown(self):
        await APITests.asyncTearDown(self)
        self.key_patch.stop()

    async def seed(self, telegram=False):
        if not telegram: await self.register(); return
        await db.get_account(1234)
        await db.save_profile(1234, {'nickname':'bot_security','display_name':'Security User','age':'18+'})
        await auth.set_bot_password_hash(1234, await auth.hash_password(PASSWORD))
        r = await self.client.post('/api/v1/auth/login', json={'nickname':'bot_security','password':PASSWORD})
        self.assertEqual(r.status_code, 200, r.text); self.csrf = r.json()['csrf_token']

    async def authorization(self):
        r = await self.request('POST', '/me/security/authorize', json={'current_password':PASSWORD})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    async def totp(self):
        challenge = await self.authorization()
        r = await self.request('POST', '/me/security/totp/setup', json={
            'challenge_token':challenge['challenge_token'],'method':'none','code':''})
        self.assertEqual(r.status_code, 200, r.text); setup = r.json()
        self.assertTrue(setup['qr_code'].startswith('data:image/png;base64,'))
        code = pyotp.TOTP(setup['secret']).now()
        r = await self.request('POST', '/me/security/totp/enable', json={'setup_token':setup['setup_token'],'code':code})
        self.assertEqual(r.status_code, 200, r.text)
        return setup['secret'], r.json()['recovery_codes']

    async def pending(self, nickname='website_user', password=PASSWORD):
        self.client.cookies.clear()
        r = await self.client.post('/api/v1/auth/login', json={'nickname':nickname,'password':password})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()['two_factor_required'])
        self.assertNotIn('fn_session', self.client.cookies)
        self.assertIn('fn_mfa', self.client.cookies)
        self.assertEqual((await self.client.get('/api/v1/me')).status_code, 401)
        return r.json()

    async def finish(self, challenge, code, method='totp'):
        return await self.client.post('/api/v1/auth/2fa/verify', json={
            'challenge_token':challenge['challenge_token'],'method':method,'code':code})

    async def test_password_minimum_is_eight_everywhere(self):
        r = await self.client.post('/api/v1/auth/register', json={
            'nickname':'eight_user','display_name':'Eight User','password':'Abcd1234'})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((await self.client.get('/api/v1/bootstrap')).json()['password_min_length'], 8)
        r = await self.client.post('/api/v1/auth/register', json={
            'nickname':'short_user','display_name':'Short User','password':'Abcd123'})
        self.assertEqual(r.status_code, 422)
        self.assertNotIn('Abcd123', r.text)

    async def test_private_avatar_is_reencoded_and_survives_profile_edits(self):
        await self.seed(); data = io.BytesIO()
        Image.new('RGB',(800,400),'red').save(data,'JPEG',exif=b'Exif\x00\x00PRIVATE-METADATA')
        r = await self.client.put('/api/v1/me/avatar', content=data.getvalue(), headers={
            'Content-Type':'image/jpeg','X-CSRF-Token':self.csrf})
        self.assertEqual(r.status_code, 200, r.text); url = r.json()['avatar_url']
        photo = await self.client.get(url)
        self.assertEqual(photo.headers['content-type'],'image/webp')
        self.assertIn('no-store',photo.headers['cache-control'])
        self.assertNotIn(b'PRIVATE-METADATA',photo.content)
        image=Image.open(io.BytesIO(photo.content)); self.assertEqual(image.size,(512,512))
        r = await self.request('PUT','/me/profile',json={'nickname':'website_user','display_name':'Updated name','age':'18+'})
        self.assertEqual(r.json()['avatar_url'],url)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app),base_url='https://example.org') as other:
            self.assertEqual((await other.get(url)).status_code,401)
        self.assertEqual((await self.request('DELETE','/me/avatar')).json()['avatar_url'],None)
        self.assertEqual((await self.client.get(url)).status_code,404)

    async def test_avatar_rejects_csrf_svg_fake_and_oversized_uploads(self):
        await self.seed()
        for headers,body,status in [({'Content-Type':'image/png'},b'fake',403),
            ({'Content-Type':'image/svg+xml','X-CSRF-Token':self.csrf},b'<svg onload="alert(1)"/>',415),
            ({'Content-Type':'image/png','X-CSRF-Token':self.csrf},b'not really a PNG',422),
            ({'Content-Type':'image/png','X-CSRF-Token':self.csrf},b'x'*(2*1024*1024+1),413)]:
            self.assertEqual((await self.client.put('/api/v1/me/avatar',headers=headers,content=body)).status_code,status)
        self.assertIsNone((await self.client.get('/api/v1/me')).json()['avatar_url'])

    async def test_totp_enrollment_encrypts_secret_and_requires_a_valid_setup_code(self):
        await self.seed()
        self.assertEqual((await self.request('POST','/me/security/authorize',json={'current_password':'incorrect'})).status_code,403)
        secret,codes = await self.totp(); self.assertEqual(len(codes),8)
        state = (await self.client.get('/api/v1/me/security')).json()
        self.assertTrue(state['totp_enabled']); self.assertEqual(state['recovery_codes_remaining'],8)
        self.assertNotIn(secret,str(state)); self.assertNotIn(codes[0],str(state))
        async with db.Session() as session:
            row=await session.scalar(select(db.TwoFactor))
            self.assertNotEqual(row.totp_secret,secret)
            self.assertEqual(mfa.decrypt(row.totp_secret),secret)
            self.assertNotIn(codes[0],str(row.recovery_hashes))

    async def test_totp_login_creates_session_only_after_code_and_blocks_replay(self):
        await self.seed(); secret,codes=await self.totp()
        verified=await auth.authenticate('website_user',PASSWORD,'qa-direct')
        with self.assertRaises(auth.AuthError): await auth.issue_session(verified)
        challenge=await self.pending()
        future=time.time()+31
        with patch('two_factor.time.time',return_value=future):
            code=pyotp.TOTP(secret).at(future)
            r=await self.finish(challenge,code)
            self.assertEqual(r.status_code,200,r.text)
            self.assertIn('fn_session',self.client.cookies)
            self.assertNotIn('fn_mfa',self.client.cookies)
            self.assertEqual((await self.finish(challenge,code)).status_code,409)
            other=await self.pending()
            r=await self.finish(other,code)
            self.assertEqual(r.status_code,422,r.text)
            self.assertEqual(r.json()['error']['code'],'two_factor_code_used')

    async def test_login_challenge_is_browser_bound_expires_and_locks_after_five_failures(self):
        await self.seed(); secret,codes=await self.totp(); challenge=await self.pending()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app),base_url='https://example.org') as other:
            r=await other.post('/api/v1/auth/2fa/verify',json={'challenge_token':challenge['challenge_token'],'method':'recovery','code':codes[0]})
            self.assertEqual(r.status_code,409)
        for _ in range(5): self.assertEqual((await self.finish(challenge,'INVALID','recovery')).status_code,422)
        self.assertEqual((await self.finish(challenge,codes[0],'recovery')).status_code,409)
        new=await self.pending()
        async with db.Session() as session:
            row=await session.get(db.AuthChallenge,auth.token_hash(new['challenge_token']))
            row.expires_at=db.utcnow();await session.commit()
        self.assertEqual((await self.finish(new,codes[0],'recovery')).status_code,409)

    async def test_recovery_codes_are_single_use(self):
        await self.seed(); secret,codes=await self.totp(); challenge=await self.pending()
        r=await self.finish(challenge,codes[0],'recovery');self.assertEqual(r.status_code,200,r.text)
        self.assertEqual((await self.client.get('/api/v1/me/security')).json()['recovery_codes_remaining'],7)
        challenge=await self.pending()
        self.assertEqual((await self.finish(challenge,codes[0],'recovery')).status_code,422)

    async def test_telegram_enrollment_and_login_require_the_linked_telegram(self):
        await self.seed(telegram=True); authorization=await self.authorization()
        r=await self.request('POST','/me/security/telegram/setup',json={
            'challenge_token':authorization['challenge_token'],'method':'none'})
        self.assertEqual(r.status_code,200,r.text);setup=r.json()
        with self.assertRaises(auth.AuthError): await mfa.telegram_code(setup['challenge_token'],9999)
        code,nickname,purpose=await mfa.telegram_code(setup['challenge_token'],1234)
        self.assertEqual(purpose,'telegram_enroll')
        with self.assertRaises(auth.AuthError): await mfa.telegram_code(setup['challenge_token'],1234)
        r=await self.request('POST','/me/security/telegram/enable',json={
            'challenge_token':setup['challenge_token'],'method':'telegram','code':code})
        self.assertEqual(r.status_code,200,r.text)
        challenge=await self.pending('bot_security')
        code,_,_=await mfa.telegram_code(challenge['challenge_token'],1234)
        r=await self.finish(challenge,code,'telegram');self.assertEqual(r.status_code,200,r.text)

    async def test_unlinked_account_cannot_enable_telegram_or_link_without_totp(self):
        await self.seed(); authorization=await self.authorization()
        r=await self.request('POST','/me/security/telegram/setup',json={'challenge_token':authorization['challenge_token'],'method':'none'})
        self.assertEqual(r.status_code,409)
        secret,codes=await self.totp(); verified=await auth.authenticate('website_user',PASSWORD,'qa-link')
        await db.get_account(1234)
        with self.assertRaises(auth.AuthError): await auth.attach_website_account(verified,1234)
        proof=await mfa.verify_bot_link(verified,codes[0])
        linked=await auth.attach_website_account(verified,1234,factor_proof=proof)
        self.assertEqual(linked.telegram_id,1234)
        self.assertTrue((await mfa.status(verified.id,1234))['totp_enabled'])

    async def test_disabling_mfa_requires_existing_factor_and_revokes_other_sessions(self):
        await self.seed(); secret,codes=await self.totp(); authorization=await self.authorization()
        r=await self.request('POST','/me/security/totp/disable',json={'challenge_token':authorization['challenge_token'],'method':'none'})
        self.assertEqual(r.status_code,422)
        r=await self.request('POST','/me/security/totp/disable',json={'challenge_token':authorization['challenge_token'],'method':'recovery','code':codes[0]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertFalse((await self.client.get('/api/v1/me/security')).json()['totp_enabled'])
        self.client.cookies.clear()
        self.assertIn('user',(await self.client.post('/api/v1/auth/login',json={'nickname':'website_user','password':PASSWORD})).json())

    async def test_bot_password_reset_preserves_mfa_and_invalidates_pending_login(self):
        await self.seed(telegram=True);secret,codes=await self.totp();challenge=await self.pending('bot_security')
        await auth.set_bot_password_hash(1234,await auth.hash_password('Newpass8'))
        self.assertEqual((await self.finish(challenge,codes[0],'recovery')).status_code,409)
        new=await self.pending('bot_security','Newpass8')
        self.assertIn('totp',new['methods'])

    async def test_deletion_removes_encrypted_secrets_challenges_and_avatars(self):
        await self.seed();secret,codes=await self.totp()
        data=io.BytesIO();Image.new('RGB',(20,20),'blue').save(data,'PNG')
        await self.client.put('/api/v1/me/avatar',content=data.getvalue(),headers={'Content-Type':'image/png','X-CSRF-Token':self.csrf})
        self.assertEqual((await self.request('DELETE','/me',json={'password':PASSWORD,'confirmation':'website_user'})).status_code,204)
        async with db.Session() as session:
            for model in (db.TwoFactor,db.AuthChallenge,db.Avatar,db.Credential):
                self.assertEqual(await session.scalar(select(func.count()).select_from(model)),0)

    async def test_missing_or_wrong_encryption_key_fails_closed(self):
        await self.seed();secret,codes=await self.totp();challenge=await self.pending()
        with patch.dict(os.environ,{'AUTH_ENCRYPTION_KEY':Fernet.generate_key().decode()}):
            r=await self.finish(challenge,pyotp.TOTP(secret).now())
            self.assertEqual(r.status_code,503)
        with patch.dict(os.environ,{'AUTH_ENCRYPTION_KEY':''}):
            self.client.cookies.clear()
            r=await self.client.post('/api/v1/auth/login',json={'nickname':'website_user','password':PASSWORD})
            self.assertEqual(r.status_code,503)


    async def test_incomplete_totp_enrollment_is_not_active_and_is_session_bound(self):
        await self.seed();authorization=await self.authorization()
        setup=(await self.request('POST','/me/security/totp/setup',json={'challenge_token':authorization['challenge_token'],'method':'none'})).json()
        r=await self.request('POST','/me/security/totp/enable',json={'setup_token':setup['setup_token'],'code':'ABCDEF'})
        self.assertEqual(r.status_code,422)
        self.assertFalse((await self.client.get('/api/v1/me/security')).json()['totp_enabled'])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app),base_url='https://example.org') as other:
            login=await other.post('/api/v1/auth/login',json={'nickname':'website_user','password':PASSWORD})
            csrf=login.json()['csrf_token']
            r=await other.post('/api/v1/me/security/totp/enable',headers={'X-CSRF-Token':csrf},json={'setup_token':setup['setup_token'],'code':pyotp.TOTP(setup['secret']).now()})
            self.assertEqual(r.status_code,409)

    async def test_enabling_factor_revokes_preexisting_other_browser_sessions(self):
        await self.seed()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app),base_url='https://example.org') as other:
            self.assertEqual((await other.post('/api/v1/auth/login',json={'nickname':'website_user','password':PASSWORD})).status_code,200)
            await self.totp()
            self.assertEqual((await other.get('/api/v1/me')).status_code,401)
            self.assertEqual((await self.client.get('/api/v1/me')).status_code,200)

    async def test_both_methods_can_be_enabled_and_telegram_can_confirm_security_changes(self):
        await self.seed(telegram=True);secret,codes=await self.totp();authorization=await self.authorization()
        r=await self.request('POST','/me/security/telegram/setup',json={'challenge_token':authorization['challenge_token'],'method':'recovery','code':codes[0]})
        self.assertEqual(r.status_code,200,r.text);setup=r.json()
        code,_,_=await mfa.telegram_code(setup['challenge_token'],1234)
        r=await self.request('POST','/me/security/telegram/enable',json={'challenge_token':setup['challenge_token'],'method':'telegram','code':code})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['recovery_codes'],[])
        state=(await self.client.get('/api/v1/me/security')).json()
        self.assertTrue(state['totp_enabled'] and state['telegram_enabled'])
        authorization=await self.authorization();code,_,_=await mfa.telegram_code(authorization['challenge_token'],1234)
        r=await self.request('POST','/me/security/totp/disable',json={'challenge_token':authorization['challenge_token'],'method':'telegram','code':code})
        self.assertEqual(r.status_code,200,r.text)
        state=(await self.client.get('/api/v1/me/security')).json()
        self.assertFalse(state['totp_enabled']);self.assertTrue(state['telegram_enabled'])

    async def test_avatar_transfers_when_linking_the_website_account(self):
        await self.seed();data=io.BytesIO();Image.new('RGB',(40,30),'green').save(data,'PNG')
        r=await self.client.put('/api/v1/me/avatar',content=data.getvalue(),headers={'Content-Type':'image/png','X-CSRF-Token':self.csrf})
        self.assertEqual(r.status_code,200)
        verified=await auth.authenticate('website_user',PASSWORD,'avatar-transfer')
        old_id=verified.account_id;await db.get_account(1234)
        await auth.attach_website_account(verified,1234)
        async with db.Session() as session:
            self.assertIsNone(await session.get(db.Avatar,old_id))
            self.assertIsNotNone(await session.get(db.Avatar,1234))
        user=(await self.client.get('/api/v1/me')).json()
        self.assertTrue(user['telegram_linked']);self.assertIsNotNone(user['avatar_url'])
        self.assertEqual((await self.client.get(user['avatar_url'])).status_code,200)

    async def test_non_ascii_one_time_codes_are_rejected_without_server_errors(self):
        await self.seed();secret,codes=await self.totp();challenge=await self.pending()
        r=await self.finish(challenge,'١٢٣٤٥٦')
        self.assertEqual(r.status_code,422,r.text)
        import json
        for values in ({'challenge_token':challenge['challenge_token'],'method':'recovery','code':'\ud800'*10},
                       {'challenge_token':'A'*42+'\ud800','method':'recovery','code':codes[0]}):
            response=await self.client.post('/api/v1/auth/2fa/verify',content=json.dumps(values,ensure_ascii=True).encode(),headers={'Content-Type':'application/json'})
            self.assertEqual(response.status_code,422,response.text)



def load_tests(loader,tests,pattern):
    return loader.loadTestsFromTestCase(SecurityTests)
