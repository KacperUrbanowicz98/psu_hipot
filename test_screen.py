# test_screen.py
"""Ekran testowania Hi-Pot"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date, timedelta
import threading
import time
import os
import re
from logger import save_report
from tkinter import ttk

# ======================================================================== #
# SHIFT STATS                                                               #
# ======================================================================== #

_SHIFTS = [
    (1, "I",   6,  14),
    (2, "II",  14, 22),
    (3, "III", 22,  6),
]

_FNAME_TS_RE = re.compile(
    r'^.+_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.txt$',
    re.IGNORECASE
)


def _get_current_shift(now=None):
    if now is None:
        now = datetime.now()
    h     = now.hour
    today = now.date()

    for num, name, s, e in _SHIFTS:
        if s < e:
            if s <= h < e:
                start = datetime(today.year, today.month, today.day, s)
                end   = datetime(today.year, today.month, today.day, e)
                return num, name, start, end
        else:
            if h >= s:
                start    = datetime(today.year, today.month, today.day, s)
                tomorrow = today + timedelta(days=1)
                end      = datetime(tomorrow.year, tomorrow.month, tomorrow.day, e)
                return num, name, start, end
            elif h < e:
                yesterday = today - timedelta(days=1)
                start = datetime(yesterday.year, yesterday.month, yesterday.day, s)
                end   = datetime(today.year, today.month, today.day, e)
                return num, name, start, end

    start = datetime(today.year, today.month, today.day, 0)
    return 0, "?", start, start + timedelta(hours=8)


def _parse_result_from_file(filepath):
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
    """Zlicza PASS/FAIL bieżącej zmiany. Odbudowuje się z logów po restarcie."""

    def __init__(self, log_dir: str):
        self.log_dir     = log_dir
        self._lock       = threading.Lock()
        self._app_start  = datetime.now()

        num, name, start, end = _get_current_shift()
        self.shift_num   = num
        self.shift_name  = name
        self.shift_start = start
        self.shift_end   = end

        self.total   = 0
        self.passed  = 0
        self.failed  = 0
        self.retests = 0

        self.on_rebuilt = None
        threading.Thread(target=self._rebuild_from_logs, daemon=True).start()

    def _rebuild_from_logs(self):
        if not self.shift_start or not os.path.isdir(self.log_dir):
            return
        total = passed = failed = retests = 0
        try:
            for fname in os.listdir(self.log_dir):
                m = _FNAME_TS_RE.match(fname)
                if not m:
                    continue
                yr, mo, dy, hh, mm, ss = (int(x) for x in m.groups())
                try:
                    ts = datetime(yr, mo, dy, hh, mm, ss)
                except ValueError:
                    continue
                if not (self.shift_start <= ts < self.shift_end):
                    continue
                if ts >= self._app_start:
                    continue
                result = _parse_result_from_file(os.path.join(self.log_dir, fname))
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
            self.total   = total
            self.passed  = passed
            self.failed  = failed
            self.retests = retests

        print(f"[SHIFT] Odbudowano: {total} testów (PASS={passed} FAIL={failed}), "
              f"zmiana {self.shift_name} od {self.shift_start.strftime('%H:%M')}")

        if self.on_rebuilt:
            self.on_rebuilt()

    def add_result(self, result: str, is_duplicate: bool = False):
        num, name, start, end = _get_current_shift()
        with self._lock:
            if num != self.shift_num:
                self.shift_num   = num
                self.shift_name  = name
                self.shift_start = start
                self.shift_end   = end
                self.total   = 0
                self.passed  = 0
                self.failed  = 0
                self.retests = 0
                print(f"[SHIFT] Przełom zmiany: {name}")
            if is_duplicate:
                self.retests += 1
            else:
                self.total += 1
                if result.upper() == "PASS":
                    self.passed += 1
                else:
                    self.failed += 1

    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "shift_num":   self.shift_num,
                "shift_name":  self.shift_name,
                "shift_start": self.shift_start,
                "shift_end":   self.shift_end,
                "total":       self.total,
                "passed":      self.passed,
                "failed":      self.failed,
                "retests":     self.retests,
            }


# ======================================================================== #
# TEST SCREEN                                                               #
# ======================================================================== #

class TestScreen:

    def __init__(self, parent, config, serial_number, model_info, operator,
                 app_ref=None, stats=None):
        self.parent        = parent
        self.config        = config
        self.serial_number = serial_number
        self.model_info    = model_info
        self.operator      = operator
        self.app_ref       = app_ref
        self.stats         = stats  # StatsManager (dzienne)

        self.device       = None
        self.test_running = False
        self.test_thread  = None
        self.start_time   = None

        self.current_voltage = 0.0
        self.current_current = 0.0
        self.elapsed_time    = 0.0
        self.test_result     = None

        self.last_valid_voltage = 0.0
        self.last_valid_current = 0.0

        self.interlock               = None
        self._prev_interlock_closed  = None
        self._test_completed_called  = False

        self.sn_dialog       = None
        self.sn_entry        = None
        self.sn_result_label = None
        self.sn_status_lbl   = None
        self.retests         = 0

        self.lbl_shift_name  = None
        self.lbl_shift_hours = None
        self.lbl_total       = None
        self.lbl_pass        = None
        self.lbl_fail        = None
        self.lbl_retests     = None

        self._recent_results = []
        self._history_frame  = None

        self.shift_stats: ShiftStats | None = None
        self._current_sn_is_duplicate = False
        self._dup_banner = None

    # ------------------------------------------------------------------ #
    # SHOW                                                                 #
    # ------------------------------------------------------------------ #
    def show(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

        self.create_header()

        self.main_frame = tk.Frame(self.parent, bg=self.config.COLOR_BG)
        self.main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        self.create_device_info()
        self.create_test_params()
        self.create_live_display()
        self.create_progress_bar()
        self.create_interlock_status()
        self.create_control_buttons()
        self.create_history_panel()
        self.create_counter_panel()
        self.create_footer()

        self.shift_stats = ShiftStats(log_dir=self.config.LOG_DIR)
        self.shift_stats.on_rebuilt = lambda: self.parent.after(0, self.update_counter)

        self.connect_device()
        self.connect_interlock()

    # ------------------------------------------------------------------ #
    # HEADER / FOOTER                                                      #
    # ------------------------------------------------------------------ #
    def create_header(self):
        header_frame = tk.Frame(self.parent, bg=self.config.COLOR_PRIMARY, height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Reconext Hi-Pot PSU",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 22, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

        tk.Label(header_frame, text=f"Operator: {self.operator}",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=20, pady=15)

        back_border = tk.Frame(header_frame, bg=self.config.COLOR_WHITE, padx=1, pady=1)
        back_border.pack(side=tk.RIGHT, padx=10, pady=15)

        self.back_button = tk.Button(
            back_border, text="← Powrót do menu",
            bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
            padx=10, pady=4, command=self.go_back)
        self.back_button.pack()
        self.back_button.bind("<Enter>",
                              lambda e: self.back_button.config(bg="#1a5276"))
        self.back_button.bind("<Leave>",
                              lambda e: self.back_button.config(bg=self.config.COLOR_PRIMARY))

    def create_footer(self):
        footer_frame = tk.Frame(self.parent, bg=self.config.COLOR_PRIMARY, height=40)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)
        tk.Label(footer_frame, text="Autor: Kacper Urbanowicz",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=20, pady=10)

    def go_back(self):
        if self.test_running:
            messagebox.showwarning(
                "Test w toku",
                "Nie można wrócić do menu podczas testu!\n"
                "Zatrzymaj test przyciskiem STOP.")
            return
        self._cleanup_and_go_back()

    def _cleanup_and_go_back(self):
        if self.sn_dialog and self.sn_dialog.winfo_exists():
            self.sn_dialog.grab_release()
            self.sn_dialog.destroy()
            self.sn_dialog = None
        if self.interlock:
            self.interlock.disconnect()
        if self.device:
            self.device.disconnect()
        if self.app_ref:
            self.app_ref.show_scan_screen()

    # ------------------------------------------------------------------ #
    # PANELE INFORMACYJNE                                                  #
    # ------------------------------------------------------------------ #
    def create_device_info(self):
        info_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                              relief=tk.RAISED, borderwidth=2)
        info_frame.pack(fill=tk.X, pady=(0, 15))

        info_content = tk.Frame(info_frame, bg=self.config.COLOR_WHITE)
        info_content.pack(padx=20, pady=15)

        tk.Label(info_content, text="Model:", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 11, "bold")).grid(row=0, column=0, sticky='w', padx=(0, 10))
        tk.Label(info_content, text=self.model_info['name'],
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).grid(row=0, column=1, sticky='w', padx=(0, 30))
        tk.Label(info_content, text="S/N:", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 11, "bold")).grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.sn_display_label = tk.Label(
            info_content, text=self.serial_number,
            bg=self.config.COLOR_WHITE, fg="#333333", font=("Arial", 11))
        self.sn_display_label.grid(row=0, column=3, sticky='w')

    def create_test_params(self):
        params_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                                relief=tk.RAISED, borderwidth=2)
        params_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(params_frame, text="Parametry testu",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(pady=(15, 10))

        params_grid = tk.Frame(params_frame, bg=self.config.COLOR_WHITE)
        params_grid.pack(padx=20, pady=(0, 15))

        p          = self.model_info['test_params']
        total_time = p['ramp_time'] + p['test_time'] + p['fall_time']

        self.create_param_label(params_grid, 0, 0, "Napięcie:",
                                f"{p['voltage']}V ±{p['voltage_tolerance']}V")
        self.create_param_label(params_grid, 0, 2, "Tryb:", p['mode'])
        self.create_param_label(params_grid, 1, 0, "Limit prądu:",
                                f"{p['current_limit_low']}mA – {p['current_limit_high']}mA")
        self.create_param_label(params_grid, 1, 2, "Czas całkowity:", f"{total_time}s")

    def create_param_label(self, parent, row, col, label_text, value_text):
        tk.Label(parent, text=label_text, bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)
                 ).grid(row=row, column=col, sticky='w', padx=(0, 5), pady=5)
        tk.Label(parent, text=value_text, bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 10, "bold")
                 ).grid(row=row, column=col + 1, sticky='w', padx=(0, 30), pady=5)

    # ------------------------------------------------------------------ #
    # LIVE DISPLAY                                                         #
    # ------------------------------------------------------------------ #
    def create_live_display(self):
        display_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                                 relief=tk.RAISED, borderwidth=2)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        tk.Label(display_frame, text="Pomiary na żywo",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(pady=(15, 10))

        display_grid = tk.Frame(display_frame, bg=self.config.COLOR_WHITE)
        display_grid.pack(expand=True, pady=20)

        vf = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        vf.grid(row=0, column=0, padx=40)
        tk.Label(vf, text="NAPIĘCIE", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.voltage_label = tk.Label(vf, text="0 V",
                                      bg=self.config.COLOR_WHITE,
                                      fg=self.config.COLOR_PRIMARY,
                                      font=("Arial", 32, "bold"))
        self.voltage_label.pack(pady=5)

        cf = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        cf.grid(row=0, column=1, padx=40)
        tk.Label(cf, text="PRĄD", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.current_label = tk.Label(cf, text="0.00 mA",
                                      bg=self.config.COLOR_WHITE,
                                      fg=self.config.COLOR_ACCENT,
                                      font=("Arial", 32, "bold"))
        self.current_label.pack(pady=5)

        tf = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        tf.grid(row=0, column=2, padx=40)
        tk.Label(tf, text="CZAS", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.time_label = tk.Label(tf, text="0.0 s",
                                   bg=self.config.COLOR_WHITE,
                                   fg="#333333", font=("Arial", 32, "bold"))
        self.time_label.pack(pady=5)

    # ------------------------------------------------------------------ #
    # PASEK POSTĘPU                                                        #
    # ------------------------------------------------------------------ #
    def create_progress_bar(self):
        progress_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = tk.Label(
            progress_frame, text="Gotowy do rozpoczęcia testu",
            bg=self.config.COLOR_BG, fg="#666666", font=("Arial", 11))
        self.status_label.pack(pady=(0, 8))

        self.progress_canvas = tk.Canvas(
            progress_frame, height=30,
            bg=self.config.COLOR_WHITE,
            highlightthickness=1,
            highlightbackground="#cccccc")
        self.progress_canvas.pack(fill=tk.X)
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 30, fill=self.config.COLOR_ACCENT, outline="")

    # ------------------------------------------------------------------ #
    # INTERLOCK                                                            #
    # ------------------------------------------------------------------ #
    def create_interlock_status(self):
        self.interlock_frame = tk.Frame(
            self.main_frame, bg="#fff8e1", relief=tk.RAISED, borderwidth=2)
        self.interlock_frame.pack(fill=tk.X, pady=(0, 10))

        self.interlock_label = tk.Label(
            self.interlock_frame,
            text="⏳ Łączenie z interlockiem (Arduino)...",
            bg="#fff8e1", fg="#FF9800", font=("Arial", 11, "bold"))
        self.interlock_label.pack(pady=8)

    def connect_interlock(self):
        if not getattr(self.config, "INTERLOCK_ENABLED", True):
            self.interlock_label.config(
                text="⚠ Interlock wyłączony — tryb ręczny",
                fg="#FF9800", bg="#fff8e1")
            self.start_button.config(state="normal")
            return

        port = getattr(self.config, "INTERLOCK_PORT", None)
        if not port:
            self.interlock_label.config(
                text="⚠ Brak portu Arduino — tryb ręczny",
                fg="#FF9800", bg="#fff8e1")
            self.start_button.config(state="normal")
            return

        from interlock import InterlockMonitor
        baud = getattr(self.config, "INTERLOCK_BAUDRATE", 9600)
        self.interlock = InterlockMonitor(port=port, baudrate=baud)

        if self.interlock.connect():
            self.interlock.set_on_change(self._on_interlock_change)
            self.interlock.start_monitoring()
            self.interlock_label.config(
                text="⏳ Oczekiwanie na stan klapy...",
                fg="#FF9800", bg="#fff8e1")
            self.start_button.config(state="disabled")
        else:
            self.interlock_label.config(
                text=f"✗ Błąd połączenia z Arduino ({port}) — tryb ręczny",
                fg=self.config.COLOR_ERROR, bg="#ffebee")
            self.interlock_frame.config(bg="#ffebee")
            self.start_button.config(state="normal")

    def _on_interlock_change(self, closed: bool):
        try:
            self.parent.after(0, lambda: self._apply_interlock_state(closed))
        except Exception:
            pass

    def _apply_interlock_state(self, closed):
        if closed is None:
            self.interlock_label.config(
                text="⚠ Utracono połączenie z Arduino — tryb ręczny",
                fg="#FF9800", bg="#fff8e1")
            self.interlock_frame.config(bg="#fff8e1")
            if not self.test_running:
                self.start_button.config(state="normal")
            return

        if closed:
            self.interlock_label.config(
                text="🔒 Klapa ZAMKNIĘTA — uruchamiam test...",
                fg=self.config.COLOR_ACCENT, bg="#e8f5e9")
            self.interlock_frame.config(bg="#e8f5e9")

            if not self.test_running and self._prev_interlock_closed is False:
                if self.sn_dialog and self.sn_dialog.winfo_exists():
                    if not self._try_auto_confirm_sn():
                        self._prev_interlock_closed = closed
                        return
                else:
                    if self.device and self.device.connected:
                        self.start_test()
                    else:
                        self.start_button.config(state="normal")
        else:
            self.interlock_label.config(
                text="🔓 Klapa OTWARTA — wyjmij urządzenie i zamknij klapę",
                fg=self.config.COLOR_ERROR, bg="#ffebee")
            self.interlock_frame.config(bg="#ffebee")

            if self.test_running:
                self.test_running = False
                if self.device:
                    self.device.stop_test()
                self.start_button.config(state='disabled')
                self.stop_button.config(state='disabled')
                self.back_button.config(state='normal')
                self.status_label.config(
                    text="⛔ Test przerwany — klapa została otwarta!",
                    fg=self.config.COLOR_ERROR)
                messagebox.showwarning(
                    "Test przerwany",
                    "Klapa została otwarta podczas testu!\n"
                    "Test został automatycznie zatrzymany.\n\n"
                    "Zamknij klapę aby uruchomić nowy test.",
                    parent=self.parent)
            else:
                self.start_button.config(state="disabled")

        self._prev_interlock_closed = closed

    def _try_auto_confirm_sn(self) -> bool:
        new_serial = self.sn_entry.get().strip().upper()
        from models import PowerSupplyModels
        valid, msg = PowerSupplyModels.validate_serial(
            self.model_info['model_key'], new_serial)

        if not valid:
            self.sn_status_lbl.config(
                text=f"✗ {msg} — popraw SN i zamknij klapę ponownie",
                fg=self.config.COLOR_ERROR)
            self.sn_entry.config(state='normal')
            self.sn_entry.focus()
            return False

        self._current_sn_is_duplicate = False
        self.serial_number = new_serial
        self.sn_display_label.config(text=self.serial_number)

        self.test_result     = None
        self.elapsed_time    = 0.0
        self.current_voltage = 0.0
        self.current_current = 0.0
        self.last_valid_voltage = 0.0
        self.last_valid_current = 0.0

        self.voltage_label.config(text="0 V")
        self.current_label.config(text="0.00 mA")
        self.time_label.config(text="0.0 s")
        self.progress_canvas.coords(self.progress_rect, 0, 0, 0, 30)
        self.status_label.config(text="Gotowy do rozpoczęcia testu", fg="#666666")

        self.sn_dialog.grab_release()
        self.sn_dialog.destroy()
        self.sn_dialog = None

        threading.Thread(
            target=self._check_duplicate_async,
            args=(new_serial,),
            daemon=True
        ).start()

        return True

    def _check_duplicate_async(self, serial: str):
        """Sprawdza duplikat SN w tle — nie blokuje GUI ani startu testu."""
        try:
            dup = self.check_serial_duplicate(serial)
            self._current_sn_is_duplicate = dup["found"]

            if dup["found"]:
                where_txt  = ("tej zmiany" if dup["where"] == "session"
                              else f"logów ({dup['last_time']})")
                result_txt = f" (wynik: {dup['last_result']})" if dup["last_result"] else ""
                msg_short  = f"⚠ DUPLIKAT: SN {serial} był już testowany — {where_txt}{result_txt}"
                msg_full   = (f"SN {serial} był już testowany w tej zmianie!\n"
                              f"{where_txt}{result_txt}\n\n"
                              f"Na pewno chcesz kontynuować?")

                def show_dup_warning():
                    self.status_label.config(text=msg_short, fg="#E65100")
                    if self.sn_dialog and self.sn_dialog.winfo_exists():
                        self.sn_status_lbl.config(
                            text=f"⚠ DUPLIKAT! Testowany {where_txt}{result_txt}",
                            fg="white", bg="#E65100")
                        if not getattr(self, '_dup_banner', None) or \
                                not self._dup_banner.winfo_exists():
                            self._dup_banner = tk.Label(
                                self.sn_dialog,
                                text=f"⚠ DUPLIKAT SN — już testowany {where_txt}{result_txt}",
                                bg="#FF6F00", fg="white",
                                font=("Arial", 10, "bold"),
                                pady=6, anchor="center")
                            self._dup_banner.pack(fill=tk.X, padx=0, pady=(0, 4))
                        self.sn_dialog.lift()
                    else:
                        ans = messagebox.askyesno(
                            "Duplikat SN!", msg_full, parent=self.parent)
                        if ans and self.device and self.device.connected:
                            self.start_test()

                self.parent.after(0, show_dup_warning)

            else:
                def do_start():
                    print(f"[DUP] do_start: device={self.device}, "
                          f"connected={getattr(self.device, 'connected', None)}, "
                          f"test_running={self.test_running}")
                    if self.device and self.device.connected and not self.test_running:
                        self.start_test()
                    else:
                        print("[DUP] BLOKADA start_test — warunek nie spełniony!")

                self.parent.after(0, do_start)

        except Exception as e:
            print(f"[DUP] Błąd sprawdzania duplikatu: {e}")

            def do_start_fallback():
                if self.device and self.device.connected and not self.test_running:
                    self.start_test()

            self.parent.after(0, do_start_fallback)

    # ------------------------------------------------------------------ #
    # PRZYCISKI STEROWANIA                                                 #
    # ------------------------------------------------------------------ #
    def create_control_buttons(self):
        button_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        button_frame.pack(fill=tk.X)

        self.start_button = tk.Button(
            button_frame, text="START TEST",
            bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
            font=('Arial', 16, 'bold'), height=2, relief=tk.FLAT,
            cursor='hand2', command=self.start_test)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_button = tk.Button(
            button_frame, text="STOP",
            bg=self.config.COLOR_ERROR, fg=self.config.COLOR_WHITE,
            font=('Arial', 16, 'bold'), height=2, relief=tk.FLAT,
            cursor='hand2', state='disabled', command=self.stop_test)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.next_sn_button = tk.Button(
            button_frame, text="➜ Następny SN",
            bg='#607D8B', fg=self.config.COLOR_WHITE,
            font=('Arial', 16, 'bold'), height=2, relief=tk.FLAT,
            cursor='hand2', state='disabled',
            command=self._open_sn_dialog_manually)
        self.next_sn_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    # ------------------------------------------------------------------ #
    # HISTORIA + LICZNIK ZMIANY                                           #
    # ------------------------------------------------------------------ #
    def create_history_panel(self):
        outer = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        outer.pack(fill=tk.X, pady=(6, 0))

        top = tk.Frame(outer, bg=self.config.COLOR_WHITE)
        top.pack(fill=tk.X, padx=10, pady=(5, 2))

        tk.Label(top, text="Ostatnie wyniki zmiany",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 9, "bold")).pack(side=tk.LEFT)

        counter_bar = tk.Frame(top, bg=self.config.COLOR_WHITE)
        counter_bar.pack(side=tk.RIGHT)

        self.lbl_shift_name = tk.Label(counter_bar, text="Zmiana ?:",
                                       bg=self.config.COLOR_WHITE,
                                       fg="#888888", font=("Arial", 9))
        self.lbl_shift_name.pack(side=tk.LEFT, padx=(0, 4))

        self.lbl_shift_hours = tk.Label(counter_bar, text="",
                                        bg=self.config.COLOR_WHITE,
                                        fg="#aaaaaa", font=("Arial", 8))
        self.lbl_shift_hours.pack(side=tk.LEFT, padx=(0, 10))

        for lbl_text, attr, fg in [
            ("Razem:", 'lbl_total',   "#222222"),
            ("✓ PASS:", 'lbl_pass',  None),
            ("✗ FAIL:", 'lbl_fail',  None),
            ("RETEST:", 'lbl_retests', "#FF9800"),
        ]:
            tk.Label(counter_bar, text=lbl_text,
                     bg=self.config.COLOR_WHITE,
                     fg="#555555", font=("Arial", 9)).pack(side=tk.LEFT)
            color = (self.config.COLOR_ACCENT if attr == 'lbl_pass'
                     else self.config.COLOR_ERROR if attr == 'lbl_fail'
                     else fg)
            lbl = tk.Label(counter_bar, text="0",
                           bg=self.config.COLOR_WHITE,
                           fg=color, font=("Arial", 9, "bold"))
            lbl.pack(side=tk.LEFT, padx=(2, 10))
            setattr(self, attr, lbl)

        tk.Button(counter_bar, text="📊 Statystyki",
                  bg="#eeeeee", fg="#555555",
                  font=("Arial", 8), relief=tk.FLAT,
                  cursor="hand2", padx=4, pady=1,
                  command=self._show_daily_stats).pack(side=tk.LEFT)

        hdr = tk.Frame(outer, bg=self.config.COLOR_PRIMARY)
        hdr.pack(fill=tk.X, padx=10, pady=(2, 0))
        for text, width in [("Czas", 8), ("Numer seryjny", 22),
                             ("Model", 16), ("Wynik", 7)]:
            tk.Label(hdr, text=text,
                     bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                     font=("Arial", 8, "bold"),
                     width=width, anchor='center', pady=2).pack(side=tk.LEFT)

        self._history_frame = tk.Frame(outer, bg=self.config.COLOR_WHITE)
        self._history_frame.pack(fill=tk.X, padx=10, pady=(1, 5))
        self._refresh_history_panel()

    def create_counter_panel(self):
        pass

    def _refresh_history_panel(self):
        if not self._history_frame or not self._history_frame.winfo_exists():
            return
        for widget in self._history_frame.winfo_children():
            widget.destroy()

        if not self._recent_results:
            tk.Label(self._history_frame,
                     text="Brak wyników — zmiana dopiero wystartowała",
                     bg=self.config.COLOR_WHITE, fg="#aaaaaa",
                     font=("Arial", 8, "italic")).pack(pady=3)
            return

        for idx, entry in enumerate(reversed(self._recent_results)):
            bg        = "#f5f5f5" if idx % 2 == 0 else self.config.COLOR_WHITE
            row       = tk.Frame(self._history_frame, bg=bg)
            row.pack(fill=tk.X)
            result_fg = (self.config.COLOR_ACCENT if entry["result"] == "PASS"
                         else self.config.COLOR_ERROR)
            dup_marker = " ⚠" if entry.get("duplicate") else ""
            for text, width, fg in [
                (entry["time"],              8,  "#666666"),
                (entry["serial"] + dup_marker, 22,
                 "#FF9800" if entry.get("duplicate") else "#333333"),
                (entry["model"],             16, "#333333"),
                (entry["result"],             7, result_fg),
            ]:
                tk.Label(row, text=text, bg=bg, fg=fg,
                         font=("Arial", 8), width=width,
                         anchor='center', pady=2).pack(side=tk.LEFT)

    def _add_recent_result(self, serial, model_key, result, duplicate=False):
        self._recent_results.append({
            "time":      datetime.now().strftime("%H:%M:%S"),
            "serial":    serial,
            "model":     model_key,
            "result":    result,
            "duplicate": duplicate,
        })
        if len(self._recent_results) > 5:
            self._recent_results = self._recent_results[-5:]
        self._refresh_history_panel()

    def update_counter(self):
        if self.lbl_total is None:
            return
        # Jeden licznik — z plików TXT (niezawodny)
        snap = self.stats.count_today() if self.stats else None

        if self.shift_stats:
            s = self.shift_stats.get_snapshot()
            self.lbl_shift_name.config(text=f"Zmiana {s['shift_name']}")
            if s['shift_start'] and s['shift_end']:
                self.lbl_shift_hours.config(
                    text=f"{s['shift_start'].strftime('%H:%M')}–"
                         f"{s['shift_end'].strftime('%H:%M')}")

        if snap:
            self.lbl_total.config(text=str(snap["total"]))
            self.lbl_pass.config(text=str(snap["passed"]))
            self.lbl_fail.config(text=str(snap["failed"]))
            if hasattr(self, 'lbl_retests') and self.lbl_retests:
                dup = snap["duplicates"]
                self.lbl_retests.config(
                    text=f"RETEST {dup}" if dup > 0 else "")
    # ------------------------------------------------------------------ #
    # STATYSTYKI DZIENNE                                                   #
    # ------------------------------------------------------------------ #
    def _show_daily_stats(self):
        from datetime import date as _date, timedelta as td
        from tkinter import ttk
        import json as _json

        log_dir = getattr(self.config, "LOG_DIR", "logs")
        stats_dir = os.path.join(log_dir, "Daily PSU Hi-Pot stats")  # ← poprawna ścieżka

        shift_retests = 0
        shift_name = ""
        if self.shift_stats:
            snap = self.shift_stats.get_snapshot()
            shift_retests = snap.get("retests", 0)
            shift_name = snap.get("shift_name", "")

        def load_stats_for_day(day: _date) -> dict:
            """Czyta z JSON w podfolderze Daily PSU Hi-Pot stats."""
            path = os.path.join(stats_dir, f"stats_{day.strftime('%Y-%m-%d')}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw = _json.load(f)
                    result = {}
                    for operator, rows in raw.items():
                        result[operator] = []
                        for entry in rows.values():
                            result[operator].append({
                                "model": entry["model"],
                                "mode": entry.get("mode", "AC"),
                                "pass": entry["pass"],
                                "fail": entry["fail"],
                                "retest": entry.get("retest", 0),
                                "total": entry["pass"] + entry["fail"],
                            })
                    return result
                except Exception as e:
                    print(f"[STATS] Błąd odczytu statystyk: {e}")
            return {}

        state = {"day": _date.today()}

        # ── Buduj okno ───────────────────────────────────────────────────
        win = tk.Toplevel(self.parent)
        win.title("Statystyki dzienne")
        win.configure(bg=self.config.COLOR_BG)
        win_w, win_h = 900, 700
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{win_w}x{win_h}+{sw // 2 - win_w // 2}+{sh // 2 - win_h // 2}")
        win.resizable(True, True)
        win.transient(self.parent)
        win.grab_set()

        # Nagłówek
        hdr = tk.Frame(win, bg=self.config.COLOR_PRIMARY, height=60)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Statystyki dzienne",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 18, "bold")).pack(side=tk.LEFT, padx=20, pady=10)
        tk.Button(hdr, text="Zamknij",
                  bg=self.config.COLOR_ERROR, fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  command=win.destroy).pack(side=tk.RIGHT, padx=15, pady=15)

        # Pasek nawigacji dni
        nav = tk.Frame(win, bg=self.config.COLOR_BG)
        nav.pack(fill=tk.X, padx=20, pady=(10, 0))
        day_label = tk.Label(nav, text="", bg=self.config.COLOR_BG,
                             fg=self.config.COLOR_PRIMARY, font=("Arial", 13, "bold"))
        day_label.pack(side=tk.LEFT, padx=10)

        # Pasek retestów bieżącej zmiany
        if shift_retests > 0:
            rb = tk.Frame(win, bg="#FFF3E0")
            rb.pack(fill=tk.X, padx=20, pady=(6, 0))
            tk.Label(rb,
                     text=f"  Zmiana {shift_name}: {shift_retests} duplikatów SN"
                          f" — nie wliczone do totalu",
                     bg="#FFF3E0", fg="#E65100",
                     font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10, pady=6)
        else:
            rb = tk.Frame(win, bg="#E8F5E9")
            rb.pack(fill=tk.X, padx=20, pady=(6, 0))
            tk.Label(rb,
                     text=f"  Zmiana {shift_name}: brak duplikatów",
                     bg="#E8F5E9", fg="#2E7D32",
                     font=("Arial", 10)).pack(side=tk.LEFT, padx=10, pady=6)

        # Scrollable area
        container = tk.Frame(win, bg=self.config.COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        canvas = tk.Canvas(container, bg=self.config.COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_frame = tk.Frame(canvas, bg=self.config.COLOR_BG)
        canvas_window = canvas.create_window(0, 0, window=scroll_frame, anchor="nw")
        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        def render_day(day: _date):
            for w in scroll_frame.winfo_children():
                w.destroy()
            day_label.config(
                text="Dzisiaj" if day == _date.today()
                else day.strftime("%A, %d.%m.%Y"))

            data = load_stats_for_day(day)
            if not data:
                tk.Label(scroll_frame,
                         text="Brak danych dla wybranego dnia.",
                         bg=self.config.COLOR_BG, fg="#888888",
                         font=("Arial", 12)).pack(pady=40)
                return

            grand_total = grand_pass = grand_fail = grand_retest = 0

            col_widths = [260, 70, 70, 70, 70, 70]
            col_names = ["Model", "Tryb", "PASS", "FAIL", "DUPLIKAT", "Razem"]

            for operator, rows in data.items():
                op_total = sum(r["total"] for r in rows)
                op_pass = sum(r["pass"] for r in rows)
                op_fail = sum(r["fail"] for r in rows)
                op_retest = sum(r["retest"] for r in rows)
                grand_total += op_total
                grand_pass += op_pass
                grand_fail += op_fail
                grand_retest += op_retest

                # Nagłówek operatora
                op_hdr = tk.Frame(scroll_frame, bg=self.config.COLOR_PRIMARY)
                op_hdr.pack(fill=tk.X, pady=(10, 0))
                label_txt = (f"  Operator: {operator}   "
                             f"Razem: {op_total}   "
                             f"PASS: {op_pass}   "
                             f"FAIL: {op_fail}")
                if op_retest:
                    label_txt += f"   DUPLIKAT: {op_retest}"
                tk.Label(op_hdr, text=label_txt,
                         bg=self.config.COLOR_PRIMARY, fg="white",
                         font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10, pady=5)

                # Nagłówek kolumn
                col_hdr = tk.Frame(scroll_frame, bg="#ECEFF1")
                col_hdr.pack(fill=tk.X)
                for i, (txt, w) in enumerate(zip(col_names, col_widths)):
                    col_hdr.columnconfigure(i, minsize=w)
                    tk.Label(col_hdr, text=txt, bg="#ECEFF1", fg="#333333",
                             font=("Arial", 9, "bold"),
                             anchor="center").grid(row=0, column=i, sticky="ew", pady=3)

                # Wiersze
                for i, row in enumerate(rows):
                    bg = self.config.COLOR_WHITE if i % 2 == 0 else "#F5F5F5"
                    rf = tk.Frame(scroll_frame, bg=bg)
                    rf.pack(fill=tk.X)
                    fail_fg = self.config.COLOR_ERROR if row["fail"] > 0 else "#333333"
                    retest_fg = "#FF9800" if row["retest"] > 0 else "#aaaaaa"
                    vals = [
                        (row["model"], "#333333"),
                        (row["mode"], "#555555"),
                        (row["pass"], self.config.COLOR_ACCENT),
                        (row["fail"], fail_fg),
                        (row["retest"], retest_fg),
                        (row["total"], "#222222"),
                    ]
                    for j, (val, fg) in enumerate(vals):
                        rf.columnconfigure(j, minsize=col_widths[j])
                        tk.Label(rf, text=str(val), bg=bg, fg=fg,
                                 font=("Arial", 10),
                                 anchor="center").grid(row=0, column=j,
                                                       sticky="ew", pady=3)

            # Suma dnia
            summary = tk.Frame(scroll_frame, bg="#263238")
            summary.pack(fill=tk.X, pady=(14, 4))
            summary_txt = (f"  SUMA DNIA:   Razem {grand_total}   "
                           f"PASS {grand_pass}   FAIL {grand_fail}")
            if grand_retest:
                summary_txt += f"   DUPLIKAT {grand_retest} (poza totalem)"
            tk.Label(summary, text=summary_txt,
                     bg="#263238", fg="white",
                     font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=15, pady=8)

            # Retesty bieżącej zmiany w sumie (tylko dla dzisiaj)
            if day == _date.today() and shift_retests > 0:
                tk.Label(summary,
                         text=f"   RETEST zmiany: {shift_retests}",
                         bg="#263238", fg="#FF9800",
                         font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10, pady=8)

        def change_day(delta: int):
            state["day"] = state["day"] + td(days=delta)
            render_day(state["day"])

        # Przyciski nawigacji (po zdefiniowaniu change_day)
        tk.Button(nav, text="◀ Poprzedni dzień",
                  bg="#607D8B", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, cursor="hand2",
                  command=lambda: change_day(-1)).pack(side=tk.LEFT, padx=5)
        tk.Button(nav, text="Następny dzień ▶",
                  bg="#607D8B", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, cursor="hand2",
                  command=lambda: change_day(1)).pack(side=tk.LEFT, padx=5)

        render_day(state["day"])
    # ------------------------------------------------------------------ #
    # POŁĄCZENIE Z URZĄDZENIEM                                             #
    # ------------------------------------------------------------------ #
    def connect_device(self):
        try:
            from hipot_device import ChromaHiPotDevice
            self.device = ChromaHiPotDevice(
                port=self.config.DEFAULT_COM_PORT,
                baudrate=self.config.DEFAULT_BAUDRATE)
            self.status_label.config(
                text="Łączenie z urządzeniem Hi-Pot...", fg="#FF9800")
            if self.device.connect():
                self.status_label.config(
                    text="✓ Połączono z urządzeniem Hi-Pot",
                    fg=self.config.COLOR_ACCENT)
                self.configure_test()
            else:
                self.status_label.config(
                    text="✗ Błąd połączenia z urządzeniem!",
                    fg=self.config.COLOR_ERROR)
                self.start_button.config(state='disabled')
        except Exception as e:
            self.status_label.config(
                text=f"✗ Błąd: {str(e)}", fg=self.config.COLOR_ERROR)
            self.start_button.config(state='disabled')

    def configure_test(self):
        try:
            p = self.model_info['test_params']
            self.device.clear_steps()
            self.device.configure_test(
                step=1,
                mode=p['mode'],
                params={
                    'voltage':            p['voltage'],
                    'current_limit_high': p['current_limit_high'] / 1000,
                    'current_limit_low':  p['current_limit_low']  / 1000,
                    'duration':           p['test_time'],
                    'ramp_time':          p['ramp_time'],
                    'fall_time':          p['fall_time'],
                })
            self.status_label.config(
                text="✓ Urządzenie skonfigurowane i gotowe",
                fg=self.config.COLOR_ACCENT)
        except Exception as e:
            self.status_label.config(
                text=f"✗ Błąd konfiguracji: {str(e)}", fg=self.config.COLOR_ERROR)

    # ------------------------------------------------------------------ #
    # LOGIKA TESTU                                                         #
    # ------------------------------------------------------------------ #
    def start_test(self):
        self._test_completed_called = False
        self.test_running = True
        self.start_time   = time.time()

        self.sn_display_label.config(text=self.serial_number)
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.back_button.config(state='disabled')
        self.status_label.config(text="🔄 Test w toku...", fg="#FF9800")

        self.test_thread = threading.Thread(
            target=self.run_test_background, daemon=True)
        self.test_thread.start()

    def run_test_background(self):
        try:
            self.device.start_test()
            p          = self.model_info['test_params']
            total_time = p['ramp_time'] + p['test_time'] + p['fall_time']

            time.sleep(1.5)
            if not self.test_running:
                return

            min_run_time = 2.0

            while self.test_running:
                status  = self.device.get_status()
                elapsed = time.time() - self.start_time

                if status == "STOPPED" and elapsed >= min_run_time:
                    break

                measurements = self.device.read_measurements()
                if measurements:
                    v = measurements['output_voltage']
                    i = measurements['measure_current'] * 1000  # A → mA

                    self.current_voltage = v
                    self.current_current = i

                    # ── Filtr overflow Chromy (9.91e+37 = brak pomiaru) ──
                    if 0 < v < 1e6:
                        self.last_valid_voltage = v
                    if 0 < i < 9999:
                        self.last_valid_current = i

                self.elapsed_time = time.time() - self.start_time
                self.parent.after(0, self.update_display)

                if self.elapsed_time > total_time + 5:
                    break

                time.sleep(0.1)

            self.parent.after(0, self.test_completed)

        except Exception as e:
            self.parent.after(0, lambda: self.test_error(str(e)))

    def update_display(self):
        self.voltage_label.config(text=f"{int(self.current_voltage)} V")
        self.current_label.config(text=f"{self.current_current:.2f} mA")
        self.time_label.config(text=f"{self.elapsed_time:.1f} s")

        p          = self.model_info['test_params']
        total_time = p['ramp_time'] + p['test_time'] + p['fall_time']
        progress   = min(self.elapsed_time / total_time, 1.0) if total_time > 0 else 0
        cw         = self.progress_canvas.winfo_width()
        self.progress_canvas.coords(self.progress_rect, 0, 0, cw * progress, 30)

    def test_completed(self):
        if self._test_completed_called:
            return
        self._test_completed_called = True
        self.test_running = False

        result, data = self.device.get_test_result()
        self.test_result = result

        self.start_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.back_button.config(state='normal')
        self.next_sn_button.config(state='normal')

        if result == "PASS":
            self.status_label.config(
                text="✓ TEST ZALICZONY (PASS)", fg=self.config.COLOR_ACCENT)
        else:
            self.status_label.config(
                text="✗ TEST NIEZALICZONY (FAIL)", fg=self.config.COLOR_ERROR)

        p          = self.model_info['test_params']
        error_code = str(data.get("error_code", "")) if data else ""

        # ── ZAPIS LOGU ───────────────────────────────────────────────
        # Pobierz vtm/im z FETCH? (data), z filtrem overflow i fallbackiem
        print(f"[DATA] {data}")   # DEBUG — usuń po weryfikacji

        if data:
            try:
                raw_v = float(data.get("output_voltage")   or 0)
                raw_i = float(data.get("measured_current") or 0) * 1000  # A → mA
            except (TypeError, ValueError):
                raw_v, raw_i = 0.0, 0.0
            vtm_val = (raw_v / 1000 if 0 < raw_v < 1e6
                       else self.last_valid_voltage / 1000)
            im_val  = raw_i if 0 < raw_i < 9999 else self.last_valid_current
        else:
            vtm_val = self.last_valid_voltage / 1000
            im_val  = self.last_valid_current

        try:
            log_path = save_report(
                operator   = self.operator,
                program    = self.model_info["model_key"],
                serial     = self.serial_number,
                mode       = p.get("mode", "WVAC"),
                vtm        = vtm_val,
                im         = im_val,
                low        = p["current_limit_low"],
                high       = p["current_limit_high"],
                result     = result,
                error_code = error_code,
                log_dir    = self.config.LOG_DIR,
            )
        except Exception as e:
            print(f"[LOG] Błąd zapisu logu: {e}")
        # ─────────────────────────────────────────────────────────────

        # ── SHIFT STATS ───────────────────────────────────────────────
        if self.shift_stats:
            try:
                is_dup = getattr(self, '_current_sn_is_duplicate', False)
                self.shift_stats.add_result(result, is_duplicate=is_dup)
                self.parent.after(0, self.update_counter)
            except Exception as e:
                print(f"[SHIFT] Błąd zapisu: {e}")
        # ─────────────────────────────────────────────────────────────

        # ── STATS DZIENNE ─────────────────────────────────────────────
        if self.stats:
            try:
                is_dup = getattr(self, '_current_sn_is_duplicate', False)
                self.stats.add_result(
                    operator  = self.operator,
                    model_key = self.model_info['model_key'],
                    mode      = p.get('mode', 'AC'),
                    result    = result,
                    is_retest = is_dup,
                )
            except Exception as e:
                print(f"[STATS] Błąd zapisu: {e}")
        # ─────────────────────────────────────────────────────────────

        self._add_recent_result(
            serial    = self.serial_number,
            model_key = self.model_info["model_key"],
            result    = result,
        )

        self.parent.after(2000,
                          lambda: self.show_result_and_next_serial(result, data))

    def test_error(self, error_message):
        self.test_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.back_button.config(state='normal')
        self.next_sn_button.config(state='disabled')
        self.status_label.config(
            text=f"✗ Błąd testu: {error_message}", fg=self.config.COLOR_ERROR)

    def stop_test(self):
        self.test_running = False
        if self.device:
            self.device.stop_test()
        self.start_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.back_button.config(state='normal')
        self.next_sn_button.config(state='disabled')
        self.status_label.config(
            text="⚠ Test przerwany przez użytkownika", fg="#FF9800")

    # ------------------------------------------------------------------ #
    # DUPLIKAT SN                                                          #
    # ------------------------------------------------------------------ #
    def check_serial_duplicate(self, serial: str) -> dict:
        for entry in self._recent_results:
            if entry["serial"].upper() == serial.upper():
                return {
                    "found":       True,
                    "where":       "session",
                    "last_time":   entry["time"],
                    "last_result": entry["result"],
                }

        log_dir = getattr(self.config, "LOG_DIR", "logs")
        if not os.path.isdir(log_dir):
            return {"found": False, "where": None,
                    "last_time": None, "last_result": None}

        shift_start = self.shift_stats.shift_start if self.shift_stats else None
        shift_end   = self.shift_stats.shift_end   if self.shift_stats else None

        pattern = re.compile(
            r'^' + re.escape(serial.upper()) + r'_(\d{14})\.txt$',
            re.IGNORECASE)

        matches = []
        try:
            for fname in os.listdir(log_dir):
                m = pattern.match(fname)
                if not m:
                    continue
                ts_str = m.group(1)
                try:
                    ts = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                except ValueError:
                    continue
                if shift_start and shift_end:
                    if not (shift_start <= ts < shift_end):
                        continue
                matches.append((ts_str, fname))
        except Exception:
            return {"found": False, "where": None,
                    "last_time": None, "last_result": None}

        if not matches:
            return {"found": False, "where": None,
                    "last_time": None, "last_result": None}

        matches.sort(key=lambda x: x[0], reverse=True)
        latest_ts, latest_fname = matches[0]

        try:
            dt        = datetime.strptime(latest_ts, "%Y%m%d%H%M%S")
            last_time = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            last_time = latest_ts

        last_result = None
        try:
            fpath = os.path.join(log_dir, latest_fname)
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().lower().startswith("total result:"):
                        val = line.split(":", 1)[-1].strip().upper()
                        last_result = "PASS" if val == "PASS" else "FAIL"
                        break
        except Exception:
            pass

        return {
            "found":       True,
            "where":       "logs",
            "last_time":   last_time,
            "last_result": last_result,
        }

    # ------------------------------------------------------------------ #
    # OKNO NASTĘPNY SN                                                     #
    # ------------------------------------------------------------------ #
    def _open_sn_dialog_manually(self):
        if self.sn_dialog and self.sn_dialog.winfo_exists():
            self.sn_dialog.lift()
            self.sn_dialog.focus()
            return
        self.show_result_and_next_serial(self.test_result or "PASS", {})

    def show_result_and_next_serial(self, result, data):
        if self.sn_dialog and self.sn_dialog.winfo_exists():
            self.update_sn_dialog(result)
            self.sn_dialog.lift()
            self.sn_dialog.focus()
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title("Następny numer seryjny")
        dialog.geometry("450x300")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth()  // 2) - (dialog.winfo_width()  // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        self.sn_dialog = dialog

        result_color = (self.config.COLOR_ACCENT if result == "PASS"
                        else self.config.COLOR_ERROR)

        self.sn_result_label = tk.Label(
            dialog, text=f"Ostatni wynik: {result}",
            bg=self.config.COLOR_WHITE, fg=result_color,
            font=("Arial", 13, "bold"))
        self.sn_result_label.pack(pady=(15, 5))

        tk.Frame(dialog, bg="#cccccc", height=1).pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(dialog, text="Zeskanuj kolejny numer seryjny:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11, "bold")).pack(pady=(0, 5))

        self.sn_entry = tk.Entry(
            dialog, font=("Arial", 14, "bold"), width=28,
            justify='center', relief=tk.SOLID, borderwidth=2)
        self.sn_entry.pack(pady=5, padx=30)
        self.sn_entry.focus()

        self.sn_status_lbl = tk.Label(
            dialog, text="⬆ Zeskanuj SN i zamknij klapę aby rozpocząć test",
            bg=self.config.COLOR_WHITE, fg="#888888", font=("Arial", 9))
        self.sn_status_lbl.pack()

        tk.Button(dialog, text="Powrót do menu",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 11, "bold"), width=18, height=1,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._back_to_menu_from_dialog).pack(pady=15)

    def update_sn_dialog(self, result):
        if getattr(self, "_dup_banner", None):
            try:
                self._dup_banner.destroy()
            except Exception:
                pass
            self._dup_banner = None
        self.sn_dialog.configure(bg=self.config.COLOR_WHITE)
        result_color = (self.config.COLOR_ACCENT if result == "PASS"
                        else self.config.COLOR_ERROR)
        self.sn_result_label.config(
            text=f"Ostatni wynik: {result}", fg=result_color)
        self.sn_entry.config(state="normal")
        self.sn_entry.delete(0, tk.END)
        self.sn_status_lbl.config(
            text="Zeskanuj SN i zamknij klapę aby rozpocząć test",
            fg="#888888", bg=self.config.COLOR_WHITE)
        self.sn_entry.focus()

    def _back_to_menu_from_dialog(self):
        if self.sn_dialog and self.sn_dialog.winfo_exists():
            self.sn_dialog.grab_release()
            self.sn_dialog.destroy()
            self.sn_dialog = None
        self._cleanup_and_go_back()