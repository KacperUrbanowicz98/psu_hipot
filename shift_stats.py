# shift_stats.py
"""
Statystyki zmiany produkcyjnej.
Zmiana jest wyznaczana na podstawie bieżącej godziny:
  I   → 06:00 – 13:59
  II  → 14:00 – 21:59
  III → 22:00 – 05:59 (przez noc)

Przy starcie apki odbudowuje licznik z plików TXT w LOG_DIR
— odporne na restart, wywalenie prądu itp.
"""

import os
import re
import threading
from datetime import datetime, date, timedelta


SHIFTS = [
    (1, "I",   6,  14),   # (numer, nazwa, start_h, end_h)
    (2, "II",  14, 22),
    (3, "III", 22, 6),    # nocna — end_h < start_h
]


def get_current_shift(now: datetime | None = None):
    """
    Zwraca (shift_num, shift_name, shift_start: datetime, shift_end: datetime)
    dla podanej chwili (domyślnie datetime.now()).
    """
    if now is None:
        now = datetime.now()

    h = now.hour
    today = now.date()

    for num, name, s, e in SHIFTS:
        if s < e:                        # zmiana dzienna (nie przekracza północy)
            if s <= h < e:
                start = datetime(today.year, today.month, today.day, s, 0, 0)
                end   = datetime(today.year, today.month, today.day, e, 0, 0)
                return num, name, start, end
        else:                            # zmiana nocna (22→06, przekracza północ)
            if h >= s:
                # przed północą: 22:00–23:59
                start = datetime(today.year, today.month, today.day, s, 0, 0)
                end   = datetime(today.year, today.month, today.day, 0, 0, 0) + timedelta(days=1)
                end   = end.replace(hour=e)
                return num, name, start, end
            elif h < e:
                # po północy: 00:00–05:59
                yesterday = today - timedelta(days=1)
                start = datetime(yesterday.year, yesterday.month, yesterday.day, s, 0, 0)
                end   = datetime(today.year, today.month, today.day, e, 0, 0)
                return num, name, start, end

    # fallback — nie powinien się zdarzyć przy poprawnych danych SHIFTS
    start = datetime(today.year, today.month, today.day, 0, 0, 0)
    end   = start + timedelta(hours=8)
    return 0, "?", start, end


# Regex do wyciągania znacznika czasu z nazwy pliku SN_YYYYMMDDHHmmss.txt
_FNAME_RE = re.compile(r'^.+_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.txt$', re.IGNORECASE)


def _parse_result_from_file(filepath: str) -> str | None:
    """Zwraca 'PASS' lub 'FAIL' czytając linię 'Total result:' z pliku."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip().lower().startswith("total result:"):
                    val = line.split(":", 1)[-1].strip().upper()
                    return "PASS" if val == "PASS" else "FAIL"
    except Exception:
        pass
    return None


class ShiftStats:
    """
    Zlicza PASS/FAIL bieżącej zmiany.
    Dane odbudowywane z LOG_DIR przy inicjalizacji (w wątku tła).
    """

    def __init__(self, log_dir: str):
        self.log_dir = log_dir

        self._lock = threading.Lock()
        self.shift_num  = 0
        self.shift_name = "?"
        self.shift_start: datetime | None = None
        self.shift_end:   datetime | None = None

        self.total = 0
        self.passed = 0
        self.failed = 0

        # Callback wywoływany po odbudowaniu z dysku: fn() → None
        self.on_rebuilt: callable | None = None

        self._init_shift()
        # Odbuduj licznik z logów w wątku tła
        threading.Thread(target=self._rebuild_from_logs, daemon=True).start()

    # ------------------------------------------------------------------ #

    def _init_shift(self):
        num, name, start, end = get_current_shift()
        self.shift_num  = num
        self.shift_name = name
        self.shift_start = start
        self.shift_end   = end

    def _rebuild_from_logs(self):
        """
        Skanuje LOG_DIR i zlicza wyniki z bieżącej zmiany.
        Uruchamiany raz przy starcie — w wątku tła.
        """
        if not self.shift_start:
            return

        total = passed = failed = 0

        try:
            if not os.path.isdir(self.log_dir):
                return

            for fname in os.listdir(self.log_dir):
                m = _FNAME_RE.match(fname)
                if not m:
                    continue

                yr, mo, dy, hh, mm, ss = (int(x) for x in m.groups())
                try:
                    ts = datetime(yr, mo, dy, hh, mm, ss)
                except ValueError:
                    continue

                if not (self.shift_start <= ts < self.shift_end):
                    continue

                fpath = os.path.join(self.log_dir, fname)
                result = _parse_result_from_file(fpath)
                if result is None:
                    continue

                total += 1
                if result == "PASS":
                    passed += 1
                else:
                    failed += 1

        except Exception as e:
            print(f"[SHIFT] Błąd odbudowy z logów: {e}")
            return

        with self._lock:
            # Dodaj do tego co już było zliczone w RAM od startu apki
            # (żeby nie tracić testów zrobionych przed końcem _rebuild)
            self.total  += total
            self.passed += passed
            self.failed += failed

        print(f"[SHIFT] Odbudowano z logów: {total} testów (PASS={passed} FAIL={failed})")

        if self.on_rebuilt:
            self.on_rebuilt()

    # ------------------------------------------------------------------ #

    def add_result(self, result: str):
        """
        Dodaje wynik testu do licznika bieżącej zmiany.
        Wywołuj z test_completed() zamiast stats.add_result().
        """
        # Sprawdź czy zmiana się nie zmieniła (o północy, przy długich sesjach)
        num, name, start, end = get_current_shift()
        with self._lock:
            if num != self.shift_num:
                # Przełom zmiany — zeruj i zacznij od nowa
                self.shift_num  = num
                self.shift_name = name
                self.shift_start = start
                self.shift_end   = end
                self.total  = 0
                self.passed = 0
                self.failed = 0
                print(f"[SHIFT] Przełom zmiany → {name}")

            self.total += 1
            if result.upper() == "PASS":
                self.passed += 1
            else:
                self.failed += 1

    def get_snapshot(self) -> dict:
        """Zwraca aktualny stan (thread-safe)."""
        with self._lock:
            return {
                "shift_num":  self.shift_num,
                "shift_name": self.shift_name,
                "shift_start": self.shift_start,
                "shift_end":   self.shift_end,
                "total":  self.total,
                "passed": self.passed,
                "failed": self.failed,
            }