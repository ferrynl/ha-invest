"""Validate the release version and extract its notes for GitHub Actions."""
import ast
import os
import re
from pathlib import Path


def prepare(root):
    module = ast.parse((root / 'portfolio/app/version.py').read_text(encoding='utf-8'))
    version = next(ast.literal_eval(node.value) for node in module.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'APP_VERSION'
                           for target in node.targets))
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid application version')
    config = (root / 'portfolio/config.yaml').read_text(encoding='utf-8')
    if not re.search(r'^version:\s*[\'"]?' + re.escape(version) + r'[\'"]?\s*$', config, re.M):
        raise ValueError('Application and Home Assistant versions differ')
    sections = []
    for filename in ('CHANGELOG.md', 'portfolio/CHANGELOG.md'):
        text = (root / filename).read_text(encoding='utf-8')
        heading = re.search(r'^#{1,2}[ \t]+' + re.escape(version) + r'(?:[ \t]+[^\n]*)?$', text, re.M)
        if not heading:
            raise ValueError(f'Missing changelog section in {filename}')
        tail = text[heading.end():]
        section = re.split(r'^#{1,2}\s+', tail, maxsplit=1, flags=re.M)[0].strip()
        if not section:
            raise ValueError(f'Empty release notes in {filename}')
        sections.append(section)
    if sections[0] != sections[1]:
        raise ValueError('Release notes differ between changelogs')
    return version, sections[0] + '\n'


if __name__ == '__main__':
    version, notes = prepare(Path(__file__).resolve().parents[1])
    (Path(os.environ['RUNNER_TEMP']) / 'release-notes.md').write_text(notes, encoding='utf-8')
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as environment:
        environment.write(f'APP_VERSION={version}\n')
