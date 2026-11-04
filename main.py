"""Standalone Future Now website backend. Does not import or run the Telegram bot."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./website.db')

import database as db
from web_api import install as install_api

SERVERLESS = os.getenv('VERCEL') == '1'
DEPLOYMENT_ENV = os.getenv('VERCEL_ENV', 'production')
STATIC = Path(__file__).resolve().parent / 'static'


def serverless_configuration_error():
    if DEPLOYMENT_ENV != 'production': return 'Only the production deployment serves the website API'
    if db.engine.dialect.name != 'postgresql': return 'Set DATABASE_URL to the shared PostgreSQL database'
    return ''


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    app.state.configuration_error = ''
    try:
        if SERVERLESS:
            # Schema setup is explicit; cold starts never change the database.
            app.state.configuration_error = serverless_configuration_error()
        else:
            await db.init_db()
        app.state.ready = not app.state.configuration_error
        yield
    finally:
        app.state.ready = False
        await db.close_db()


app = FastAPI(title='Future Now Website API', version='1.2.0', lifespan=lifespan)
app.state.ready = False
app.state.configuration_error = ''
install_api(app)
app.mount('/assets', StaticFiles(directory=STATIC), name='assets')


@app.middleware('http')
async def require_ready(request: Request, call_next):
    if request.url.path.startswith('/api/v1') and not app.state.ready:
        return JSONResponse({'error': {'code': 'not_ready', 'message': 'Website API is not ready'}},
                            status_code=503, headers={'Cache-Control': 'no-store'})
    return await call_next(request)


@app.get('/', response_class=HTMLResponse)
async def root():
    frontend = STATIC / 'react' / 'index.html'
    if not frontend.is_file():
        return PlainTextResponse('Build the React frontend: cd frontend && npm ci && npm run build', status_code=503)
    return FileResponse(frontend, headers={
        'Cache-Control': 'no-cache',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    })


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(STATIC / 'favicon.svg', media_type='image/svg+xml')


@app.get('/health', response_class=PlainTextResponse)
async def health():
    if not app.state.ready:
        return PlainTextResponse(app.state.configuration_error or 'Not ready', status_code=503)
    try:
        await db.database_ready(require_schema=True)
    except Exception:
        return PlainTextResponse('Database unavailable', status_code=503)
    return 'OK'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8002')))
