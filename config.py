# config.py
"""Konfiguracja aplikacji"""
from settings_manager import SettingsManager


class Config:
    # Kolory
    COLOR_PRIMARY   = "#375ea9"
    COLOR_ACCENT    = "#4CAF50"
    COLOR_BG        = "#f5f5f5"
    COLOR_WHITE     = "#FFFFFF"
    COLOR_ERROR     = "#f44336"

    # Okno
    WINDOW_WIDTH    = 1000
    WINDOW_HEIGHT   = 750
    WINDOW_TITLE    = "Reconext Hi-Pot Tester"

    # RS232
    DEFAULT_COM_PORT    = "COM6"
    DEFAULT_BAUDRATE    = 9600
    DEFAULT_PARITY      = "NONE"
    DEFAULT_FLOW_CONTROL = "NONE"

    # Inne
    AUTO_SAVE_RESULTS = True
    TEST_TIMEOUT      = 300

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
        self.AUTHORIZED_USERS = sm.load_operators(self.AUTHORIZED_USERS)
        sm.load_config(self)