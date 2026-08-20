import pytest
from core.render_service import RenderService
from unittest.mock import patch

@pytest.fixture
def render_service():
    return RenderService()

from core.render_scheduler import Job, JobStatus

from core.render_scheduler import Job, JobStatus

def test_render_service_batch_success(qtbot, render_service):
    videos = ['video1.mp4', 'video2.mp4', 'video3.mp4']

    # We need to patch get_progress_updates to return mock Jobs since we changed the RenderScheduler interface
    mock_jobs = [
        Job(id="1", input_path="video1.mp4", output_path="", status=JobStatus.COMPLETED, progress=100),
        Job(id="2", input_path="video2.mp4", output_path="", status=JobStatus.COMPLETED, progress=100),
        Job(id="3", input_path="video3.mp4", output_path="", status=JobStatus.FAILED, progress=50),
    ]

    with patch('core.render_scheduler.RenderScheduler.start') as mock_start,          patch('core.render_scheduler.RenderScheduler.is_finished', return_value=True),          patch('core.render_scheduler.RenderScheduler.get_progress_updates', side_effect=[mock_jobs, []]):

        progress_calls = []
        status_calls = []

        render_service.progress_updated.connect(lambda v, p: progress_calls.append((v, p)))
        render_service.video_status_updated.connect(lambda v, s: status_calls.append((v, s)))

        with qtbot.waitSignal(render_service.processing_finished, timeout=1000):
            render_service.start_processing(videos, '/output', {}, 1)
            # Simulate timer timeout calling _check_progress
            render_service._check_progress()

        mock_start.assert_called_once()
        assert len(status_calls) == 3
        assert status_calls[0] == ('video1.mp4', 'Concluído')
        assert status_calls[1] == ('video2.mp4', 'Concluído')
        assert status_calls[2] == ('video3.mp4', 'Falha')

def test_render_service_cancel(qtbot, render_service):
    with patch('core.render_scheduler.RenderScheduler.cancel') as mock_cancel:
        with qtbot.waitSignal(render_service.processing_cancelled, timeout=1000):
            render_service.cancel_processing()

        mock_cancel.assert_called_once()
