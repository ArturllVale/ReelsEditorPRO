import subprocess
import imageio_ffmpeg
from typing import List

class HardwareEncoderDetector:
    """
    Verifica quais encoders de H.264 o FFmpeg embarcado realmente suporta.
    O método recomendado e mais confiável do que apenas checar o SO ou a placa,
    pois exige que o próprio FFmpeg tenha sido compilado/equipado para usar.
    """
    def __init__(self, ffmpeg_exe: str = None):
        if ffmpeg_exe is None:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.ffmpeg_exe = ffmpeg_exe

    def get_supported_encoders(self) -> List[str]:
        """
        Retorna uma lista dos encoders suportados entre os requisitados:
        libx264, h264_nvenc, h264_amf.
        """
        try:
            # -hide_banner reduz o tamanho da saida
            # -encoders lista todos encoders.
            cmd = [self.ffmpeg_exe, "-hide_banner", "-encoders"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

            if res.returncode != 0:
                return []

            output = res.stdout

            supported = []

            # Formato de saida do ffmpeg -encoders para video:
            # V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
            # V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
            # V..... h264_amf             AMD AMF H.264 encoder (codec h264)

            # Procuramos os nomes isolados.
            if " libx264 " in output:
                supported.append("libx264")
            if " h264_nvenc " in output:
                supported.append("h264_nvenc")
            if " h264_amf " in output:
                supported.append("h264_amf")

            return supported
        except Exception:
            return []
