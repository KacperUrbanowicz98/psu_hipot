# interlock.py
"""Monitor stanu klapy bezpieczeństwa — Arduino Leonardo via Serial"""
import threading
import time
from typing import Callable, Optional


class InterlockMonitor:

    def __init__(self, port: str, baudrate: int = 9600):
        self.port     = port
        self.baudrate = baudrate
        self._serial  = None
        self._thread  = None
        self._running = False
        self._on_change_cb: Optional[Callable[[bool], None]] = None
        self._last_state: Optional[bool] = None   # True = CLOSED, False = OPEN

    # ------------------------------------------------------------------ #

    def connect(self) -> bool:
        try:
            import serial
            self._serial = serial.Serial(
                self.port, self.baudrate, timeout=1)
            time.sleep(1.5)   # Arduino resetuje się przy otwarciu portu
            self._serial.reset_input_buffer()
            return True
        except Exception as e:
            print(f"[INTERLOCK] Błąd połączenia: {e}")
            self._serial = None
            return False

    def disconnect(self):
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

    def set_on_change(self, callback: Callable[[bool], None]):
        """Callback wywoływany przy każdej zmianie stanu klapy."""
        self._on_change_cb = callback

    def start_monitoring(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ #

    def _monitor_loop(self):
        last_forced = 0

        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    break

                raw = self._serial.readline()
                line = raw.decode("ascii", errors="ignore").strip()

                if line not in ("OPEN", "CLOSED"):
                    continue

                closed = (line == "CLOSED")
                now = time.time()

                # Wywołuj callback przy zmianie ALBO co 1 sekundę
                if closed != self._last_state or (now - last_forced) >= 1.0:
                    self._last_state = closed
                    last_forced = now
                    if self._on_change_cb:
                        self._on_change_cb(closed)

            except Exception as e:
                print(f"[INTERLOCK] Błąd odczytu: {e}")
                time.sleep(0.5)

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open