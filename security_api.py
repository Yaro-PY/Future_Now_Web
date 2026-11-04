"""Website profile media and MFA routes. The bot uses the same underlying services."""
from typing import Literal
from fastapi import Depends, Request, Response

import database as db
import web_auth as auth
import web_schemas as schema
import two_factor as mfa
import profile_media as media


def install(router, *, current_user, changing_user, check_origin, client_bucket,
            login_response, user_out, mfa_cookie, mfa_cookie_path):
    @router.post('/auth/2fa/verify', response_model=schema.SessionOut, tags=['Authentication'])
    async def finish_login(body: schema.FactorAnswer, request: Request, response: Response):
        check_origin(request)
        await auth.reserve_attempt('mfa-ip:' + client_bucket(request), 60)
        binding = auth.token_hash(request.cookies.get(mfa_cookie, ''))
        credential, proof = await mfa.finish_login(body.challenge_token, binding, body.method, body.code.get_secret_value())
        return await login_response(credential, request, response, factor_proof=proof)

    @router.post('/auth/2fa/cancel', status_code=204, tags=['Authentication'])
    async def cancel_login(request: Request):
        check_origin(request)
        response = Response(status_code=204)
        response.delete_cookie(mfa_cookie, path=mfa_cookie_path)
        return response

    @router.get('/me/security', tags=['Security'])
    async def security(user=Depends(current_user)):
        return await mfa.status(user.credential.id, user.account.telegram_id)

    @router.post('/me/security/authorize', tags=['Security'])
    async def authorize(body: schema.FactorAuthorize, user=Depends(changing_user)):
        return await mfa.authorize(user.credential.id, body.current_password.get_secret_value(), user.session.token_hash)

    def answer(body):
        return {'challenge_token': body.challenge_token, 'method': body.method, 'code': body.code.get_secret_value()}

    @router.post('/me/security/{factor}/setup', tags=['Security'])
    async def setup(factor: Literal['totp', 'telegram'], body: schema.FactorAnswer, user=Depends(changing_user)):
        return await mfa.manage(user.credential.id, user.session.token_hash, answer(body), factor + '_setup')

    @router.post('/me/security/totp/enable', tags=['Security'])
    async def confirm_totp(body: schema.TotpConfirm, user=Depends(changing_user)):
        return await mfa.enable_totp(user.credential.id, user.session.token_hash, body.setup_token, body.code.get_secret_value())

    @router.post('/me/security/telegram/enable', tags=['Security'])
    async def confirm_telegram(body: schema.FactorAnswer, user=Depends(changing_user)):
        return await mfa.enable_telegram(user.credential.id, user.session.token_hash, body.challenge_token, body.code.get_secret_value())

    @router.post('/me/security/{factor}/disable', tags=['Security'])
    async def disable(factor: Literal['totp', 'telegram'], body: schema.FactorAnswer, user=Depends(changing_user)):
        return await mfa.manage(user.credential.id, user.session.token_hash, answer(body), factor + '_disable')

    @router.post('/me/security/recovery-codes', tags=['Security'])
    async def recovery_codes(body: schema.FactorAnswer, user=Depends(changing_user)):
        return await mfa.manage(user.credential.id, user.session.token_hash, answer(body), 'recovery_codes')

    @router.get('/me/avatar', tags=['Profile'])
    async def avatar(user=Depends(current_user)):
        content = await media.avatar_content(user.account.telegram_id)
        if not content: raise auth.AuthError('not_found', 404)
        return Response(content, media_type='image/webp', headers={'Cache-Control': 'private, no-store',
            'X-Content-Type-Options': 'nosniff'})

    @router.put('/me/avatar', response_model=schema.UserOut, tags=['Profile'])
    async def upload_avatar(request: Request, user=Depends(changing_user)):
        await auth.reserve_attempt('avatar:' + str(user.account.telegram_id), 20)
        if request.headers.get('content-type', '').split(';')[0] not in ('image/jpeg', 'image/png', 'image/webp'):
            raise auth.AuthError('avatar_invalid', 415)
        try:
            if int(request.headers.get('content-length', '0')) > media.MAX_UPLOAD: raise auth.AuthError('avatar_size', 413)
        except ValueError: raise auth.AuthError('avatar_invalid', 422) from None
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > media.MAX_UPLOAD: raise auth.AuthError('avatar_size', 413)
            data.extend(chunk)
        await media.save_avatar(user.account.telegram_id, bytes(data))
        return user_out(await db.get_account(user.account.telegram_id))

    @router.delete('/me/avatar', response_model=schema.UserOut, tags=['Profile'])
    async def delete_avatar(user=Depends(changing_user)):
        await media.remove_avatar(user.account.telegram_id)
        return user_out(await db.get_account(user.account.telegram_id))
