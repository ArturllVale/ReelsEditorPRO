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
        self.video_progress = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_progress)

    def start_processing(self, videos, output_dir, config, num_workers):
        self.video_progress.clear()
        for video_path in videos:
            name = Path(video_path).name
            self.video_progress[name] = 0

        # Start now doesn't need to take the self.progress_queue, it creates its own internally
        self.scheduler.start(videos, output_dir, config, num_workers)
        self.timer.start(500)

    def cancel_processing(self):
        self.scheduler.cancel()
        self.timer.stop()
        self.processing_cancelled.emit()

    def _check_progress(self):
        updated_jobs = self.scheduler.get_progress_updates()

        has_updates = False
        for job in updated_jobs:
            # We map Job to video name for backwards compatibility in UI signals
            vid_name = Path(job.input_path).name

            # Emit progress only if it changes or job reaches completion
            if self.video_progress.get(vid_name) != job.progress:
                self.video_progress[vid_name] = job.progress
                self.progress_updated.emit(vid_name, job.progress)
                has_updates = True

            # If job failed or completed, emit status update
            # We check the enum values
            if job.status.value == "COMPLETED":
                self.video_status_updated.emit(vid_name, "Concluído")
            elif job.status.value == "FAILED":
                self.video_status_updated.emit(vid_name, "Falha")

        if has_updates:
            self.log_updated.emit(self.video_progress.copy())

        if self.scheduler.is_finished():
            # Get any final remaining updates
            final_updates = self.scheduler.get_progress_updates()
            for job in final_updates:
                vid_name = Path(job.input_path).name
                self.video_progress[vid_name] = job.progress
                self.progress_updated.emit(vid_name, job.progress)
                if job.status.value == "COMPLETED":
                    self.video_status_updated.emit(vid_name, "Concluído")
                elif job.status.value == "FAILED":
                    self.video_status_updated.emit(vid_name, "Falha")

            self.timer.stop()
            self.processing_finished.emit()
