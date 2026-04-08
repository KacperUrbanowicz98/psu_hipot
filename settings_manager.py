# settings_manager.py
"""Zarządzanie zapisem i odczytem ustawień aplikacji z plików JSON"""
import json
import os
from typing import List

OPERATORS_FILE = "operators.json"
CONFIG_FILE    = "config.json"
MODELS_FILE    = "models.json"


class SettingsManager:

    def load_operators(self, default_list: List[str]) -> List[str]:
        if not os.path.exists(OPERATORS_FILE):
            self.save_operators(default_list)
            return default_list.copy()
        try:
            with open(OPERATORS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("authorized_users", default_list)
        except Exception as e:
            print(f"Błąd odczytu {OPERATORS_FILE}: {e}")
            return default_list.copy()

    def save_operators(self, users: List[str]):
        try:
            with open(OPERATORS_FILE, "w", encoding="utf-8") as f:
                json.dump({"authorized_users": sorted(users)}, f,
                          indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisu {OPERATORS_FILE}: {e}")

    def load_config(self, config_obj):
        if not os.path.exists(CONFIG_FILE):
            self.save_config(config_obj)
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            rs = data.get("rs232", {})
            config_obj.DEFAULT_COM_PORT     = rs.get("com_port",     config_obj.DEFAULT_COM_PORT)
            config_obj.DEFAULT_BAUDRATE     = rs.get("baudrate",     config_obj.DEFAULT_BAUDRATE)
            config_obj.DEFAULT_PARITY       = rs.get("parity",       config_obj.DEFAULT_PARITY)
            config_obj.DEFAULT_FLOW_CONTROL = rs.get("flow_control",  config_obj.DEFAULT_FLOW_CONTROL)
            gen = data.get("general", {})
            config_obj.AUTO_SAVE_RESULTS = gen.get("auto_save_results", True)
            config_obj.TEST_TIMEOUT      = gen.get("test_timeout",      300)
        except Exception as e:
            print(f"Błąd odczytu {CONFIG_FILE}: {e}")

    def save_config(self, config_obj):
        try:
            data = {
                "rs232": {
                    "com_port":     config_obj.DEFAULT_COM_PORT,
                    "baudrate":     config_obj.DEFAULT_BAUDRATE,
                    "parity":       config_obj.DEFAULT_PARITY,
                    "flow_control": config_obj.DEFAULT_FLOW_CONTROL,
                },
                "general": {
                    "auto_save_results": getattr(config_obj, "AUTO_SAVE_RESULTS", True),
                    "test_timeout":      getattr(config_obj, "TEST_TIMEOUT", 300),
                }
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisu {CONFIG_FILE}: {e}")

    def load_models(self, default_models: dict) -> dict:
        if not os.path.exists(MODELS_FILE):
            self.save_models(default_models)
            return default_models.copy()
        try:
            with open(MODELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Błąd odczytu {MODELS_FILE}: {e}")
            return default_models.copy()

    def save_models(self, models: dict):
        try:
            with open(MODELS_FILE, "w", encoding="utf-8") as f:
                json.dump(models, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisu {MODELS_FILE}: {e}")