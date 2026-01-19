# models.py
"""
Definicje modeli zasilaczy i ich parametrów testowych
"""


class PowerSupplyModels:
    """Baza danych modeli zasilaczy"""

    MODELS = {
        "MODEL_A": {
            "name": "Zasilacz Model A",
            "identifier": "MA",  # Znaki identyfikacyjne w S/N
            "test_params": {
                "voltage": 1500,
                "duration": 60,
                "current_limit": 5.0
            }
        },
        "MODEL_B": {
            "name": "Zasilacz Model B",
            "identifier": "MB",
            "test_params": {
                "voltage": 2000,
                "duration": 45,
                "current_limit": 3.5
            }
        },
        # TODO: Dodać pozostałe modele
    }

    @staticmethod
    def identify_model(serial_number):
        """
        Identyfikuje model na podstawie numeru seryjnego

        Args:
            serial_number: Numer seryjny zasilacza

        Returns:
            Słownik z danymi modelu lub None jeśli nie rozpoznano
        """
        serial_upper = serial_number.upper()

        for model_key, model_data in PowerSupplyModels.MODELS.items():
            identifier = model_data["identifier"]
            if identifier in serial_upper:
                return {
                    "model_key": model_key,
                    **model_data
                }

        return None
