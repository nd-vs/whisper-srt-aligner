"""Publish measured demo outputs, a timeline graphic, and a narrated comparison.

Requires Pillow for rendering (development only), FFmpeg/libass, and real sync
outputs from the documented demo run. Does not invent recognition timestamps.
"""
import argparse
import html
import json
import importlib.metadata
import platform
import shutil
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from whisper_srt_aligner.subtitles import parse_srt
from whisper_srt_aligner.report import write_html_report

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/demo'
parser=argparse.ArgumentParser()
parser.add_argument('--work-dir',type=Path,required=True)
parser.add_argument('--elapsed-seconds',type=float,required=True)
parser.add_argument('--hardware',required=True)
args=parser.parse_args()
work=args.work_dir.resolve()
report=json.loads((work/'result-report.json').read_text(encoding='utf-8'))
source=parse_srt(OUT/'source.srt');reference=parse_srt(OUT/'reference.srt')
aligned=parse_srt(work/'result.srt')
if [c.text for c in source]!=[c.text for c in aligned]:
    raise ValueError('Demo lost or rewrote text; inspect actual results before publication')
shutil.copyfile(work/'result.srt',OUT/'result.srt')
for key in ('subtitle','transcript','supplemental_transcript','output','media'):
    if key in report['metadata']:
        report['metadata'][key]={'subtitle':'source.srt','transcript':'primary-transcript.json',
          'supplemental_transcript':'supplemental-transcript.json','output':'result.srt','media':'speech.wav'}[key]
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
write_html_report(OUT/'report.html',report)
for filename,public in [('demo.whisper.json','primary-transcript.json'),('demo.vad.whisper.json','supplemental-transcript.json')]:
    data=json.loads((work/filename).read_text(encoding='utf-8'))
    data['media']={'path':'speech.wav','note':'Local path/mtime removed for publication; recognition unchanged.'}
    (OUT/public).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
rows=[dict(cue=i+1,reference_start=r.start,source_start=s.start,aligned_start=a.start,
           source_start_error=round(s.start-r.start,3),aligned_start_error=round(a.start-r.start,3))
      for i,(r,s,a) in enumerate(zip(reference,source,aligned))]
metrics=dict(scenario='Controlled synthetic speech, six cues, two six-second timing jumps',
             reference='Insertion positions of synthesized utterances, not human phonetic annotation',
             command='sync speech.wav source.srt --complete --model small --device cpu --compute-type int8 --output result.srt',
             model='small',device='cpu',compute_type='int8',hardware=args.hardware,
             duration_seconds=57,elapsed_seconds=args.elapsed_seconds,
             model_download_included=False,run_count=1,
             mean_absolute_start_error_before=round(sum(abs(r['source_start_error']) for r in rows)/len(rows),3),
             mean_absolute_start_error_after=round(sum(abs(r['aligned_start_error']) for r in rows)/len(rows),3),
             max_absolute_start_error_after=max(abs(r['aligned_start_error']) for r in rows),
             original_text_preserved=True,cues=rows)
metrics['runtime_versions']={name:importlib.metadata.version(name) for name in
    ('faster-whisper','ctranslate2','av','huggingface-hub','tokenizers','numpy')}
metrics['python_version']=platform.python_version()
(OUT/'measurements.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')

def font(size):
    for candidate in ('C:/Windows/Fonts/segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(candidate).exists():return ImageFont.truetype(candidate,size)
    return ImageFont.load_default(size=size)

BG='#101827';INK='#edf3ff';MUTED='#aab8cf';BLUE='#5baaff';RED='#fb8d87';GREEN='#75dfb2'
canvas=Image.new('RGB',(1200,450),BG);draw=ImageDraw.Draw(canvas)
draw.text((38,25),'Same words. Different timing.',font=font(31),fill=INK)
draw.text((38,72),'Controlled demo: two added pauses shift later dialogue by 6 and 12 seconds.',font=font(18),fill=MUTED)
x0=215;scale=16
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="450" viewBox="0 0 1200 450"><rect width="1200" height="450" fill="{BG}"/>']
def svgtext(x,y,text,size,color):svg.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}">{html.escape(text)}</text>')
svgtext(38,52,'Same words. Different timing.',31,INK)
svgtext(38,93,'Controlled demo: two added pauses shift later dialogue by 6 and 12 seconds.',18,MUTED)
for t in range(0,58,5):
    x=x0+t*scale
    draw.line((x,133,x,339),fill='#29384f',width=1)
    draw.text((x-5,345),str(t),font=font(14),fill=MUTED)
    svg.append(f'<path d="M{x} 133V339" stroke="#29384f"/>');svgtext(x-5,361,str(t),14,MUTED)
