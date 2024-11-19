import json
import os
import logging
from threading import Lock

class ConfigManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, config_path='config.json'):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._config_path = config_path
                cls._instance._load_config()
            return cls._instance

    def _load_config(self):
        if not os.path.exists(self._config_path):
            logging.error(f"Configuration file not found at {self._config_path}")
            raise FileNotFoundError(f"Configuration file not found at {self._config_path}")

        with open(self._config_path, 'r') as f:
            try:
                self._config = json.load(f)
                logging.debug(f"Configuration loaded: {self._config}")
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON from config file: {e}")
                raise e

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value
        self._save_config()

    def _save_config(self):
        with open(self._config_path, 'w') as f:
            json.dump(self._config, f, indent=4)
        logging.debug(f"Configuration saved: {self._config}")

# Initialize the ConfigManager
config_manager = ConfigManager()