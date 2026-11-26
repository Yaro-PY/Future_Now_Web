"""Connection options for local SQLite and Neon/PostgreSQL."""
import ssl

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def connection_settings(value, serverless=False):
    url = make_url(value)
    options = {'pool_pre_ping': True}
    if url.drivername in ('postgres', 'postgresql'):
        url = url.set(drivername='postgresql+asyncpg')
    if url.drivername == 'postgresql+asyncpg':
        query = dict(url.query)
        sslmode = query.pop('sslmode', None)
        # Neon supplies libpq options; asyncpg uses an SSL context instead.
        query.pop('channel_binding', None)
        if sslmode:
            if sslmode not in ('require', 'verify-ca', 'verify-full', 'disable'):
                raise ValueError('Use sslmode=require, verify-ca, verify-full or disable')
            if sslmode == 'disable' and (url.host or '').endswith('.neon.tech'):
                raise ValueError('Neon requires TLS')
            options['connect_args'] = {'ssl': False if sslmode == 'disable' else ssl.create_default_context()}
        elif (url.host or '').endswith('.neon.tech'):
            options['connect_args'] = {'ssl': ssl.create_default_context()}
        url = url.set(query=query)
        if serverless:
            # Neon owns the connection pool; do not retain connections in frozen instances.
            options['poolclass'] = NullPool
    return url, options
