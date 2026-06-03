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
        self._lock = threading.Lock()              # ← NOWE: guard na _serial

    # ------------------------------------------------------------------ #

    def connect(self) -> bool:
        try:
            import serial
            self._serial = serial.Serial(
                self.port, self.baudrate,
                timeout=2,          # ← wydłużony (był 1) — daje readline() czas na odpowiedź
                write_timeout=2,    # ← NOWE
                exclusive=True)     # ← NOWE: wyłączny dostęp, zapobiega PermissionError przy reconnect
            time.sleep(1.5)         # Arduino resetuje się przy otwarciu portu
            self._serial.reset_input_buffer()
            return True
        except Exception as e:
            print(f"[INTERLOCK] Błąd połączenia: {e}")
            self._serial = None
            return False

    def disconnect(self):
        self._running = False
        with self._lock:                        # ← NOWE: lock przed operacją na porcie
            if self._serial:
                try:
                    if self._serial.is_open:
                        self._serial.cancel_read()  # ← NOWE: przerywa blokujące readline()
                        self._serial.close()
                except Exception:
                    pass
                self._serial = None             # ← przeniesione do bloku lock

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
        consecutive_errors = 0          # ← NOWE: licznik błędów z rzędu

        while self._running:
            try:
                with self._lock:        # ← NOWE: bezpieczny dostęp do _serial
                    if not self._serial or not self._serial.is_open:
                        break
                    ser = self._serial  # lokalna referencja poza lockiem

                raw = ser.readline()

                if not self._running:   # ← NOWE: sprawdź po readline() (mógł czekać)
                    break

                # Pusty odczyt = timeout bez danych — nie jest błędem
                if not raw:             # ← NOWE
                    consecutive_errors = 0
                    continue

                line = raw.decode("ascii", errors="ignore").strip()
                consecutive_errors = 0  # ← NOWE: reset licznika po udanym odczycie

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
                consecutive_errors += 1
                print(f"[INTERLOCK] Błąd odczytu ({consecutive_errors}): {e}")

                # ← NOWE: po 3 błędach z rzędu port uznajemy za martwy
                if consecutive_errors >= 3:
                    print("[INTERLOCK] Port niedostępny — zatrzymuję monitoring")
                    self._running = False
                    if self._on_change_cb:
                        try:
                            self._on_change_cb(None)  # None = utrata połączenia
                        except Exception:
                            pass
                    break

                time.sleep(0.5)

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open