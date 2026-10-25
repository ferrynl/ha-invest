"""Translation coverage gate. Technical identifiers are explicitly inventoried.

New interface text belongs in translations.js with nl/en/es and in ui(...) in JS.
Do not add interface copy to i18n_technical_strings.json to silence this check.
"""
import ast
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'portfolio/app/static'

def catalog():
    return json.loads((STATIC/'translations.js').read_text(encoding='utf-8').split('const UI_TRANSLATIONS = ',1)[1].rstrip(';\n'))

def literals(source):
    """Read this project's quoted JS literals, skipping comments.

    Template strings with expressions deliberately fail coverage: use named
    placeholders in the catalogue instead, keeping the complete sentence together.
    """
    i=0
    while i<len(source):
        if source.startswith('//',i):
            end=source.find('\n',i);i=len(source) if end<0 else end;continue
        if source.startswith('/*',i):
            end=source.find('*/',i+2);i=len(source) if end<0 else end+2;continue
        if source[i] in "'\"`":
            start=i;quote=source[i];i+=1
            while i<len(source):
                if source[i]=='\\':i+=2;continue
                if source[i]==quote:break
                i+=1
            i+=1
            yield start,i,source[start+1:i-1]
        else:i+=1

class Markup(HTMLParser):
    def __init__(self):super().__init__();self.strings=set()
    def handle_data(self,value):
        if re.search('[A-Za-z]',value):self.strings.add(value.strip())
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('title','placeholder','aria-label') and value:self.strings.add(value.strip())

def check():
    entries=catalog();errors=[]
    for key,translations in entries.items():
        if set(translations)!=set(('nl','en','es')) or any(not isinstance(v,str) or not v.strip() for v in translations.values()):errors.append('Incomplete translation: '+key)
        if translations.get('nl')!=key:errors.append('Dutch source differs from key: '+key)
        placeholders=re.findall(r'\{\w+\}',key)
        if any(sorted(re.findall(r'\{\w+\}',v))!=sorted(placeholders) for v in translations.values()):errors.append('Placeholder mismatch: '+key)
    technical=json.loads((ROOT/'scripts/i18n_technical_strings.json').read_text(encoding='utf-8'))
    markup=Markup();markup.feed((STATIC/'index.html').read_text(encoding='utf-8'))
    for value in markup.strings-set(entries)-set(technical['html']):errors.append('Untranslated HTML: '+value)
    for path in STATIC.glob('*.js'):
        if path.stem=='translations':continue
        source=path.read_text(encoding='utf-8')
        for start,end,value in literals(source):
            if value.strip() not in entries and value not in technical['js']:errors.append(path.name+': unregistered string '+repr(value))
            elif value.strip() in entries and path.stem!='i18n' and source[max(0,start-3):start]!='ui(':errors.append(path.name+': call ui() for '+repr(value))
    for path in (ROOT/'portfolio/app').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and node.exc.args:
                message=node.exc.args[0]
                if isinstance(message,ast.Constant) and isinstance(message.value,str) and not re.fullmatch('[a-z_]+',message.value) and message.value.strip() not in entries:errors.append(str(path.relative_to(ROOT))+': untranslated error '+message.value)
            messages=[]
            fields={'error','message','reason','warnings','warning','match_reason','hint','help','status_label','type_label'}
            if isinstance(node,ast.Dict):
                messages.extend(value for key,value in zip(node.keys,node.values) if isinstance(key,ast.Constant) and key.value in fields)
            if isinstance(node,ast.keyword) and node.arg in fields:messages.append(node.value)
            if isinstance(node,ast.Assign) and any(isinstance(target,ast.Subscript) and isinstance(target.slice,ast.Constant) and target.slice.value in fields for target in node.targets):messages.append(node.value)
            for expression in messages:
                for part in ast.walk(expression):
                    if isinstance(part,ast.Constant) and isinstance(part.value,str):
                        text=part.value.strip()
                        if re.search('[A-Za-z]',text) and not re.fullmatch('[a-z_]+',text) and text not in entries and text not in (' · Log-ID',' · ISIN'):
                            errors.append(str(path.relative_to(ROOT))+': untranslated message '+repr(part.value))
    return sorted(set(errors))

if __name__=='__main__':
    errors=check()
    if errors:print('\n'.join(errors));sys.exit(1)
    print('Dutch, English and Spanish translation coverage passed.')
