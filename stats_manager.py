# stats_manager.py
"""Zarządzanie statystykami dziennymi per operator."""
import json
import os
from datetime import date
from typing import Dict


class StatsManager:

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        # Statystyki sesji — tylko RAM
        self.session_pass  = 0
        self.session_fail  = 0

    # ------------------------------------------------------------------ #
    # ŚCIEŻKA PLIKU                                                        #
    # ------------------------------------------------------------------ #
    def _stats_path(self) -> str:
        today = date.today().strftime("%Y-%m-%d")
        os.makedirs(self.log_dir, exist_ok=True)
        return os.path.join(self.log_dir, f"stats_{today}.json")

    # ------------------------------------------------------------------ #
    # ODCZYT / ZAPIS                                                       #
    # ------------------------------------------------------------------ #
    def _load(self) -> dict:
        path = self._stats_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self, data: dict):
        path = self._stats_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[STATS] Błąd zapisu statystyk: {e}")

    # ------------------------------------------------------------------ #
    # DODAJ WYNIK                                                          #
    # ------------------------------------------------------------------ #
    def add_result(self, operator: str, model_key: str, mode: str, result: str):
        """Dodaj wynik testu (PASS/FAIL). Zapisuje natychmiast do pliku."""
        # Sesja
        if result == "PASS":
            self.session_pass += 1
        else:
            self.session_fail += 1

        # Dzienne
        data = self._load()
        if operator not in data:
            data[operator] = {}
        key = f"{model_key}|{mode}"
        if key not in data[operator]:
            data[operator][key] = {"model": model_key, "mode": mode, "pass": 0, "fail": 0}
        if result == "PASS":
            data[operator][key]["pass"] += 1
        else:
            data[operator][key]["fail"] += 1

        self._save(data)

    # ------------------------------------------------------------------ #
    # RESET SESJI                                                          #
    # ------------------------------------------------------------------ #
    def reset_session(self):
        self.session_pass = 0
        self.session_fail = 0

    # ------------------------------------------------------------------ #
    # POBIERZ DANE DO WIDOKU                                               #
    # ------------------------------------------------------------------ #
    @property
    def session_total(self) -> int:
        return self.session_pass + self.session_fail

    def get_daily_stats(self) -> Dict[str, list]:
        """
        Zwraca słownik: {operator: [{model, mode, pass, fail, total}, ...]}
        """
        data = self._load()
        result = {}
        for operator, rows in data.items():
            result[operator] = []
            for entry in rows.values():
                result[operator].append({
                    "model": entry["model"],
                    "mode":  entry["mode"],
                    "pass":  entry["pass"],
                    "fail":  entry["fail"],
                    "total": entry["pass"] + entry["fail"],
                })
        return result

    def flush(self):
        """Wymuś zapis — wywołaj przy wylogowaniu i zamknięciu apki."""
        # Dane są zapisywane po każdym teście więc flush tylko loguje
        print("[STATS] Statystyki zsynchronizowane.")