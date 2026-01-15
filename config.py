# config.py
"""
Konfiguracja aplikacji
"""


class Config:
    # Kolory z logo ReconEXT
    COLOR_PRIMARY = "#375ea9"  # Niebieski główny
    COLOR_ACCENT = "#4CAF50"  # Zielony akcent
    COLOR_BG = "#f5f5f5"  # Tło
    COLOR_WHITE = "#FFFFFF"

    # Ustawienia okna
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 700
    WINDOW_TITLE = "ReconEXT Hi-Pot Tester"

    # Domyślne parametry testów
    DEFAULT_VOLTAGE = 1500
    DEFAULT_DURATION = 60
    DEFAULT_CURRENT_LIMIT = 5.0
