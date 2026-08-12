# main.py
"""
Reconext Hi-Pot Tester
Główny plik aplikacji
"""
import os
import sys
import tkinter as tk
import traceback
from datetime import datetime

from app_paths import data_path


def _log_crash(exc_type, exc_value, exc_tb):
    """
    Zapisuje nieobsłużony wyjątek do pliku obok aplikacji.
    W wersji EXE (--windowed) nie ma konsoli — bez tego każdy błąd kończył
    się cichym zniknięciem okna i operator nie miał czego zgłosić.
    """
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(text, file=sys.stderr)
    try:
        with open(data_path("hipot_errors.log"), "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}")
    except Exception:
        pass
    try:
        from tkinter import messagebox
        messagebox.showerror(
            "Błąd aplikacji",
            f"Wystąpił nieoczekiwany błąd:\n\n{exc_value}\n\n"
            f"Szczegóły zapisano w pliku hipot_errors.log")
    except Exception:
        pass


def main():
    sys.excepthook = _log_crash

    root = tk.Tk()
    # Wyjątki w callbackach Tk też trafiają do logu.
    root.report_callback_exception = _log_crash

    from gui import HiPotTesterApp
    app = HiPotTesterApp(root)      # noqa: F841 — referencja trzyma obiekt
    root.mainloop()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
