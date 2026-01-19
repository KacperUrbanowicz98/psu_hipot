# config.py
"""
Konfiguracja aplikacji
"""


class Config:
    # Kolory z logo Reconext
    COLOR_PRIMARY = "#375ea9"  # Niebieski główny
    COLOR_ACCENT = "#4CAF50"  # Zielony akcent
    COLOR_BG = "#f5f5f5"  # Tło
    COLOR_WHITE = "#FFFFFF"
    COLOR_ERROR = "#f44336"  # Czerwony dla błędów

    # Ustawienia okna
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 700
    WINDOW_TITLE = "Reconext Hi-Pot Tester"

    # Domyślne parametry testów
    DEFAULT_VOLTAGE = 1500
    DEFAULT_DURATION = 60
    DEFAULT_CURRENT_LIMIT = 5.0

    # Autoryzowani użytkownicy (HRID)
    AUTHORIZED_USERS = [
        "44963", "12100667", "81705", "45216", "45061", "12100171",
        "12100741", "81560", "81563", "81564", "45233", "12101333",
        "12101111", "12100174", "12100475", "12101090", "12100587",
        "12101094", "45016", "TEST", "12100524", "12101639",
        "12101644", "45466", "12100269", "12101487", "45518", "12101673"
    ]
