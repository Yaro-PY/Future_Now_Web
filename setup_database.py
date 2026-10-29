"""Explicit additive schema setup using DATABASE_URL; no Telegram calls."""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./website.db')
import database as db


async def main():
    try:
        await db.init_db()
        print('Future Now database schema is ready. Existing records were retained.')
    finally:
        await db.close_db()


if __name__ == '__main__':
    asyncio.run(main())
