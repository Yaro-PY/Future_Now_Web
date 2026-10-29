"""Profile identity validation; no website authentication or database migrations."""
import re
import unicodedata

AGE_GROUPS = ('13-16', '16-18', '18+')

def normalize_nickname(value):
    if not isinstance(value, str): raise ValueError('nickname_invalid')
    value = value.strip().removeprefix('@').lower()
    if not re.fullmatch(r'[a-z][a-z0-9_]{2,31}', value):
        raise ValueError('nickname_invalid')
    return value

def normalize_name(value):
    if not isinstance(value, str): raise ValueError('name_invalid')
    value = unicodedata.normalize('NFC', value).strip()
    if not 2 <= len(value) <= 80 or any(unicodedata.category(char).startswith('C') for char in value):
        raise ValueError('name_invalid')
    if not any(char.isalpha() for char in value):
        raise ValueError('name_invalid')
    return value

def age_group(value):
    """Map manually entered/legacy ages to the three new profile choices."""
    value = str(value).replace('–', '-').strip()
    if value in AGE_GROUPS: return value
    if value == '13-14': return '13-16'
    if value == '15-17': return '16-18'
    if not value.isdecimal() or not 13 <= int(value) <= 100:
        raise ValueError('invalid_age')
    return '13-16' if int(value) < 16 else '16-18' if int(value) < 18 else '18+'

def identity_complete(profile):
    if not profile: return False
    try:
        normalize_nickname(profile.get('nickname', ''))
        normalize_name(profile.get('display_name', ''))
    except ValueError:
        return False
    return True
