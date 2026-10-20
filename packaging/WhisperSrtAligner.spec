# Build on Windows in an isolated environment with the project's runtime deps.
import importlib.metadata
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
datas = []
binaries = []
hiddenimports = []
for module in ('faster_whisper', 'ctranslate2', 'onnxruntime', 'av', 'tokenizers'):
    data, binary, hidden = collect_all(module)
    datas += data; binaries += binary; hiddenimports += hidden
hiddenimports += collect_submodules('huggingface_hub')
# Ship distribution metadata and its license directories with the portable build.
for distribution in importlib.metadata.distributions():
    name = distribution.metadata.get('Name')
    if name:
        datas += copy_metadata(name)
python_license = Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():datas.append((str(python_license),'licenses/Python'))
datas += [(str(root/'LICENSE'),'licenses/whisper-srt-aligner')]

a = Analysis([str(root/'scripts/gui_entry.py')], pathex=[str(root/'src')],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=['torch','tensorflow','IPython','matplotlib','pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='WhisperSrtAligner',
          debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='WhisperSrtAligner')
