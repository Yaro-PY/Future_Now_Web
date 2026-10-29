"""QA-only HTTP server backed by an isolated SQLite file."""
import os
import sys
import uvicorn

os.environ.update(DATABASE_URL='sqlite+aiosqlite:///' + sys.argv[1], VERCEL='0',
                  WEB_COOKIE_SECURE='false', WEB_COOKIE_SAMESITE='lax')
import main

server = uvicorn.Server(uvicorn.Config(main.app, host='127.0.0.1', port=int(sys.argv[2]), log_level='warning'))


@main.app.post('/__qa__/shutdown')
async def shutdown():
    server.should_exit = True
    return {'ok': True}


server.run()
