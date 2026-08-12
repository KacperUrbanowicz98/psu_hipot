# config.py
"""Konfiguracja aplikacji"""
import os

from app_paths import app_dir
from settings_manager import SettingsManager


class Config:
    # Kolory
    COLOR_PRIMARY = "#375ea9"
    COLOR_ACCENT = "#4CAF50"
    COLOR_BG = "#f5f5f5"
    COLOR_WHITE = "#FFFFFF"
    COLOR_ERROR = "#f44336"

    # Okno
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 750
    WINDOW_TITLE = "Reconext Hi-Pot Tester"

    # RS232 — Chroma Hi-Pot
    DEFAULT_COM_PORT     = "COM6"
    DEFAULT_BAUDRATE     = 9600
    DEFAULT_PARITY       = "NONE"
    DEFAULT_FLOW_CONTROL = "NONE"

    # Interlock — Arduino
    INTERLOCK_PORT     = "COM5"
    INTERLOCK_BAUDRATE = 9600
    INTERLOCK_ENABLED  = True

    # Inne
    AUTO_SAVE_RESULTS = True
    TEST_TIMEOUT      = 300      # [s] twardy limit czasu jednego testu
    LOG_DIR           = "logs"

    # Autoryzowani operatorzy (fallback — nadpisywane z operators.json)
    AUTHORIZED_USERS = [
        "44963","12100667","81705","45216","45061","12100171","12100741",
        "81560","81563","81564","45233","12101333","12101111","12100174",
        "12100475","12101090","12100587","12101094","45016","TEST",
        "12100524","12101639","12101644","45466","12100269","12101487",
        "45518","12101673"
    ]

    def __init__(self):
        sm = SettingsManager()
        # Kopia listy — bez tego panel administratora modyfikowałby
        # atrybut KLASY, wspólny dla wszystkich instancji Config.
        self.AUTHORIZED_USERS = list(sm.load_operators(Config.AUTHORIZED_USERS))
        sm.load_config(self)

        # Ścieżka względna ("logs") musi być liczona od katalogu aplikacji,
        # a nie od katalogu roboczego procesu.
        self.LOG_DIR = self.resolve_log_dir()

    def resolve_log_dir(self) -> str:
        path = (self.LOG_DIR or "logs").strip()
        if not os.path.isabs(path) and not path.startswith("\\\\"):
            path = os.path.join(app_dir(), path)
        return path
