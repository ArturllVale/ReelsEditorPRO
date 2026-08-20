import os
import re
import subprocess
from pathlib import Path
import imageio_ffmpeg
from proglog import ProgressBarLogger

from domain.models import Project, ExportSettings
from domain.composition import build_composition_plan, CompositionPlan

def get_video_info(filepath):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg_exe, "-hide_banner", "-i", str(filepath)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    output = res.stderr
    
    duration = 0.0
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", output)
    if duration_match:
        h, m, s = duration_match.groups()
        duration = int(h)*3600 + int(m)*60 + float(s)
        
    w, h = 1920, 1080
    dim_match = re.search(r"Stream.*Video.*?\s(\d+)x(\d+)[\s,]", output)
    if dim_match:
        w = int(dim_match.group(1))
        h = int(dim_match.group(2))
        
    has_audio = "Audio:" in output
    return w, h, duration, has_audio

def build_ffmpeg_command(video_path, output_path, plan: CompositionPlan, export_settings: ExportSettings, has_audio: bool, ffmpeg_exe=None):
    if ffmpeg_exe is None:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    inputs = ["-i", str(video_path)]
    filters = []
    
    curr_video = "[0:v]"
    input_idx = 1
    
    # 1. Mirror
    if plan.enable_mirror:
        filters.append(f"{curr_video}hflip[v_mir]")
        curr_video = "[v_mir]"
        
    # Iterate over elements from the composition plan
    for i, element in enumerate(plan.elements):
        if element.type == "image":
            if os.path.exists(element.content):
                inputs.extend(["-i", element.content])

                # Use pre-calculated values from plan
                scale_w = element.image_width
                x_pct = element.x_pct
                y_pct = element.y_pct
                opacity = element.opacity

                filters.append(f"[{input_idx}:v]scale={scale_w}:-1,format=rgba,colorchannelmixer=aa={opacity}[eimg{input_idx}]")
                filters.append(f"{curr_video}[eimg{input_idx}]overlay=x=(W-w)*{x_pct}:y=(H-h)*{y_pct}[v_eimg{input_idx}]")
                curr_video = f"[v_eimg{input_idx}]"
                input_idx += 1

        elif element.type == "text":
            txt = element.content
            if not txt: continue
            
            f_size = element.font_size
            color = element.color
            opacity = element.opacity
            x_pct = element.x_pct
            y_pct = element.y_pct
            
            # Use fixed font for FFmpeg (Arial is assumed here, but could be dynamic)
            drawtext = f"drawtext=text='{txt}':font='Arial':fontsize={f_size}:fontcolor={color}@{opacity}"
            drawtext += f":x=(w-tw)*{x_pct}:y=(h-th)*{y_pct}"
            
            if element.shadow:
                drawtext += f":shadowcolor=black@{opacity}:shadowx=2:shadowy=2"

            filters.append(f"{curr_video}{drawtext}[v_txt{i}]")
            curr_video = f"[v_txt{i}]"
        
    # Build Final FFmpeg Command
    cmd = [ffmpeg_exe, "-y"]
    cmd.extend(inputs)
    
    if filters:
        cmd.extend(["-filter_complex", ";".join(filters)])
        cmd.extend(["-map", curr_video])
    else:
        cmd.extend(["-map", "0:v"])
        
    if has_audio:
        cmd.extend(["-map", "0:a"])
        cmd.extend(["-c:a", "aac"])
        
    # Codec and presets
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


def editar_video(video_path: str, output_dir: str, config: dict, queue=None):
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_filename = f"edited_{video_path.name}"
    output_path = output_dir / output_filename

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    vid_w, vid_h, duration, has_audio = get_video_info(video_path)

    # Convert dictionary config to Project model and then to CompositionPlan
    project = Project.from_dict(config)
    plan = build_composition_plan(project, vid_w, vid_h)

    cmd = build_ffmpeg_command(video_path, output_path, plan, project.export_settings, has_audio, ffmpeg_exe)
    
    # Run FFmpeg and capture progress
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, universal_newlines=True, encoding='utf-8', errors='ignore')
    time_regex = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    
    for line in process.stderr:
        match = time_regex.search(line)
        if match and duration > 0 and queue:
            h, m, s = match.groups()
            current_time = int(h) * 3600 + int(m) * 60 + float(s)
            pct = min(100, int((current_time / duration) * 100))
            queue.put((video_path.name, pct))
            
    process.wait()
    if process.returncode != 0:
        raise Exception(f"FFmpeg error: {process.stderr.read() if process.stderr else ''}")
        
    if queue:
        queue.put((video_path.name, 100))
        
    return {"status": "success", "file": video_path.name, "output": str(output_path)}
