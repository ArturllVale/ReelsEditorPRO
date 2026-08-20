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
