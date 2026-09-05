import yaml
from pathlib import Path

class Config:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Make sure it points to the correct location relative to the project root
            config_path = Path('.agents/config.yaml')
            if not config_path.exists():
                # Fallback to absolute path or some relative path if called from weird places
                # Try relative to this script
                config_path = Path(__file__).parent.parent.parent.parent.parent / 'config.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    cls._config = yaml.safe_load(f)
            else:
                cls._config = {}
        return cls._instance
    
    def get(self, key_path: str, default=None):
        """يحصل على قيمة بمسار مثل 'audio.voiceover_lufs'"""
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
