"""Stable JSON contracts for a future website; no Telegram message markup."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from flow_catalog import TYPES, COUNTRIES, CITIES, FORMATS, DATES, CRITERIA
from identity import normalize_name, normalize_nickname
from import_events import Opportunity
from proposals import canonical_url

Language = Literal['uk', 'en']
Age = Literal['any', '13-16', '16-18', '18+']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Filters(Input):
    type: str = 'any'
    age: Age = 'any'
    country: str = 'any'
    city: str = 'any'
    format: str = 'any'
    date: str = 'any'
    criteria: list[str] = Field(default_factory=list, max_length=4)

    @field_validator('type', 'country', 'city', 'format', 'date')
    @classmethod
    def catalog_key(cls, value, info):
        catalogs = {'type': TYPES, 'country': COUNTRIES, 'city': CITIES, 'format': FORMATS, 'date': DATES}
        if value not in catalogs[info.field_name]: raise ValueError('Unknown option')
        return value

    @field_validator('criteria')
    @classmethod
    def criteria_keys(cls, value):
        if any(key not in CRITERIA for key in value): raise ValueError('Unknown criterion')
        if 'free' in value and 'paid' in value: raise ValueError('Free and paid cannot be selected together')
        return sorted(set(value))

    @model_validator(mode='after')
    def location(self):
        if self.country != 'ukraine': self.city = 'any'
        return self


class Register(Input):
    nickname: str
    display_name: str
    password: SecretStr = Field(min_length=8, max_length=128)
    language: Language = 'uk'
    _nickname = field_validator('nickname')(normalize_nickname)
    _name = field_validator('display_name')(normalize_name)


class Login(Input):
    nickname: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)


class PasswordChange(Input):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)


class AccountDelete(Input):
    password: SecretStr = Field(min_length=1, max_length=128)
    confirmation: str = Field(min_length=3, max_length=32)


class Profile(Input):
    nickname: str
    display_name: str
    age: Literal['13-16', '16-18', '18+']
    country: str = 'any'
    city: str = 'any'
    format: str = 'any'
    criteria: list[str] = Field(default_factory=list, max_length=4)
    _nickname = field_validator('nickname')(normalize_nickname)
    _name = field_validator('display_name')(normalize_name)

    @field_validator('country', 'city', 'format')
    @classmethod
    def catalog_key(cls, value, info):
        return Filters.catalog_key(value, info)

    @field_validator('criteria')
    @classmethod
    def criteria_keys(cls, value):
        return Filters.criteria_keys(value)

    @model_validator(mode='after')
    def location(self):
        if self.country != 'ukraine': self.city = 'any'
        return self


class Notifications(Input):
    new: bool = False
    deadlines: bool = False
    expired: bool = True


class Settings(Input):
    language: Language | None = None
    notifications: Notifications | None = None


class Search(Input):
    filters: Filters | None = None
    query: str = Field(default='', max_length=120)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)


class Report(Input):
    event_id: int | None = Field(default=None, ge=1)
    category: Literal['bad_info', 'bad_link', 'broken_link', 'ended', 'other']
    message: str = Field(min_length=1, max_length=2000)

    @field_validator('message')
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value: raise ValueError('Message is empty')
        return value


class Proposal(Opportunity):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=8, max_length=150)
    description: str = Field(min_length=40, max_length=1500)

    @field_validator('url', mode='before')
    @classmethod
    def public_link(cls, value):
        return canonical_url(str(value))


class Revision(Input):
    expected_revision: int = Field(ge=1)


class ProposalEdit(Revision):
    values: Proposal


class AdminProposal(Proposal):
    expected_revision: int | None = Field(default=None, ge=1)


class Decision(Input):
    expected_revision: int | None = Field(default=None, ge=1)
    decision: Literal['approved', 'rejected']
    reason: str = Field(default='', max_length=500)


class PublishedOpportunity(Opportunity):
    model_config = ConfigDict(extra='forbid')
    is_closed: bool = False

    @field_validator('title')
    @classmethod
    def title_nonempty(cls, value):
        value = value.strip()
        if not value: raise ValueError('Title is empty')
        return value

    @field_validator('url', mode='before')
    @classmethod
    def public_link(cls, value): return canonical_url(str(value))


class PublishedEdit(Input):
    expected_revision: int = Field(ge=1)
    values: PublishedOpportunity


class ReportReview(Input):
    expected_revision: int = Field(ge=1)
    status: Literal['new', 'in_progress', 'resolved', 'dismissed']
    review_note: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def meaningful_resolution(self):
        self.review_note = self.review_note.strip()
        if self.status in ('resolved','dismissed') and len(self.review_note) < 5:
            raise ValueError('Explain the resolution')
        return self


class Subscription(Input):
    enabled: bool


class UserOut(BaseModel):
    avatar_url: str | None = None
    public_id: str | None
    nickname: str | None
    display_name: str | None
    language: Language
    role: Literal['user', 'admin']
    telegram_linked: bool
    profile: dict | None
    filters: Filters
    notifications: Notifications
    onboarding_required: bool
    filters_setup_required: bool


class FactorChallenge(BaseModel):
    two_factor_required: bool = True
    challenge_token: str
    methods: list[str]
    expires_in: int
    telegram_url: str | None = None


class FactorAnswer(Input):
    challenge_token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')
    method: Literal['totp', 'telegram', 'recovery', 'none']
    code: SecretStr = Field(default=SecretStr(''), max_length=32)


class FactorAuthorize(Input):
    current_password: SecretStr = Field(min_length=1, max_length=128)


class TotpConfirm(Input):
    setup_token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')
    code: SecretStr = Field(min_length=6, max_length=6)


class SessionOut(BaseModel):
    user: UserOut
    csrf_token: str


class EventOut(BaseModel):
    id: int
    title: str
    description: str
    source: str
    url: str | None
    registration_url: str | None
    event_type: str
    event_type_label: str
    topics: list[str]
    tags: list[dict[str, str]]
    country: str
    country_label: str
    city: str
    city_label: str
    format: str
    format_label: str
    min_age: int | None
    max_age: int | None
    start_at: datetime | None
    deadline: datetime | None
    status: str
    price: dict
    criteria: list[str]
    organizer: str
    participation_language: str
    requirements: str
    saved: bool
    subscribed: bool
    is_self_paced: bool = False
    verified_at: datetime | None = None


class EventPage(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    page_size: int
    pages: int
    filters: Filters | None = None


class ProposalOut(BaseModel):
    revision: int
    updated_at: datetime
    id: int
    payload: Opportunity
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    review_note: str
    event_id: int | None
