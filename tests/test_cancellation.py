import pytest
from core.render_scheduler import RenderScheduler, JobStatus

@pytest.fixture
def scheduler():
    return RenderScheduler()

def test_cancel_before_start(scheduler):
    scheduler.start(["v1.mp4"], "/tmp", {}, 1)
    scheduler.cancel()
    results = scheduler.get_results()
    assert results[0].status == JobStatus.CANCELLED

def dummy_editar_hang(*args, **kwargs):
    import time
    cancel_event = args[4] # queue is 3, cancel_event is 4
    while not cancel_event.is_set():
        time.sleep(0.1)
    raise Exception("CANCELLED")

def test_cancel_with_jobs_in_queue(scheduler):
    import core.render_scheduler
    original = core.render_scheduler.editar_video
    core.render_scheduler.editar_video = dummy_editar_hang
    try:
        scheduler.start(["v1.mp4", "v2.mp4"], "/tmp", {}, 1)
        # Give it a moment to start
        import time
        time.sleep(0.5)

        scheduler.cancel()
        # Give it a moment to process the cancel
        time.sleep(0.5)

        results = scheduler.get_results()
        assert results[0].status == JobStatus.CANCELLED
        assert results[1].status == JobStatus.CANCELLED
    finally:
        core.render_scheduler.editar_video = original

def test_cancel_during_processing(scheduler):
    import core.render_scheduler
    original = core.render_scheduler.editar_video
    core.render_scheduler.editar_video = dummy_editar_hang
    try:
        scheduler.start(["v1.mp4"], "/tmp", {}, 1)
        # Give it a moment to start
        import time
        time.sleep(0.5)

        scheduler.cancel()
        # Give it a moment to process the cancel
        time.sleep(0.5)

        results = scheduler.get_results()
        assert results[0].status == JobStatus.CANCELLED
    finally:
        core.render_scheduler.editar_video = original

def dummy_editar_success(*args, **kwargs):
    return {"status": "success"}

def test_cancel_with_completed(scheduler):
    import core.render_scheduler
    original = core.render_scheduler.editar_video
    core.render_scheduler.editar_video = dummy_editar_success
    try:
        scheduler.start(["v1.mp4"], "/tmp", {}, 1)
        # Give it a moment to complete
        import time
        time.sleep(0.5)

        # update state
        scheduler.get_progress_updates()

        scheduler.cancel()

        results = scheduler.get_results()
        assert results[0].status == JobStatus.COMPLETED
    finally:
        core.render_scheduler.editar_video = original
