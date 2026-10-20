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
from .gui_batch import BatchQueue
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
        'single': 'One file', 'batch': 'Folder / season', 'folder_in': 'Season folder',
        'output_dir': 'Output folder', 'video_glob': 'Video mask', 'subtitle_glob': 'SRT mask',
        'recursive': 'Include subfolders', 'batch_audio': 'Audio selection',
        'auto_audio': 'Match spoken language', 'index_audio': 'Use track index',
        'overwrite_batch': 'Replace existing results (requires confirmation)',
        'scan': 'Check folder', 'preview': 'Show episodes', 'batch_ready': 'Check the folder before starting.',
        'plan': '{ready} ready · {skipped} skipped · {errors} errors / pairing issues',
        'need_scan': 'Check the folder again after changing paths, language or audio settings.',
        'confirm_batch': 'Start {count} episodes? {skipped} existing results and {errors} errors / pairing issues will not run.',
        'confirm_overwrite': 'Existing SRT files and their reports may be replaced. Original inputs are protected.',
        'batch_progress': 'Episode {number}/{total} · {key} · {stage}',
        'batch_done': 'Batch finished: {completed} completed · {failed} failed · {skipped} skipped · {remaining} not run.',
        'episode': 'Episode', 'state': 'Status', 'ready_state': 'Ready', 'skipped_state': 'Existing — skipped',
        'error_state': 'Check failed', 'running_state': 'Running', 'completed_state': 'Completed',
        'failed_state': 'Failed', 'cancelled_state': 'Cancelled', 'issues': 'Pairing issues',
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
        'single': 'Один файл', 'batch': 'Папка / сезон', 'folder_in': 'Папка сезона',
        'output_dir': 'Папка результата', 'video_glob': 'Маска видео', 'subtitle_glob': 'Маска SRT',
        'recursive': 'Включая подпапки', 'batch_audio': 'Выбор аудио',
        'auto_audio': 'По языку речи', 'index_audio': 'По номеру дорожки',
        'overwrite_batch': 'Заменять готовые результаты (с подтверждением)',
        'scan': 'Проверить папку', 'preview': 'Показать серии', 'batch_ready': 'Перед запуском проверьте папку.',
        'plan': 'Готово к запуску: {ready} · пропущено: {skipped} · ошибок / проблем пар: {errors}',
        'need_scan': 'Повторите проверку после изменения путей, языка или настроек аудио.',
        'confirm_batch': 'Запустить {count} серий? Готовых результатов пропущено: {skipped}; ошибок / проблем пар: {errors}.',
        'confirm_overwrite': 'Существующие выходные SRT и их отчёты могут быть заменены. Исходники защищены.',
        'batch_progress': 'Серия {number}/{total} · {key} · {stage}',
        'batch_done': 'Пакет завершён: готово {completed} · ошибок {failed} · пропущено {skipped} · не запущено {remaining}.',
        'episode': 'Серия', 'state': 'Статус', 'ready_state': 'Готово к запуску', 'skipped_state': 'Уже есть — пропуск',
        'error_state': 'Ошибка проверки', 'running_state': 'Обработка', 'completed_state': 'Готово',
        'failed_state': 'Ошибка', 'cancelled_state': 'Отменено', 'issues': 'Проблемы сопоставления',
    },
}


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.lang = 'ru' if (locale.getlocale()[0] or '').lower().startswith('ru') else 'en'
        self.values = {key: tk.StringVar() for key in ('media', 'srt', 'output', 'ffmpeg')}
        self.mode = tk.StringVar(value='single')
        self.batch_values = {key: tk.StringVar(value=value) for key, value in
                             [('folder', ''), ('output_dir', ''), ('video_glob', '*.mkv'),
                              ('subtitle_glob', '*.srt')]}
        self.recursive = tk.BooleanVar(value=False)
        self.overwrite_batch = tk.BooleanVar(value=False)
        self.batch_audio_mode = tk.StringVar(value='auto')
        self.batch_audio_index = tk.StringVar(value='0')
        self.batch_plan = None
        self.batch_signature = None
        self.batch_queue = None
        self.batch_window = None
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
        width = min(1040, root.winfo_screenwidth()-80)
        height = min(920, root.winfo_screenheight()-80)
        root.geometry(f'{width}x{height}'); root.minsize(min(900, width), min(650, height))
        style = ttk.Style(root)
        if 'vista' in style.theme_names(): style.theme_use('vista')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI Semibold', 22))
        style.configure('Hint.TLabel', foreground='#52637b')
        canvas = tk.Canvas(root, highlightthickness=0)
        page_scroll = ttk.Scrollbar(root, orient='vertical', command=canvas.yview)
        page_scroll.pack(side='right', fill='y'); canvas.pack(fill='both', expand=True)
        canvas.configure(yscrollcommand=page_scroll.set)
        frame = ttk.Frame(canvas, padding=24)
        content = canvas.create_window(0, 0, window=frame, anchor='nw')
        def layout(event=None):
            canvas.itemconfigure(content, width=canvas.winfo_width(),
                                 height=max(frame.winfo_reqheight(), canvas.winfo_height()))
            canvas.configure(scrollregion=canvas.bbox('all'))
        frame.bind('<Configure>', layout); canvas.bind('<Configure>', layout)
        def page_wheel(event):
            if isinstance(event.widget, (tk.Text, ttk.Combobox, ttk.Spinbox, ttk.Treeview)):return
            if frame.winfo_height()>canvas.winfo_height():
                canvas.yview_scroll(-int(event.delta/120), 'units')
        root.bind('<MouseWheel>', page_wheel)
        top = ttk.Frame(frame); top.pack(fill='x')
        ttk.Label(top, text='Whisper SRT Aligner', style='Title.TLabel').pack(side='left')
        interface = ttk.Combobox(top, values=['English', 'Русский'], state='readonly', width=12)
        interface.set('Русский' if self.lang == 'ru' else 'English'); interface.pack(side='right')
        interface.bind('<<ComboboxSelected>>', lambda e: self.translate('ru' if interface.get() == 'Русский' else 'en'))
        self.label(frame, 'tagline', style='Hint.TLabel').pack(anchor='w', pady=(2, 18))
        modes = ttk.Frame(frame); modes.pack(fill='x', pady=(0, 8))
        for key in ('single', 'batch'):
            radio = ttk.Radiobutton(modes, variable=self.mode, value=key, command=self.change_mode)
            self.labels.append((radio, key)); radio.pack(side='left', padx=(0, 20)); self.inputs.append(radio)
        self.file_frame = files = ttk.LabelFrame(frame, padding=14)
        self.labels.append((files, 'files')); files.pack(fill='x')
        files.columnconfigure(1, weight=1)
        for row,key in enumerate(('media','srt','output')):
            self.label(files,key).grid(row=row,column=0,sticky='w',padx=(0,12),pady=5)
            entry=ttk.Entry(files,textvariable=self.values[key]); entry.grid(row=row,column=1,sticky='ew',pady=5)
            self.inputs.append(entry)
            button=self.button(files,'browse',lambda k=key:self.choose(k)); button.grid(row=row,column=2,padx=(10,0),pady=5)
            self.inputs.append(button)
        self.batch_frame = ttk.LabelFrame(frame, padding=10)
        self.labels.append((self.batch_frame, 'batch'))
        self.build_batch_controls()
        settings=ttk.LabelFrame(frame,padding=14); self.labels.append((settings,'settings')); settings.pack(fill='x',pady=14)
        self.settings_frame = settings
        settings.columnconfigure(1,weight=1)
        self.label(settings,'spoken').grid(row=0,column=0,sticky='w',padx=(0,12))
        spoken=ttk.Combobox(settings,textvariable=self.spoken,values=['en','ru','es','fr','de','it','pt','ja','zh'],width=8)
        spoken.grid(row=0,column=1,sticky='w');self.inputs.append(spoken)
        self.track_label = self.label(settings,'track'); self.track_label.grid(row=1,column=0,sticky='w',pady=9)
        self.track=ttk.Combobox(settings,state='readonly');self.track.grid(row=1,column=1,sticky='ew',pady=9)
        self.inputs.append(self.track)
        probe=self.button(settings,'inspect',self.probe);probe.grid(row=1,column=2,padx=(10,0));self.inputs.append(probe)
        self.probe_button = probe
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
        if not self.runner and not self.batch_queue:self.status.configure(text=self.t('batch_ready' if self.mode.get()=='batch' else 'ready'))
        if hasattr(self, 'batch_audio_combo'):
            self.batch_audio_combo.configure(values=[self.t('auto_audio'), self.t('index_audio')])
            self.batch_audio_combo.current(1 if self.batch_audio_mode.get()=='index' else 0)
        self.refresh_batch_preview()

    def append(self,text):
        self.log.configure(state='normal');self.log.insert('end',text+'\n');self.log.see('end');self.log.configure(state='disabled')

    def build_batch_controls(self):
        frame = self.batch_frame
        frame.columnconfigure(1, weight=1)
        for row, key, label in [(0, 'folder', 'folder_in'), (1, 'output_dir', 'output_dir')]:
            self.label(frame, label).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=3)
            entry = ttk.Entry(frame, textvariable=self.batch_values[key])
            entry.grid(row=row, column=1, sticky='ew'); self.inputs.append(entry)
            button = self.button(frame, 'browse', lambda k=key: self.choose_batch_folder(k))
            button.grid(row=row, column=2, padx=(8, 0)); self.inputs.append(button)
        masks = ttk.Frame(frame); masks.grid(row=2, column=0, columnspan=3, sticky='ew', pady=5)
        for key in ('video_glob', 'subtitle_glob'):
            self.label(masks, key).pack(side='left', padx=(0, 6))
            entry = ttk.Entry(masks, textvariable=self.batch_values[key], width=18)
            entry.pack(side='left', padx=(0, 15)); self.inputs.append(entry)
        recursive = ttk.Checkbutton(masks, variable=self.recursive)
        self.labels.append((recursive, 'recursive')); recursive.pack(side='left'); self.inputs.append(recursive)
        audio = ttk.Frame(frame); audio.grid(row=3, column=0, columnspan=3, sticky='ew', pady=3)
        self.label(audio, 'batch_audio').pack(side='left', padx=(0, 10))
        self.batch_audio_combo = ttk.Combobox(audio, state='readonly', width=24)
        self.batch_audio_combo.pack(side='left'); self.inputs.append(self.batch_audio_combo)
        self.batch_audio_combo.bind('<<ComboboxSelected>>', self.change_batch_audio)
        index = ttk.Spinbox(audio, from_=0, to=99, width=4, textvariable=self.batch_audio_index)
        index.pack(side='left', padx=8); self.inputs.append(index)
        self.batch_index_widget = index
        index.state(['disabled'])
        overwrite = ttk.Checkbutton(frame, variable=self.overwrite_batch)
        self.labels.append((overwrite, 'overwrite_batch'))
        overwrite.grid(row=4, column=0, columnspan=3, sticky='w', pady=3); self.inputs.append(overwrite)
        actions = ttk.Frame(frame); actions.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(5, 0))
        scan = self.button(actions, 'scan', self.scan_batch); scan.pack(side='left'); self.inputs.append(scan)
        self.button(actions, 'preview', self.show_batch_preview).pack(side='left', padx=8)
        self.batch_summary = ttk.Label(actions); self.batch_summary.pack(side='left')

    def change_mode(self):
        batch = self.mode.get() == 'batch'
        self.file_frame.pack_forget(); self.batch_frame.pack_forget()
        (self.batch_frame if batch else self.file_frame).pack(fill='x', before=self.settings_frame)
        for widget in (self.track_label, self.track, self.probe_button):
            widget.grid_remove() if batch else widget.grid()
        self.status.configure(text=self.t('batch_ready' if batch else 'ready'))

    def change_batch_audio(self, event=None):
        self.batch_audio_mode.set('index' if self.batch_audio_combo.current()==1 else 'auto')
        self.batch_index_widget.state(['!disabled'] if self.batch_audio_mode.get()=='index' else ['disabled'])

    def choose_batch_folder(self, key):
        path = filedialog.askdirectory(mustexist=(key=='folder'))
        if path:
            self.batch_values[key].set(path)
            if key == 'folder':self.batch_values['output_dir'].set(str(Path(path)/'aligned'))

    def batch_config(self):
        return dict(**{key: var.get().strip() for key, var in self.batch_values.items()},
                    recursive=self.recursive.get(), overwrite=self.overwrite_batch.get(),
                    batch_audio_mode=self.batch_audio_mode.get(), batch_audio_index=self.batch_audio_index.get(),
                    language=self.spoken.get().strip(), ffmpeg_dir=self.values['ffmpeg'].get().strip())

    def scan_batch(self):
        if self.runner or self.batch_queue:return
        if self.batch_values['folder'].get().strip() and not self.batch_values['output_dir'].get().strip():
            self.batch_values['output_dir'].set(str(Path(self.batch_values['folder'].get().strip())/'aligned'))
        config = self.batch_config()
        if not config['language']:
            messagebox.showerror(self.t('error'), 'Choose the spoken language.'); return
        self.batch_plan = None; self.batch_signature = None
        self.refresh_batch_preview()
        self.scanning_config = config
        self.launch(dict(config, action='scan_batch'))

    def refresh_batch_preview(self):
        if not hasattr(self, 'batch_summary'):return
        items = self.batch_queue.items if self.batch_queue else (self.batch_plan or {}).get('items', [])
        issues = (self.batch_plan or {}).get('issues', [])
        if self.batch_plan:
            self.batch_summary.configure(text=self.t('plan').format(
                ready=sum(i['state']=='ready' for i in items), skipped=sum(i['state']=='skipped' for i in items),
                errors=sum(i['state'] in ('error', 'failed') for i in items)+len(issues)))
        else:self.batch_summary.configure(text='')
        if not self.batch_window or not self.batch_window.winfo_exists():return
        tree = self.batch_tree
        selected = tree.selection()
        tree.delete(*tree.get_children())
        for index, item in enumerate(items):
            tree.insert('', 'end', iid=str(index), values=(item['key'], Path(item['media']).name,
                        Path(item['subtitle']).name, item['audio'], self.t(item['state']+'_state')))
        for column, key in [('episode','episode'), ('media','media'), ('subtitle','srt'), ('audio','track'), ('state','state')]:
            tree.heading(column, text=self.t(key))
        if selected and tree.exists(selected[0]):tree.selection_set(selected[0])
        self.batch_issues.configure(state='normal');self.batch_issues.delete('1.0', 'end')
        if issues:
            self.batch_issues.insert('end', self.t('issues')+':\n'+'\n'.join(issues))
            self.batch_issues.pack(fill='x')
        else:self.batch_issues.pack_forget()
        self.batch_issues.configure(state='disabled')

    def show_batch_preview(self):
        if not self.batch_plan:return
        if self.batch_window and self.batch_window.winfo_exists():
            self.batch_window.lift(); return
        window = self.batch_window = tk.Toplevel(self.root)
        window.title(self.t('batch')); window.geometry('1120x480'); window.minsize(800, 350)
        frame = ttk.Frame(window, padding=12); frame.pack(fill='both', expand=True)
        columns = ('episode', 'media', 'subtitle', 'audio', 'state')
        self.batch_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        for column, width in zip(columns, (75, 260, 260, 230, 170)):
            self.batch_tree.column(column, width=width, minwidth=60)
        scroll = ttk.Scrollbar(frame, orient='horizontal', command=self.batch_tree.xview)
        vertical = ttk.Scrollbar(frame, orient='vertical', command=self.batch_tree.yview)
        self.batch_tree.configure(xscrollcommand=scroll.set, yscrollcommand=vertical.set)
        vertical.pack(side='right', fill='y'); self.batch_tree.pack(fill='both', expand=True)
        scroll.pack(fill='x')
        self.batch_detail = ttk.Label(frame, wraplength=1050); self.batch_detail.pack(anchor='w', pady=8)
        self.batch_issues = tk.Text(frame, height=4, wrap='word', state='disabled', font=('Segoe UI', 10))
        def details(event):
            selection = self.batch_tree.selection()
            if not selection:return
            items = self.batch_queue.items if self.batch_queue else self.batch_plan['items']
            item = items[int(selection[0])]
            self.batch_detail.configure(text='\n'.join([item['media'], item['subtitle'], item['output'], item['message']]))
        self.batch_tree.bind('<<TreeviewSelect>>', details)
        self.refresh_batch_preview()

    def start_batch(self):
        if not self.batch_plan or self.batch_signature != self.batch_config():
            messagebox.showinfo(self.t('batch'), self.t('need_scan'));return
        queue = BatchQueue(self.batch_plan['items'])
        if not queue.total:
            self.show_batch_preview();return
        counts = queue.counts
        prompt = self.t('confirm_batch').format(count=queue.total, skipped=counts['skipped'],
                                               errors=counts['error']+len(self.batch_plan['issues']))
        if self.overwrite_batch.get():prompt += '\n\n'+self.t('confirm_overwrite')
        if not messagebox.askyesno(self.t('batch'), prompt):return
        self.batch_queue = queue
        self.batch_options = self.config('align')
        self.batch_options['overwrite'] = self.overwrite_batch.get()
        self.batch_last_result = None
        self.result = None;self.report_button.state(['disabled']);self.folder_button.state(['disabled'])
        self.busy(True);self.next_batch_episode()

    def next_batch_episode(self):
        queue = self.batch_queue
        if queue is None:return
        item = queue.next()
        if item is None:
            counts = queue.counts
            self.bar['value'] = counts['completed']+counts['failed']
            message = self.t('batch_done').format(completed=counts['completed'], failed=counts['failed']+counts['error']+len(self.batch_plan['issues']),
                       skipped=counts['skipped'], remaining=counts['ready']+counts['cancelled'])
            self.batch_plan['items'] = queue.items
            self.batch_queue = None;self.busy(False)
            self.status.configure(text=message);self.append(message)
            if self.batch_last_result:
                self.result = self.batch_last_result
                self.report_button.state(['!disabled']);self.folder_button.state(['!disabled'])
            self.refresh_batch_preview()
            if self.close_when_done:self.root.destroy()
            return
        self.append(f"{item['key']}: {item['media']}\n{item['subtitle']} → {item['output']}\n{item['audio']}")
        config = {**self.batch_options, **{key: item[key] for key in ('media','subtitle','output','audio_stream')}}
        if not self.launch(config):
            queue.finish('failed', self.last_launch_error)
            self.root.after(0, self.next_batch_episode)
        self.refresh_batch_preview()

    def batch_stage(self, stage):
        queue = self.batch_queue
        if queue and queue.active is not None:
            counts = queue.counts
            return self.t('batch_progress').format(number=counts['completed']+counts['failed']+1,
                   total=queue.total, key=queue.items[queue.active]['key'], stage=stage)
        return stage

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
        self.batch_index_widget.state(['disabled'] if on or self.batch_audio_mode.get()!='index' else ['!disabled'])
        if str(self.bar.cget('mode'))=='indeterminate':self.bar.stop()
        if on and self.batch_queue:
            self.bar.configure(mode='determinate', maximum=max(1, self.batch_queue.total))
            counts = self.batch_queue.counts
            self.bar['value'] = counts['completed']+counts['failed']
        elif on:
            self.bar.configure(mode='indeterminate', maximum=100, value=0);self.bar.start(12)

    def launch(self,config):
        try:self.runner=JobProcess(config)
        except Exception as error:
            self.last_launch_error = str(error)
            self.append(str(error))
            if not self.batch_queue:messagebox.showerror(self.t('error'),str(error))
            return False
        self.action=config['action'];self.pending_event=None;self.busy(True)
        self.status.configure(text=self.batch_stage(self.t('probing' if self.action in ('probe','scan_batch') else 'running')))
        return True

    def probe(self):
        if self.runner:return
        self.probed_media=None;self.streams=[];self.track.set('');self.track.configure(values=[])
        if not Path(self.values['media'].get()).is_file():
            messagebox.showerror(self.t('error'),'Choose an existing video/audio file.');return
        self.launch(self.config('probe'))

    def align(self):
        if self.runner:return
        if self.device.get()=='cpu' and self.precision.get() not in ('int8','float32'):
            messagebox.showerror(self.t('error'),'CPU: choose int8 or float32.');return
        if self.mode.get()=='batch':
            self.start_batch();return
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
                        if key:self.status.configure(text=self.batch_stage(self.t(key)))
                    else:self.pending_event=event
                if self.runner.finished:
                    # Drain after exit as the last write may follow the preceding read.
                    for event in self.runner.poll():
                        if event['type'] in ('done','error'):self.pending_event=event
                    cancelled=self.runner.cancelled;diagnostic=self.runner.diagnostic()
                    self.runner.close();self.runner=None
                    if self.close_when_done:self.root.destroy();return
                    if self.batch_queue:
                        event = self.pending_event
                        if event and event['type']=='done':
                            self.batch_last_result = event
                            self.batch_queue.finish('completed')
                            self.append(event['output'])
                        elif cancelled:
                            self.batch_queue.finish('cancelled')
                        else:
                            message = (event or {}).get('message', self.t('failed'))
                            self.batch_queue.finish('failed', message)
                            self.append((event or {}).get('details', diagnostic or message))
                        self.refresh_batch_preview()
                        self.next_batch_episode()
                    elif self.pending_event and self.pending_event['type']=='done':
                        self.busy(False);self.done(self.pending_event)
                    elif cancelled:self.status.configure(text=self.t('cancelled'))
                    else:
                        event=self.pending_event or {'message':self.t('failed'),'details':diagnostic}
                        self.status.configure(text=self.t('error'));self.append(event.get('details',event['message']))
                        messagebox.showerror(self.t('error'),event['message'])
                    if not self.batch_queue and not self.runner:self.busy(False)
        except Exception as error:
            self.append(str(error));self.status.configure(text=self.t('error'))
        self.root.after(150,self.poll)

    def done(self,event):
        if self.action=='scan_batch':
            self.batch_plan = event
            self.batch_signature = self.scanning_config
            self.refresh_batch_preview();self.show_batch_preview()
            self.status.configure(text=self.batch_summary.cget('text'))
            for issue in event['issues']:self.append(issue)
        elif self.action=='probe':
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
        if self.batch_queue:self.batch_queue.stop()
        if self.runner:self.runner.cancel();self.cancel_button.state(['disabled'])
        elif self.batch_queue:self.next_batch_episode()

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
        if self.runner or self.batch_queue:
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
