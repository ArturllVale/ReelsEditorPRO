from unittest.mock import patch, MagicMock
from core.video_processor import MetadataReader
from domain.models import VideoMetadata
import json

def test_metadata_reader_ffprobe_success():
    reader = MetadataReader()

    mock_ffprobe_output = json.dumps({
        "format": {
            "duration": "10.5"
        },
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "codec_name": "h264",
                "r_frame_rate": "60000/1001",
                "tags": {
                    "rotate": "90"
                }
            },
            {
                "codec_type": "audio",
                "codec_name": "aac"
            }
        ]
    })

    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_ffprobe_output
        mock_run.return_value = mock_result

        meta = reader.get_info("test.mp4")

        assert isinstance(meta, VideoMetadata)
        assert meta.width == 1920
        assert meta.height == 1080
        assert meta.duration == 10.5
        assert meta.fps == 60000 / 1001
        assert meta.codec == "h264"
        assert meta.has_audio is True
        assert meta.audio_codec == "aac"
        assert meta.rotation == 90

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'ffprobe'

def test_metadata_reader_ffprobe_side_data_rotation():
    reader = MetadataReader()

    mock_ffprobe_output = json.dumps({
        "format": {
            "duration": "5.0"
        },
        "streams": [
            {
                "codec_type": "video",
                "width": 1280,
                "height": 720,
                "side_data_list": [
                    {
                        "side_data_type": "Display Matrix",
                        "rotation": "-90.000000"
                    }
                ]
            }
        ]
    })

    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_ffprobe_output
        mock_run.return_value = mock_result

        meta = reader.get_info("test.mp4")

        assert meta.width == 1280
        assert meta.height == 720
        assert meta.rotation == -90
        assert meta.has_audio is False

def test_metadata_reader_ffprobe_failure_fallback():
    reader = MetadataReader()

    mock_ffmpeg_output = "Duration: 00:01:30.50, start: 0.000000, bitrate: 1000 kb/s\nStream #0:0(und): Video: h264 (Main) (avc1 / 0x31637661), yuv420p(tv, bt709), 1920x1080 [SAR 1:1 DAR 16:9], 1000 kb/s, 30 fps, 30 tbr, 15360 tbn, 60 tbc (default)\nAudio: aac"

    def side_effect(cmd, **kwargs):
        if cmd[0] == 'ffprobe':
            res = MagicMock()
            res.returncode = 1
            return res
        else:
            res = MagicMock()
            res.returncode = 0
            res.stderr = mock_ffmpeg_output
            return res

    with patch('subprocess.run', side_effect=side_effect) as mock_run:
        with patch('imageio_ffmpeg.get_ffmpeg_exe', return_value='ffmpeg'):
            meta = reader.get_info("test.mp4")

            assert meta.width == 1920
            assert meta.height == 1080
            assert meta.duration == 90.5
            assert meta.has_audio is True
            assert mock_run.call_count == 2
