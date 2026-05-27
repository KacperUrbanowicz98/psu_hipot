# screenshot_helper.py
"""
Pomocniczy skrypt do robienia zdjęć ekranów na potrzeby instrukcji.
Uruchamia wybrane okna apki w trybie DEMO (bez połączenia z urządzeniem).
"""
import tkinter as tk
from unittest.mock import MagicMock
from config import Config

config = Config()

# ── MOCK danych — podstaw co chcesz pokazać ──────────────────
FAKE_OPERATOR = "Jan Kowalski"
FAKE_SERIAL = "SN-TEST-001"
FAKE_MODEL = {
    "name": "Bose SoundLink Max",
    "model_key": "SOUNDLINK_MAX",
    "test_params": {
        "mode": "WVAC",
        "voltage": 1500,
        "voltage_tolerance": 50,
        "current_limit_low": 0.5,
        "current_limit_high": 5.0,
        "ramp_time": 3,
        "test_time": 5,
        "fall_time": 2,
    }
}

def mock_device():
    """Fałszywe urządzenie — nie próbuje łączyć się z COM portem."""
    d = MagicMock()
    d.connected = True
    d.connect.return_value = True
    d.get_status.return_value = "IDLE"
    d.read_measurements.return_value = {
        "output_voltage": 1500,
        "measure_current": 0.0025,
    }
    d.get_test_result.return_value = ("PASS", {"error_code": ""})
    return d

# ================================================================
# Wybierz co chcesz pokazać:
# ================================================================
SHOW = "test_screen"   # opcje: "test_screen" | "admin" | "gui" | "sn_dialog" | "result_pass" | "result_fail"
# ================================================================

root = tk.Tk()
root.title("HiPot PSU — DEMO")
root.geometry("1100x750")

if SHOW == "test_screen":
    from test_screen import TestScreen
    screen = TestScreen(
        parent=root,
        config=config,
        serial_number=FAKE_SERIAL,
        model_info=FAKE_MODEL,
        operator=FAKE_OPERATOR,
        app_ref=None)
    screen.show()
    # Podmień urządzenie na mock żeby nie próbowało łączyć się z COM
    screen.device = mock_device()
    screen.status_label.config(
        text="✓ Urządzenie skonfigurowane i gotowe",
        fg=config.COLOR_ACCENT)

elif SHOW == "result_pass":
    from test_screen import TestScreen
    screen = TestScreen(
        parent=root,
        config=config,
        serial_number=FAKE_SERIAL,
        model_info=FAKE_MODEL,
        operator=FAKE_OPERATOR,
        app_ref=None)
    screen.show()
    screen.device = mock_device()
    # Symuluj stan po teście PASS
    screen.start_button.config(state='disabled')
    screen.stop_button.config(state='disabled')
    screen.back_button.config(state='normal')
    screen.status_label.config(text="✓ TEST ZALICZONY (PASS)", fg=config.COLOR_ACCENT)
    screen.voltage_label.config(text="1500 V")
    screen.current_label.config(text="2.50 mA")
    screen.time_label.config(text="10.0 s")
    # Pasek postępu pełny
    root.update()
    w = screen.progress_canvas.winfo_width()
    screen.progress_canvas.coords(screen.progress_rect, 0, 0, w, 30)

elif SHOW == "result_fail":
    from test_screen import TestScreen
    screen = TestScreen(
        parent=root,
        config=config,
        serial_number=FAKE_SERIAL,
        model_info=FAKE_MODEL,
        operator=FAKE_OPERATOR,
        app_ref=None)
    screen.show()
    screen.device = mock_device()
    screen.start_button.config(state='disabled')
    screen.stop_button.config(state='disabled')
    screen.back_button.config(state='normal')
    screen.status_label.config(text="✗ TEST NIEZALICZONY (FAIL)", fg=config.COLOR_ERROR)
    screen.voltage_label.config(text="1480 V")
    screen.current_label.config(text="6.80 mA")
    screen.time_label.config(text="4.3 s")

elif SHOW == "sn_dialog":
    from test_screen import TestScreen
    screen = TestScreen(
        parent=root,
        config=config,
        serial_number=FAKE_SERIAL,
        model_info=FAKE_MODEL,
        operator=FAKE_OPERATOR,
        app_ref=None)
    screen.show()
    screen.device = mock_device()
    screen.status_label.config(text="✓ TEST ZALICZONY (PASS)", fg=config.COLOR_ACCENT)
    # Otwórz okno SN z wynikiem PASS
    root.after(500, lambda: screen.show_result_and_next_serial("PASS", {}))

elif SHOW == "admin":
    from admin_panel import AdminPanel
    panel = AdminPanel(parent=root, config=config, app_ref=None)
    panel.show()

elif SHOW == "gui":
    from gui import MainApp
    app = MainApp(root, config)

root.mainloop()