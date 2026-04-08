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
    "PSU-000033": {
        "name": "PSU-000033",
        "identifier": "",
        "description": "Zasilacz PSU-000033",
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
        "serial_length": [18, 19],
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
}


class PowerSupplyModels:
    """Baza danych modeli zasilaczy — wczytywana z models.json przy starcie"""
    MODELS: dict = _sm.load_models(_DEFAULT_MODELS)

    @staticmethod
    def validate_serial(model_key: str, serial_number: str):
        """Waliduje długość numeru seryjnego dla danego modelu.
        Zwraca (True, 'OK') lub (False, komunikat)."""
        model = PowerSupplyModels.MODELS.get(model_key)
        if not model:
            return False, "Nieznany model"
        expected = model["serial_length"]
        actual = len(serial_number.strip())
        if isinstance(expected, int):
            expected = [expected]
        if actual not in expected:
            if len(expected) == 1:
                return False, f"Zły SN! Długość {actual} znaków, wymagana {expected[0]}"
            else:
                return False, (f"Zły SN! Długość {actual} znaków, wymagana "
                               f"{' lub '.join(str(x) for x in expected)}")
        return True, "OK"

    @staticmethod
    def identify_model(serial_number: str):
        """Identyfikuje model na podstawie numeru seryjnego (przez pole identifier)."""
        serial_upper = serial_number.upper().strip()
        for model_key, model_data in PowerSupplyModels.MODELS.items():
            identifier = model_data.get("identifier", "").upper()
            if identifier and identifier in serial_upper:
                return model_key, model_data
        return None

    @staticmethod
    def get_all_models():
        """Zwraca listę wszystkich kluczy modeli."""
        return list(PowerSupplyModels.MODELS.keys())

    @staticmethod
    def get_model_info(model_key: str):
        """Pobiera słownik danych modelu."""
        return PowerSupplyModels.MODELS.get(model_key)