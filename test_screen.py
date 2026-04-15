# test_screen.py
"""Ekran testowania Hi-Pot"""
import tkinter as tk
from tkinter import messagebox
import threading
import time
from datetime import datetime
from hipot_device import ChromaHiPotDevice
from logger import save_report


class TestScreen:

    def __init__(self, parent, config, serial_number, model_info, operator, app_ref=None):
        self.parent = parent
        self.config = config
        self.serial_number = serial_number
        self.model_info = model_info
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

        # Ostatni niezerowy pomiar — do zapisu w logu
        self.last_valid_voltage = 0.0
        self.last_valid_current = 0.0

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
        self.create_control_buttons()
        self.create_footer()

        self.connect_device()

    # ------------------------------------------------------------------ #
    #  HEADER / FOOTER                                                     #
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
        if self.device:
            self.device.disconnect()
        if self.app_ref:
            self.app_ref.show_scan_screen()

    # ------------------------------------------------------------------ #
    #  PANELE INFORMACYJNE                                                 #
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
        tk.Label(info_content, text=self.serial_number, bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 11)
                 ).grid(row=0, column=3, sticky='w')

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
    #  LIVE DISPLAY                                                        #
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
    #  PASEK POSTĘPU + PRZYCISKI                                           #
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
    #  POŁĄCZENIE I KONFIGURACJA                                           #
    # ------------------------------------------------------------------ #
    def connect_device(self):
        try:
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
    #  LOGIKA TESTU                                                        #
    # ------------------------------------------------------------------ #
    def start_test(self):
        self.test_running = True
        self.start_time = time.time()

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

            while self.test_running:
                status = self.device.get_status()
                if status == "STOPPED":
                    break

                measurements = self.device.read_measurements()
                if measurements:
                    v = measurements['output_voltage']
                    i = measurements['measure_current'] * 1000  # A → mA

                    self.current_voltage = v
                    self.current_current = i

                    # Zapamiętaj ostatni niezerowy pomiar
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

        # ── ZAPIS LOGU ────────────────────────────────────────────────
        p = self.model_info['test_params']
        error_code = str(data.get("error_code", "")) if data else ""
        try:
            log_path = save_report(
                operator   = self.operator,
                program    = self.model_info["model_key"],
                serial     = self.serial_number,
                mode       = p.get("mode", "WVAC"),
                vtm        = self.last_valid_voltage / 1000,  # V → kV
                im         = self.last_valid_current,          # już w mA
                low        = p["current_limit_low"],
                high       = p["current_limit_high"],
                result     = result,
                error_code = error_code,
            )
            print(f"[LOG] Zapisano: {log_path}")
        except Exception as e:
            print(f"[LOG] Błąd zapisu logu: {e}")
        # ─────────────────────────────────────────────────────────────

        self.show_result_and_next_serial(result, data)

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
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.back_button.config(state='normal')
        self.status_label.config(
            text="⚠ Test przerwany przez użytkownika", fg="#FF9800")

    # ------------------------------------------------------------------ #
    #  OKNO WYNIKÓW + KOLEJNY SN                                           #
    # ------------------------------------------------------------------ #
    def show_result_and_next_serial(self, result, data):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Wynik testu")
        dialog.geometry("450x420")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth()  // 2) - (dialog.winfo_width()  // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        result_color = self.config.COLOR_ACCENT if result == "PASS" else self.config.COLOR_ERROR

        tk.Label(dialog, text="WYNIK TESTU", bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 11)).pack(pady=(20, 5))

        tk.Label(dialog, text=result, bg=self.config.COLOR_WHITE,
                 fg=result_color, font=("Arial", 40, "bold")).pack()

        details = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        details.pack(pady=10)

        for text in [
            f"Model: {self.model_info['name']}",
            f"S/N: {self.serial_number}",
            f"Operator: {self.operator}",
            f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]:
            tk.Label(details, text=text, bg=self.config.COLOR_WHITE,
                     font=("Arial", 10)).pack(anchor='w')

        tk.Frame(dialog, bg="#cccccc", height=1).pack(fill=tk.X, padx=20, pady=10)

        tk.Label(dialog, text="Zeskanuj kolejny numer seryjny:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11, "bold")).pack(pady=(0, 5))

        next_serial_entry = tk.Entry(
            dialog, font=("Arial", 14, "bold"), width=28,
            justify='center', relief=tk.SOLID, borderwidth=2)
        next_serial_entry.pack(pady=5, padx=30)
        next_serial_entry.focus()

        status_lbl = tk.Label(dialog, text="", bg=self.config.COLOR_WHITE,
                              font=("Arial", 9))
        status_lbl.pack()

        btn_frame = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        btn_frame.pack(pady=15)

        def next_test():
            new_serial = next_serial_entry.get().strip().upper()
            from models import PowerSupplyModels
            valid, msg = PowerSupplyModels.validate_serial(
                self.model_info['model_key'], new_serial)
            if not valid:
                status_lbl.config(text=f"✗ {msg}", fg=self.config.COLOR_ERROR)
                next_serial_entry.delete(0, tk.END)
                next_serial_entry.focus()
                return

            # Aktualizuj SN i resetuj wszystkie zmienne
            self.serial_number = new_serial
            self.test_result = None
            self.elapsed_time = 0.0
            self.current_voltage = 0.0
            self.current_current = 0.0
            self.last_valid_voltage = 0.0
            self.last_valid_current = 0.0

            # Reset wyświetlania
            self.voltage_label.config(text="0 V")
            self.current_label.config(text="0.00 mA")
            self.time_label.config(text="0.0 s")
            self.progress_canvas.coords(self.progress_rect, 0, 0, 0, 30)
            self.status_label.config(
                text="✓ Gotowy do testu — urządzenie skonfigurowane",
                fg=self.config.COLOR_ACCENT)

            # Odblokuj przyciski
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.back_button.config(state='normal')

            dialog.destroy()

        def back_to_menu():
            dialog.destroy()
            if self.device:
                self.device.disconnect()
            if self.app_ref:
                self.app_ref.show_scan_screen()

        next_serial_entry.bind("<Return>", lambda e: next_test())

        tk.Button(btn_frame, text="ZATWIERDŹ",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 12, "bold"), width=14, height=2,
                  relief=tk.FLAT, cursor="hand2",
                  command=next_test).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Powrót do menu",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 12, "bold"), width=14, height=2,
                  relief=tk.FLAT, cursor="hand2",
                  command=back_to_menu).pack(side=tk.LEFT, padx=5)