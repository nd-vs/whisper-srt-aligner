from multiprocessing import freeze_support
from whisper_srt_aligner.gui import main

if __name__ == '__main__':
    freeze_support()
    raise SystemExit(main())
