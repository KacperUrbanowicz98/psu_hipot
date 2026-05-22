# interlock.py
"""Obsługa hardware interlock przez Arduino (Serial, pin 6 → GND)"""
import serial
import threading
import time
from typing import Optional, Callable


class InterlockMonitor:
    """
    Odpytuje Arduino przez Serial w osobnym wątku.
    Arduino wysyła 'CLOSED' lub 'OPEN' co 100ms.
    CLOSED = pin 6 zwarty do GND = klapa zamknięta = można testować.
    """

    def __init__(self, port: str, baudrate: int = 9600):
        self.port     = port
        self.baudrate = baudrate
        self._serial:    Optional[serial.Serial]          = None
        self._state:     Optional[bool]                   = None
        self._running    = False
        self._thread:    Optional[threading.Thread]       = None
        self._on_change: Optional[Callable[[bool], None]] = None

    # ── Połączenie ──────────────────────────────────────────────────────
    def connect(self) -> bool:
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1)
            time.sleep(1.5)   # Arduino resetuje się po otwarciu portu COM
            self._serial.reset_input_buffer()
            print(f"[INTERLOCK] Połączono z Arduino: {self.port}")
            return True
        except Exception as e:
            print(f"[INTERLOCK] Błąd połączenia: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._serial and self._serial.is_open:
            self._serial.close()
        print("[INTERLOCK] Rozłączono")

    # ── Callback ────────────────────────────────────────────────────────
    def set_on_change(self, callback: Callable[[bool], None]):
        """
        callback(closed: bool):
            True  → klapa zamknięta → test możliwy
            False → klapa otwarta   → test zablokowany
        """
        self._on_change = callback

    # ── Stan bieżący ────────────────────────────────────────────────────
    @property
    def is_closed(self) -> Optional[bool]:
        """True=zamknięta, False=otwarta, None=brak danych"""
        return self._state

    # ── Wątek monitorowania ─────────────────────────────────────────────
    def start_monitoring(self):
        if not self._serial or not self._serial.is_open:
            print("[INTERLOCK] Brak połączenia!")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[INTERLOCK] Monitoring uruchomiony")

    def _monitor_loop(self):
        while self._running:
            try:
                if self._serial.in_waiting > 0:
                    line = self._serial.readline()\
                           .decode("ascii", errors="ignore").strip()
                    if line in ("CLOSED", "OPEN"):
                        new_state = (line == "CLOSED")
                        if new_state != self._state:
                            self._state = new_state
                            if self._on_change:
                                self._on_change(new_state)
            except Exception as e:
                print(f"[INTERLOCK] Błąd odczytu: {e}")
                self._running = False
                break
            time.sleep(0.05)