for label,y,color,cues in [('Speech slots',145,BLUE,reference),('Before / SRT',215,RED,source),('After / aligned',285,GREEN,aligned)]:
    draw.text((38,y+2),label,font=font(20),fill=INK);svgtext(38,y+24,label,20,INK)
    for i,c in enumerate(cues):
        left=x0+c.start*scale;right=x0+c.end*scale
        draw.rounded_rectangle((left,y,right,y+34),radius=5,fill=color)
        draw.text((left+6,y+4),str(i+1),font=font(16),fill=BG)
        svg.append(f'<rect x="{left}" y="{y}" width="{right-left}" height="34" rx="5" fill="{color}"/>');svgtext(left+6,y+24,str(i+1),16,BG)
draw.text((38,393),'6/6 original lines retained | Actual CPU / small result | Review is still required on real media.',font=font(18),fill=MUTED)
svgtext(38,416,'6/6 original lines retained | Actual CPU / small result | Review is still required on real media.',18,MUTED)
svg.append('</svg>');(OUT/'timing.svg').write_text(''.join(svg),encoding='utf-8');canvas.save(OUT/'timing.png')

base=Image.new('RGB',(1280,720),BG);d=ImageDraw.Draw(base)
d.text((60,32),'Fix timing. Keep the original subtitle text.',font=font(34),fill=INK)
d.text((60,90),'ACTUAL AUDIO  /  original synthetic speech',font=font(20),fill=BLUE)
for x,label,color,detail in [(40,'BEFORE',RED,'Original SRT: later lines are 6 or 12 seconds early'),(660,'AFTER',GREEN,'Actual small / CPU alignment; no manual retiming')]:
    d.rounded_rectangle((x,315,x+580,570),radius=14,fill='#1b293d')
    d.text((x+20,333),label,font=font(24),fill=color)
    d.text((x+20,534),detail,font=font(13),fill=MUTED)
d.text((60,615),'A 57-second controlled example, not a film/TV accuracy benchmark.',font=font(21),fill=MUTED)
d.text((60,655),'whisper-srt-aligner  |  nd-vs/whisper-srt-aligner',font=font(18),fill=INK)
base.save(work/'background.png')
def ass_time(t):
    cent=int(round(t*100));return f'{cent//360000}:{cent//6000%60:02d}:{cent//100%60:02d}.{cent%100:02d}'
header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,27,&H00FFFFFF,&H00FFFFFF,&H00101827,&H00101827,0,0,0,0,100,100,0,0,1,0,0,8,20,20,20,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
events=[]
for cues,x,y,width in [(reference,640,180,68),(source,330,412,33),(aligned,950,412,33)]:
    for c in cues:
        text=r'\N'.join(textwrap.wrap(c.text,width))
        events.append(f'Dialogue: 0,{ass_time(c.start)},{ass_time(c.end)},Default,,0,0,0,,{{\\pos({x},{y})}}{text}')
(work/'comparison.ass').write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(work/'background.png'),'-i',str(OUT/'speech.wav'),
    '-vf','ass=comparison.ass','-t','57','-r','15','-c:v','libx264','-preset','fast','-tune','stillimage','-crf','25',
    '-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart',str(OUT/'comparison.mp4')],cwd=work,check=True)
print(json.dumps(metrics,indent=2))
