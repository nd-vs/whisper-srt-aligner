"""Generate a controlled example from original text and Windows SAPI speech.

This creates demo fixtures, not measured alignment results. Run the actual CLI
separately, then render_demo.py to publish the measured result and visual assets.
"""
import argparse
import json
import subprocess
import wave
from pathlib import Path

from whisper_srt_aligner.subtitles import format_timestamp

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
args = parser.parse_args()
args.work_dir.mkdir(parents=True, exist_ok=True)
config = ROOT / 'docs/demo/script.json'
settings = json.loads(config.read_text(encoding='utf-8'))
subprocess.run(['powershell.exe','-NoProfile','-File',str(ROOT/'scripts/speak_demo.ps1'),
                '-Config',str(config),'-OutputDirectory',str(args.work_dir)],check=True)
audio = bytearray(16000 * 2 * 57)
expected=[]
source=[]
for index, cue in enumerate(settings['cues']):
    normalized = args.work_dir / f'normalized-{index}.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(args.work_dir/f'line-{index}.wav'),
                    '-ac','1','-ar','16000','-c:a','pcm_s16le',str(normalized)],check=True)
    with wave.open(str(normalized),'rb') as handle:
        frames=handle.readframes(handle.getnframes())
    duration=len(frames)/32000
    start=cue['actual_start']
    if start+duration > (settings['cues'][index+1]['actual_start'] if index+1<len(settings['cues']) else 57):
        raise ValueError('Synthetic line does not fit its slot')
    offset=int(start*32000)
    audio[offset:offset+len(frames)]=frames
    for target,begin in [(expected,start),(source,cue['source_start'])]:
        target.append(f'{index+1}\n{format_timestamp(begin)} --> {format_timestamp(begin+duration)}\n{cue["text"]}\n')
out=ROOT/'docs/demo'
with wave.open(str(out/'speech.wav'),'wb') as handle:
    handle.setnchannels(1);handle.setsampwidth(2);handle.setframerate(16000);handle.writeframes(audio)
(out/'source.srt').write_text('\n'.join(source),encoding='utf-8')
(out/'reference.srt').write_text('\n'.join(expected),encoding='utf-8')
print('Generated speech.wav, source.srt, reference.srt. Next run sync on speech.wav.')
