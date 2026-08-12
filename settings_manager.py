# settings_manager.py
"""Zarządzanie zapisem i odczytem ustawień aplikacji z plików JSON"""
import json
import os
import tempfile
from typing import List

from app_paths import data_path, seed_path

OPERATORS_FILE = data_path("operators.json")
CONFIG_FILE    = data_path("config.json")
MODELS_FILE    = data_path("models.json")

# Klucz techniczny w models.json — lista profili domyślnych skasowanych
# świadomie przez administratora. Bez tego profil usunięty w panelu
# wracał po każdym restarcie (był ponownie dosypywany z _DEFAULT_MODELS).
_DELETED_KEY = "__deleted_defaults__"


def _atomic_write_json(path: str, data) -> None:
    """
    Zapis przez plik tymczasowy + os.replace.
    Zapobiega uszkodzeniu pliku przy zaniku zasilania lub zerwaniu
    połączenia z dyskiem sieciowym w trakcie zapisu.
    """
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise


def _read_json(path: str):
    """Czyta JSON z pliku obok aplikacji; jeśli brak — próbuje wzorca z EXE."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    seed = seed_path(os.path.basename(path))
    if seed:
        with open(seed, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


class SettingsManager:

    # ------------------------------------------------------------------ #
    # OPERATORZY                                                          #
    # ------------------------------------------------------------------ #
    def load_operators(self, default_list: List[str]) -> List[str]:
        try:
            data = _read_json(OPERATORS_FILE)
        except Exception as e:
            print(f"[SETTINGS] Błąd odczytu {OPERATORS_FILE}: {e}")
            return list(default_list)

        if data is None:
            self.save_operators(default_list)
            return list(default_list)

        users = data.get("authorized_users")
        if not isinstance(users, list):
            print(f"[SETTINGS] {OPERATORS_FILE}: zły format — używam domyślnych")
            return list(default_list)
        # Odfiltruj puste/nietekstowe wpisy — pusty HRID przepuszczałby
        # logowanie pustym polem po stronie porównania.
        return [str(u).strip() for u in users if str(u).strip()]

    def save_operators(self, users: List[str]) -> bool:
        try:
            clean = sorted({str(u).strip() for u in users if str(u).strip()})
            _atomic_write_json(OPERATORS_FILE, {"authorized_users": clean})
            return True
        except Exception as e:
            print(f"[SETTINGS] Błąd zapisu {OPERATORS_FILE}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # KONFIGURACJA                                                        #
    # ------------------------------------------------------------------ #
    def load_config(self, config_obj) -> None:
        try:
            data = _read_json(CONFIG_FILE)
        except Exception as e:
            print(f"[SETTINGS] Błąd odczytu {CONFIG_FILE}: {e}")
            return

        if data is None:
            self.save_config(config_obj)
            return

        try:
            rs = data.get("rs232", {}) or {}
            config_obj.DEFAULT_COM_PORT     = rs.get("com_port",           config_obj.DEFAULT_COM_PORT)
            config_obj.DEFAULT_BAUDRATE     = int(rs.get("baudrate",       config_obj.DEFAULT_BAUDRATE))
            config_obj.DEFAULT_PARITY       = rs.get("parity",             config_obj.DEFAULT_PARITY)
            config_obj.DEFAULT_FLOW_CONTROL = rs.get("flow_control",       config_obj.DEFAULT_FLOW_CONTROL)
            config_obj.INTERLOCK_PORT       = rs.get("interlock_port",     config_obj.INTERLOCK_PORT)
            config_obj.INTERLOCK_BAUDRATE   = int(rs.get("interlock_baudrate", config_obj.INTERLOCK_BAUDRATE))
            config_obj.INTERLOCK_ENABLED    = bool(rs.get("interlock_enabled",  config_obj.INTERLOCK_ENABLED))

            gen = data.get("general", {}) or {}
            config_obj.AUTO_SAVE_RESULTS = bool(gen.get("auto_save_results", config_obj.AUTO_SAVE_RESULTS))
            config_obj.TEST_TIMEOUT      = int(gen.get("test_timeout",       config_obj.TEST_TIMEOUT))
            config_obj.LOG_DIR           = gen.get("log_dir",                config_obj.LOG_DIR)
        except Exception as e:
            # Uszkodzony wpis nie może wywalić startu aplikacji —
            # zostajemy przy wartościach domyślnych z klasy Config.
            print(f"[SETTINGS] Nieprawidłowe dane w {CONFIG_FILE}: {e}")

    def save_config(self, config_obj) -> bool:
        try:
            data = {
                "rs232": {
                    "com_port":           config_obj.DEFAULT_COM_PORT,
                    "baudrate":           int(config_obj.DEFAULT_BAUDRATE),
                    "parity":             config_obj.DEFAULT_PARITY,
                    "flow_control":       config_obj.DEFAULT_FLOW_CONTROL,
                    "interlock_port":     getattr(config_obj, "INTERLOCK_PORT",     "COM7"),
                    "interlock_baudrate": int(getattr(config_obj, "INTERLOCK_BAUDRATE", 9600)),
                    "interlock_enabled":  bool(getattr(config_obj, "INTERLOCK_ENABLED", True)),
                },
                "general": {
                    "auto_save_results": bool(getattr(config_obj, "AUTO_SAVE_RESULTS", True)),
                    "test_timeout":      int(getattr(config_obj, "TEST_TIMEOUT", 300)),
                    "log_dir":           getattr(config_obj, "LOG_DIR", "logs"),
                }
            }
            _atomic_write_json(CONFIG_FILE, data)
            return True
        except Exception as e:
            print(f"[SETTINGS] Błąd zapisu {CONFIG_FILE}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # MODELE / PROFILE TESTOWE                                            #
    # ------------------------------------------------------------------ #
    def load_models(self, default_models: dict) -> dict:
        try:
            saved = _read_json(MODELS_FILE)
        except Exception as e:
            print(f"[SETTINGS] Błąd odczytu {MODELS_FILE}: {e}")
            return {k: dict(v) for k, v in default_models.items()}

        if saved is None:
            self.save_models(default_models)
            return {k: dict(v) for k, v in default_models.items()}

        if not isinstance(saved, dict):
            print(f"[SETTINGS] {MODELS_FILE}: zły format — używam domyślnych")
            return {k: dict(v) for k, v in default_models.items()}

        deleted = set(saved.pop(_DELETED_KEY, []) or [])

        # Dosypz nowe profile fabryczne, ale NIE te skasowane ręcznie.
        updated = False
        for key, value in default_models.items():
            if key in saved or key in deleted:
                continue
            saved[key] = value
            updated = True

        # Odrzuć profile bez wymaganych pól — uszkodzony wpis potrafił
        # wywalić okno wyboru modelu przy starcie.
        clean = {}
        for key, value in saved.items():
            if self._model_is_valid(key, value):
                clean[key] = value
            else:
                print(f"[SETTINGS] Pomijam uszkodzony profil: {key}")
                updated = True

        if updated:
            self.save_models(clean, deleted)

        return clean

    @staticmethod
    def _model_is_valid(key, value) -> bool:
        if not isinstance(value, dict):
            return False
        p = value.get("test_params")
        if not isinstance(p, dict):
            return False
        required = ("mode", "voltage", "current_limit_high",
                    "current_limit_low", "ramp_time", "test_time", "fall_time")
        if any(r not in p for r in required):
            return False
        if "serial_length" not in value:
            return False
        return True

    def save_models(self, models: dict, deleted_defaults=None) -> bool:
        try:
            payload = {k: v for k, v in models.items() if k != _DELETED_KEY}
            if deleted_defaults is None:
                deleted_defaults = self._read_deleted_defaults()
            if deleted_defaults:
                payload[_DELETED_KEY] = sorted(deleted_defaults)
            _atomic_write_json(MODELS_FILE, payload)
            return True
        except Exception as e:
            print(f"[SETTINGS] Błąd zapisu {MODELS_FILE}: {e}")
            return False

    def _read_deleted_defaults(self) -> set:
        try:
            data = _read_json(MODELS_FILE)
            if isinstance(data, dict):
                return set(data.get(_DELETED_KEY, []) or [])
        except Exception:
            pass
        return set()

    def mark_model_deleted(self, model_key: str, models: dict) -> bool:
        """Zapisuje modele i zapamiętuje, że profil fabryczny ma nie wracać."""
        deleted = self._read_deleted_defaults()
        deleted.add(model_key)
        return self.save_models(models, deleted)
