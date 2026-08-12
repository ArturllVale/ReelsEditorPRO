import json
import os
from pathlib import Path

class ConfigManager:
    """Gerencia a persistência das configurações da UI em arquivo."""
    
    def __init__(self):
        # Salvar na pasta do usuário ~/.reelseditorpro/
        self.config_dir = Path.home() / ".reelseditorpro"
        self.config_file = self.config_dir / "settings.json"
        self._ensure_dir()
        self.settings = self._load()

    def _ensure_dir(self):
        if not self.config_dir.exists():
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Erro ao criar pasta de config: {e}")

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao ler configs: {e}")
                return self._default_settings()
        return self._default_settings()

    def _default_settings(self):
        return {
            "output_dir": str(Path.home() / "Videos" / "ReelsEditorPRO_Output"),
            "enable_mirror": True,
            "enable_overlay": True,
            "overlay_path": "",
            "overlay_position": "Canto Inferior Direito",
            "overlay_scale": 15,
            "bitrate": "Original",
            "keep_fps": True,
            "num_workers": max(1, os.cpu_count() - 1)
        }

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configs: {e}")
