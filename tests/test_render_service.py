import pytest
from core.render_service import RenderService
from unittest.mock import patch, MagicMock

@pytest.fixture
def render_service():
    return RenderService()

def test_render_service_batch_success(qtbot, render_service):
    videos = ['video1.mp4', 'video2.mp4', 'video3.mp4']

    with patch('core.render_scheduler.RenderScheduler.start') as mock_start, \
         patch('core.render_scheduler.RenderScheduler.is_finished', return_value=True), \
         patch('core.render_scheduler.RenderScheduler.get_results', return_value=[
             {"status": "success", "file": "video1.mp4"},
             {"status": "success", "file": "video2.mp4"},
             {"status": "error", "file": "video3.mp4"}
         ]):

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
