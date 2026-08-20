import os
import re
import subprocess
import json
import logging
from pathlib import Path
import imageio_ffmpeg

from domain.models import Project, ExportSettings, VideoMetadata
from domain.composition import build_composition_plan, CompositionPlan, RenderElement

class MetadataReader:
    def get_info(self, filepath: str, ffmpeg_exe: str = None) -> VideoMetadata:
        try:
            # Try ffprobe first
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(filepath)]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                meta = VideoMetadata()

                # Format level info
                fmt = data.get('format', {})
                if 'duration' in fmt:
                    meta.duration = float(fmt['duration'])

                # Stream level info
                streams = data.get('streams', [])
                for stream in streams:
                    codec_type = stream.get('codec_type')
                    if codec_type == 'video':
                        if 'width' in stream: meta.width = int(stream['width'])
                        if 'height' in stream: meta.height = int(stream['height'])
                        if 'codec_name' in stream: meta.codec = stream['codec_name']

                        # Calculate FPS
                        if 'r_frame_rate' in stream:
                            num, den = stream['r_frame_rate'].split('/')
                            if int(den) > 0:
                                meta.fps = float(num) / float(den)

                        # Handle rotation from tags/side_data
                        tags = stream.get('tags', {})
                        if 'rotate' in tags:
                            meta.rotation = int(tags['rotate'])
                        else:
                            side_data = stream.get('side_data_list', [])
                            for sd in side_data:
                                if sd.get('side_data_type') == 'Display Matrix' and 'rotation' in sd:
                                    # FFprobe side data rotation is sometimes float like "-90.000000"
                                    meta.rotation = int(float(sd['rotation']))
                                    break
                    elif codec_type == 'audio':
                        meta.has_audio = True
                        if 'codec_name' in stream: meta.audio_codec = stream['codec_name']

                return meta
            else:
                logging.warning(f"FFprobe failed with return code {res.returncode}. Falling back to FFmpeg regex parsing.")
        except Exception as e:
            logging.warning(f"Error extracting metadata with FFprobe: {e}. Falling back to FFmpeg regex parsing.")

        # Fallback to FFmpeg regex parsing
        return self._get_info_fallback(filepath, ffmpeg_exe)

    def _get_info_fallback(self, filepath: str, ffmpeg_exe: str = None) -> VideoMetadata:
        if ffmpeg_exe is None:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg_exe, "-hide_banner", "-i", str(filepath)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        output = res.stderr
        
        meta = VideoMetadata()

        duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", output)
        if duration_match:
            h, m, s = duration_match.groups()
            meta.duration = int(h)*3600 + int(m)*60 + float(s)

        dim_match = re.search(r"Stream.*Video.*?\s(\d+)x(\d+)[\s,]", output)
        if dim_match:
            meta.width = int(dim_match.group(1))
            meta.height = int(dim_match.group(2))
        else:
            logging.error(f"Cannot determine video dimensions for {filepath}. Falling back to 1920x1080.")
            meta.width = 1920
            meta.height = 1080

        meta.has_audio = "Audio:" in output
        return meta

class MirrorFilter:
    def apply(self, curr_video: str) -> tuple[str, str]:
        # returns the new curr_video, and the filter string
        return "[v_mir]", f"{curr_video}hflip[v_mir]"

class ImageFilter:
    def apply(self, input_idx: int, element: RenderElement) -> str:
        # Prepares the image stream
        scale_w = element.image_width
        opacity = element.opacity
        return f"[{input_idx}:v]scale={scale_w}:-1,format=rgba,colorchannelmixer=aa={opacity}[eimg{input_idx}]"

class OverlayFilter:
    def apply(self, curr_video: str, input_idx: int, element: RenderElement) -> tuple[str, str]:
        # Applies overlay
        x_pct = element.x_pct
        y_pct = element.y_pct
        out_video = f"[v_eimg{input_idx}]"
        return out_video, f"{curr_video}[eimg{input_idx}]overlay=x=(W-w)*{x_pct}:y=(H-h)*{y_pct}{out_video}"

class TextFilter:
    def apply(self, curr_video: str, filter_idx: int, element: RenderElement) -> tuple[str, str]:
        txt = element.content
        f_size = element.font_size
        color = element.color
        opacity = element.opacity
        x_pct = element.x_pct
        y_pct = element.y_pct
        
        drawtext = f"drawtext=text='{txt}':font='Arial':fontsize={f_size}:fontcolor={color}@{opacity}"
        drawtext += f":x=(w-tw)*{x_pct}:y=(h-th)*{y_pct}"

        if element.shadow:
            drawtext += f":shadowcolor=black@{opacity}:shadowx=2:shadowy=2"

        out_video = f"[v_txt{filter_idx}]"
        return out_video, f"{curr_video}{drawtext}{out_video}"

class InputBuilder:
    def build(self, video_path: str, plan: CompositionPlan) -> tuple[list[str], int]:
        inputs = ["-i", str(video_path)]
        input_idx = 1
        for element in plan.elements:
            if element.type == "image":
                if os.path.exists(element.content):
                    inputs.extend(["-i", element.content])
                    input_idx += 1
        return inputs, input_idx

