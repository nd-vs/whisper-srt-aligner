"""Export reviewed wiki sources locally. Does not push or change GitHub."""
import argparse
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/wiki'
BASE = 'https://github.com/nd-vs/whisper-srt-aligner/blob/main/'
parser=argparse.ArgumentParser()
parser.add_argument('output',type=Path)
args=parser.parse_args()
if args.output.resolve().is_relative_to(ROOT):
    raise SystemExit('Choose a separate output folder for wiki export')
args.output.mkdir(parents=True,exist_ok=True)
for path in SOURCE.glob('*.md'):
    def rewrite(match):
        label,url=match.groups()
        if '://' in url or url.startswith('#'):
            return match.group(0)
        name,sep,anchor=url.partition('#')
        target=(path.parent/name).resolve()
        if target.parent==SOURCE and target.suffix=='.md':
            destination=target.stem
        else:
            destination=BASE+quote(target.relative_to(ROOT).as_posix())
        return f'[{label}]({destination}{sep}{anchor})'
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',rewrite,path.read_text(encoding='utf-8'))
    (args.output/path.name).write_text(text,encoding='utf-8')
print(f'Exported wiki sources to {args.output}; nothing published')
