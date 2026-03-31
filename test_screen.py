# test_screen.py
"""
Ekran testowania Hi-Pot
"""
import tkinter as tk
from tkinter import messagebox
import threading
import time
from datetime import datetime
from hipot_device import ChromaHiPotDevice


class TestScreen:
    """Klasa ekranu testowania Hi-Pot"""

    def __init__(self, parent, config, serial_number, model_info, operator):
        self.parent = parent
        self.config = config
        self.serial_number = serial_number
        self.model_info = model_info
        self.operator = operator

        self.device = None
        self.test_running = False
        self.test_thread = None
        self.start_time = None

        # Zmienne do wyświetlania
        self.current_voltage = 0.0
        self.current_current = 0.0
        self.elapsed_time = 0.0
        self.test_result = None

    def show(self):
        """Wyświetla ekran testowania"""
        # Usuń poprzednią zawartość (oprócz nagłówka i stopki)
        for widget in self.parent.winfo_children():
            if widget.winfo_class() != 'Frame':
                continue
            # Sprawdź czy to nie nagłówek ani stopka
            if widget.winfo_y() > 70 and widget.winfo_y() < self.parent.winfo_height() - 50:
                widget.destroy()

        # Główna ramka testowania
        self.main_frame = tk.Frame(self.parent, bg=self.config.COLOR_BG)
        self.main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(90, 60))

        # Informacje o testowanym urządzeniu
        self.create_device_info()

        # Panel parametrów testu
        self.create_test_params()

        # Wyświetlacz wyników na żywo
        self.create_live_display()

        # Pasek postępu
        self.create_progress_bar()

        # Przyciski sterowania
        self.create_control_buttons()

        # Połącz z urządzeniem
        self.connect_device()

    def create_device_info(self):
        """Tworzy panel z informacjami o testowanym urządzeniu"""
        info_frame = tk.Frame(
            self.main_frame,
            bg=self.config.COLOR_WHITE,
            relief=tk.RAISED,
            borderwidth=2
        )
        info_frame.pack(fill=tk.X, pady=(0, 15))

        # Grid layout
        info_content = tk.Frame(info_frame, bg=self.config.COLOR_WHITE)
        info_content.pack(padx=20, pady=15)

        # Model
        tk.Label(
            info_content,
            text="Model:",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 11, "bold")
        ).grid(row=0, column=0, sticky='w', padx=(0, 10))

        tk.Label(
            info_content,
            text=self.model_info['name'],
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=0, column=1, sticky='w', padx=(0, 30))

        # Numer seryjny
        tk.Label(
            info_content,
            text="S/N:",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 11, "bold")
        ).grid(row=0, column=2, sticky='w', padx=(0, 10))

        tk.Label(
            info_content,
            text=self.serial_number,
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=0, column=3, sticky='w')

    def create_test_params(self):
        """Tworzy panel z parametrami testu"""
        params_frame = tk.Frame(
            self.main_frame,
            bg=self.config.COLOR_WHITE,
            relief=tk.RAISED,
            borderwidth=2
        )
        params_frame.pack(fill=tk.X, pady=(0, 15))

        # Tytuł
        tk.Label(
            params_frame,
            text="Parametry testu",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 12, "bold")
        ).pack(pady=(15, 10))

        # Grid z parametrami
        params_grid = tk.Frame(params_frame, bg=self.config.COLOR_WHITE)
        params_grid.pack(padx=20, pady=(0, 15))

        params = self.model_info['test_params']

        # Napięcie
        self.create_param_label(params_grid, 0, 0, "Napięcie:",
                                f"{params['voltage']}V ±{params['voltage_tolerance']}V")

        # Tryb
        self.create_param_label(params_grid, 0, 2, "Tryb:",
                                f"{params['mode']}")

        # Limit prądu
        self.create_param_label(params_grid, 1, 0, "Limit prądu:",
                                f"{params['current_limit_low']}mA - {params['current_limit_high']}mA")

        # Czas testu
        total_time = params['ramp_time'] + params['test_time'] + params['fall_time']
        self.create_param_label(params_grid, 1, 2, "Czas całkowity:",
                                f"{total_time}s")

    def create_param_label(self, parent, row, col, label_text, value_text):
        """Pomocnicza funkcja do tworzenia etykiet parametrów"""
        tk.Label(
            parent,
            text=label_text,
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 10)
        ).grid(row=row, column=col, sticky='w', padx=(0, 5), pady=5)

        tk.Label(
            parent,
            text=value_text,
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 10, "bold")
        ).grid(row=row, column=col + 1, sticky='w', padx=(0, 30), pady=5)

    def create_live_display(self):
        """Tworzy wyświetlacz pomiarów na żywo"""
        display_frame = tk.Frame(
            self.main_frame,
            bg=self.config.COLOR_WHITE,
            relief=tk.RAISED,
            borderwidth=2
        )
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Tytuł
        tk.Label(
            display_frame,
            text="Pomiary na żywo",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 12, "bold")
        ).pack(pady=(15, 10))

        # Grid z wyświetlaczami
        display_grid = tk.Frame(display_frame, bg=self.config.COLOR_WHITE)
        display_grid.pack(expand=True, pady=20)

        # Napięcie
        voltage_frame = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        voltage_frame.grid(row=0, column=0, padx=40)

        tk.Label(
            voltage_frame,
            text="NAPIĘCIE",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 10)
        ).pack()

        self.voltage_label = tk.Label(
            voltage_frame,
            text="0 V",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 32, "bold")
        )
        self.voltage_label.pack(pady=5)

        # Prąd
        current_frame = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        current_frame.grid(row=0, column=1, padx=40)

        tk.Label(
            current_frame,
            text="PRĄD",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 10)
        ).pack()

        self.current_label = tk.Label(
            current_frame,
            text="0.00 mA",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_ACCENT,
            font=("Arial", 32, "bold")
        )
        self.current_label.pack(pady=5)

        # Czas
        time_frame = tk.Frame(display_grid, bg=self.config.COLOR_WHITE)
        time_frame.grid(row=0, column=2, padx=40)

        tk.Label(
            time_frame,
            text="CZAS",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 10)
        ).pack()

        self.time_label = tk.Label(
            time_frame,
            text="0.0 s",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 32, "bold")
        )
        self.time_label.pack(pady=5)

    def create_progress_bar(self):
        """Tworzy pasek postępu"""
        progress_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        # Status testu
        self.status_label = tk.Label(
            progress_frame,
            text="Gotowy do rozpoczęcia testu",
            bg=self.config.COLOR_BG,
            fg="#666666",
            font=("Arial", 11)
        )
        self.status_label.pack(pady=(0, 8))

        # Pasek postępu (canvas)
        self.progress_canvas = tk.Canvas(
            progress_frame,
            height=30,
            bg=self.config.COLOR_WHITE,
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.progress_canvas.pack(fill=tk.X)

        # Prostokąt postępu
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 30,
            fill=self.config.COLOR_ACCENT,
            outline=""
        )

    def create_control_buttons(self):
        """Tworzy przyciski sterowania"""
        button_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_BG)
        button_frame.pack(fill=tk.X)

        # Przycisk START
        self.start_button = tk.Button(
            button_frame,
            text="START TEST",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"),
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.start_test
        )
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        # Przycisk STOP
        self.stop_button = tk.Button(
            button_frame,
            text="STOP",
            bg=self.config.COLOR_ERROR,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"),
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            state='disabled',
            command=self.stop_test
        )
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # Przycisk NOWY TEST
        self.new_test_button = tk.Button(
            button_frame,
            text="NOWY TEST",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"),
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.new_test
        )
        self.new_test_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    def connect_device(self):
        """Łączy się z urządzeniem Hi-Pot"""
        try:
            # Użyj symulatora jeśli włączony tryb symulacji
            if self.config.SIMULATION_MODE:
                from hipot_device import ChromaHiPotDeviceSimulator
                self.device = ChromaHiPotDeviceSimulator()
                self.status_label.config(
                    text="🔧 Tryb symulacji (bez fizycznego urządzenia)",
                    fg="#FF9800"
                )
            else:
                from hipot_device import ChromaHiPotDevice
                self.device = ChromaHiPotDevice(
                    port=self.config.DEFAULT_COM_PORT,
                    baudrate=self.config.DEFAULT_BAUDRATE
                )
                self.status_label.config(
                    text="Łączenie z urządzeniem Hi-Pot...",
                    fg="#FF9800"
                )

            if self.device.connect():
                if self.config.SIMULATION_MODE:
                    self.status_label.config(
                        text="✓ Symulator gotowy do pracy",
                        fg=self.config.COLOR_ACCENT
                    )
                else:
                    self.status_label.config(
                        text="✓ Połączono z urządzeniem Hi-Pot",
                        fg=self.config.COLOR_ACCENT
                    )
                # Konfiguruj test
                self.configure_test()
            else:
                self.status_label.config(
                    text="✗ Błąd połączenia z urządzeniem!",
                    fg=self.config.COLOR_ERROR
                )
                self.start_button.config(state='disabled')

        except Exception as e:
            self.status_label.config(
                text=f"✗ Błąd: {str(e)}",
                fg=self.config.COLOR_ERROR
            )
            self.start_button.config(state='disabled')

    def configure_test(self):
        """Konfiguruje parametry testu w urządzeniu"""
        try:
            params = self.model_info['test_params']

            # Wyczyść poprzednie kroki
            self.device.clear_steps()

            # Skonfiguruj STEP 1
            self.device.configure_test(
                step=1,
                mode=params['mode'],
                params={
                    'voltage': params['voltage'],
                    'current_limit': params['current_limit_high'] / 1000,  # Convert mA to A
                    'duration': params['test_time'],
                    'ramp_time': params['ramp_time']
                }
            )

            self.status_label.config(
                text="✓ Urządzenie skonfigurowane i gotowe",
                fg=self.config.COLOR_ACCENT
            )

        except Exception as e:
            self.status_label.config(
                text=f"✗ Błąd konfiguracji: {str(e)}",
                fg=self.config.COLOR_ERROR
            )

    def start_test(self):
        """Rozpoczyna test w osobnym wątku"""
        self.test_running = True
        self.start_time = time.time()

        # Zmień stan przycisków
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.new_test_button.config(state='disabled')

        # Status
        self.status_label.config(
            text="🔄 Test w toku...",
            fg="#FF9800"
        )

        # Uruchom test w osobnym wątku
        self.test_thread = threading.Thread(target=self.run_test_background, daemon=True)
        self.test_thread.start()

    def run_test_background(self):
        """Test wykonywany w tle (nie blokuje GUI)"""
        try:
            # Wyślij komendę START do urządzenia
            self.device.start_test()

            params = self.model_info['test_params']
            total_time = params['ramp_time'] + params['test_time'] + params['fall_time']

            # Pętla monitorowania testu
            while self.test_running:
                # Sprawdź status urządzenia
                status = self.device.get_status()

                if status == "STOPPED":
                    # Test zakończony
                    break

                # Odczytaj pomiary
                measurements = self.device.read_measurements()

                if measurements:
                    self.current_voltage = measurements['output_voltage']
                    self.current_current = measurements['measure_current'] * 1000  # A to mA

                # Oblicz upłynięty czas
                self.elapsed_time = time.time() - self.start_time

                # Aktualizuj GUI (przez root.after!)
                self.parent.after(0, self.update_display)

                # Sprawdź czy przekroczono czas
                if self.elapsed_time > total_time + 5:  # +5s bufora
                    break

                time.sleep(0.1)  # Odświeżanie co 100ms

            # Test zakończony - pobierz wyniki
            self.parent.after(0, self.test_completed)

        except Exception as e:
            self.parent.after(0, lambda: self.test_error(str(e)))

    def update_display(self):
        """Aktualizuje wyświetlacz (wywoływane z głównego wątku)"""
        # Aktualizuj wartości
        self.voltage_label.config(text=f"{int(self.current_voltage)} V")
        self.current_label.config(text=f"{self.current_current:.2f} mA")
        self.time_label.config(text=f"{self.elapsed_time:.1f} s")

        # Aktualizuj pasek postępu
        params = self.model_info['test_params']
        total_time = params['ramp_time'] + params['test_time'] + params['fall_time']
        progress_percent = min(self.elapsed_time / total_time, 1.0)

        canvas_width = self.progress_canvas.winfo_width()
        progress_width = canvas_width * progress_percent

        self.progress_canvas.coords(
            self.progress_rect,
            0, 0, progress_width, 30
        )

    def test_completed(self):
        """Wywoływane gdy test się zakończył"""
        self.test_running = False

        # Pobierz wynik
        result, data = self.device.get_test_result()
        self.test_result = result

        # Zmień stan przycisków
        self.start_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.new_test_button.config(state='normal')

        # Wyświetl wynik
        if result == "PASS":
            self.status_label.config(
                text="✓ TEST ZALICZONY (PASS)",
                fg=self.config.COLOR_ACCENT
            )
            self.show_result_dialog("PASS", data)
        else:
            self.status_label.config(
                text="✗ TEST NIEZALICZONY (FAIL)",
                fg=self.config.COLOR_ERROR
            )
            self.show_result_dialog("FAIL", data)

    def test_error(self, error_message):
        """Wywoływane gdy wystąpił błąd"""
        self.test_running = False

        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.new_test_button.config(state='normal')

        self.status_label.config(
            text=f"✗ Błąd testu: {error_message}",
            fg=self.config.COLOR_ERROR
        )

    def stop_test(self):
        """Zatrzymuje test"""
        self.test_running = False

        if self.device:
            self.device.stop_test()

        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.new_test_button.config(state='normal')

        self.status_label.config(
            text="⚠ Test przerwany przez użytkownika",
            fg="#FF9800"
        )

    def show_result_dialog(self, result, data):
        """Pokazuje dialog z wynikiem testu"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Wynik testu")
        dialog.geometry("400x300")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.parent)
        dialog.grab_set()

        # Wycentruj dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        # Wynik
        result_color = self.config.COLOR_ACCENT if result == "PASS" else self.config.COLOR_ERROR

        tk.Label(
            dialog,
            text="WYNIK TESTU",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 11)
        ).pack(pady=(20, 5))

        tk.Label(
            dialog,
            text=result,
            bg=self.config.COLOR_WHITE,
            fg=result_color,
            font=("Arial", 36, "bold")
        ).pack(pady=10)

        # Szczegóły
        details_frame = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        details_frame.pack(pady=20)

        tk.Label(
            details_frame,
            text=f"Model: {self.model_info['name']}",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 10)
        ).pack(anchor='w')

        tk.Label(
            details_frame,
            text=f"S/N: {self.serial_number}",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 10)
        ).pack(anchor='w')

        tk.Label(
            details_frame,
            text=f"Operator: {self.operator}",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 10)
        ).pack(anchor='w')

        tk.Label(
            details_frame,
            text=f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 10)
        ).pack(anchor='w')

        # Przycisk OK
        tk.Button(
            dialog,
            text="OK",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 12, "bold"),
            width=15,
            relief=tk.FLAT,
            cursor="hand2",
            command=dialog.destroy
        ).pack(pady=20)

    def new_test(self):
        """Powrót do skanowania nowego numeru seryjnego"""
        # Rozłącz urządzenie
        if self.device:
            self.device.disconnect()

        # Usuń ekran testowania
        self.main_frame.destroy()

        # Pokaż ekran skanowania (reimport aby uniknąć circular import)
        from gui import HiPotTesterApp
        # Tutaj trzeba będzie wywołać metodę create_scan_panel z gui.py
        # Na razie wyświetl komunikat
        messagebox.showinfo("Nowy test", "Powrót do skanowania numeru seryjnego...")