class FilterBuilder:
    def build(self, plan: CompositionPlan) -> tuple[list[str], str]:
        filters = []
        curr_video = "[0:v]"

        if plan.enable_mirror:
            curr_video, f_str = MirrorFilter().apply(curr_video)
            filters.append(f_str)

        input_idx = 1
        for i, element in enumerate(plan.elements):
            if element.type == "image":
                if os.path.exists(element.content):
                    filters.append(ImageFilter().apply(input_idx, element))
                    curr_video, f_str = OverlayFilter().apply(curr_video, input_idx, element)
                    filters.append(f_str)
                    input_idx += 1
            elif element.type == "text":
                if not element.content:
                    continue
                curr_video, f_str = TextFilter().apply(curr_video, i, element)
                filters.append(f_str)

        return filters, curr_video

class OutputBuilder:
    def build(self, output_path: str, export_settings: ExportSettings, has_audio: bool, filters: list[str], curr_video: str) -> list[str]:
        cmd = []
        if filters:
            cmd.extend(["-filter_complex", ";".join(filters)])
            cmd.extend(["-map", curr_video])
        else:
            cmd.extend(["-map", "0:v"])
            
        if has_audio:
            cmd.extend(["-map", "0:a"])
            cmd.extend(["-c:a", "aac"])
            
        codec = export_settings.codec
        cmd.extend(["-c:v", codec])

        if codec == "libx264":
            cmd.extend(["-preset", "ultrafast"])

        bitrate = export_settings.bitrate
        if bitrate != "Original":
            cmd.extend(["-b:v", bitrate])
            
        if not export_settings.keep_fps:
            cmd.extend(["-r", "30"])

        cmd.append(str(output_path))
        return cmd

class FFmpegCommandBuilder:
    def __init__(self):
        self.input_builder = InputBuilder()
        self.filter_builder = FilterBuilder()
        self.output_builder = OutputBuilder()
        
    def build(self, video_path: str, output_path: str, plan: CompositionPlan, export_settings: ExportSettings, has_audio: bool, ffmpeg_exe: str = None) -> list[str]:
        if ffmpeg_exe is None:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [ffmpeg_exe, "-y"]
        
        inputs, _ = self.input_builder.build(video_path, plan)
        cmd.extend(inputs)
        
        filters, curr_video = self.filter_builder.build(plan)
        
        outputs = self.output_builder.build(output_path, export_settings, has_audio, filters, curr_video)
        cmd.extend(outputs)
        
        return cmd

class ProcessRunner:
    def run(self, cmd: list[str], duration: float, queue, video_name: str, cancel_event=None):
        import threading
        import time
        import subprocess
        import collections
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, universal_newlines=True, encoding='utf-8', errors='ignore')
        time_regex = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        
        def monitor():
            while process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    process.terminate()
                    break
                time.sleep(0.1)

        if cancel_event:
            t = threading.Thread(target=monitor, daemon=True)
            t.start()

        stderr_tail = collections.deque(maxlen=100)

        for line in process.stderr:
            stderr_tail.append(line.rstrip('\n'))
            match = time_regex.search(line)
            if match and duration > 0 and queue:
                h, m, s = match.groups()
                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                pct = min(100, int((current_time / duration) * 100))
                queue.put((video_name, pct))

        process.wait()

        if cancel_event and cancel_event.is_set():
            raise Exception("CANCELLED")

        if process.returncode != 0:
            err_msg = "\n".join(stderr_tail)
            raise Exception(f"FFmpeg error (code {process.returncode}):\n{err_msg}")

        if queue:
            queue.put((video_name, 100))

class VideoProcessor:
    def __init__(self):
        self.metadata_reader = MetadataReader()
        self.command_builder = FFmpegCommandBuilder()
        self.process_runner = ProcessRunner()

    def process(self, video_path: str, output_dir: str, project_or_config, queue=None, cancel_event=None) -> dict:
        video_path_obj = Path(video_path)
        output_dir_obj = Path(output_dir)
        output_filename = f"edited_{video_path_obj.name}"
        output_path = output_dir_obj / output_filename

        if cancel_event and cancel_event.is_set():
            raise Exception("CANCELLED")

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        meta = self.metadata_reader.get_info(str(video_path_obj), ffmpeg_exe)
        vid_w, vid_h, duration, has_audio = meta.width, meta.height, meta.duration, meta.has_audio

        if isinstance(project_or_config, dict):
            project = Project.from_dict(project_or_config)
        else:
            project = project_or_config
        plan = build_composition_plan(project, vid_w, vid_h)

        cmd = self.command_builder.build(str(video_path_obj), str(output_path), plan, project.export_settings, has_audio, ffmpeg_exe)

        self.process_runner.run(cmd, duration, queue, video_path_obj.name, cancel_event)

        return {"status": "success", "file": video_path_obj.name, "output": str(output_path)}

# Maintain original function signatures for backwards compatibility
def get_video_info(filepath):
    return MetadataReader().get_info(filepath)

def build_ffmpeg_command(video_path, output_path, plan: CompositionPlan, export_settings: ExportSettings, has_audio: bool, ffmpeg_exe=None):
    return FFmpegCommandBuilder().build(video_path, output_path, plan, export_settings, has_audio, ffmpeg_exe)

def editar_video(video_path: str, output_dir: str, project_or_config, queue=None, cancel_event=None):
    processor = VideoProcessor()
    return processor.process(video_path, output_dir, project_or_config, queue, cancel_event)

