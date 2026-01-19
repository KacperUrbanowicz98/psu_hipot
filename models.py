# models.py
"""
Definicje modeli zasilaczy i ich parametrów testowych
"""


class PowerSupplyModels:
    """Baza danych modeli zasilaczy"""

    MODELS = {
        "PSU-000019-00": {
            "name": "PSU-000019-00 (SSW-3503UK)",
            "identifier": "SSW-3503UK",
            "description": "Zasilacz SSW-3503UK",
            "test_params": {
                "mode": "AC",  # Tryb testu AC
                "voltage": 3000,  # Napięcie testowe 3000V AC RMS
                "voltage_tolerance": 50,  # Tolerancja +/- 50V
                "current_limit_high": 2.5,  # Górny limit prądu 2.5mA
                "current_limit_low": 0.3,  # Dolny limit prądu 0.3mA
                "ramp_time": 0.5,  # Czas narastania 0.5s
                "test_time": 3.0,  # Czas testu 3.0s
                "fall_time": 0.5,  # Czas opadania 0.5s
                "frequency": 50,  # Częstotliwość 50Hz (AC)
                "arc_detection": 0.0  # ARC detection (domyślnie wyłączone)
            }
        },
        # TODO: Dodać kolejne modele
    }

    @staticmethod
    def identify_model(serial_number):
        """
        Identyfikuje model na podstawie numeru seryjnego

        Args:
            serial_number: Numer seryjny zasilacza (np. "SSW-3503UK 239C608046")

        Returns:
            Słownik z danymi modelu lub None jeśli nie rozpoznano
        """
        serial_upper = serial_number.upper().strip()

        for model_key, model_data in PowerSupplyModels.MODELS.items():
            identifier = model_data["identifier"].upper()
            if identifier in serial_upper:
                return {
                    "model_key": model_key,
                    **model_data
                }

        return None

    @staticmethod
    def get_all_models():
        """
        Zwraca listę wszystkich dostępnych modeli

        Returns:
            Lista kluczy modeli
        """
        return list(PowerSupplyModels.MODELS.keys())

    @staticmethod
    def get_model_info(model_key):
        """
        Pobiera informacje o konkretnym modelu

        Args:
            model_key: Klucz modelu (np. "PSU-000019-00")

        Returns:
            Słownik z danymi modelu lub None
        """
        return PowerSupplyModels.MODELS.get(model_key)
