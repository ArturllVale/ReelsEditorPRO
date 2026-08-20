import time
import pytest
from workers.processing_worker import ProcessingWorker

def test_processing_worker_batch_success(qtbot):
    def mock_success(video_path, output_dir, config):
        return {'status': 'success', 'file': video_path, 'output': '/out/' + video_path}

    videos = ['video1.mp4', 'video2.mp4', 'video3.mp4']
    worker = ProcessingWorker(videos, '/output', {}, num_workers=1)

    logs = []
    statuses = []
    finished = []

    worker.log_signal.connect(lambda msg, lvl: logs.append((msg, lvl)))
    worker.video_status_signal.connect(lambda v, s: statuses.append((v, s)))
    worker.finished_signal.connect(lambda: finished.append(True))

    with qtbot.waitSignal(worker.finished_signal, timeout=5000):
        worker.start()

    assert len(finished) == 1
    assert worker._cancelar is False

def test_processing_worker_cancel(qtbot):
    videos = ['v1.mp4', 'v2.mp4']
    worker = ProcessingWorker(videos, '/output', {}, num_workers=1)
    worker.cancelar()
    assert worker._cancelar is True
