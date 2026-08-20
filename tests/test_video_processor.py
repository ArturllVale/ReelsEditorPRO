import pytest
from pathlib import Path
from core.video_processor import build_ffmpeg_command, editar_video

def test_build_ffmpeg_command_basic():
    video_path = Path('/tmp/test_video.mp4')
    output_path = Path('/tmp/output/edited_test_video.mp4')
    config = {
        'enable_mirror': False,
        'enable_overlay': False,
        'texts': [],
        'extra_images': [],
        'codec': 'libx264',
        'bitrate': 'Original',
        'keep_fps': True
    }
    cmd = build_ffmpeg_command(video_path, output_path, config, 1920, 1080, has_audio=True, ffmpeg_exe='ffmpeg')
    assert cmd[0] == 'ffmpeg'
    assert '-i' in cmd
    assert str(video_path) in cmd
    assert '-c:v' in cmd
    assert 'libx264' in cmd
    assert '-preset' in cmd
    assert 'ultrafast' in cmd
    assert '-map' in cmd
    assert str(output_path) in cmd

def test_build_ffmpeg_command_full_effects(tmp_path):
    overlay_img = tmp_path / 'overlay.png'
    overlay_img.write_bytes(b'fake_png')

    extra_img = tmp_path / 'extra.png'
    extra_img.write_bytes(b'fake_png')

    config = {
        'enable_mirror': True,
        'enable_overlay': True,
        'overlay_path': str(overlay_img),
        'overlay_x': 10,
        'overlay_y': 20,
        'overlay_scale': 15,
        'extra_images': [
            {'path': str(extra_img), 'scale': 25, 'pos_x': 30, 'pos_y': 40, 'opacity': 80}
        ],
        'texts': [
            {'content': 'Hello World', 'size': 60, 'color': 'yellow', 'x': 50, 'y': 50, 'opacity': 90, 'shadow': True}
        ],
        'codec': 'h264_nvenc',
        'bitrate': '5000k',
        'keep_fps': False
    }

    cmd = build_ffmpeg_command('/tmp/input.mp4', '/tmp/out.mp4', config, 1080, 1920, has_audio=True, ffmpeg_exe='ffmpeg')

    filter_arg = cmd[cmd.index('-filter_complex') + 1]
    assert 'hflip' in filter_arg
    assert 'scale=162:-1' in filter_arg  # 1080 * 0.15 = 162
    assert 'overlay=x=(W-w)*0.1:y=(H-h)*0.2' in filter_arg
    assert 'colorchannelmixer=aa=0.8' in filter_arg
    assert "drawtext=text='Hello World'" in filter_arg
    assert 'fontsize=60' in filter_arg
    assert 'fontcolor=yellow@0.9' in filter_arg
    assert 'shadowcolor=black@0.9' in filter_arg

    assert '-b:v' in cmd
    assert '5000k' in cmd
    assert '-r' in cmd
    assert '30' in cmd
    assert 'h264_nvenc' in cmd
