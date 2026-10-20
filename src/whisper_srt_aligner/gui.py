"""Small desktop frontend; recognition and probing run outside the Tk process."""
from __future__ import annotations

import json
import locale
import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .gui_process import JobProcess


TEXT = {
    'en': {
        'tagline': 'Fix subtitle timing. Keep the words you trust.',
        'files': '1  Choose your files', 'media': 'Video / audio', 'srt': 'Original SRT',
        'output': 'Save new SRT', 'browse': 'Browse…', 'settings': '2  Alignment settings',
        'spoken': 'Spoken language', 'track': 'Audio track', 'inspect': 'Find tracks',
        'model': 'Whisper model', 'device': 'Run on', 'precision': 'Precision',
        'complete': 'Recover short and quiet lines (two passes; slower)',
        'hint': 'CPU + small works without NVIDIA setup. Audio and subtitles must use the same language.',
        'ffmpeg': 'FFmpeg folder (optional)', 'ffhint': 'Leave blank if ffmpeg and ffprobe are on PATH. Otherwise choose their bin folder.',
        'download': 'FFmpeg setup', 'first': 'First run downloads the model. Processing stays local. Estimated timings still need review.',
        'start': 'Align subtitles', 'cancel': 'Cancel', 'ready': 'Choose a video and SRT to begin.',
        'probing': 'Reading audio tracks…', 'running': 'Working… the first model download can take a while.',
        'stage1': 'Pass 1 of 2 — listening for speech', 'stage2': 'Pass 2 of 2 — recovering missed lines',
        'report': 'Open report', 'folder': 'Open folder', 'copy': 'Copy log', 'log': 'Progress / details',
        'choose_track': 'Choose a track', 'tracks_ready': 'Audio tracks found. Choose the matching track, then start.',
        'need_track': 'Use Find tracks for this video and select the spoken audio track first.',
        'replace': 'Replace existing output files?', 'replace_text': 'The SRT or its reports already exist. Replace only these generated files?',
        'error': 'Could not complete the task', 'cancelled': 'Cancelled. Previously completed output files were kept.',
        'result': 'Done: {kept}/{total} lines kept · {dropped} dropped · {inferred} inferred. Review the report.',
        'close': 'Cancel the running task and close?', 'failed': 'Worker stopped unexpectedly. See the log below.',
    },
    'ru': {
        'tagline': 'Исправьте тайминги. Сохраните готовый текст субтитров.',
        'files': '1  Выберите файлы', 'media': 'Видео / аудио', 'srt': 'Исходный SRT',
        'output': 'Новый SRT', 'browse': 'Выбрать…', 'settings': '2  Настройка выравнивания',
        'spoken': 'Язык речи', 'track': 'Аудиодорожка', 'inspect': 'Найти дорожки',
        'model': 'Модель Whisper', 'device': 'Устройство', 'precision': 'Точность вычислений',
        'complete': 'Восстанавливать короткие и тихие реплики (два прохода; дольше)',
        'hint': 'CPU + small не требуют NVIDIA. Речь и субтитры должны быть на одном языке.',
        'ffmpeg': 'Папка FFmpeg (необязательно)', 'ffhint': 'Оставьте пустой, если ffmpeg и ffprobe есть в PATH. Иначе укажите их папку bin.',
        'download': 'Установка FFmpeg', 'first': 'При первом запуске загрузится модель. Обработка локальная. Расчётные тайминги нужно проверить.',
        'start': 'Выровнять субтитры', 'cancel': 'Отмена', 'ready': 'Выберите видео и исходные субтитры.',
        'probing': 'Поиск аудиодорожек…', 'running': 'Обработка… первая загрузка модели может занять время.',
        'stage1': 'Проход 1 из 2 — распознавание речи', 'stage2': 'Проход 2 из 2 — поиск пропущенных реплик',
        'report': 'Открыть отчёт', 'folder': 'Открыть папку', 'copy': 'Скопировать лог', 'log': 'Ход обработки / подробности',
        'choose_track': 'Выберите дорожку', 'tracks_ready': 'Дорожки найдены. Выберите нужную и запустите выравнивание.',
        'need_track': 'Сначала нажмите «Найти дорожки» для этого видео и выберите нужную аудиодорожку.',
        'replace': 'Заменить существующий результат?', 'replace_text': 'SRT или отчёты уже существуют. Заменить только эти выходные файлы?',
        'error': 'Не удалось завершить задачу', 'cancelled': 'Обработка отменена. Ранее готовые файлы сохранены.',
        'result': 'Готово: {kept}/{total} строк · пропущено {dropped} · расчётных {inferred}. Проверьте отчёт.',
        'close': 'Отменить текущую обработку и закрыть окно?', 'failed': 'Рабочий процесс неожиданно завершился. Подробности в логе.',
    },
}


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.lang = 'ru' if (locale.getlocale()[0] or '').lower().startswith('ru') else 'en'
        self.values = {key: tk.StringVar() for key in ('media', 'srt', 'output', 'ffmpeg')}
        self.spoken = tk.StringVar(value='en')
        self.model = tk.StringVar(value='small')
        self.device = tk.StringVar(value='cpu')
        self.precision = tk.StringVar(value='int8')
        self.complete = tk.BooleanVar(value=True)
        self.runner = None
        self.action = None
        self.result = None
        self.streams = []
        self.probed_media = None
        self.pending_event = None
        self.close_when_done = False
        self.labels = []
        self.inputs = []
        root.title(f'Whisper SRT Aligner · {__version__}')
        root.geometry('970x850'); root.minsize(850, 780)
        style = ttk.Style(root)
        if 'vista' in style.theme_names(): style.theme_use('vista')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI Semibold', 22))
        style.configure('Hint.TLabel', foreground='#52637b')
        frame = ttk.Frame(root, padding=24); frame.pack(fill='both', expand=True)
        top = ttk.Frame(frame); top.pack(fill='x')
        ttk.Label(top, text='Whisper SRT Aligner', style='Title.TLabel').pack(side='left')
        interface = ttk.Combobox(top, values=['English', 'Русский'], state='readonly', width=12)
        interface.set('Русский' if self.lang == 'ru' else 'English'); interface.pack(side='right')
        interface.bind('<<ComboboxSelected>>', lambda e: self.translate('ru' if interface.get() == 'Русский' else 'en'))
        self.label(frame, 'tagline', style='Hint.TLabel').pack(anchor='w', pady=(2, 18))
        files = ttk.LabelFrame(frame, padding=14); self.labels.append((files, 'files')); files.pack(fill='x')
        files.columnconfigure(1, weight=1)
        for row,key in enumerate(('media','srt','output')):
            self.label(files,key).grid(row=row,column=0,sticky='w',padx=(0,12),pady=5)
            entry=ttk.Entry(files,textvariable=self.values[key]); entry.grid(row=row,column=1,sticky='ew',pady=5)
            self.inputs.append(entry)
            button=self.button(files,'browse',lambda k=key:self.choose(k)); button.grid(row=row,column=2,padx=(10,0),pady=5)
            self.inputs.append(button)
        settings=ttk.LabelFrame(frame,padding=14); self.labels.append((settings,'settings')); settings.pack(fill='x',pady=14)
        settings.columnconfigure(1,weight=1)
        self.label(settings,'spoken').grid(row=0,column=0,sticky='w',padx=(0,12))
        spoken=ttk.Combobox(settings,textvariable=self.spoken,values=['en','ru','es','fr','de','it','pt','ja','zh'],width=8)
        spoken.grid(row=0,column=1,sticky='w');self.inputs.append(spoken)
        self.label(settings,'track').grid(row=1,column=0,sticky='w',pady=9)
        self.track=ttk.Combobox(settings,state='readonly');self.track.grid(row=1,column=1,sticky='ew',pady=9)
        self.inputs.append(self.track)
        probe=self.button(settings,'inspect',self.probe);probe.grid(row=1,column=2,padx=(10,0));self.inputs.append(probe)
        choices=ttk.Frame(settings);choices.grid(row=2,column=0,columnspan=3,sticky='ew')
        for col,key,var,options in [(0,'model',self.model,['small','medium','large-v3','tiny','base']),
                                    (1,'device',self.device,['cpu','cuda']),
                                    (2,'precision',self.precision,['int8','float16','float32','int8_float16'])]:
            cell=ttk.Frame(choices);cell.grid(row=0,column=col,sticky='w',padx=(0,24))
            self.label(cell,key).pack(anchor='w')
            combo=ttk.Combobox(cell,textvariable=var,values=options,state='readonly',width=17);combo.pack(anchor='w',pady=4)
            self.inputs.append(combo)
            if key=='device':combo.bind('<<ComboboxSelected>>',lambda e:self.precision.set('int8' if self.device.get()=='cpu' else 'float16'))
        check=ttk.Checkbutton(settings,variable=self.complete);self.labels.append((check,'complete'))
        check.grid(row=3,column=0,columnspan=3,sticky='w',pady=(8,5));self.inputs.append(check)
        self.label(settings,'hint',style='Hint.TLabel',wraplength=830).grid(row=4,column=0,columnspan=3,sticky='w')
        ff=ttk.Frame(frame);ff.pack(fill='x')
        self.label(ff,'ffmpeg').pack(side='left',padx=(0,10))
        ffentry=ttk.Entry(ff,textvariable=self.values['ffmpeg']);ffentry.pack(side='left',fill='x',expand=True);self.inputs.append(ffentry)
        ffb=self.button(ff,'browse',self.choose_ffmpeg);ffb.pack(side='left',padx=8);self.inputs.append(ffb)
        self.button(ff,'download',lambda:webbrowser.open('https://ffmpeg.org/download.html')).pack(side='left')
        self.label(frame,'ffhint',style='Hint.TLabel',wraplength=880).pack(anchor='w',pady=(5,10))
        self.label(frame,'first',style='Hint.TLabel',wraplength=880).pack(anchor='w',pady=(0,12))
        actions=ttk.Frame(frame);actions.pack(fill='x')
        self.start=self.button(actions,'start',self.align);self.start.pack(side='left')
        self.cancel_button=self.button(actions,'cancel',self.cancel);self.cancel_button.pack(side='left',padx=8);self.cancel_button.state(['disabled'])
        self.report_button=self.button(actions,'report',lambda:self.open_result('report'));self.report_button.pack(side='right');self.report_button.state(['disabled'])
        self.folder_button=self.button(actions,'folder',lambda:self.open_result('folder'));self.folder_button.pack(side='right',padx=8);self.folder_button.state(['disabled'])
        self.bar=ttk.Progressbar(frame,mode='indeterminate');self.bar.pack(fill='x',pady=(14,8))
        self.status=ttk.Label(frame,wraplength=880);self.status.pack(anchor='w')
        logtop=ttk.Frame(frame);logtop.pack(fill='x',pady=(12,4))
        self.label(logtop,'log').pack(side='left');self.button(logtop,'copy',self.copy_log).pack(side='right')
        logframe=ttk.Frame(frame);logframe.pack(fill='both',expand=True)
        self.log=tk.Text(logframe,height=7,font=('Consolas',9),wrap='word',state='disabled',background='#f5f7fa',relief='flat')
        scroll=ttk.Scrollbar(logframe,command=self.log.yview);self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.log.pack(side='left',fill='both',expand=True)
        self.translate(self.lang)
        root.protocol('WM_DELETE_WINDOW',self.on_close)
        root.after(150,self.poll)

    def t(self,key):return TEXT[self.lang][key]

    def label(self,parent,key,**kwargs):
        widget=ttk.Label(parent,**kwargs);self.labels.append((widget,key));return widget

    def button(self,parent,key,command):
        widget=ttk.Button(parent,command=command);self.labels.append((widget,key));return widget

    def translate(self,lang):
        self.lang=lang
        for widget,key in self.labels:widget.configure(text=self.t(key))
        if not self.runner:self.status.configure(text=self.t('ready'))

    def append(self,text):
        self.log.configure(state='normal');self.log.insert('end',text+'\n');self.log.see('end');self.log.configure(state='disabled')

    def choose(self,key):
        if key=='output':path=filedialog.asksaveasfilename(defaultextension='.srt',filetypes=[('SubRip','*.srt')])
        else:path=filedialog.askopenfilename(filetypes=([('SubRip','*.srt')] if key=='srt' else [('Media','*.mkv *.mp4 *.avi *.mov *.webm *.wav *.mp3 *.m4a'),('All files','*.*')]))
        if not path:return
        self.values[key].set(path)
        if key=='media':
            self.values['output'].set(str(Path(path).with_suffix('.fixed.srt')))
            self.result=None;self.report_button.state(['disabled']);self.folder_button.state(['disabled'])
            self.probe()

    def choose_ffmpeg(self):
        path=filedialog.askdirectory()
        if path:self.values['ffmpeg'].set(path)

    def config(self,action):
        return dict(action=action,media=self.values['media'].get().strip(),subtitle=self.values['srt'].get().strip(),
                    output=self.values['output'].get().strip(),ffmpeg_dir=self.values['ffmpeg'].get().strip(),
                    language=self.spoken.get().strip(),model=self.model.get(),device=self.device.get(),
                    compute_type=self.precision.get(),complete=self.complete.get())

    def busy(self,on):
        for widget in self.inputs:
            if on:widget.state(['disabled'])
            else:widget.state(['!disabled'])
        self.start.state(['disabled'] if on else ['!disabled'])
        self.cancel_button.state(['!disabled'] if on else ['disabled'])
        if on:self.bar.start(12)
        else:self.bar.stop()

    def launch(self,config):
        try:self.runner=JobProcess(config)
        except Exception as error:
            self.append(str(error));messagebox.showerror(self.t('error'),str(error));return
        self.action=config['action'];self.pending_event=None;self.busy(True)
        self.status.configure(text=self.t('probing' if self.action=='probe' else 'running'))

    def probe(self):
        if self.runner:return
        self.probed_media=None;self.streams=[];self.track.set('');self.track.configure(values=[])
        if not Path(self.values['media'].get()).is_file():
            messagebox.showerror(self.t('error'),'Choose an existing video/audio file.');return
        self.launch(self.config('probe'))

    def align(self):
        if self.runner:return
        if self.probed_media != str(Path(self.values['media'].get()).resolve()) or self.track.current()<0:
            messagebox.showinfo(self.t('track'),self.t('need_track'));return
        if not self.spoken.get().strip():
            messagebox.showerror(self.t('error'),'Choose the spoken language.');return
        if self.device.get()=='cpu' and self.precision.get() not in ('int8','float32'):
            messagebox.showerror(self.t('error'),'CPU: choose int8 or float32.');return
        config=self.config('align');config['audio_stream']=self.streams[self.track.current()]['relative_index']
        output=Path(config['output'])
        candidates=[output,output.with_suffix('.alignment.json'),output.with_suffix('.alignment.html')]
        config['overwrite']=False
        if any(p.exists() for p in candidates):
            if not messagebox.askyesno(self.t('replace'),self.t('replace_text')+'\n'+str(output)):return
            config['overwrite']=True
        self.result=None;self.report_button.state(['disabled']);self.folder_button.state(['disabled'])
        self.launch(config)

    def poll(self):
        try:
            if self.runner:
                for event in self.runner.poll():
                    if event['type']=='progress':
                        message=event['message'];self.append(message)
                        key='stage1' if 'pass 1/2' in message else 'stage2' if 'pass 2/2' in message else None
                        if key:self.status.configure(text=self.t(key))
                    else:self.pending_event=event
                if self.runner.finished:
                    # Drain after exit as the last write may follow the preceding read.
                    for event in self.runner.poll():
                        if event['type'] in ('done','error'):self.pending_event=event
                    cancelled=self.runner.cancelled;diagnostic=self.runner.diagnostic()
                    self.runner.close();self.runner=None;self.busy(False)
                    if self.close_when_done:self.root.destroy();return
                    if self.pending_event and self.pending_event['type']=='done':self.done(self.pending_event)
                    elif cancelled:self.status.configure(text=self.t('cancelled'))
                    else:
                        event=self.pending_event or {'message':self.t('failed'),'details':diagnostic}
                        self.status.configure(text=self.t('error'));self.append(event.get('details',event['message']))
                        messagebox.showerror(self.t('error'),event['message'])
        except Exception as error:
            self.append(str(error));self.status.configure(text=self.t('error'))
        self.root.after(150,self.poll)

    def done(self,event):
        if self.action=='probe':
            self.streams=event['streams'];self.probed_media=str(Path(self.values['media'].get()).resolve())
            self.track.configure(values=[f"{s['relative_index']} · {s['language'] or 'und'} · {s['codec']} · {s['channels']} ch · {s['title'] or ''}" for s in self.streams])
            expected={'en':'eng','ru':'rus'}.get(self.spoken.get(),self.spoken.get())
            preferred=next((i for i,s in enumerate(self.streams) if s['language'] in (expected,self.spoken.get())),None)
            if preferred is not None:self.track.current(preferred)
            elif len(self.streams)==1:self.track.current(0)
            self.status.configure(text=self.t('tracks_ready'))
        else:
            self.result=event;s=event['summary']
            message=self.t('result').format(kept=s['output_cues'],total=s['source_cues'],dropped=s['dropped_cues'],inferred=s['inferred_cues'])
            self.status.configure(text=message);self.append(message+'\n'+event['output'])
            self.report_button.state(['!disabled']);self.folder_button.state(['!disabled'])

    def cancel(self):
        if self.runner:self.runner.cancel();self.cancel_button.state(['disabled'])

    def open_result(self,key):
        if not self.result:return
        path=Path(self.result[key])
        try:
            if os.name=='nt':os.startfile(path)
            else:webbrowser.open(path.as_uri())
        except OSError as error:messagebox.showerror(self.t('error'),str(error))

    def copy_log(self):
        self.root.clipboard_clear();self.root.clipboard_append(self.log.get('1.0','end-1c'))

    def on_close(self):
        if self.runner:
            if messagebox.askyesno('Whisper SRT Aligner',self.t('close')):
                self.close_when_done=True;self.cancel()
        else:self.root.destroy()


def main() -> int:
    if len(sys.argv)==4 and sys.argv[1]=='--worker':
        # Windowed frozen programs have no stdout/stderr; provide real log files
        # for third-party progress/logging instead of relying on console handles.
        log=Path(sys.argv[3]).with_suffix('.runtime.log').open('a',encoding='utf-8')
        sys.stdout=log;sys.stderr=log
        from .gui_jobs import worker_main
        return worker_main(sys.argv[2],sys.argv[3])
    root=tk.Tk();App(root);root.mainloop();return 0


if __name__=='__main__':
    raise SystemExit(main())
