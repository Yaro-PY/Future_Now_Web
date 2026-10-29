"""Refresh official catalog sources without starting Telegram or changing its webhook."""
import argparse
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()
import database as db
from catalog.providers import collect
from catalog.sync import source_keys, sync_catalog


async def run(args):
    if args.local_only and db.engine.dialect.name != 'sqlite': raise SystemExit('--local-only requires SQLite')
    keys = source_keys(args.sources)
    try:
        if args.apply:
            await db.init_db()
            result = await sync_catalog(keys,limit=args.limit,workers=2)
        else:
            batches = await asyncio.to_thread(collect,keys,args.limit,2)
            result = {'dry_run':True,'sources':[{'key':r.key,'status':r.status,'count':len(r.events)} for r in batches],
                      'ok':any(r.events for r in batches)}
        print(json.dumps(result,ensure_ascii=True))
        return 0 if result['ok'] else 1
    finally: await db.close_db()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Upsert fetched records and save source health')
    parser.add_argument('--local-only',action='store_true',help='Refuse to write to PostgreSQL')
    parser.add_argument('--sources',default=None,help='Comma-separated: man,prometheus,diia')
    parser.add_argument('--limit',type=int,choices=range(1,41),default=12,metavar='1..40')
    raise SystemExit(asyncio.run(run(parser.parse_args())))
