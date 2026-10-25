"""Localise application-authored response messages, never portfolio/account data."""
import json
import re
from pathlib import Path

CATALOG = json.loads((Path(__file__).parent/'static'/'translations.js').read_text(encoding='utf-8').split('const UI_TRANSLATIONS = ',1)[1].rstrip(';\n'))
LANGUAGES = ('nl','en','es')
MESSAGE_FIELDS = frozenset(('error','message','reason','warnings','warning','match_reason','hint','help','status_label','type_label'))
# Legacy composed messages contain counts, tickers and diagnostic references.
# Replace known message fragments in one pass; do not run translation on names/notes.
fragments=sorted((key for key in CATALOG if len(key)>=12 and ' ' in key),key=len,reverse=True)
FRAGMENTS=re.compile('|'.join(re.escape(key) for key in fragments))

def translate(text,language):
    if language not in LANGUAGES or language=='nl' or not isinstance(text,str):return text
    key=text.strip()
    if key in CATALOG:return text.replace(key,CATALOG[key][language],1)
    return FRAGMENTS.sub(lambda match:CATALOG[match[0]][language],text)

def localize(value,language,field=None):
    if language not in ('en','es'):return value
    if isinstance(value,dict):
        return {key:localize(item,language,key) for key,item in value.items()}
    if isinstance(value,list):return [localize(item,language,field) for item in value]
    if field in MESSAGE_FIELDS:return translate(value,language)
    return value
