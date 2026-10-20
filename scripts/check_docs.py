"""Check repository Markdown links and balanced fenced blocks, without a network."""
import re
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
errors=[]
paths=[ROOT/'README.md',ROOT/'CHANGELOG.md',*sorted((ROOT/'docs').rglob('*.md'))]
for path in paths:
    body=path.read_text(encoding='utf-8')
    if len(re.findall(r'^```',body,re.M))%2:
        errors.append(f'{path.relative_to(ROOT)}: unbalanced fenced code')
    for url in re.findall(r'\[[^\]]*\]\(([^)]+)\)',body):
        if '://' in url or url.startswith('#'):continue
        target=url.split('#',1)[0]
        if target and not (path.parent/unquote(target)).exists():
            errors.append(f'{path.relative_to(ROOT)}: missing {url}')
if errors:raise SystemExit('\n'.join(errors))
print(f'{len(paths)} Markdown files: local link targets and fences OK')
