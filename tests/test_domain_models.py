import pytest
from PySide6.QtWidgets import QApplication
from domain.models import (
    Media,
    Composition,
    OverlayLayer,
    ImageLayer,
    TextLayer,
    Layers,
    ExportSettings,
    Project,
)
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_default_project_creation():
    project = Project()
    assert isinstance(project.media, Media)
    assert isinstance(project.composition, Composition)
    assert isinstance(project.layers, Layers)
    assert isinstance(project.export_settings, ExportSettings)

    assert project.composition.enable_mirror is True
    assert project.layers.overlay.enabled is True
    assert project.layers.overlay.scale == 15
    assert project.export_settings.bitrate == "Original"
    assert project.export_settings.codec == "libx264"
    assert project.export_settings.keep_fps is True


def test_project_to_config_dict():
    project = Project(
        media=Media(paths=["video1.mp4", "video2.mp4"]),
        composition=Composition(enable_mirror=False),
        layers=Layers(
            overlay=OverlayLayer(
                enabled=True,
                path="/tmp/overlay.png",
                pos_x=10,
                pos_y=20,
                scale=25,
            ),
            extra_images=[
                ImageLayer(
                    path="/tmp/extra.png",
                    scale=30,
                    pos_x=15,
                    pos_y=25,
                    opacity=80,
                )
            ],
            texts=[
                TextLayer(
                    content="Test Title",
                    size=60,
                    color="yellow",
                    pos_x=50,
                    pos_y=70,
                    opacity=90,
                    shadow=True,
                )
            ],
        ),
        export_settings=ExportSettings(
            output_dir="/tmp/output",
            bitrate="5000k",
            codec="h264_nvenc",
            keep_fps=False,
            num_workers=4,
        ),
    )

    cfg = project.to_config_dict()

    assert cfg["enable_mirror"] is False
    assert cfg["enable_overlay"] is True
    assert cfg["overlay_path"] == "/tmp/overlay.png"
    assert cfg["overlay_x"] == 10
    assert cfg["overlay_y"] == 20
    assert cfg["overlay_scale"] == 25
    assert cfg["bitrate"] == "5000k"
    assert cfg["keep_fps"] is False
    assert cfg["codec"] == "h264_nvenc"
    assert cfg["output_dir"] == "/tmp/output"
    assert cfg["num_workers"] == 4

    assert len(cfg["extra_images"]) == 1
    assert cfg["extra_images"][0] == {
        "path": "/tmp/extra.png",
        "scale": 30,
        "pos_x": 15,
        "pos_y": 25,
        "opacity": 80,
    }

    assert len(cfg["texts"]) == 1
    assert cfg["texts"][0] == {
        "content": "Test Title",
        "size": 60,
        "color": "yellow",
        "x": 50,
        "y": 70,
        "opacity": 90,
        "shadow": True,
    }


def test_project_from_dict():
    raw_dict = {
        "enable_mirror": False,
        "enable_overlay": True,
        "overlay_path": "/tmp/overlay.png",
        "overlay_x": 5,
        "overlay_y": 10,
        "overlay_scale": 20,
        "bitrate": "8000k",
        "keep_fps": True,
        "codec": "libx264",
        "output_dir": "/tmp/out",
        "num_workers": 2,
        "extra_images": [
            {"path": "/tmp/extra.png", "scale": 15, "pos_x": 40, "pos_y": 60, "opacity": 100}
        ],
        "texts": [
            {"content": "Caption", "size": 40, "color": "red", "x": 30, "y": 80, "opacity": 100, "shadow": False}
        ],
    }

    project = Project.from_dict(raw_dict)

    assert project.composition.enable_mirror is False
    assert project.layers.overlay.enabled is True
    assert project.layers.overlay.path == "/tmp/overlay.png"
    assert project.layers.overlay.pos_x == 5
    assert project.layers.overlay.pos_y == 10
    assert project.layers.overlay.scale == 20

    assert len(project.layers.extra_images) == 1
    img = project.layers.extra_images[0]
    assert img.path == "/tmp/extra.png"
    assert img.scale == 15
    assert img.pos_x == 40
    assert img.pos_y == 60
    assert img.opacity == 100

    assert len(project.layers.texts) == 1
    txt = project.layers.texts[0]
    assert txt.content == "Caption"
    assert txt.size == 40
    assert txt.color == "red"
    assert txt.pos_x == 30
    assert txt.pos_y == 80
    assert txt.opacity == 100
    assert txt.shadow is False

    assert project.export_settings.output_dir == "/tmp/out"
    assert project.export_settings.bitrate == "8000k"
    assert project.export_settings.codec == "libx264"
    assert project.export_settings.keep_fps is True
    assert project.export_settings.num_workers == 2


def test_project_dict_roundtrip():
    original = Project(
        media=Media(paths=["v1.mp4"]),
        composition=Composition(enable_mirror=True),
        layers=Layers(
            overlay=OverlayLayer(enabled=True, path="overlay.png", pos_x=12, pos_y=34, scale=56),
            extra_images=[ImageLayer(path="extra.png", scale=10, pos_x=20, pos_y=30, opacity=90)],
            texts=[TextLayer(content="Hello", size=45, color="white", pos_x=50, pos_y=50, opacity=100, shadow=True)],
        ),
        export_settings=ExportSettings(
            output_dir="/out",
            bitrate="3000k",
            codec="libx264",
            keep_fps=True,
            num_workers=2,
        ),
    )

    d = original.to_config_dict()
    reconstructed = Project.from_dict(d)

    assert reconstructed.composition.enable_mirror == original.composition.enable_mirror
    assert reconstructed.layers.overlay == original.layers.overlay
    assert reconstructed.layers.extra_images == original.layers.extra_images
    assert reconstructed.layers.texts == original.layers.texts
    assert reconstructed.export_settings.output_dir == original.export_settings.output_dir
    assert reconstructed.export_settings.bitrate == original.export_settings.bitrate
    assert reconstructed.export_settings.codec == original.export_settings.codec
    assert reconstructed.export_settings.keep_fps == original.export_settings.keep_fps
    assert reconstructed.export_settings.num_workers == original.export_settings.num_workers


def test_project_from_ui(qapp):
    window = MainWindow()
    project = Project.from_ui(window)

    assert isinstance(project, Project)
    assert project.composition.enable_mirror == window.chk_mirror.isChecked()
    assert project.layers.overlay.enabled == window.chk_overlay.isChecked()
    assert project.export_settings.bitrate == window.cmb_bitrate.currentText()
    assert project.export_settings.keep_fps == window.chk_fps.isChecked()


def test_export_settings_codecs_and_acceleration():
    s_cpu = ExportSettings(codec="libx264")
    s_nv = ExportSettings(codec="h264_nvenc")
    s_amf = ExportSettings(codec="h264_amf")

    assert s_cpu.acceleration_type == "CPU"
    assert s_nv.acceleration_type == "NVIDIA"
    assert s_amf.acceleration_type == "AMD"

    assert not s_cpu.is_gpu_codec()
    assert s_nv.is_gpu_codec()
    assert s_amf.is_gpu_codec()

    assert not ExportSettings.is_gpu_codec("libx264")
    assert ExportSettings.is_gpu_codec("h264_nvenc")
    assert ExportSettings.is_gpu_codec("h264_amf")

    assert ExportSettings.MAX_GPU_WORKERS == 2
