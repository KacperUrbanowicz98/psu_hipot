# stats_manager.py
"""Statystyki dzienne — źródłem prawdy są pliki TXT w LOG_DIR."""
import json
import os
import re
import time
import random
from datetime import date, datetime
from typing import Dict

_STATS_SUBDIR = "Daily PSU Hi-Pot stats"

# Regex do parsowania nazwy pliku: SN_YYYYMMDDHHmmss.txt
_FNAME_RE = re.compile(
    r'^.+_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.txt$',
    re.IGNORECASE
)


def _parse_result_from_file(filepath: str):
    """Czyta 'Total result: Pass/Fail' z pliku TXT."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip().lower().startswith("total result:"):
                    val = line.split(":", 1)[-1].strip().upper()
                    return "PASS" if val == "PASS" else "FAIL"
    except Exception:
        pass
    return None


def _parse_sn_from_filename(fname: str) -> str:
    """Wyciąga SN z nazwy pliku: SN_YYYYMMDDHHmmss.txt → SN"""
    m = _FNAME_RE.match(fname)
    if not m:
        return ""
    return fname.rsplit("_", 1)[0].upper()


class StatsManager:

    def __init__(self, log_dir: str):
        self.log_dir    = log_dir
        self.stats_dir  = os.path.join(log_dir, _STATS_SUBDIR)
        os.makedirs(self.stats_dir, exist_ok=True)

        # Liczniki sesji (używane przez test_screen.py)
        self.session_pass   = 0
        self.session_fail   = 0
        self.session_retest = 0

    # ------------------------------------------------------------------ #
    # ŚCIEŻKA PLIKU JSON                                                   #
    # ------------------------------------------------------------------ #
    def _stats_path(self, for_date: date = None) -> str:
        d = (for_date or date.today()).strftime("%Y-%m-%d")
        return os.path.join(self.stats_dir, f"stats_{d}.json")

    def _load(self, for_date: date = None) -> dict:
        path = self._stats_path(for_date)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self, data: dict, for_date: date = None):
        """Atomowy zapis — bezpieczny przy dwóch komputerach na tym samym udziale."""
        path = self._stats_path(for_date)
        for attempt in range(3):
            try:
                tmp = path + f".tmp{os.getpid()}"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, path)  # atomowe — nie nadpisze w połowie zapisu
                return
            except Exception as e:
                print(f"[STATS] Retry zapisu ({attempt + 1}/3): {e}")
                time.sleep(random.uniform(0.05, 0.2))

    # ------------------------------------------------------------------ #
    # DODAJ WYNIK                                                          #
    # ------------------------------------------------------------------ #
    def add_result(self, operator: str, model_key: str, mode: str,
                   result: str, is_retest: bool = False):
        """Zapisuje wynik do JSON per-operator i aktualizuje liczniki sesji."""
        # Liczniki sesji
        if is_retest:
            self.session_retest += 1
        elif result == "PASS":
            self.session_pass += 1
        else:
            self.session_fail += 1

        # Zapis do JSON (widok per-operator w oknie Statystyki)
        target_date = date.today()
        data = self._load(target_date)
        if operator not in data:
            data[operator] = {}
        key = f"{model_key}|{mode}"
        if key not in data[operator]:
            data[operator][key] = {
                "model": model_key, "mode": mode,
                "pass": 0, "fail": 0, "retest": 0,
            }
        entry = data[operator][key]
        if "retest" not in entry:
            entry["retest"] = 0

        if is_retest:
            entry["retest"] += 1
        elif result == "PASS":
            entry["pass"] += 1
        else:
            entry["fail"] += 1

        self._save(data, target_date)

    # ------------------------------------------------------------------ #
    # RESET SESJI                                                          #
    # ------------------------------------------------------------------ #
    def reset_session(self):
        self.session_pass   = 0
        self.session_fail   = 0
        self.session_retest = 0

    @property
    def session_total(self) -> int:
        return self.session_pass + self.session_fail

    # ------------------------------------------------------------------ #
    # GŁÓWNY LICZNIK — czyta z plików TXT (niezawodne)                    #
    # ------------------------------------------------------------------ #
    def count_today(self) -> dict:
        """
        Liczy PASS/FAIL/duplikaty dla dzisiejszego dnia
        bezpośrednio z plików TXT w LOG_DIR.
        Duplikat = ten sam SN pojawia się więcej niż raz dzisiaj.
        Zwraca: {total, passed, failed, duplicates}
        """
        today = date.today()
        if not os.path.isdir(self.log_dir):
            return {"total": 0, "passed": 0, "failed": 0, "duplicates": 0}

        total = passed = failed = duplicates = 0
        seen_sns: dict[str, int] = {}

        try:
            entries = []
            for fname in os.listdir(self.log_dir):
                m = _FNAME_RE.match(fname)
                if not m:
                    continue
                yr, mo, dy, hh, mm, ss = (int(x) for x in m.groups())
                try:
                    ts = datetime(yr, mo, dy, hh, mm, ss)
                except ValueError:
                    continue
                if ts.date() != today:
                    continue
                entries.append((ts, fname))

            entries.sort(key=lambda x: x[0])

            for ts, fname in entries:
                sn     = _parse_sn_from_filename(fname)
                result = _parse_result_from_file(
                    os.path.join(self.log_dir, fname))
                if result is None:
                    continue

                seen_sns[sn] = seen_sns.get(sn, 0) + 1
                if seen_sns[sn] > 1:
                    duplicates += 1
                    continue  # duplikat nie idzie do totalu

                total += 1
                if result == "PASS":
                    passed += 1
                else:
                    failed += 1

        except Exception as e:
            print(f"[STATS] Błąd count_today: {e}")

        return {
            "total":      total,
            "passed":     passed,
            "failed":     failed,
            "duplicates": duplicates,
        }

    # ------------------------------------------------------------------ #
    # WIDOK PER-OPERATOR (z JSON)                                          #
    # ------------------------------------------------------------------ #
    def get_daily_stats(self, for_date: date = None) -> Dict[str, list]:
        data = self._load(for_date)
        result = {}
        for operator, rows in data.items():
            result[operator] = []
            for entry in rows.values():
                result[operator].append({
                    "model":  entry["model"],
                    "mode":   entry.get("mode", "AC"),
                    "pass":   entry["pass"],
                    "fail":   entry["fail"],
                    "retest": entry.get("retest", 0),
                    "total":  entry["pass"] + entry["fail"],
                })
        return result

    def flush(self):
        print("[STATS] Statystyki zsynchronizowane.")