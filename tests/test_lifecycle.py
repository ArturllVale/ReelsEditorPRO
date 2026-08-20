import pytest
from core.render_scheduler import RenderScheduler, JobStatus
import multiprocessing
import time
import core.render_scheduler

def dummy_editar_success(*args, **kwargs):
    return {"status": "success"}

def test_scheduler_lifecycle():
    original = core.render_scheduler.editar_video
    core.render_scheduler.editar_video = dummy_editar_success

    try:
        scheduler = RenderScheduler()

        # Batch 1
        scheduler.start(["v1.mp4", "v2.mp4"], "/tmp", {}, 2)

        assert scheduler.executor is not None
        assert scheduler.manager is not None

        # Wait for completion
        time.sleep(0.5)

        # Process updates
        while not scheduler.is_finished():
            scheduler.get_progress_updates()
            time.sleep(0.1)
        # One final update to process completed futures and trigger cleanup
        scheduler.get_progress_updates()

        results = scheduler.get_results()
        assert len(results) == 2
        assert all(r.status == JobStatus.COMPLETED for r in results)

        # Verify resources are cleaned up
        assert scheduler.executor is None
        assert scheduler.manager is None

        # Batch 2
        scheduler.start(["v3.mp4"], "/tmp", {}, 1)

        assert scheduler.executor is not None
        assert scheduler.manager is not None

        # Wait for completion
        time.sleep(0.5)

        # Process updates
        while not scheduler.is_finished():
            scheduler.get_progress_updates()
            time.sleep(0.1)
        scheduler.get_progress_updates()

        results = scheduler.get_results()
        # Since it's a new batch, it replaces self.jobs, so there is only 1 job
        assert len(results) == 1
        assert results[0].input_path == "v3.mp4"
        assert results[0].status == JobStatus.COMPLETED

        # Verify resources are cleaned up again
        assert scheduler.executor is None
        assert scheduler.manager is None

    finally:
        core.render_scheduler.editar_video = original


def test_scheduler_worker_limits_by_codec():
    original = core.render_scheduler.editar_video
    core.render_scheduler.editar_video = dummy_editar_success

    try:
        scheduler = RenderScheduler()

        # CPU codec: libx264 allows user-configured workers (e.g. 4)
        scheduler.start(["v1.mp4"], "/tmp", {"codec": "libx264"}, 4)
        assert scheduler.executor._max_workers == 4
        scheduler.cancel()

        # GPU NVIDIA codec: h264_nvenc limits max workers to 2
        scheduler.start(["v1.mp4"], "/tmp", {"codec": "h264_nvenc"}, 4)
        assert scheduler.executor._max_workers == 2
        scheduler.cancel()

        # GPU AMD codec: h264_amf limits max workers to 2
        scheduler.start(["v1.mp4"], "/tmp", {"codec": "h264_amf"}, 4)
        assert scheduler.executor._max_workers == 2
        scheduler.cancel()

        # GPU codec with 1 requested worker maintains 1
        scheduler.start(["v1.mp4"], "/tmp", {"codec": "h264_nvenc"}, 1)
        assert scheduler.executor._max_workers == 1
        scheduler.cancel()

    finally:
        core.render_scheduler.editar_video = original
