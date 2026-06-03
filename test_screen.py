# test_screen.py
"""Ekran testowania Hi-Pot"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import threading
import time
from logger import save_report


class TestScreen:

    def __init__(self, parent, config, serial_number, model_info, operator, app_ref=None, stats=None):
        self.parent = parent
        self.config = config
        self.serial_number = serial_number
        self.model_info = model_info
        self.operator = operator
        self.app_ref = app_ref
        self.stats = stats  # StatsManager lub None

        self.device = None
        self.test_running = False
        self.test_thread = None
        self.start_time = None

        self.current_voltage = 0.0
        self.current_current = 0.0
        self.elapsed_time = 0.0
        self.test_result = None

        self.last_valid_voltage = 0.0
        self.last_valid_current = 0.0

        # Interlock
        self.interlock = None
        self._prev_interlock_closed = None

        # Guard — zapobiega podwójnemu test_completed
        self._test_completed_called = False

        # Okno SN — jedna trwała instancja
        self.sn_dialog = None
        self.sn_entry = None
        self.sn_result_label = None
        self.sn_status_lbl = None

        # Etykiety licznika
        self.lbl_total = None
        self.lbl_pass = None
        self.lbl_fail = None

        # Historia 5 ostatnich wyników na ekranie testowym
        self._recent_results = []
        self._history_frame = None

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
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            cursor="hand2", padx=10, pady=4,
            command=self.go_back)
        self.back_button.pack()
        self.back_button.bind("<Enter>", lambda e: self.back_button.config(bg="#1a5276"))
        self.back_button.bind("<Leave>", lambda e: self.back_button.config(bg=self.config.COLOR_PRIMARY))

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
                "Nie można wrócić do menu podczas testu!\nZatrzymaj test przyciskiem STOP.")
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
                 fg=self.config.COLOR_PRIMARY, font=("Arial", 11, "bold")
                 ).grid(row=0, column=0, sticky='w', padx=(0, 10))
        tk.Label(info_content, text=self.model_info['name'], bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 11)
                 ).grid(row=0, column=1, sticky='w', padx=(0, 30))
        tk.Label(info_content, text="S/N:", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY, font=("Arial", 11, "bold")
                 ).grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.sn_display_label = tk.Label(
            info_content, text=self.serial_number, bg=self.config.COLOR_WHITE,
            fg="#333333", font=("Arial", 11))
        self.sn_display_label.grid(row=0, column=3, sticky='w')

    def create_test_params(self):
        params_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                                relief=tk.RAISED, borderwidth=2)
        params_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(params_frame, text="Parametry testu", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY, font=("Arial", 12, "bold")
                 ).pack(pady=(15, 10))

        params_grid = tk.Frame(params_frame, bg=self.config.COLOR_WHITE)
        params_grid.pack(padx=20, pady=(0, 15))

        p = self.model_info['test_params']
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

        tk.Label(display_frame, text="Pomiary na żywo", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY, font=("Arial", 12, "bold")
                 ).pack(pady=(15, 10))

        display_grid = tk.Frame(display_frame, bg=self.config.COLOR_WHITE)
        display_grid.pack(expand=True, pady=20)

        vf = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        vf.grid(row=0, column=0, padx=40)
        tk.Label(vf, text="NAPIĘCIE", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.voltage_label = tk.Label(vf, text="0 V", bg=self.config.COLOR_WHITE,
                                      fg=self.config.COLOR_PRIMARY,
                                      font=("Arial", 32, "bold"))
        self.voltage_label.pack(pady=5)

        cf = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        cf.grid(row=0, column=1, padx=40)
        tk.Label(cf, text="PRĄD", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.current_label = tk.Label(cf, text="0.00 mA", bg=self.config.COLOR_WHITE,
                                      fg=self.config.COLOR_ACCENT,
                                      font=("Arial", 32, "bold"))
        self.current_label.pack(pady=5)

        tf = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        tf.grid(row=0, column=2, padx=40)
        tk.Label(tf, text="CZAS", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.time_label = tk.Label(tf, text="0.0 s", bg=self.config.COLOR_WHITE,
                                   fg="#333333", font=("Arial", 32, "bold"))
        self.time_label.pack(pady=5)

    # ------------------------------------------------------------------ #
    # PASEK POSTĘPU                                                        #
    # ------------------------------------------------------------------ #
    def create_progress_bar(self):
        progress_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = tk.Label(progress_frame, text="Gotowy do rozpoczęcia testu",
                                     bg=self.config.COLOR_BG, fg="#666666",
                                     font=("Arial", 11))
        self.status_label.pack(pady=(0, 8))

        self.progress_canvas = tk.Canvas(progress_frame, height=30,
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
            self.main_frame, bg="#fff8e1",
            relief=tk.RAISED, borderwidth=2)
        self.interlock_frame.pack(fill=tk.X, pady=(0, 10))

        self.interlock_label = tk.Label(
            self.interlock_frame,
            text="⏳ Łączenie z interlockiem (Arduino)...",
            bg="#fff8e1", fg="#FF9800",
            font=("Arial", 11, "bold"))
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
                text="⚠ Brak portu Arduino w konfiguracji — tryb ręczny",
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
        #  None = utrata połączenia z Arduino
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

        self.serial_number = new_serial
        self.sn_display_label.config(text=self.serial_number)

        self.test_result = None
        self.elapsed_time = 0.0
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

        return True

    # ------------------------------------------------------------------ #
    # PRZYCISKI STEROWANIA                                                 #
    # ------------------------------------------------------------------ #
    def create_control_buttons(self):
        button_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        button_frame.pack(fill=tk.X)

        self.start_button = tk.Button(
            button_frame, text="START TEST",
            bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"), height=2, relief=tk.FLAT,
            cursor="hand2", command=self.start_test)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_button = tk.Button(
            button_frame, text="STOP",
            bg=self.config.COLOR_ERROR, fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"), height=2, relief=tk.FLAT,
            cursor="hand2", state='disabled', command=self.stop_test)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    # ------------------------------------------------------------------ #
    # HISTORIA OSTATNICH WYNIKÓW                                           #
    # ------------------------------------------------------------------ #
    def create_history_panel(self):
        outer = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        outer.pack(fill=tk.X, pady=(8, 0))

        tk.Label(outer, text="Ostatnie wyniki sesji",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 10, "bold")).pack(anchor='w', padx=15, pady=(8, 4))

        hdr = tk.Frame(outer, bg=self.config.COLOR_PRIMARY)
        hdr.pack(fill=tk.X, padx=15)

        for text, width in [("Czas", 10), ("Numer seryjny", 24), ("Model", 18), ("Wynik", 8)]:
            tk.Label(hdr, text=text,
                     bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                     font=("Arial", 9, "bold"),
                     width=width, anchor='center', pady=3).pack(side=tk.LEFT)

        self._history_frame = tk.Frame(outer, bg=self.config.COLOR_WHITE)
        self._history_frame.pack(fill=tk.X, padx=15, pady=(2, 8))

        self._refresh_history_panel()

    def _refresh_history_panel(self):
        if not self._history_frame or not self._history_frame.winfo_exists():
            return

        for widget in self._history_frame.winfo_children():
            widget.destroy()

        if not self._recent_results:
            tk.Label(self._history_frame,
                     text="Brak wyników — sesja dopiero wystartowała",
                     bg=self.config.COLOR_WHITE, fg="#aaaaaa",
                     font=("Arial", 9, "italic")).pack(pady=6)
            return

        for idx, entry in enumerate(reversed(self._recent_results)):
            bg = "#f9f9f9" if idx % 2 == 0 else self.config.COLOR_WHITE
            row = tk.Frame(self._history_frame, bg=bg)
            row.pack(fill=tk.X, pady=1)

            result_fg = self.config.COLOR_ACCENT if entry["result"] == "PASS" else self.config.COLOR_ERROR

            for text, width, fg in [
                (entry["time"], 10, "#666666"),
                (entry["serial"], 24, "#333333"),
                (entry["model"], 18, "#333333"),
                (entry["result"], 8, result_fg),
            ]:
                tk.Label(row, text=text, bg=bg, fg=fg,
                         font=("Arial", 9), width=width,
                         anchor='center', pady=4).pack(side=tk.LEFT)

    def _add_recent_result(self, serial, model_key, result):
        self._recent_results.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "serial": serial,
            "model": model_key,
            "result": result,
        })
        if len(self._recent_results) > 5:
            self._recent_results = self._recent_results[-5:]
        self._refresh_history_panel()

    # ------------------------------------------------------------------ #
    # LICZNIK PRODUKCJI                                                    #
    # ------------------------------------------------------------------ #
    def create_counter_panel(self):
        counter_frame = tk.Frame(self.main_frame, bg="#1a1a2e",
                                 relief=tk.FLAT, borderwidth=0)
        counter_frame.pack(fill=tk.X, pady=(8, 0))

        inner = tk.Frame(counter_frame, bg="#1a1a2e")
        inner.pack(padx=15, pady=6, fill=tk.X)

        tk.Label(inner, text="Sesja:", bg="#1a1a2e", fg="#aaaaaa",
                 font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(inner, text="Razem:", bg="#1a1a2e", fg="#cccccc",
                 font=("Arial", 10)).pack(side=tk.LEFT)
        self.lbl_total = tk.Label(inner, text="0", bg="#1a1a2e",
                                  fg="#ffffff", font=("Arial", 11, "bold"))
        self.lbl_total.pack(side=tk.LEFT, padx=(2, 14))

        tk.Label(inner, text="✓ PASS:", bg="#1a1a2e", fg="#cccccc",
                 font=("Arial", 10)).pack(side=tk.LEFT)
        self.lbl_pass = tk.Label(inner, text="0", bg="#1a1a2e",
                                 fg=self.config.COLOR_ACCENT,
                                 font=("Arial", 11, "bold"))
        self.lbl_pass.pack(side=tk.LEFT, padx=(2, 14))

        tk.Label(inner, text="✗ FAIL:", bg="#1a1a2e", fg="#cccccc",
                 font=("Arial", 10)).pack(side=tk.LEFT)
        self.lbl_fail = tk.Label(inner, text="0", bg="#1a1a2e",
                                 fg=self.config.COLOR_ERROR,
                                 font=("Arial", 11, "bold"))
        self.lbl_fail.pack(side=tk.LEFT, padx=(2, 20))

        tk.Button(inner, text="↺ Reset sesji",
                  bg="#2d2d44", fg="#cccccc",
                  font=("Arial", 9), relief=tk.FLAT,
                  cursor="hand2", padx=8, pady=3,
                  command=self._reset_session_confirm
                  ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(inner, text="📊 Statystyki dnia",
                  bg="#2d2d44", fg="#cccccc",
                  font=("Arial", 9), relief=tk.FLAT,
                  cursor="hand2", padx=8, pady=3,
                  command=self._show_daily_stats
                  ).pack(side=tk.LEFT)

    def update_counter(self):
        if not self.stats or self.lbl_total is None:
            return
        self.lbl_total.config(text=str(self.stats.session_total))
        self.lbl_pass.config(text=str(self.stats.session_pass))
        self.lbl_fail.config(text=str(self.stats.session_fail))

    def _reset_session_confirm(self):
        if not self.stats:
            return
        if messagebox.askyesno(
                "Reset licznika",
                "Czy na pewno chcesz zresetować licznik sesji?\n"
                "Statystyki dzienne NIE zostaną usunięte.",
                parent=self.parent):
            self.stats.reset_session()
            self.update_counter()

    def _show_daily_stats(self):
        from datetime import date
        if not self.stats:
            messagebox.showinfo("Statystyki", "Brak danych — StatsManager nie jest aktywny.",
                                parent=self.parent)
            return

        daily = self.stats.get_daily_stats()
        today = date.today().strftime("%d.%m.%Y")

        win = tk.Toplevel(self.parent)
        win.title(f"Statystyki dnia — {today}")
        win.configure(bg=self.config.COLOR_WHITE)
        win.transient(self.parent)
        win.grab_set()
        win.resizable(True, True)

        tk.Label(win, text=f"Statystyki dzienne — {today}",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).pack(pady=(15, 10))

        frame = tk.Frame(win, bg=self.config.COLOR_WHITE)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        headers = ["Operator", "Model", "Mode", "✓ PASS", "✗ FAIL", "Razem"]
        col_widths = [16, 18, 8, 7, 7, 7]
        for c, (h, w) in enumerate(zip(headers, col_widths)):
            tk.Label(frame, text=h, bg=self.config.COLOR_PRIMARY,
                     fg=self.config.COLOR_WHITE,
                     font=("Arial", 10, "bold"),
                     width=w, anchor='center',
                     relief=tk.FLAT, padx=6, pady=4
                     ).grid(row=0, column=c, sticky='nsew', padx=1, pady=(0, 2))

        if not daily:
            tk.Label(frame, text="Brak danych na dziś",
                     bg=self.config.COLOR_WHITE, fg="#888888",
                     font=("Arial", 10)).grid(row=1, column=0, columnspan=6, pady=20)
        else:
            row_idx = 1
            total_pass = total_fail = 0

            for operator, rows in sorted(daily.items()):
                total_pass += sum(r["pass"] for r in rows)
                total_fail += sum(r["fail"] for r in rows)

                for i, r in enumerate(rows):
                    bg = "#f9f9f9" if row_idx % 2 == 0 else self.config.COLOR_WHITE
                    vals = [
                        operator if i == 0 else "",
                        r["model"], r["mode"],
                        str(r["pass"]), str(r["fail"]), str(r["total"])
                    ]
                    fgs = [
                        "#333333", "#333333", "#333333",
                        self.config.COLOR_ACCENT,
                        self.config.COLOR_ERROR,
                        "#333333"
                    ]
                    for c, (v, fg) in enumerate(zip(vals, fgs)):
                        tk.Label(frame, text=v, bg=bg, fg=fg,
                                 font=("Arial", 10),
                                 anchor='center', padx=6, pady=3
                                 ).grid(row=row_idx, column=c,
                                        sticky='nsew', padx=1, pady=1)
                    row_idx += 1

            for c in range(6):
                tk.Frame(frame, bg=self.config.COLOR_PRIMARY, height=2
                         ).grid(row=row_idx, column=c, sticky='ew', padx=1, pady=4)
            row_idx += 1

            totals = ["ŁĄCZNIE", "", "",
                      str(total_pass), str(total_fail),
                      str(total_pass + total_fail)]
            t_fgs = ["#333333", "#333333", "#333333",
                     self.config.COLOR_ACCENT,
                     self.config.COLOR_ERROR, "#333333"]
            for c, (v, fg) in enumerate(zip(totals, t_fgs)):
                tk.Label(frame, text=v, bg="#eef6f0",
                         fg=fg, font=("Arial", 10, "bold"),
                         anchor='center', padx=6, pady=4
                         ).grid(row=row_idx, column=c,
                                sticky='nsew', padx=1, pady=1)

        tk.Button(win, text="Zamknij",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 11, "bold"), relief=tk.FLAT,
                  cursor="hand2", padx=20, pady=6,
                  command=win.destroy).pack(pady=15)

        win.update_idletasks()
        w = max(win.winfo_reqwidth() + 40, 620)
        h = min(win.winfo_reqheight() + 40, 600)
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

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
                    'current_limit_low':  p['current_limit_low'] / 1000,
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
        self.start_time = time.time()

        self.sn_display_label.config(text=self.serial_number)

        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.back_button.config(state='disabled')
        self.status_label.config(text="🔄 Test w toku...", fg="#FF9800")

        self.test_thread = threading.Thread(target=self.run_test_background, daemon=True)
        self.test_thread.start()

    def run_test_background(self):
        try:
            self.device.start_test()
            p = self.model_info['test_params']
            total_time = p['ramp_time'] + p['test_time'] + p['fall_time']

            # Daj Chromie czas na przejście ze STOP → TESTING
            # przy 9600 baud każda komenda to ~50-100ms, start_test() wysyła 2 komendy
            time.sleep(1.5)

            if not self.test_running:
                return  # zatrzymano zanim urządzenie ruszyło

            min_run_time = 2.0  # nie akceptuj STOPPED przed upływem tego czasu

            while self.test_running:
                status = self.device.get_status()
                elapsed = time.time() - self.start_time

                if status == "STOPPED" and elapsed >= min_run_time:
                    break

                measurements = self.device.read_measurements()
                if measurements:
                    v = measurements['output_voltage']
                    i = measurements['measure_current'] * 1000

                    self.current_voltage = v
                    self.current_current = i

                    if v > 0:
                        self.last_valid_voltage = v
                    if i > 0:
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

        p = self.model_info['test_params']
        total_time = p['ramp_time'] + p['test_time'] + p['fall_time']
        progress = min(self.elapsed_time / total_time, 1.0) if total_time > 0 else 0
        canvas_width = self.progress_canvas.winfo_width()
        self.progress_canvas.coords(self.progress_rect, 0, 0, canvas_width * progress, 30)

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

        if result == "PASS":
            self.status_label.config(
                text="✓ TEST ZALICZONY (PASS)", fg=self.config.COLOR_ACCENT)
        else:
            self.status_label.config(
                text="✗ TEST NIEZALICZONY (FAIL)", fg=self.config.COLOR_ERROR)

        p = self.model_info['test_params']
        error_code = str(data.get("error_code", "")) if data else ""

        # ── ZAPIS LOGU ──────────────────────────────────────────────────
        try:
            log_path = save_report(
                operator=self.operator,
                program=self.model_info["model_key"],
                serial=self.serial_number,
                mode=p.get("mode", "WVAC"),
                vtm=self.last_valid_voltage / 1000,
                im=self.last_valid_current,
                low=p["current_limit_low"],
                high=p["current_limit_high"],
                result=result,
                error_code=error_code,
                log_dir=self.config.LOG_DIR,
            )
            print(f"[LOG] Zapisano: {log_path}")
        except Exception as e:
            print(f"[LOG] Błąd zapisu logu: {e}")
        # ────────────────────────────────────────────────────────────────

        # ── STATS ───────────────────────────────────────────────────────
        if self.stats:
            try:
                self.stats.add_result(
                    operator=self.operator,
                    model_key=self.model_info["model_key"],
                    mode=p.get("mode", "WVAC"),
                    result=result,
                )
                self.update_counter()
            except Exception as e:
                print(f"[STATS] Błąd zapisu statystyk: {e}")
        # ────────────────────────────────────────────────────────────────

        # ── HISTORIA NA EKRANIE TESTOWYM ────────────────────────────────
        self._add_recent_result(
            serial=self.serial_number,
            model_key=self.model_info["model_key"],
            result=result,
        )
        # ────────────────────────────────────────────────────────────────

        self.parent.after(2000, lambda: self.show_result_and_next_serial(result, data))

    def test_error(self, error_message):
        self.test_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.back_button.config(state='normal')
        self.status_label.config(
            text=f"✗ Błąd testu: {error_message}", fg=self.config.COLOR_ERROR)

    def stop_test(self):
        self.test_running = False
        if self.device:
            self.device.stop_test()
        self.start_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.back_button.config(state='normal')
        self.status_label.config(
            text="⚠ Test przerwany przez użytkownika", fg="#FF9800")

    # ------------------------------------------------------------------ #
    # OKNO SN                                                              #
    # ------------------------------------------------------------------ #
    def show_result_and_next_serial(self, result, data):
        if self.sn_dialog and self.sn_dialog.winfo_exists():
            self._update_sn_dialog(result)
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
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        self.sn_dialog = dialog

        result_color = self.config.COLOR_ACCENT if result == "PASS" else self.config.COLOR_ERROR

        self.sn_result_label = tk.Label(
            dialog, text=f"Ostatni wynik: {result}",
            bg=self.config.COLOR_WHITE,
            fg=result_color, font=("Arial", 13, "bold"))
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

    def _update_sn_dialog(self, result):
        result_color = self.config.COLOR_ACCENT if result == "PASS" else self.config.COLOR_ERROR
        self.sn_result_label.config(text=f"Ostatni wynik: {result}", fg=result_color)
        self.sn_entry.config(state='normal')
        self.sn_entry.delete(0, tk.END)
        self.sn_status_lbl.config(
            text="⬆ Zeskanuj SN i zamknij klapę aby rozpocząć test",
            fg="#888888")
        self.sn_entry.focus()

    def _back_to_menu_from_dialog(self):
        if self.sn_dialog and self.sn_dialog.winfo_exists():
            self.sn_dialog.grab_release()
            self.sn_dialog.destroy()
            self.sn_dialog = None
        self._cleanup_and_go_back()