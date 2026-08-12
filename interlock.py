# interlock.py
"""
Monitor stanu klapy bezpieczeństwa — Arduino Leonardo via Serial.

Zmiany względem wersji pierwotnej:
  * automatyczne wznawianie połączenia po wyrwaniu/zawieszeniu USB —
    wcześniej po 3 błędach wątek kończył się na stałe i stanowisko
    zostawało w "trybie ręcznym" aż do restartu aplikacji;
  * port jest zamykany także na ścieżce awaryjnej (wcześniej wyciekał);
  * stan klapy jest publicznie odczytywalny (is_closed) — logika startu
    testu musi móc sprawdzić klapę SYNCHRONICZNIE, tuż przed załączeniem
    wysokiego napięcia, a nie polegać wyłącznie na callbacku;
  * heartbeat: brak jakichkolwiek danych przez STALE_AFTER sekund jest
    traktowany jak utrata interlocka, a nie jak "klapa bez zmian".
"""
import threading
import time
from typing import Callable, Optional

STATE_OPEN    = False
STATE_CLOSED  = True
STATE_UNKNOWN = None


class InterlockMonitor:

    STALE_AFTER      = 5.0    # [s] brak danych = utrata interlocka
    RECONNECT_DELAY  = 2.0    # [s] odstęp między próbami wznowienia
    MAX_ERRORS       = 3      # kolejne błędy odczytu → reconnect

    def __init__(self, port: str, baudrate: int = 9600):
        self.port     = port
        self.baudrate = baudrate
        self._serial  = None
        self._thread  = None
        self._running = False
        self._on_change_cb: Optional[Callable[[Optional[bool]], None]] = None
        self._last_state: Optional[bool] = STATE_UNKNOWN
        self._last_rx = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # POŁĄCZENIE                                                          #
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        try:
            import serial
            with self._lock:
                self._close_locked()
                self._serial = serial.Serial(
                    self.port, self.baudrate,
                    timeout=1,
                    write_timeout=2,
                    exclusive=True)
            time.sleep(1.5)          # Arduino resetuje się przy otwarciu portu
            with self._lock:
                if self._serial:
                    self._serial.reset_input_buffer()
            self._last_rx = time.time()
            return True
        except Exception as e:
            print(f"[INTERLOCK] Błąd połączenia: {e}")
            with self._lock:
                self._close_locked()
            return False

    def _close_locked(self):
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    try:
                        self._serial.cancel_read()
                    except Exception:
                        pass
                    self._serial.close()
            except Exception:
                pass
            self._serial = None

    def disconnect(self):
        self._running = False
        with self._lock:
            self._close_locked()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=3.0)
        self._thread = None

    # ------------------------------------------------------------------ #

    def set_on_change(self, callback: Callable[[Optional[bool]], None]):
        """Callback(closed) — True=zamknięta, False=otwarta, None=brak łączności."""
        self._on_change_cb = callback

    def start_monitoring(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.disconnect()

    # ------------------------------------------------------------------ #
    # STAN                                                                #
    # ------------------------------------------------------------------ #
    @property
    def connected(self) -> bool:
        with self._lock:
            return self._serial is not None and self._serial.is_open

    @property
    def is_closed(self) -> Optional[bool]:
        """
        Ostatni znany stan klapy. Zwraca None gdy stan jest nieznany
        (brak danych, świeży start, utrata łączności) — wywołujący MUSI
        traktować None jak "nie wolno startować".
        """
        if self._last_state is not None and \
                (time.time() - self._last_rx) > self.STALE_AFTER:
            return STATE_UNKNOWN
        return self._last_state

    def _emit(self, state: Optional[bool]):
        self._last_state = state
        cb = self._on_change_cb
        if cb:
            try:
                cb(state)
            except Exception as e:
                print(f"[INTERLOCK] Błąd callbacku: {e}")

    # ------------------------------------------------------------------ #
    # PĘTLA                                                               #
    # ------------------------------------------------------------------ #
    def _monitor_loop(self):
        last_forced = 0.0
        consecutive_errors = 0

        while self._running:
            with self._lock:
                ser = self._serial
            if ser is None or not ser.is_open:
                # Port padł — najpierw powiadom aplikację (blokada klapy
                # przestaje działać!), dopiero potem próbuj wznowić.
                if self._last_state is not STATE_UNKNOWN:
                    self._handle_link_lost()
                if not self._try_reconnect():
                    continue
                consecutive_errors = 0
                continue

            try:
                raw = ser.readline()
            except Exception as e:
                if not self._running:
                    break
                consecutive_errors += 1
                print(f"[INTERLOCK] Błąd odczytu ({consecutive_errors}): {e}")
                if consecutive_errors >= self.MAX_ERRORS or not ser.is_open:
                    self._handle_link_lost()
                    consecutive_errors = 0
                else:
                    time.sleep(0.3)
                continue

            if not self._running:
                break

            now = time.time()

            if not raw:
                # Timeout bez danych — nie jest błędem, ale przedłużająca się
                # cisza oznacza, że Arduino przestało nadawać.
                if self._last_state is not STATE_UNKNOWN and \
                        (now - self._last_rx) > self.STALE_AFTER:
                    print("[INTERLOCK] Brak danych z Arduino — utrata interlocka")
                    self._handle_link_lost()
                continue

            line = raw.decode("ascii", errors="ignore").strip()
            consecutive_errors = 0
            if line not in ("OPEN", "CLOSED"):
                continue

            self._last_rx = now
            closed = (line == "CLOSED")

            # Callback przy zmianie stanu albo odświeżająco co 1 s.
            if closed != self._last_state or (now - last_forced) >= 1.0:
                last_forced = now
                self._emit(closed)

    def _handle_link_lost(self):
        with self._lock:
            self._close_locked()
        self._emit(STATE_UNKNOWN)

    def _try_reconnect(self) -> bool:
        """Czeka RECONNECT_DELAY i próbuje otworzyć port ponownie."""
        deadline = time.time() + self.RECONNECT_DELAY
        while self._running and time.time() < deadline:
            time.sleep(0.1)
        if not self._running:
            return False
        print(f"[INTERLOCK] Próba wznowienia połączenia z {self.port}...")
        if self.connect():
            print("[INTERLOCK] Połączenie wznowione")
            return True
        return False
