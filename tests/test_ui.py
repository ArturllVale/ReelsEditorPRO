from unittest.mock import patch
import sys
import pytest
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.custom_widgets import VideoGridArea, VideoPlayerCard

@pytest.fixture(scope='session')
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_main_window_config_building(qapp):
    window = MainWindow()
    cfg = window._get_current_config()
    assert 'enable_mirror' in cfg
    assert 'enable_overlay' in cfg
    assert 'overlay_x' in cfg
    assert 'overlay_y' in cfg
    assert 'overlay_scale' in cfg
    assert 'bitrate' in cfg
    assert 'keep_fps' in cfg
    assert 'codec' in cfg
    assert 'texts' in cfg
    assert 'extra_images' in cfg

def test_grid_area_add_clear_videos(qapp, tmp_path):
    grid = VideoGridArea()
    v1 = tmp_path / 'v1.mp4'
    v2 = tmp_path / 'v2.mov'
    v1.write_bytes(b'video1')
    v2.write_bytes(b'video2')

    grid.add_videos([str(v1), str(v2)])
    assert len(grid.cards) == 2
    assert grid.cards[0].video_path == str(v1)
    assert grid.cards[1].video_path == str(v2)

    grid.clear_videos()
    assert len(grid.cards) == 0

def test_card_status_update(qapp, tmp_path):
    v1 = tmp_path / 'v1.mp4'
    v1.write_bytes(b'video1')
    card = VideoPlayerCard(str(v1))

    card.update_status('Concluído')
    assert card.lbl_status.text() == 'Concluído'

    card.update_status('Falha')
    assert card.lbl_status.text() == 'Falha'


def test_debounce_preview_updates(qapp, qtbot):
    with patch.object(MainWindow, '_do_update_previews') as mock_do_update:
        window = MainWindow()
        qtbot.addWidget(window)

        # Simulate multiple rapid property changes
        window.chk_mirror.setChecked(not window.chk_mirror.isChecked())
        window.chk_overlay.setChecked(not window.chk_overlay.isChecked())
        window.spin_overlay_x.setValue(window.spin_overlay_x.value() + 10)
        window.spin_scale.setValue(window.spin_scale.value() + 10)

        # Method should not be called immediately due to debounce
        mock_do_update.assert_not_called()

        # Wait for the timer (75ms) + some margin
        qtbot.wait(150)

        # Method should be called exactly once
        assert mock_do_update.call_count == 1
