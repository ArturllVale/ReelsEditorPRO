import pytest
from unittest.mock import patch, MagicMock
from core.hardware_detector import HardwareEncoderDetector

@patch("subprocess.run")
def test_detector_libx264_only(mock_run):
    # Mocking standard CPU support
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = " V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)\n"
    mock_run.return_value = mock_res

    detector = HardwareEncoderDetector(ffmpeg_exe="fake_ffmpeg")
    supported = detector.get_supported_encoders()

    assert "libx264" in supported
    assert "h264_nvenc" not in supported
    assert "h264_amf" not in supported

@patch("subprocess.run")
def test_detector_libx264_and_nvenc(mock_run):
    # Mocking NVIDIA support
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = (
        " V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)\n"
        " V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)\n"
    )
    mock_run.return_value = mock_res

    detector = HardwareEncoderDetector(ffmpeg_exe="fake_ffmpeg")
    supported = detector.get_supported_encoders()

    assert "libx264" in supported
    assert "h264_nvenc" in supported
    assert "h264_amf" not in supported

@patch("subprocess.run")
def test_detector_libx264_and_amf(mock_run):
    # Mocking AMD support
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = (
        " V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)\n"
        " V..... h264_amf             AMD AMF H.264 encoder (codec h264)\n"
    )
    mock_run.return_value = mock_res

    detector = HardwareEncoderDetector(ffmpeg_exe="fake_ffmpeg")
    supported = detector.get_supported_encoders()

    assert "libx264" in supported
    assert "h264_nvenc" not in supported
    assert "h264_amf" in supported

@patch("subprocess.run")
def test_detector_no_encoders_expected(mock_run):
    # Mocking a weird ffmpeg without any of the expected encoders
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = " V..... some_other_codec    Description\n"
    mock_run.return_value = mock_res

    detector = HardwareEncoderDetector(ffmpeg_exe="fake_ffmpeg")
    supported = detector.get_supported_encoders()

    assert supported == []

@patch("subprocess.run")
def test_detector_subprocess_error(mock_run):
    # Mocking command failure (e.g., ffmpeg not found)
    mock_res = MagicMock()
    mock_res.returncode = 127
    mock_run.return_value = mock_res

    detector = HardwareEncoderDetector(ffmpeg_exe="fake_ffmpeg")
    supported = detector.get_supported_encoders()

    assert supported == []

@patch("subprocess.run")
def test_detector_subprocess_exception(mock_run):
    # Mocking python exception during execution
    mock_run.side_effect = Exception("OS Error")

    detector = HardwareEncoderDetector(ffmpeg_exe="fake_ffmpeg")
    supported = detector.get_supported_encoders()

    assert supported == []
