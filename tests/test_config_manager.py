import os
import json
from pathlib import Path
from utils.config_manager import ConfigManager

def test_config_manager_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    cm = ConfigManager()
    assert cm.get('enable_mirror') is True
    assert cm.get('enable_overlay') is True
    assert cm.get('bitrate') == 'Original'
    assert cm.get('keep_fps') is True
    assert 'ReelsEditorPRO_Output' in cm.get('output_dir')

def test_config_manager_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    cm = ConfigManager()
    cm.set('bitrate', '5000k')
    cm.set('enable_mirror', False)
    cm.save()

    cm2 = ConfigManager()
    assert cm2.get('bitrate') == '5000k'
    assert cm2.get('enable_mirror') is False
