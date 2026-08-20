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
