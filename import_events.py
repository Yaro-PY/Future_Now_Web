"""Validate and import a curated JSON feed without inventing missing metadata."""
import argparse
import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from database import EventData, init_db, upsert_events, close_db
from flow_catalog import TYPES, TOPICS, COUNTRIES, CITIES, FORMATS, BENEFITS

class Opportunity(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    source: str = Field(default='Curated import', max_length=200)
    description: str = Field(default='', max_length=5000)
    event_type: str = 'other'
    topics: list[str] = Field(default_factory=list)
    country: str = 'international'
    city: str = ''
    format: str = 'unknown'
    min_age: int | None = Field(default=None, ge=0, le=100)
    max_age: int | None = Field(default=None, ge=0, le=100)
    start_at: datetime | None = None
    deadline: datetime | None = None
    is_free: bool | None = None
    price_text: str = Field(default='', max_length=200)
    criteria: list[str] = Field(default_factory=list)
    organizer: str = Field(default='', max_length=500)
    participation_language: str = Field(default='', max_length=100)
    requirements: str = Field(default='', max_length=3000)
    is_self_paced: bool = False

    @field_validator('event_type', 'country', 'city', 'format')
    @classmethod
    def valid_key(cls, value, info):
        catalogs = {'event_type': TYPES, 'country': COUNTRIES, 'city': CITIES, 'format': FORMATS}
        if value in ('any',) or (value not in catalogs[info.field_name] and not (info.field_name == 'city' and value == '') and not (info.field_name == 'format' and value == 'unknown')):
            raise ValueError(f'Invalid {info.field_name}: {value}')
        return value

    @field_validator('topics', 'criteria')
    @classmethod
    def valid_list(cls, value, info):
        catalog = TOPICS if info.field_name == 'topics' else BENEFITS
        if any(key not in catalog for key in value): raise ValueError(f'Invalid {info.field_name}')
        return sorted(set(value))

    @field_validator('start_at', 'deadline')
    @classmethod
    def local_date(cls, value):
        return value.astimezone(ZoneInfo('Europe/Kyiv')).replace(tzinfo=None) if value and value.tzinfo else value

    @model_validator(mode='after')
    def valid_opportunity(self):
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError('min_age must not exceed max_age')
        if 'free' in self.criteria and self.is_free is not True:
            raise ValueError('The free criterion requires is_free=true')
        if 'paid' in self.criteria and self.is_free is not False:
            raise ValueError('The paid criterion requires is_free=false')
        return self

    def event(self):
        values = self.model_dump()
        url = str(self.url)
        return EventData(**{**values, 'url': url, 'external_id': hashlib.sha256(url.encode()).hexdigest(),
                            'subjects': [], 'raw_text': self.description,
                            'is_free': self.is_free is True, 'price_known': self.is_free is not None})

def read_feed(filename):
    payload = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
    rows = payload['opportunities'] if isinstance(payload, dict) else payload
    if not isinstance(rows, list): raise ValueError('Expected a list of opportunities')
    return [Opportunity.model_validate(row).event() for row in rows]

async def run(filename):
    events = read_feed(filename)  # Validate every row before making any database changes.
    try:
        await init_db()
        print(f'Imported / updated: {await upsert_events(events)}')
    finally:
        await close_db()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filename', help='Path to a curated JSON feed')
    args = parser.parse_args()
    asyncio.run(run(args.filename))
