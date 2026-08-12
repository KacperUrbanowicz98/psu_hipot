# models.py
"""Definicje modeli zasilaczy i ich parametrów testowych"""
from settings_manager import SettingsManager

_sm = SettingsManager()

_DEFAULT_MODELS = {
    "PSU-000016-00": {
        "name": "PSU-000016-00",
        "identifier": "",
        "description": "Zasilacz PSU-000016-00",
        "serial_length": [10, 21],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.15,
            "ramp_time": 0.5, "test_time": 1.0, "fall_time": 0.5,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-000019-00": {
        "name": "PSU-000019-00",
        "identifier": "",
        "description": "Zasilacz PSU-000019-00",
        "serial_length": [10, 21],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.3,
            "ramp_time": 0.5, "test_time": 1.0, "fall_time": 0.5,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-000033-00": {
        "name": "PSU-000033-00",
        "identifier": "",
        "description": "Zasilacz PSU-000033-00",
        "serial_length": [21],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.15,
            "ramp_time": 0.5, "test_time": 1.0, "fall_time": 0.5,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-000013-00": {
        "name": "PSU-000013-00",
        "identifier": "",
        "description": "Zasilacz PSU-000013-00",
        "serial_length": [10, 21],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.15,
            "ramp_time": 0.5, "test_time": 1.0, "fall_time": 0.5,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-00007-00": {
        "name": "PSU-00007-00",
        "identifier": "",
        "description": "Zasilacz PSU-00007-00",
        "serial_length": [9, 10],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.3,
            "ramp_time": 0.0, "test_time": 1.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-00008-00": {
        "name": "PSU-00008-00",
        "identifier": "",
        "description": "Zasilacz PSU-00008-00",
        "serial_length": [10],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.3,
            "ramp_time": 0.0, "test_time": 1.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-00006-00": {
        "name": "PSU-00006-00",
        "identifier": "",
        "description": "Zasilacz PSU-00006-00",
        "serial_length": [10],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.3,
            "ramp_time": 0.0, "test_time": 1.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-00005-00": {
        "name": "PSU-00005-00",
        "identifier": "",
        "description": "Zasilacz PSU-00005-00",
        "serial_length": [12],
        "test_params": {
            "mode": "AC", "voltage": 3300, "voltage_tolerance": 50,
            "current_limit_high": 10.0, "current_limit_low": 0.01,
            "ramp_time": 0.1, "test_time": 3.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 10.0,
        }
    },

    "PSU-00003-00": {
        "name": "PSU-00003-00",
        "identifier": "",
        "description": "Zasilacz PSU-00003-00",
        "serial_length": [10],
        "test_params": {
            "mode": "AC", "voltage": 3000, "voltage_tolerance": 50,
            "current_limit_high": 2.5, "current_limit_low": 0.3,
            "ramp_time": 0.0, "test_time": 1.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "01403-00516": {
        "name": "01403-00516",
        "identifier": "",
        "description": "Zasilacz 01403-00516",
        "serial_length": [17, 18, 19],
        "test_params": {
            "mode": "AC", "voltage": 3750, "voltage_tolerance": 50,
            "current_limit_high": 10.0, "current_limit_low": 0.23,
            "ramp_time": 0.0, "test_time": 3.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "01403-00307": {
        "name": "01403-00307",
        "identifier": "",
        "description": "Zasilacz 01403-00307",
        "serial_length": [17],
        "test_params": {
            "mode": "AC", "voltage": 3750, "voltage_tolerance": 50,
            "current_limit_high": 10.0, "current_limit_low": 0.23,
            "ramp_time": 0.0, "test_time": 3.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "01403-00244": {
        "name": "01403-00244",
        "identifier": "",
        "description": "Zasilacz 01403-00244",
        "serial_length": [18],
        "test_params": {
            "mode": "AC", "voltage": 3750, "voltage_tolerance": 50,
            "current_limit_high": 10.0, "current_limit_low": 0.23,
            "ramp_time": 0.0, "test_time": 3.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "MPD-PW00476AA": {
        "name": "MPD-PW00476AA",
        "identifier": "",
        "description": "Zasilacz MPD-PW00476AA",
        "serial_length": [22],
        "test_params": {
            "mode": "AC", "voltage": 3750, "voltage_tolerance": 50,
            "current_limit_high": 10.0, "current_limit_low": 0.23,
            "ramp_time": 0.0, "test_time": 3.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },

    "PSU-000049-00": {
        "name": "PSU-000049-00",
        "identifier": "",
        "description": "Zasilacz PSU-000049-00",
        "serial_length": [10, 21],
        "test_params": {
            "mode": "DC", "voltage": 4242, "voltage_tolerance": 50,
            "current_limit_high": 3.5, "current_limit_low": 0.0,
            "ramp_time": 0.0, "test_time": 1.0, "fall_time": 0.0,
            "frequency": 50, "arc_detection": 0.0,
        }
    },
}


class PowerSupplyModels:
    """Baza danych modeli zasilaczy — wczytywana z models.json przy starcie"""

    MODELS: dict = _sm.load_models(_DEFAULT_MODELS)

    # ------------------------------------------------------------------ #
    @staticmethod
    def reload():
        """Ponowne wczytanie profili z dysku (po edycji w panelu admina)."""
        PowerSupplyModels.MODELS = _sm.load_models(_DEFAULT_MODELS)
        return PowerSupplyModels.MODELS

    @staticmethod
    def save():
        return _sm.save_models(PowerSupplyModels.MODELS)

    @staticmethod
    def delete_model(model_key: str) -> bool:
        """
        Usuwa profil i zapamiętuje to na stałe.
        Wcześniej usunięty profil fabryczny wracał po restarcie aplikacji,
        bo load_models() bezwarunkowo dosypywało wszystkie wpisy domyślne.
        """
        PowerSupplyModels.MODELS.pop(model_key, None)
        if model_key in _DEFAULT_MODELS:
            return _sm.mark_model_deleted(model_key, PowerSupplyModels.MODELS)
        return _sm.save_models(PowerSupplyModels.MODELS)

    # ------------------------------------------------------------------ #
    @staticmethod
    def validate_serial(model_key: str, serial_number: str):
        model = PowerSupplyModels.MODELS.get(model_key)
        if not model:
            return False, "Nieznany model"

        serial_number = (serial_number or "").strip().upper()
        if not serial_number:
            return False, "Pusty numer seryjny"

        # Skaner potrafi wysłać znaki sterujące / spacje w środku kodu.
        if any(ch.isspace() for ch in serial_number):
            return False, "SN zawiera spację — zeskanuj ponownie"

        expected = model.get("serial_length", [])
        if isinstance(expected, int):
            expected = [expected]
        if not expected:
            return True, "OK"

        actual = len(serial_number)
        if actual not in expected:
            if len(expected) == 1:
                return False, (f"Zły SN! Długość {actual} znaków, "
                               f"wymagana {expected[0]}")
            return False, (f"Zły SN! Długość {actual} znaków, wymagana "
                           f"{' lub '.join(str(x) for x in expected)}")

        return True, "OK"

    @staticmethod
    def identify_model(serial_number: str):
        """Identyfikuje model na podstawie numeru seryjnego przez pole identifier."""
        serial_upper = (serial_number or "").upper().strip()
        for model_key, model_data in PowerSupplyModels.MODELS.items():
            identifier = (model_data.get("identifier") or "").upper()
            if identifier and identifier in serial_upper:
                return model_key, model_data
        return None

    @staticmethod
    def get_all_models():
        """Zwraca posortowaną listę kluczy modeli."""
        return sorted(PowerSupplyModels.MODELS.keys())

    @staticmethod
    def get_model_info(model_key: str):
        """Pobiera słownik danych modelu."""
        return PowerSupplyModels.MODELS.get(model_key)
