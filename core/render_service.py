import multiprocessing
from PySide6.QtCore import QObject, Signal, QTimer
from pathlib import Path
from core.render_scheduler import RenderScheduler

class RenderService(QObject):
    progress_updated = Signal(str, int) # video_name, percentage
    log_updated = Signal(dict) # video_progress dict
    video_status_updated = Signal(str, str) # video_name, status (Concluído/Falha)
    processing_finished = Signal()
    processing_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.scheduler = RenderScheduler()
        self.manager = multiprocessing.Manager()
        self.progress_queue = self.manager.Queue()
        self.video_progress = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_progress)

    def start_processing(self, videos, output_dir, config, num_workers):
        self.video_progress.clear()
        for video_path in videos:
            name = Path(video_path).name
            self.video_progress[name] = 0

        self.scheduler.start(videos, output_dir, config, self.progress_queue, num_workers)
        self.timer.start(500)

    def cancel_processing(self):
        self.scheduler.cancel()
        self.timer.stop()
        self.processing_cancelled.emit()

    def _check_progress(self):
        updated = False
        while not self.progress_queue.empty():
            try:
                vid_name, pct = self.progress_queue.get_nowait()
                self.video_progress[vid_name] = pct
                self.progress_updated.emit(vid_name, pct)
                updated = True
            except:
                break

        if updated:
            self.log_updated.emit(self.video_progress.copy())

        if self.scheduler.is_finished():
            # Process remaining items in queue just in case
            while not self.progress_queue.empty():
                try:
                    vid_name, pct = self.progress_queue.get_nowait()
                    self.video_progress[vid_name] = pct
                    self.progress_updated.emit(vid_name, pct)
                except:
                    break

            # Update final status from results
            results = self.scheduler.get_results()
            for res in results:
                if res and res.get("status") == "success":
                    self.video_status_updated.emit(res["file"], "Concluído")
                elif res:
                    self.video_status_updated.emit(res.get("file", "Desconhecido"), "Falha")

            self.timer.stop()
            self.processing_finished.emit()
