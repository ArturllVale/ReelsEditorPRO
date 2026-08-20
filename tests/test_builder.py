from core.video_processor import FFmpegCommandBuilder
from domain.models import Project
from domain.composition import build_composition_plan

def test_builder_creates_correct_command():
    video_path = '/tmp/input.mp4'
    output_path = '/tmp/output.mp4'

    config = {
        'enable_mirror': True,
        'enable_overlay': False,
        'texts': [
            {'content': 'Test Builder', 'size': 50, 'color': 'red', 'x': 10, 'y': 10, 'opacity': 100, 'shadow': False}
        ],
        'extra_images': [],
        'codec': 'libx264',
        'bitrate': '2000k',
        'keep_fps': True
    }

    project = Project.from_dict(config)
    plan = build_composition_plan(project, 1280, 720)

    builder = FFmpegCommandBuilder()
    cmd = builder.build(video_path, output_path, plan, project.export_settings, has_audio=True, ffmpeg_exe='ffmpeg')

    assert cmd[0] == 'ffmpeg'
    assert '-y' in cmd
    assert '-i' in cmd
    assert video_path in cmd

    filter_arg = cmd[cmd.index('-filter_complex') + 1]
    assert 'hflip' in filter_arg
    assert "drawtext=text='Test Builder'" in filter_arg
    assert 'fontcolor=red@1.0' in filter_arg
    assert 'fontsize=' in filter_arg

    assert '-c:v' in cmd
    assert 'libx264' in cmd
    assert '-b:v' in cmd
    assert '2000k' in cmd
    assert output_path in cmd
