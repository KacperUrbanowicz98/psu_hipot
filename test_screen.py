# test_screen.py
"""Ekran testowania Hi-Pot"""
import tkinter as tk
from tkinter import messagebox
import threading
import time
from datetime import datetime
from hipot_device import ChromaHiPotDevice


class TestScreen:

    def __init__(self, parent, config, serial_number, model_info,
                 operator, app_ref=None):
        self.parent = parent
        self.config = config
        self.serial_number = serial_number
        self.model_info = model_info        # dict z kluczem model_key + dane modelu
        self.operator = operator
        self.app_ref = app_ref
        self.device = None
        self.test_running = False
        self.test_thread = None
        self.start_time = None
        self.current_voltage = 0.0
        self.current_current = 0.0
        self.elapsed_time = 0.0
        self.test_result = None

    def show(self):
        """Buduje cały ekran testowania od zera."""
        for widget in self.parent.winfo_children():
            widget.destroy()

        self._create_header()

        self.main_frame = tk.Frame(self.parent, bg=self.config.COLOR_BG)
        self.main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        self._create_device_info()
        self._create_test_params()
        self._create_live_display()
        self._create_progress_bar()
        self._create_control_buttons()
        self._create_footer()
        self._connect_device()

    # ------------------------------------------------------------------ #
    #  HEADER / FOOTER                                                     #
    # ------------------------------------------------------------------ #
    def _create_header(self):
        header = tk.Frame(self.parent, bg=self.config.COLOR_PRIMARY, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="Reconext Hi-Pot PSU",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 22, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

        tk.Label(header, text=f"Operator: {self.operator}",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=20, pady=15)

        back_border = tk.Frame(header, bg=self.config.COLOR_WHITE,
                               padx=1, pady=1)
        back_border.pack(side=tk.RIGHT, padx=10, pady=15)
        self.back_button = tk.Button(
            back_border, text="← Powrót do menu",
            bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            cursor="hand2", padx=10, pady=4,
            command=self._go_back)
        self.back_button.pack()
        self.back_button.bind("<Enter>",
            lambda e: self.back_button.config(bg="#1a5276"))
        self.back_button.bind("<Leave>",
            lambda e: self.back_button.config(bg=self.config.COLOR_PRIMARY))

    def _create_footer(self):
        footer = tk.Frame(self.parent, bg=self.config.COLOR_PRIMARY, height=40)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        footer.pack_propagate(False)
        tk.Label(footer, text="Autor: Kacper Urbanowicz",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=20, pady=10)

    def _go_back(self):
        if self.test_running:
            messagebox.showwarning(
                "Test w toku",
                "Nie można wrócić do menu podczas testu!\nZatrzymaj test przyciskiem STOP.")
            return
        if self.device:
            self.device.disconnect()
        if self.app_ref:
            self.app_ref.show_scan_screen()

    # ------------------------------------------------------------------ #
    #  PANELE INFORMACYJNE                                                 #
    # ------------------------------------------------------------------ #
    def _create_device_info(self):
        frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.X, pady=(0, 15))

        content = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        content.pack(padx=20, pady=15)

        tk.Label(content, text="Model:", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        tk.Label(content, text=self.model_info.get("name", self.model_info.get("model_key", "")),
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).grid(row=0, column=1, sticky="w", padx=(0, 30))

        tk.Label(content, text="SN:", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 11, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 10))
        tk.Label(content, text=self.serial_number,
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).grid(row=0, column=3, sticky="w")

    def _create_test_params(self):
        frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(frame, text="Parametry testu",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(pady=(15, 10))

        grid = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        grid.pack(padx=20, pady=(0, 15))

        p = self.model_info["test_params"]
        total = p["ramp_time"] + p["test_time"] + p["fall_time"]

        self._param_label(grid, 0, 0, "Napięcie",
                          f"{p['voltage']} V ±{p['voltage_tolerance']} V")
        self._param_label(grid, 0, 2, "Tryb", p["mode"])
        self._param_label(grid, 1, 0, "Limit prądu",
                          f"{p['current_limit_low']} mA — {p['current_limit_high']} mA")
        self._param_label(grid, 1, 2, "Czas całkowity", f"{total} s")

    def _param_label(self, parent, row, col, label, value):
        tk.Label(parent, text=f"{label}:", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).grid(
            row=row, column=col, sticky="w", padx=(0, 5), pady=5)
        tk.Label(parent, text=value, bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 10, "bold")).grid(
            row=row, column=col + 1, sticky="w", padx=(0, 30), pady=5)

    def _create_live_display(self):
        frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        tk.Label(frame, text="Pomiary na żywo",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(pady=(15, 10))

        grid = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        grid.pack(expand=True, pady=20)

        # Napięcie
        vf = tk.Frame(grid, bg=self.config.COLOR_WHITE)
        vf.grid(row=0, column=0, padx=40)
        tk.Label(vf, text="NAPIĘCIE", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.voltage_label = tk.Label(vf, text="0 V",
                                      bg=self.config.COLOR_WHITE,
                                      fg=self.config.COLOR_PRIMARY,
                                      font=("Arial", 32, "bold"))
        self.voltage_label.pack(pady=5)

        # Prąd
        cf = tk.Frame(grid, bg=self.config.COLOR_WHITE)
        cf.grid(row=0, column=1, padx=40)
        tk.Label(cf, text="PRĄD", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.current_label = tk.Label(cf, text="0.00 mA",
                                      bg=self.config.COLOR_WHITE,
                                      fg=self.config.COLOR_ACCENT,
                                      font=("Arial", 32, "bold"))
        self.current_label.pack(pady=5)

        # Czas
        tf = tk.Frame(grid, bg=self.config.COLOR_WHITE)
        tf.grid(row=0, column=2, padx=40)
        tk.Label(tf, text="CZAS", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)).pack()
        self.time_label = tk.Label(tf, text="0.0 s",
                                   bg=self.config.COLOR_WHITE,
                                   fg="#333333",
                                   font=("Arial", 32, "bold"))
        self.time_label.pack(pady=5)

    def _create_progress_bar(self):
        frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = tk.Label(
            frame, text="Gotowy do rozpoczęcia testu",
            bg=self.config.COLOR_BG, fg="#666666", font=("Arial", 11))
        self.status_label.pack(pady=(0, 8))

        self.progress_canvas = tk.Canvas(
            frame, height=30, bg=self.config.COLOR_WHITE,
            highlightthickness=1, highlightbackground="#cccccc")
        self.progress_canvas.pack(fill=tk.X)
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 30, fill=self.config.COLOR_ACCENT, outline="")

    def _create_control_buttons(self):
        frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        frame.pack(fill=tk.X)

        self.start_button = tk.Button(
            frame, text="START TEST",
            bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"), height=2,
            relief=tk.FLAT, cursor="hand2",
            command=self.start_test)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_button = tk.Button(
            frame, text="STOP",
            bg=self.config.COLOR_ERROR, fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"), height=2,
            relief=tk.FLAT, cursor="hand2",
            state="disabled", command=self.stop_test)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    # ------------------------------------------------------------------ #
    #  POŁĄCZENIE I KONFIGURACJA                                           #
    # ------------------------------------------------------------------ #
    def _connect_device(self):
        try:
            self.device = ChromaHiPotDevice(
                port=self.config.DEFAULT_COM_PORT,
                baudrate=self.config.DEFAULT_BAUDRATE)
            self.status_label.config(
                text="Łączenie z urządzeniem Hi-Pot...", fg="#FF9800")
            self.parent.update()

            if self.device.connect():
                self.status_label.config(
                    text="Połączono z urządzeniem Hi-Pot",
                    fg=self.config.COLOR_ACCENT)
                self._configure_test()
            else:
                self.status_label.config(
                    text="Błąd połączenia z urządzeniem!",
                    fg=self.config.COLOR_ERROR)
                self.start_button.config(state="disabled")
        except Exception as e:
            self.status_label.config(
                text=f"Błąd: {e}", fg=self.config.COLOR_ERROR)
            self.start_button.config(state="disabled")

    def _configure_test(self):
        try:
            p = self.model_info["test_params"]
            self.device.clear_steps()
            self.device.configure_test(
                step=1,
                mode=p["mode"],
                params={
                    "voltage":             p["voltage"],
                    "current_limit_high":  p["current_limit_high"] / 1000,  # mA → A
                    "current_limit_low":   p["current_limit_low"]  / 1000,  # mA → A
                    "duration":            p["test_time"],
                    "ramp_time":           p["ramp_time"],
                    "fall_time":           p["fall_time"],
                }
            )
            self.status_label.config(
                text="Urządzenie skonfigurowane — gotowe do testu",
                fg=self.config.COLOR_ACCENT)
        except Exception as e:
            self.status_label.config(
                text=f"Błąd konfiguracji: {e}", fg=self.config.COLOR_ERROR)

    # ------------------------------------------------------------------ #
    #  STEROWANIE TESTEM                                                   #
    # ------------------------------------------------------------------ #
    def start_test(self):
        self.test_running = True
        self.start_time = time.time()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.back_button.config(state="disabled")
        self.status_label.config(text="Test w toku...", fg="#FF9800")

        self.test_thread = threading.Thread(
            target=self._run_test_background, daemon=True)
        self.test_thread.start()

    def _run_test_background(self):
        try:
            p = self.model_info["test_params"]
            total_time = p["ramp_time"] + p["test_time"] + p["fall_time"]

            ok = self.device.start_test()
            if not ok:
                self.parent.after(0, lambda: self._test_error(
                    "START zablokowany — sprawdź urządzenie"))
                return

            while self.test_running:
                status = self.device.get_status()
                meas = self.device.read_measurements()

                if meas:
                    self.current_voltage = meas.get("output_voltage", 0.0)
                    self.current_current = meas.get("measure_current", 0.0) * 1000  # A → mA

                self.elapsed_time = time.time() - self.start_time
                self.parent.after(0, self._update_display)

                if status == "STOPPED":
                    break

                if self.elapsed_time > total_time + 5:
                    break

                time.sleep(0.2)

            self.parent.after(0, self._test_completed)

        except Exception as e:
            self.parent.after(0, lambda: self._test_error(str(e)))

    def _update_display(self):
        p = self.model_info["test_params"]
        total_time = p["ramp_time"] + p["test_time"] + p["fall_time"]

        self.voltage_label.config(text=f"{int(self.current_voltage)} V")
        self.current_label.config(text=f"{self.current_current:.2f} mA")
        self.time_label.config(text=f"{self.elapsed_time:.1f} s")

        progress = min(self.elapsed_time / total_time, 1.0) if total_time > 0 else 0
        w = self.progress_canvas.winfo_width()
        self.progress_canvas.coords(self.progress_rect, 0, 0, w * progress, 30)

    def _test_completed(self):
        self.test_running = False
        result, data = self.device.get_test_result()
        self.test_result = result

        self.start_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.back_button.config(state="normal")

        if result == "PASS":
            self.status_label.config(
                text="✓ TEST ZALICZONY — PASS", fg=self.config.COLOR_ACCENT)
        else:
            self.status_label.config(
                text="✗ TEST NIEZALICZONY — FAIL", fg=self.config.COLOR_ERROR)

        self._show_result_dialog(result, data)

    def _test_error(self, msg):
        self.test_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.back_button.config(state="normal")
        self.status_label.config(text=f"Błąd testu: {msg}",
                                 fg=self.config.COLOR_ERROR)

    def stop_test(self):
        self.test_running = False
        if self.device:
            self.device.stop_test()
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.back_button.config(state="normal")
        self.status_label.config(text="Test przerwany przez użytkownika",
                                 fg="#FF9800")

    # ------------------------------------------------------------------ #
    #  DIALOG WYNIKÓW + KOLEJNY SN                                         #
    # ------------------------------------------------------------------ #
    def _show_result_dialog(self, result, data):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Wynik testu")
        dialog.geometry("460x440")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = dialog.winfo_screenwidth()  // 2 - 230
        y = dialog.winfo_screenheight() // 2 - 220
        dialog.geometry(f"460x440+{x}+{y}")

        result_color = (self.config.COLOR_ACCENT
                        if result == "PASS" else self.config.COLOR_ERROR)

        tk.Label(dialog, text="WYNIK TESTU",
                 bg=self.config.COLOR_WHITE, fg="#666666",
                 font=("Arial", 11)).pack(pady=(20, 5))
        tk.Label(dialog, text=result,
                 bg=self.config.COLOR_WHITE, fg=result_color,
                 font=("Arial", 40, "bold")).pack(pady=10)

        details = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        details.pack(pady=10)

        v = data.get("output_voltage", 0.0)
        i = data.get("measured_current", 0.0)
        for line in [
            f"Model:    {self.model_info.get('name', self.model_info.get('model_key', ''))}",
            f"SN:       {self.serial_number}",
            f"Operator: {self.operator}",
            f"Napięcie: {v:.0f} V",
            f"Prąd:     {i:.3f} mA",
            f"Data:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]:
            tk.Label(details, text=line, bg=self.config.COLOR_WHITE,
                     font=("Courier", 10)).pack(anchor="w")

        tk.Frame(dialog, bg="#cccccc", height=1).pack(
            fill=tk.X, padx=20, pady=10)

        tk.Label(dialog, text="Zeskanuj kolejny numer seryjny:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11, "bold")).pack(pady=(0, 5))

        next_entry = tk.Entry(dialog, font=("Arial", 14, "bold"), width=28,
                              justify="center", relief=tk.SOLID, borderwidth=2)
        next_entry.pack(pady=5, padx=30)
        next_entry.focus()

        status_lbl = tk.Label(dialog, text="", bg=self.config.COLOR_WHITE,
                              fg=self.config.COLOR_ERROR, font=("Arial", 9))
        status_lbl.pack()

        def next_test():
            from models import PowerSupplyModels
            new_serial = next_entry.get().strip()
            model_key = self.model_info.get("model_key", "")
            valid, msg = PowerSupplyModels.validate_serial(model_key, new_serial)
            if not valid:
                status_lbl.config(text=f"✗ {msg}")
                next_entry.delete(0, tk.END)
                next_entry.focus()
                return
            dialog.destroy()
            # Reset stanu i ponowne show() z nowym SN
            self.serial_number = new_serial
            self.test_result = None
            self.elapsed_time = 0.0
            self.current_voltage = 0.0
            self.current_current = 0.0
            self.show()

        def back_to_menu():
            dialog.destroy()
            if self.device:
                self.device.disconnect()
            if self.app_ref:
                self.app_ref.show_scan_screen()

        next_entry.bind("<Return>", lambda e: next_test())

        bf = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        bf.pack(pady=15)
        tk.Button(bf, text="ZATWIERDŹ",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 12, "bold"), width=14, height=2,
                  relief=tk.FLAT, cursor="hand2",
                  command=next_test).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Powrót do menu",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 12, "bold"), width=14, height=2,
                  relief=tk.FLAT, cursor="hand2",
                  command=back_to_menu).pack(side=tk.LEFT, padx=5)