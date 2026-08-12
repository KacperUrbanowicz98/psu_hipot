# test_screen.py
"""
Ekran testowania Hi-Pot.

Najważniejsze poprawki względem wersji pierwotnej opisane są komentarzami
"POPRAWKA:" w miejscu zmiany. Skrót:
  1. Test nigdy nie startuje przy otwartej lub nieznanej klapie.
  2. Test przerwany (STOP / otwarta klapa) nie jest już zapisywany jako FAIL.
  3. Prąd w raporcie nie jest już mnożony przez 1000 dwa razy.
  4. Łączenie z urządzeniami odbywa się w tle — wejście na ekran testu
     nie zamraża okna na kilka sekund.
  5. Błąd wątku testowego jest wreszcie pokazywany operatorowi
     (poprzednio ginął w NameError i ekran wisiał na "Test w toku").
  6. Nieudany zapis raportu jest widoczny i ma kopię awaryjną.
  7. Statystyki liczone są w tle i z pamięcią podręczną.
"""
import os
import queue
import re
import threading
import time
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from logger import save_report
from shift_stats import ShiftStats, get_current_shift, parse_shift_file

# Ile kolejnych nieudanych transakcji RS232 uznajemy za zerwaną komunikację
MAX_COMM_ERRORS = 15
# Awaryjny margines ponad zaplanowany czas testu
TEST_GRACE_SECONDS = 5.0


class TestScreen:

    def __init__(self, parent, config, serial_number, model_info, operator,
                 app_ref=None, stats=None):
        self.parent        = parent
        self.config        = config
        self.serial_number = serial_number
        self.model_info    = model_info
        self.operator      = operator
        self.app_ref       = app_ref
        self.stats         = stats            # StatsManager (dzienne)

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

        self.interlock              = None
        self._prev_interlock_closed = None
        self._test_completed_called = False

        # POPRAWKA: rozróżnienie "test zakończony przez urządzenie" od
        # "test przerwany". Bez tego każde naciśnięcie STOP i każde otwarcie
        # klapy kończyło się zapisem raportu FAIL i zliczeniem sztuki.
        self._abort_requested = False
        self._abort_reason    = ""

        self._closed        = False
        self._pending_start = False
        self._ui_queue      = queue.Queue()
        self._pump_id       = None
        self._ui_refresh_scheduled = False

        self.sn_dialog       = None
        self.sn_entry        = None
        self.sn_result_label = None
        self.sn_status_lbl   = None

        self.lbl_shift_name  = None
        self.lbl_shift_hours = None
        self.lbl_total       = None
        self.lbl_pass        = None
        self.lbl_fail        = None
        self.lbl_retests     = None

        self._recent_results = []
        self._history_frame  = None

        self.shift_stats = None
        self._current_sn_is_duplicate = False
        self._dup_banner = None

        self._prev_close_handler = None

    # ------------------------------------------------------------------ #
    # NARZĘDZIA POMOCNICZE                                                #
    # ------------------------------------------------------------------ #
    def _alive(self) -> bool:
        """Czy ekran wciąż istnieje (operator nie wrócił do menu)."""
        if self._closed:
            return False
        if threading.current_thread() is not threading.main_thread():
            # Zapytania o widgety wolno zadawać tylko z wątku GUI.
            return True
        try:
            return bool(self.parent.winfo_exists())
        except Exception:
            return False

    def _ui(self, func, *args):
        """
        Przekazanie zadania do wątku GUI.

        POPRAWKA: poprzednio wątki (test, interlock, sprawdzanie duplikatu)
        wołały bezpośrednio parent.after(). Tkinter wpuszcza takie wywołanie
        dopiero, gdy główna pętla jest wolna — przy otwartym oknie modalnym
        (np. ostrzeżenie o duplikacie) wątek interlocka ZATRZYMYWAŁ SIĘ na
        tym wywołaniu i przestawał czytać stan klapy. Teraz zadania trafiają
        do kolejki, którą wątek GUI opróżnia cyklicznie — żaden wątek
        roboczy nie dotyka już Tk.
        """
        if self._closed:
            return
        if threading.current_thread() is threading.main_thread():
            if self._alive():
                try:
                    func(*args)
                except Exception as e:
                    print(f"[UI] Błąd callbacku: {e}")
            return
        self._ui_queue.put((func, args))

    def _pump_ui(self):
        self._pump_id = None
        if self._closed:
            return
        while True:
            try:
                func, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                if self._alive():
                    func(*args)
            except Exception as e:
                print(f"[UI] Błąd callbacku z kolejki: {e}")
        if not self._closed:
            try:
                self._pump_id = self.parent.after(40, self._pump_ui)
            except Exception:
                pass

    @staticmethod
    def _cfg(widget, **kwargs):
        """config() odporny na zniszczony widget."""
        try:
            if widget is not None and widget.winfo_exists():
                widget.config(**kwargs)
        except Exception:
            pass

    def _interlock_active(self) -> bool:
        return bool(self.interlock is not None
                    and getattr(self.config, "INTERLOCK_ENABLED", True))

    # ------------------------------------------------------------------ #
    # SHOW                                                                 #
    # ------------------------------------------------------------------ #
    def show(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

        # POPRAWKA: w trakcie testu skrót Ctrl+Alt+D otwierał panel
        # administratora nad pracującym stanowiskiem.
        for seq in ("<Control-Alt-d>", "<Control-Alt-D>"):
            try:
                self.parent.unbind(seq)
            except Exception:
                pass

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
        self.create_footer()

        # POPRAWKA: zamknięcie okna krzyżykiem w trakcie testu zostawiało
        # włączone wysokie napięcie na urządzeniu.
        try:
            self._prev_close_handler = self.parent.protocol("WM_DELETE_WINDOW")
        except Exception:
            self._prev_close_handler = None
        self.parent.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self.start_button.config(state="disabled")
        self.stop_button.config(state="disabled")

        self._pump_ui()          # pompa zadań z wątków roboczych

        try:
            self.shift_stats = ShiftStats(log_dir=self.config.LOG_DIR,
                                          operator=self.operator)
            self.shift_stats.on_rebuilt = lambda: self._ui(self.update_counter)
        except Exception as e:
            # Niedostępny dysk sieciowy nie może uniemożliwić testowania.
            self.shift_stats = None
            print(f"[SHIFT] Nie udało się uruchomić licznika zmiany: {e}")

        self.update_counter()

        # POPRAWKA: łączenie z Chromą i Arduino w wątku tła. Poprzednio
        # connect() + configure_test() + interlock.connect() wykonywały się
        # w wątku GUI — okno było zamrożone nawet ~7 s przy każdym wejściu
        # na ekran testu i wyglądało jak zawieszona aplikacja.
        self.status_label.config(text="⏳ Łączenie z urządzeniami...", fg="#FF9800")
        threading.Thread(target=self._connect_hardware_worker, daemon=True).start()

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
                              lambda e: self._cfg(self.back_button, bg="#1a5276"))
        self.back_button.bind("<Leave>",
                              lambda e: self._cfg(self.back_button,
                                                  bg=self.config.COLOR_PRIMARY))

    def create_footer(self):
        footer_frame = tk.Frame(self.parent, bg=self.config.COLOR_PRIMARY, height=40)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)
        tk.Label(footer_frame, text="Autor: Kacper Urbanowicz",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=20, pady=10)

    # ------------------------------------------------------------------ #
    # ZAMYKANIE EKRANU                                                     #
    # ------------------------------------------------------------------ #
    def go_back(self):
        if self.test_running:
            messagebox.showwarning(
                "Test w toku",
                "Nie można wrócić do menu podczas testu!\n"
                "Zatrzymaj test przyciskiem STOP.",
                parent=self.parent)
            return
        self._cleanup_and_go_back()

    def _on_window_close(self):
        """Krzyżyk okna głównego w trakcie pracy ekranu testu."""
        if self.test_running:
            if not messagebox.askyesno(
                    "Test w toku",
                    "Test jest w toku. Zamknąć aplikację?\n"
                    "Wysokie napięcie zostanie wyłączone.",
                    parent=self.parent):
                return
            self._abort_test("Zamknięcie aplikacji")
            time.sleep(0.3)
        self._shutdown_hardware()
        if self.app_ref is not None:
            self.app_ref.close_application()
        else:
            self.parent.destroy()

    def _shutdown_hardware(self):
        self._closed = True
        if self._pump_id is not None:
            try:
                self.parent.after_cancel(self._pump_id)
            except Exception:
                pass
            self._pump_id = None
        if self.shift_stats:
            try:
                self.shift_stats.stop()
            except Exception:
                pass
        if self.interlock:
            try:
                self.interlock.disconnect()
            except Exception:
                pass
            self.interlock = None
        if self.device:
            try:
                self.device.disconnect()
            except Exception:
                pass
            self.device = None

    def _cleanup_and_go_back(self):
        if self.sn_dialog is not None:
            try:
                if self.sn_dialog.winfo_exists():
                    self.sn_dialog.grab_release()
                    self.sn_dialog.destroy()
            except Exception:
                pass
            self.sn_dialog = None

        try:
            if self._prev_close_handler:
                self.parent.protocol("WM_DELETE_WINDOW", self._prev_close_handler)
        except Exception:
            pass

        self._shutdown_hardware()

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
                 font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        tk.Label(info_content, text=self.model_info.get("name", "?"),
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).grid(row=0, column=1, sticky="w", padx=(0, 30))
        tk.Label(info_content, text="S/N:", bg=self.config.COLOR_WHITE,
                 fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 11, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.sn_display_label = tk.Label(
            info_content, text=self.serial_number,
            bg=self.config.COLOR_WHITE, fg="#333333", font=("Arial", 11))
        self.sn_display_label.grid(row=0, column=3, sticky="w")

    def create_test_params(self):
        params_frame = tk.Frame(self.main_frame, bg=self.config.COLOR_WHITE,
                                relief=tk.RAISED, borderwidth=2)
        params_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(params_frame, text="Parametry testu",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(pady=(15, 10))

        params_grid = tk.Frame(params_frame, bg=self.config.COLOR_WHITE)
        params_grid.pack(padx=20, pady=(0, 15))

        p = self.model_info["test_params"]
        total_time = self._total_time()

        self.create_param_label(params_grid, 0, 0, "Napięcie:",
                                f"{p['voltage']}V ±{p.get('voltage_tolerance', 0)}V")
        self.create_param_label(params_grid, 0, 2, "Tryb:", p["mode"])
        self.create_param_label(params_grid, 1, 0, "Limit prądu:",
                                f"{p['current_limit_low']}mA – {p['current_limit_high']}mA")
        self.create_param_label(params_grid, 1, 2, "Czas całkowity:", f"{total_time}s")

    def _total_time(self) -> float:
        p = self.model_info["test_params"]
        try:
            return float(p["ramp_time"]) + float(p["test_time"]) + float(p["fall_time"])
        except (KeyError, TypeError, ValueError):
            return 0.0

    def create_param_label(self, parent, row, col, label_text, value_text):
        tk.Label(parent, text=label_text, bg=self.config.COLOR_WHITE,
                 fg="#666666", font=("Arial", 10)
                 ).grid(row=row, column=col, sticky="w", padx=(0, 5), pady=5)
        tk.Label(parent, text=value_text, bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 10, "bold")
                 ).grid(row=row, column=col + 1, sticky="w", padx=(0, 30), pady=5)

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

        self.status_label = tk.Label(
            progress_frame, text="Gotowy do rozpoczęcia testu",
            bg=self.config.COLOR_BG, fg="#666666", font=("Arial", 11))
        self.status_label.pack(pady=(0, 8))

        self.progress_canvas = tk.Canvas(
            progress_frame, height=30, bg=self.config.COLOR_WHITE,
            highlightthickness=1, highlightbackground="#cccccc")
        self.progress_canvas.pack(fill=tk.X)
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 30, fill=self.config.COLOR_ACCENT, outline="")

    # ------------------------------------------------------------------ #
    # POŁĄCZENIE ZE SPRZĘTEM (w tle)                                       #
    # ------------------------------------------------------------------ #
    def _connect_hardware_worker(self):
        from hipot_device import ChromaHiPotDevice

        device = ChromaHiPotDevice(port=self.config.DEFAULT_COM_PORT,
                                   baudrate=self.config.DEFAULT_BAUDRATE)
        ok = False
        cfg_ok = False
        try:
            ok = device.connect()
            if ok:
                device.clear_steps()
                p = self.model_info["test_params"]
                cfg_ok = device.configure_test(
                    step=1,
                    mode=p["mode"],
                    params={
                        "voltage":            p["voltage"],
                        # Profil trzyma limity w mA, Chroma oczekuje A.
                        "current_limit_high": float(p["current_limit_high"]) / 1000.0,
                        "current_limit_low":  float(p["current_limit_low"]) / 1000.0,
                        "duration":           p["test_time"],
                        "ramp_time":          p["ramp_time"],
                        "fall_time":          p["fall_time"],
                    })
        except Exception as exc:
            print(f"[HIPOT] Wyjątek przy łączeniu: {exc}")
            ok = False

        if not self._alive():
            try:
                device.disconnect()
            except Exception:
                pass
            return

        self.device = device
        self._ui(self._on_device_ready, ok, cfg_ok)

    def _on_device_ready(self, ok: bool, cfg_ok: bool):
        if ok and cfg_ok:
            self._cfg(self.status_label,
                      text="✓ Urządzenie skonfigurowane i gotowe",
                      fg=self.config.COLOR_ACCENT)
        elif ok:
            self._cfg(self.status_label,
                      text="⚠ Połączono, ale konfiguracja kroku nie powiodła się "
                           "— sprawdź profil i urządzenie",
                      fg="#FF9800")
        else:
            self._cfg(self.status_label,
                      text=f"✗ Błąd połączenia z Hi-Pot ({self.config.DEFAULT_COM_PORT})",
                      fg=self.config.COLOR_ERROR)

        # Interlock dopiero po urządzeniu — jego connect() też trwa ~1,5 s.
        threading.Thread(target=self._connect_interlock_worker, daemon=True).start()

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

    def _connect_interlock_worker(self):
        if not getattr(self.config, "INTERLOCK_ENABLED", True):
            self._ui(self._interlock_manual_mode, "⚠ Interlock wyłączony — tryb ręczny")
            return

        port = getattr(self.config, "INTERLOCK_PORT", None)
        if not port:
            self._ui(self._interlock_manual_mode, "⚠ Brak portu Arduino — tryb ręczny")
            return

        from interlock import InterlockMonitor
        baud = getattr(self.config, "INTERLOCK_BAUDRATE", 9600)
        monitor = InterlockMonitor(port=port, baudrate=baud)
        connected = monitor.connect()

        if not self._alive():
            monitor.disconnect()
            return

        if connected:
            self.interlock = monitor
            monitor.set_on_change(self._on_interlock_change)
            monitor.start_monitoring()
            self._ui(self._interlock_waiting)
        else:
            self._ui(self._interlock_manual_mode,
                     f"✗ Błąd połączenia z Arduino ({port}) — tryb ręczny", True)

    def _interlock_manual_mode(self, text: str, is_error: bool = False):
        bg = "#ffebee" if is_error else "#fff8e1"
        fg = self.config.COLOR_ERROR if is_error else "#FF9800"
        self._cfg(self.interlock_label, text=text, fg=fg, bg=bg)
        self._cfg(self.interlock_frame, bg=bg)
        if not self.test_running:
            self._cfg(self.start_button, state="normal")

    def _interlock_waiting(self):
        self._cfg(self.interlock_label,
                  text="⏳ Oczekiwanie na stan klapy...",
                  fg="#FF9800", bg="#fff8e1")
        self._cfg(self.start_button, state="disabled")

    def _on_interlock_change(self, closed):
        self._ui(self._apply_interlock_state, closed)

    def _apply_interlock_state(self, closed):
        if closed is None:
            # Utrata łączności z Arduino — interlock nie chroni,
            # więc automatyczny start zostaje wyłączony.
            self._cfg(self.interlock_label,
                      text="⚠ Utracono połączenie z Arduino — próba wznowienia, "
                           "start ręczny",
                      fg="#FF9800", bg="#fff8e1")
            self._cfg(self.interlock_frame, bg="#fff8e1")
            self._pending_start = False
            if self.test_running:
                self._abort_test("Utrata interlocka w trakcie testu")
            else:
                self._cfg(self.start_button, state="normal")
            self._prev_interlock_closed = None
            return

        if closed:
            self._cfg(self.interlock_label,
                      text="🔒 Klapa ZAMKNIĘTA",
                      fg=self.config.COLOR_ACCENT, bg="#e8f5e9")
            self._cfg(self.interlock_frame, bg="#e8f5e9")

            if not self.test_running and self._prev_interlock_closed is False:
                if self.sn_dialog is not None and self._dialog_open():
                    # Zamknięcie klapy = potwierdzenie zeskanowanego SN
                    self._arm_next_test_from_dialog()
                else:
                    self._maybe_start_test()
            elif self._pending_start and not self.test_running:
                self._maybe_start_test()
            elif not self.test_running:
                self._cfg(self.start_button, state="normal")
        else:
            self._cfg(self.interlock_label,
                      text="🔓 Klapa OTWARTA — wyjmij urządzenie i zamknij klapę",
                      fg=self.config.COLOR_ERROR, bg="#ffebee")
            self._cfg(self.interlock_frame, bg="#ffebee")

            if self.test_running:
                # POPRAWKA: przerwanie testu nie zapisuje już wyniku FAIL.
                # Zrezygnowano też z modalnego okna messagebox w callbacku
                # interlocka — blokowało pętlę Tk, przez co ekran "zamierał"
                # do czasu kliknięcia OK.
                self._abort_test("Klapa otwarta w trakcie testu")
                try:
                    self.parent.bell()
                except Exception:
                    pass
            else:
                self._cfg(self.start_button, state="disabled")

        self._prev_interlock_closed = closed

    def _dialog_open(self) -> bool:
        try:
            return self.sn_dialog is not None and self.sn_dialog.winfo_exists()
        except Exception:
            return False

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
            cursor="hand2", command=self._maybe_start_test)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_button = tk.Button(
            button_frame, text="STOP",
            bg=self.config.COLOR_ERROR, fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"), height=2, relief=tk.FLAT,
            cursor="hand2", state="disabled", command=self.stop_test)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.next_sn_button = tk.Button(
            button_frame, text="➜ Następny SN",
            bg="#607D8B", fg=self.config.COLOR_WHITE,
            font=("Arial", 16, "bold"), height=2, relief=tk.FLAT,
            cursor="hand2", state="disabled",
            command=self._open_sn_dialog_manually)
        self.next_sn_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    # ------------------------------------------------------------------ #
    # HISTORIA + LICZNIK ZMIANY                                            #
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

        self.lbl_shift_name = tk.Label(counter_bar, text="Zmiana ?",
                                       bg=self.config.COLOR_WHITE,
                                       fg="#888888", font=("Arial", 9))
        self.lbl_shift_name.pack(side=tk.LEFT, padx=(0, 4))

        self.lbl_shift_hours = tk.Label(counter_bar, text="",
                                        bg=self.config.COLOR_WHITE,
                                        fg="#aaaaaa", font=("Arial", 8))
        self.lbl_shift_hours.pack(side=tk.LEFT, padx=(0, 10))

        for lbl_text, attr, fg in [
            ("Razem:",  "lbl_total",   "#222222"),
            ("✓ PASS:", "lbl_pass",    None),
            ("✗ FAIL:", "lbl_fail",    None),
            ("RETEST:", "lbl_retests", "#FF9800"),
        ]:
            tk.Label(counter_bar, text=lbl_text, bg=self.config.COLOR_WHITE,
                     fg="#555555", font=("Arial", 9)).pack(side=tk.LEFT)
            color = (self.config.COLOR_ACCENT if attr == "lbl_pass"
                     else self.config.COLOR_ERROR if attr == "lbl_fail"
                     else fg)
            lbl = tk.Label(counter_bar, text="0", bg=self.config.COLOR_WHITE,
                           fg=color, font=("Arial", 9, "bold"))
            lbl.pack(side=tk.LEFT, padx=(2, 10))
            setattr(self, attr, lbl)

        tk.Button(counter_bar, text="📊 Statystyki",
                  bg="#eeeeee", fg="#555555", font=("Arial", 8),
                  relief=tk.FLAT, cursor="hand2", padx=4, pady=1,
                  command=self._show_daily_stats).pack(side=tk.LEFT)

        hdr = tk.Frame(outer, bg=self.config.COLOR_PRIMARY)
        hdr.pack(fill=tk.X, padx=10, pady=(2, 0))
        for text, width in [("Czas", 8), ("Numer seryjny", 22),
                            ("Model", 16), ("Wynik", 7)]:
            tk.Label(hdr, text=text, bg=self.config.COLOR_PRIMARY,
                     fg=self.config.COLOR_WHITE, font=("Arial", 8, "bold"),
                     width=width, anchor="center", pady=2).pack(side=tk.LEFT)

        self._history_frame = tk.Frame(outer, bg=self.config.COLOR_WHITE)
        self._history_frame.pack(fill=tk.X, padx=10, pady=(1, 5))
        self._refresh_history_panel()

    def _refresh_history_panel(self):
        if not self._history_frame:
            return
        try:
            if not self._history_frame.winfo_exists():
                return
        except Exception:
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
            bg = "#f5f5f5" if idx % 2 == 0 else self.config.COLOR_WHITE
            row = tk.Frame(self._history_frame, bg=bg)
            row.pack(fill=tk.X)
            result_fg = (self.config.COLOR_ACCENT if entry["result"] == "PASS"
                         else self.config.COLOR_ERROR)
            dup_marker = " ⚠" if entry.get("duplicate") else ""
            for text, width, fg in [
                (entry["time"], 8, "#666666"),
                (entry["serial"] + dup_marker, 22,
                 "#FF9800" if entry.get("duplicate") else "#333333"),
                (entry["model"], 16, "#333333"),
                (entry["result"], 7, result_fg),
            ]:
                tk.Label(row, text=text, bg=bg, fg=fg, font=("Arial", 8),
                         width=width, anchor="center", pady=2).pack(side=tk.LEFT)

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
        """
        POPRAWKA: liczenie z plików TXT zeszło do wątku tła.
        Poprzednio każde odświeżenie licznika przeglądało cały katalog logów
        (na udziale sieciowym: tysiące plików) w wątku GUI — po każdym teście
        aplikacja "przymarzała" na sekundy.
        """
        if self.lbl_total is None:
            return

        if self.shift_stats:
            s = self.shift_stats.get_snapshot()
            self._cfg(self.lbl_shift_name, text=f"Zmiana {s['shift_name']}")
            if s["shift_start"] and s["shift_end"]:
                self._cfg(self.lbl_shift_hours,
                          text=f"{s['shift_start'].strftime('%H:%M')}–"
                               f"{s['shift_end'].strftime('%H:%M')}")

        if self.stats:
            self.stats.count_today_async(
                lambda snap: self._ui(self._apply_counter, snap))

    def _apply_counter(self, snap: dict):
        if not snap:
            return
        self._cfg(self.lbl_total, text=str(snap.get("total", 0)))
        self._cfg(self.lbl_pass,  text=str(snap.get("passed", 0)))
        self._cfg(self.lbl_fail,  text=str(snap.get("failed", 0)))
        # POPRAWKA: obok stoi już etykieta "RETEST:" — poprzednio wychodziło
        # "RETEST: RETEST 3".
        self._cfg(self.lbl_retests, text=str(snap.get("duplicates", 0)))

    # ------------------------------------------------------------------ #
    # STATYSTYKI DZIENNE                                                   #
    # ------------------------------------------------------------------ #
    def _show_daily_stats(self):
        import json as _json
        from datetime import timedelta as td

        log_dir   = getattr(self.config, "LOG_DIR", "logs")
        stats_dir = os.path.join(log_dir, "Daily PSU Hi-Pot stats")
        shift_dir = os.path.join(log_dir, "Shift Reports")

        win = tk.Toplevel(self.parent)
        win.title("Statystyki")
        win.configure(bg=self.config.COLOR_BG)
        win.geometry(f"960x720+{max(0, win.winfo_screenwidth() // 2 - 480)}+"
                     f"{max(0, win.winfo_screenheight() // 2 - 360)}")
        win.transient(self.parent)
        win.grab_set()

        hdr = tk.Frame(win, bg=self.config.COLOR_PRIMARY, height=55)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Statystyki", bg=self.config.COLOR_PRIMARY,
                 fg="white", font=("Arial", 17, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Button(hdr, text="Zamknij", bg=self.config.COLOR_ERROR,
                  fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT,
                  cursor="hand2", command=win.destroy
                  ).pack(side=tk.RIGHT, padx=15, pady=12)

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        def make_scroll(parent):
            c = tk.Canvas(parent, bg=self.config.COLOR_BG, highlightthickness=0)
            sb = ttk.Scrollbar(parent, orient="vertical", command=c.yview)
            c.configure(yscrollcommand=sb.set)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            sf = tk.Frame(c, bg=self.config.COLOR_BG)
            cw = c.create_window(0, 0, window=sf, anchor="nw")
            sf.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))
            c.bind("<Configure>", lambda e: c.itemconfig(cw, width=e.width))

            # POPRAWKA: było bind_all("<MouseWheel>") — globalna podpinka,
            # która po zamknięciu okna wskazywała na zniszczony Canvas
            # i przy każdym ruchu rolki sypała TclError w całej aplikacji.
            def _wheel(event):
                try:
                    c.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except Exception:
                    pass
            for widget in (c, sf):
                widget.bind("<MouseWheel>", _wheel)
                widget.bind("<Button-4>", lambda e: c.yview_scroll(-1, "units"))
                widget.bind("<Button-5>", lambda e: c.yview_scroll(1, "units"))
            return sf

        # ---------------- ZAKŁADKA 1 — ZMIANY ---------------- #
        tab_shifts = tk.Frame(nb, bg=self.config.COLOR_BG)
        nb.add(tab_shifts, text="  Zmiany  ")

        nav_f = tk.Frame(tab_shifts, bg=self.config.COLOR_BG)
        nav_f.pack(fill=tk.X, padx=10, pady=(8, 0))
        day_lbl = tk.Label(nav_f, text="", bg=self.config.COLOR_BG,
                           fg=self.config.COLOR_PRIMARY, font=("Arial", 12, "bold"))
        day_lbl.pack(side=tk.LEFT, padx=6)

        state = {"day": date.today(), "busy": False}
        scroll_shifts = make_scroll(tab_shifts)

        def collect_shifts(day):
            """Czyta pliki zmian — wołane z wątku tła (dysk sieciowy)."""
            out = []
            try:
                if not os.path.isdir(shift_dir):
                    return out
                for hrid in sorted(os.listdir(shift_dir)):
                    hrid_path = os.path.join(shift_dir, hrid)
                    if not os.path.isdir(hrid_path):
                        continue
                    files = [os.path.join(hrid_path, f)
                             for f in sorted(os.listdir(hrid_path))
                             if f.endswith(".txt") and day.strftime("%Y-%m-%d") in f]
                    rows = [d for d in (parse_shift_file(f) for f in files) if d]
                    if rows:
                        out.append((hrid, rows))
            except Exception as e:
                print(f"[STATS] Błąd czytania zmian: {e}")
            return out

        def render_shifts(day, data):
            if not win.winfo_exists():
                return
            for w in scroll_shifts.winfo_children():
                w.destroy()
            day_lbl.config(text="Dzisiaj" if day == date.today()
                           else day.strftime("%d.%m.%Y"))

            if not data:
                tk.Label(scroll_shifts,
                         text=f"Brak danych zmianowych dla {day.strftime('%d.%m.%Y')}.",
                         bg=self.config.COLOR_BG, fg="#888",
                         font=("Arial", 11)).pack(pady=30)
                return

            for hrid, rows in data:
                hf = tk.Frame(scroll_shifts, bg=self.config.COLOR_PRIMARY)
                hf.pack(fill=tk.X, pady=(12, 0))
                tk.Label(hf, text=f"  HRID: {hrid}", bg=self.config.COLOR_PRIMARY,
                         fg="white", font=("Arial", 12, "bold")
                         ).pack(side=tk.LEFT, padx=10, pady=6)

                for d in rows:
                    sf2 = tk.Frame(scroll_shifts, bg="#37474F")
                    sf2.pack(fill=tk.X, pady=(2, 0))
                    total = d["passed"] + d["failed"]
                    tk.Label(sf2,
                             text=f"  Zmiana {d['shift_name']}  ({d['hours']})    "
                                  f"Razem: {total}   PASS: {d['passed']}   "
                                  f"FAIL: {d['failed']}   RETEST: {d['retests']}",
                             bg="#37474F", fg="white",
                             font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10, pady=5)

                    if not d["models"]:
                        continue

                    col_hdr = tk.Frame(scroll_shifts, bg="#ECEFF1")
                    col_hdr.pack(fill=tk.X)
                    for txt, w in [("Model", 280), ("PASS", 80), ("FAIL", 80),
                                   ("RETEST", 80), ("Razem", 80)]:
                        tk.Label(col_hdr, text=txt, bg="#ECEFF1", fg="#333",
                                 font=("Arial", 9, "bold"), width=w // 8,
                                 anchor="center").pack(side=tk.LEFT, padx=2, pady=3)

                    for i, (mk, cnt) in enumerate(sorted(d["models"].items())):
                        bg = "#ffffff" if i % 2 == 0 else "#f5f5f5"
                        row = tk.Frame(scroll_shifts, bg=bg)
                        row.pack(fill=tk.X)
                        for val, w, fg in [
                            (mk, 280, "#333"),
                            (cnt["pass"], 80, self.config.COLOR_ACCENT),
                            (cnt["fail"], 80,
                             self.config.COLOR_ERROR if cnt["fail"] > 0 else "#333"),
                            (cnt["retest"], 80,
                             "#FF9800" if cnt["retest"] > 0 else "#aaa"),
                            (cnt["pass"] + cnt["fail"], 80, "#222"),
                        ]:
                            tk.Label(row, text=str(val), bg=bg, fg=fg,
                                     font=("Arial", 10), width=w // 8,
                                     anchor="center").pack(side=tk.LEFT, padx=2, pady=2)

        def load_shifts(day):
            if state["busy"]:
                return
            state["busy"] = True
            for w in scroll_shifts.winfo_children():
                w.destroy()
            tk.Label(scroll_shifts, text="Wczytywanie...", bg=self.config.COLOR_BG,
                     fg="#888", font=("Arial", 11)).pack(pady=30)

            def worker():
                data = collect_shifts(day)
                state["busy"] = False
                try:
                    if win.winfo_exists():
                        win.after(0, lambda: render_shifts(day, data))
                except Exception:
                    pass
            threading.Thread(target=worker, daemon=True).start()

        def change_shift_day(delta):
            state["day"] = state["day"] + td(days=delta)
            load_shifts(state["day"])

        tk.Button(nav_f, text="◀ Poprzedni", bg="#607D8B", fg="white",
                  font=("Arial", 9), relief=tk.FLAT, cursor="hand2",
                  command=lambda: change_shift_day(-1)).pack(side=tk.LEFT, padx=4)
        tk.Button(nav_f, text="Następny ▶", bg="#607D8B", fg="white",
                  font=("Arial", 9), relief=tk.FLAT, cursor="hand2",
                  command=lambda: change_shift_day(1)).pack(side=tk.LEFT, padx=4)

        # ---------------- ZAKŁADKA 2 — HISTORIA DZIENNA ---------------- #
        tab_daily = tk.Frame(nb, bg=self.config.COLOR_BG)
        nb.add(tab_daily, text="  Historia dzienna  ")

        nav2 = tk.Frame(tab_daily, bg=self.config.COLOR_BG)
        nav2.pack(fill=tk.X, padx=10, pady=(8, 0))
        day2_lbl = tk.Label(nav2, text="", bg=self.config.COLOR_BG,
                            fg=self.config.COLOR_PRIMARY, font=("Arial", 12, "bold"))
        day2_lbl.pack(side=tk.LEFT, padx=6)

        state2 = {"day": date.today(), "busy": False}
        scroll_daily = make_scroll(tab_daily)

        def load_daily(day):
            path = os.path.join(stats_dir, f"stats_{day.strftime('%Y-%m-%d')}.json")
            try:
                if not os.path.exists(path):
                    return {}
                with open(path, "r", encoding="utf-8") as f:
                    raw = _json.load(f)
                result = {}
                for op, rows in raw.items():
                    if not isinstance(rows, dict):
                        continue
                    result[op] = [{"model": e.get("model", "?"),
                                   "mode": e.get("mode", "AC"),
                                   "pass": e.get("pass", 0),
                                   "fail": e.get("fail", 0),
                                   "retest": e.get("retest", 0),
                                   "total": e.get("pass", 0) + e.get("fail", 0)}
                                  for e in rows.values() if isinstance(e, dict)]
                return result
            except Exception as e:
                print(f"[STATS] Błąd odczytu {path}: {e}")
                return {}

        def render_daily(day, data):
            if not win.winfo_exists():
                return
            for w in scroll_daily.winfo_children():
                w.destroy()
            day2_lbl.config(text="Dzisiaj" if day == date.today()
                            else day.strftime("%d.%m.%Y"))
            if not data:
                tk.Label(scroll_daily, text="Brak danych dla wybranego dnia.",
                         bg=self.config.COLOR_BG, fg="#888",
                         font=("Arial", 12)).pack(pady=40)
                return

            grand = {"total": 0, "pass": 0, "fail": 0}
            for op, rows in data.items():
                op_total = sum(r["total"] for r in rows)
                op_pass  = sum(r["pass"] for r in rows)
                op_fail  = sum(r["fail"] for r in rows)
                grand["total"] += op_total
                grand["pass"]  += op_pass
                grand["fail"]  += op_fail

                oh = tk.Frame(scroll_daily, bg=self.config.COLOR_PRIMARY)
                oh.pack(fill=tk.X, pady=(10, 0))
                tk.Label(oh, text=f"  Operator: {op}   Razem: {op_total}   "
                                  f"PASS: {op_pass}   FAIL: {op_fail}",
                         bg=self.config.COLOR_PRIMARY, fg="white",
                         font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10, pady=5)

                ch = tk.Frame(scroll_daily, bg="#ECEFF1")
                ch.pack(fill=tk.X)
                for txt, w in [("Model", 260), ("Tryb", 70), ("PASS", 70),
                               ("FAIL", 70), ("RETEST", 70), ("Razem", 70)]:
                    tk.Label(ch, text=txt, bg="#ECEFF1", fg="#333",
                             font=("Arial", 9, "bold"), width=w // 8,
                             anchor="center").pack(side=tk.LEFT, padx=2, pady=3)

                for i, row in enumerate(rows):
                    bg = "#fff" if i % 2 == 0 else "#f5f5f5"
                    rf = tk.Frame(scroll_daily, bg=bg)
                    rf.pack(fill=tk.X)
                    for val, w, fg in [
                        (row["model"], 260, "#333"),
                        (row["mode"], 70, "#555"),
                        (row["pass"], 70, self.config.COLOR_ACCENT),
                        (row["fail"], 70,
                         self.config.COLOR_ERROR if row["fail"] > 0 else "#333"),
                        (row["retest"], 70,
                         "#FF9800" if row["retest"] > 0 else "#aaa"),
                        (row["total"], 70, "#222"),
                    ]:
                        tk.Label(rf, text=str(val), bg=bg, fg=fg,
                                 font=("Arial", 10), width=w // 8,
                                 anchor="center").pack(side=tk.LEFT, padx=2, pady=2)

            sm = tk.Frame(scroll_daily, bg="#263238")
            sm.pack(fill=tk.X, pady=(14, 4))
            tk.Label(sm, text=f"  SUMA DNIA:  Razem {grand['total']}   "
                              f"PASS {grand['pass']}   FAIL {grand['fail']}",
                     bg="#263238", fg="white",
                     font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=15, pady=8)

        def load_daily_async(day):
            if state2["busy"]:
                return
            state2["busy"] = True
            for w in scroll_daily.winfo_children():
                w.destroy()
            tk.Label(scroll_daily, text="Wczytywanie...", bg=self.config.COLOR_BG,
                     fg="#888", font=("Arial", 11)).pack(pady=30)

            def worker():
                data = load_daily(day)
                state2["busy"] = False
                try:
                    if win.winfo_exists():
                        win.after(0, lambda: render_daily(day, data))
                except Exception:
                    pass
            threading.Thread(target=worker, daemon=True).start()

        def change_daily(delta):
            state2["day"] = state2["day"] + td(days=delta)
            load_daily_async(state2["day"])

        tk.Button(nav2, text="◀ Poprzedni", bg="#607D8B", fg="white",
                  font=("Arial", 9), relief=tk.FLAT, cursor="hand2",
                  command=lambda: change_daily(-1)).pack(side=tk.LEFT, padx=4)
        tk.Button(nav2, text="Następny ▶", bg="#607D8B", fg="white",
                  font=("Arial", 9), relief=tk.FLAT, cursor="hand2",
                  command=lambda: change_daily(1)).pack(side=tk.LEFT, padx=4)

        load_shifts(state["day"])
        load_daily_async(state2["day"])

    # ------------------------------------------------------------------ #
    # LOGIKA TESTU                                                         #
    # ------------------------------------------------------------------ #
    def _maybe_start_test(self):
        """
        Jedyne wejście do uruchomienia testu.
        POPRAWKA (bezpieczeństwo): sprawdzenie stanu klapy TUŻ PRZED
        załączeniem wysokiego napięcia. W poprzedniej wersji test startował
        z wątku sprawdzającego duplikat SN — jeśli operator zdążył w tym
        czasie otworzyć klapę, urządzenie podawało 3–4 kV przy otwartej
        osłonie.
        """
        if self._closed or self.test_running:
            return

        if not (self.device and self.device.is_open):
            self._cfg(self.status_label,
                      text="✗ Brak połączenia z Hi-Pot — nie można rozpocząć testu",
                      fg=self.config.COLOR_ERROR)
            self._pending_start = False
            return

        if self._interlock_active():
            state = self.interlock.is_closed
            if state is not True:
                self._pending_start = True
                self._cfg(self.status_label,
                          text=("🔓 Zamknij klapę, aby rozpocząć test"
                                if state is False
                                else "⚠ Nieznany stan klapy — czekam na Arduino"),
                          fg="#FF9800")
                self._cfg(self.start_button, state="disabled")
                return

        self._pending_start = False
        self.start_test()

    def start_test(self):
        if self._closed or self.test_running:
            return

        self._test_completed_called = False
        self._abort_requested = False
        self._abort_reason = ""
        self.test_running = True
        self.start_time = time.time()

        self._cfg(self.sn_display_label, text=self.serial_number)
        self._cfg(self.start_button, state="disabled")
        self._cfg(self.stop_button, state="normal")
        self._cfg(self.back_button, state="disabled")
        self._cfg(self.next_sn_button, state="disabled")
        self._cfg(self.status_label, text="🔄 Test w toku...", fg="#FF9800")

        self.test_thread = threading.Thread(target=self.run_test_background,
                                            daemon=True)
        self.test_thread.start()

    def run_test_background(self):
        try:
            ok, msg = self.device.start_test()
            if not ok:
                # POPRAWKA: wynik start_test() był wcześniej ignorowany —
                # odrzucona komenda kończyła się wiszącym "Test w toku".
                self.test_running = False
                self._ui(self.test_error, msg or "Urządzenie odrzuciło START")
                return

            total_time = self._total_time()
            hard_limit = max(total_time + TEST_GRACE_SECONDS,
                             min(float(getattr(self.config, "TEST_TIMEOUT", 300)),
                                 total_time + 60))
            min_run_time = min(2.0, max(0.5, total_time))

            time.sleep(min(1.5, max(0.3, total_time / 2)))
            if not self.test_running or self._abort_requested:
                return

            timed_out = False
            while self.test_running and not self._abort_requested:
                status = self.device.get_status()
                elapsed = time.time() - self.start_time

                if self.device.comm_errors >= MAX_COMM_ERRORS:
                    self.test_running = False
                    self._ui(self.test_error,
                             "Utracono komunikację z Hi-Pot (RS232) w trakcie testu")
                    return

                # POPRAWKA: było `status == "STOPPED"`, a Chroma zwraca "STOP"
                # — warunek nigdy się nie spełniał i każdy test kończył się
                # dopiero limitem czasu.
                if elapsed >= min_run_time and self.device.status_is_finished(status):
                    break

                measurements = self.device.read_measurements()
                if measurements:
                    v = measurements["output_voltage"]                 # [V]
                    i = measurements["measure_current"] * 1000.0       # [A] → [mA]
                    self.current_voltage = v
                    self.current_current = i
                    if 0 < v < 1e6:
                        self.last_valid_voltage = v
                    if 0 < i < 9999:
                        self.last_valid_current = i

                self.elapsed_time = time.time() - self.start_time
                self._schedule_display_update()

                if self.elapsed_time > hard_limit:
                    timed_out = True
                    break

                time.sleep(0.1)

            if self._abort_requested or not self.test_running:
                return

            if timed_out:
                print("[TEST] Przekroczono limit czasu — pobieram wynik mimo to")

            self._ui(self.test_completed)

        except Exception as exc:
            # POPRAWKA: w oryginale było `lambda: self.test_error(str(e))`.
            # W Pythonie 3 nazwa `e` znika po wyjściu z bloku except, więc
            # callback wywalał się na NameError, komunikat nigdy nie docierał
            # do operatora, a ekran zostawał na "Test w toku..." bez końca.
            message = str(exc)
            self.test_running = False
            self._ui(self.test_error, message)

    def _schedule_display_update(self):
        """Dławienie odświeżania — bez tego kolejka Tk zapychała się callbackami."""
        if self._ui_refresh_scheduled:
            return
        self._ui_refresh_scheduled = True
        self._ui(self._do_display_update)

    def _do_display_update(self):
        self._ui_refresh_scheduled = False
        self.update_display()

    def update_display(self):
        self._cfg(self.voltage_label, text=f"{int(self.current_voltage)} V")
        self._cfg(self.current_label, text=f"{self.current_current:.2f} mA")
        self._cfg(self.time_label, text=f"{self.elapsed_time:.1f} s")

        total_time = self._total_time()
        progress = min(self.elapsed_time / total_time, 1.0) if total_time > 0 else 0
        try:
            cw = self.progress_canvas.winfo_width()
            self.progress_canvas.coords(self.progress_rect, 0, 0, cw * progress, 30)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # ZAKOŃCZENIE TESTU                                                    #
    # ------------------------------------------------------------------ #
    def test_completed(self):
        if self._test_completed_called or self._abort_requested:
            return
        self._test_completed_called = True
        self.test_running = False

        if not (self.device and self.device.is_open):
            self.test_error("Utracono połączenie z urządzeniem przed odczytem wyniku")
            return

        result, data = self.device.get_test_result()
        self.test_result = result

        self._cfg(self.start_button, state="disabled")
        self._cfg(self.stop_button, state="disabled")
        self._cfg(self.back_button, state="normal")
        self._cfg(self.next_sn_button, state="normal")

        # POPRAWKA: brak odpowiedzi urządzenia był raportowany jako FAIL.
        # Usterka RS232 wyglądała wtedy jak wadliwy zasilacz i trafiała
        # do logów IFS. Teraz to jawny błąd — sztukę trzeba przetestować
        # ponownie, nic nie jest zapisywane.
        if result == "UNKNOWN":
            self._cfg(self.status_label,
                      text="✗ BRAK WYNIKU Z URZĄDZENIA — powtórz test (nie zapisano)",
                      fg=self.config.COLOR_ERROR)
            messagebox.showerror(
                "Brak wyniku",
                "Urządzenie Hi-Pot nie zwróciło wyniku testu.\n"
                "Sztuka NIE została zapisana — powtórz test.\n\n"
                "Jeśli problem się powtarza, sprawdź kabel RS232 i port COM.",
                parent=self.parent)
            self.parent.after(300, lambda: self.show_result_and_next_serial(
                "BRAK WYNIKU", data))
            return

        if result == "PASS":
            self._cfg(self.status_label, text="✓ TEST ZALICZONY (PASS)",
                      fg=self.config.COLOR_ACCENT)
        else:
            self._cfg(self.status_label, text="✗ TEST NIEZALICZONY (FAIL)",
                      fg=self.config.COLOR_ERROR)

        p = self.model_info["test_params"]
        error_code = str(data.get("error_code", "")) if data else ""
        is_dup = bool(self._current_sn_is_duplicate)

        # ── Wartości do raportu ──────────────────────────────────────────
        # POPRAWKA JEDNOSTEK: hipot_device.get_test_result() zwraca prąd już
        # w mA. Poprzednia wersja mnożyła go tu jeszcze raz przez 1000,
        # więc w raporcie dla IFS prąd był 1000× za duży
        # (np. 0,500 mA zapisywane jako 500,000 mA).
        raw_v  = float(data.get("output_voltage", 0.0) or 0.0)          # [V]
        raw_ma = float(data.get("measured_current_ma", 0.0) or 0.0)     # [mA]

        vtm_val = (raw_v / 1000.0) if 0 < raw_v < 1e6 else (self.last_valid_voltage / 1000.0)
        im_val  = raw_ma if 0 < raw_ma < 9999 else self.last_valid_current

        log_ok, log_msg = self._write_report(p, result, error_code, vtm_val, im_val)

        # ── Liczniki zmiany ──────────────────────────────────────────────
        if self.shift_stats:
            try:
                self.shift_stats.add_result(
                    result, is_duplicate=is_dup,
                    model_key=self.model_info["model_key"])
            except Exception as e:
                print(f"[SHIFT] Błąd zapisu: {e}")

        # ── Statystyki dzienne ───────────────────────────────────────────
        if self.stats:
            try:
                self.stats.add_result(
                    operator=self.operator,
                    model_key=self.model_info["model_key"],
                    mode=p.get("mode", "AC"),
                    result=result,
                    is_retest=is_dup)
            except Exception as e:
                print(f"[STATS] Błąd zapisu: {e}")

        self._add_recent_result(serial=self.serial_number,
                                model_key=self.model_info["model_key"],
                                result=result,
                                duplicate=is_dup)
        self.update_counter()

        if not log_ok:
            messagebox.showerror(
                "Błąd zapisu raportu",
                "Nie udało się zapisać raportu w docelowej lokalizacji:\n"
                f"{self.config.LOG_DIR}\n\n"
                f"Szczegóły: {log_msg}\n\n"
                "Sprawdź dostęp do dysku sieciowego — bez raportu system IFS "
                "nie odbierze wyniku tej sztuki.",
                parent=self.parent)

        self.parent.after(1500,
                          lambda: self.show_result_and_next_serial(result, data))

    def _write_report(self, p, result, error_code, vtm_val, im_val):
        """
        Zapisuje raport. Przy niepowodzeniu próbuje kopii awaryjnej obok
        aplikacji, żeby wynik nie przepadł, i zwraca (False, komunikat).
        """
        kwargs = dict(
            operator=self.operator,
            program=self.model_info["model_key"],
            serial=self.serial_number,
            mode=p.get("mode", "AC"),
            vtm=vtm_val,
            im=im_val,
            low=float(p["current_limit_low"]),
            high=float(p["current_limit_high"]),
            result=result,
            error_code=error_code,
        )
        try:
            save_report(log_dir=self.config.LOG_DIR, **kwargs)
            return True, ""
        except Exception as e:
            print(f"[LOG] Błąd zapisu raportu: {e}")
            try:
                from app_paths import data_path
                fallback = data_path("logs_awaryjne")
                save_report(log_dir=fallback, **kwargs)
                print(f"[LOG] Zapisano kopię awaryjną w {fallback}")
                return False, f"{e}\n\nKopia awaryjna: {fallback}"
            except Exception as e2:
                print(f"[LOG] Kopia awaryjna również nieudana: {e2}")
                return False, f"{e} / kopia awaryjna: {e2}"

    def test_error(self, error_message):
        self.test_running = False
        self._cfg(self.start_button, state="normal")
        self._cfg(self.stop_button, state="disabled")
        self._cfg(self.back_button, state="normal")
        self._cfg(self.next_sn_button, state="normal")
        self._cfg(self.status_label,
                  text=f"✗ Błąd testu: {error_message}",
                  fg=self.config.COLOR_ERROR)

    # ------------------------------------------------------------------ #
    # PRZERWANIE TESTU                                                     #
    # ------------------------------------------------------------------ #
    def stop_test(self):
        self._abort_test("Test przerwany przez operatora")

    def _abort_test(self, reason: str):
        """
        Twarde przerwanie: wyłącz wysokie napięcie i NIE zapisuj wyniku.
        POPRAWKA: poprzednio ustawienie test_running=False powodowało wyjście
        z pętli wątku i wywołanie test_completed() — przerwany test zapisywał
        się jako FAIL w raporcie IFS i w statystykach zmiany.
        """
        was_running = self.test_running
        self._abort_requested = True
        self._abort_reason = reason
        self.test_running = False

        device = self.device
        if device is not None:
            # Wysyłka w wątku tła: wątek pomiarowy może trzymać blokadę portu
            # przez ~2 s, a GUI nie może na to czekać.
            threading.Thread(target=self._stop_device_worker,
                             args=(device,), daemon=True).start()

        self._cfg(self.stop_button, state="disabled")
        self._cfg(self.back_button, state="normal")
        self._cfg(self.next_sn_button, state="normal")
        self._cfg(self.start_button, state="disabled")
        if was_running:
            self._cfg(self.status_label, text=f"⛔ {reason} — wynik NIE zapisany",
                      fg=self.config.COLOR_ERROR)

    @staticmethod
    def _stop_device_worker(device):
        try:
            device.stop_test()
        except Exception as e:
            print(f"[HIPOT] Nie udało się zatrzymać testu: {e}")

    # ------------------------------------------------------------------ #
    # DUPLIKAT SN                                                          #
    # ------------------------------------------------------------------ #
    def check_serial_duplicate(self, serial: str) -> dict:
        empty = {"found": False, "where": None, "last_time": None, "last_result": None}

        for entry in self._recent_results:
            if entry["serial"].upper() == serial.upper():
                return {"found": True, "where": "session",
                        "last_time": entry["time"], "last_result": entry["result"]}

        log_dir = getattr(self.config, "LOG_DIR", "logs")
        if not os.path.isdir(log_dir):
            return empty

        shift_start = self.shift_stats.shift_start if self.shift_stats else None
        shift_end   = self.shift_stats.shift_end if self.shift_stats else None

        pattern = re.compile(
            r'^' + re.escape(serial.upper()) + r'_(\d{14})(?:_\d+)?\.txt$',
            re.IGNORECASE)

        matches = []
        try:
            for fname in os.listdir(log_dir):
                m = pattern.match(fname)
                if not m:
                    continue
                try:
                    ts = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
                except ValueError:
                    continue
                if shift_start and shift_end and not (shift_start <= ts < shift_end):
                    continue
                matches.append((ts, fname))
        except Exception as e:
            print(f"[DUP] Błąd przeglądania logów: {e}")
            return empty

        if not matches:
            return empty

        matches.sort(key=lambda x: x[0], reverse=True)
        latest_ts, latest_fname = matches[0]

        last_result = None
        try:
            with open(os.path.join(log_dir, latest_fname),
                      encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().lower().startswith("total result:"):
                        val = line.split(":", 1)[-1].strip().upper()
                        last_result = "PASS" if val == "PASS" else "FAIL"
                        break
        except Exception:
            pass

        return {"found": True, "where": "logs",
                "last_time": latest_ts.strftime("%d.%m.%Y %H:%M"),
                "last_result": last_result}

    def _check_duplicate_async(self, serial: str):
        """Sprawdza duplikat SN w tle — nie blokuje GUI ani startu testu."""
        try:
            dup = self.check_serial_duplicate(serial)
        except Exception as e:
            print(f"[DUP] Błąd sprawdzania duplikatu: {e}")
            dup = {"found": False}

        self._current_sn_is_duplicate = bool(dup.get("found"))
        self._ui(self._after_duplicate_check, serial, dup)

    def _after_duplicate_check(self, serial: str, dup: dict):
        if self._closed or self.test_running:
            return

        if not dup.get("found"):
            self._maybe_start_test()
            return

        where_txt  = ("tej zmiany" if dup.get("where") == "session"
                      else f"logów ({dup.get('last_time')})")
        result_txt = f" (wynik: {dup.get('last_result')})" if dup.get("last_result") else ""

        self._cfg(self.status_label,
                  text=f"⚠ DUPLIKAT: SN {serial} był już testowany — "
                       f"{where_txt}{result_txt}",
                  fg="#E65100")

        answer = messagebox.askyesno(
            "Duplikat SN!",
            f"SN {serial} był już testowany w tej zmianie!\n"
            f"{where_txt}{result_txt}\n\nNa pewno chcesz kontynuować?",
            parent=self.parent)

        if answer:
            self._maybe_start_test()
        else:
            self._current_sn_is_duplicate = False
            self._cfg(self.status_label,
                      text="Test anulowany — zeskanuj inny numer seryjny",
                      fg="#666666")
            self._open_sn_dialog_manually()

    # ------------------------------------------------------------------ #
    # OKNO NASTĘPNY SN                                                     #
    # ------------------------------------------------------------------ #
    def _open_sn_dialog_manually(self):
        if self._dialog_open():
            self.sn_dialog.lift()
            self.sn_dialog.focus()
            return
        self.show_result_and_next_serial(self.test_result or "—", {})

    def _arm_next_test_from_dialog(self):
        """Walidacja SN z okna i uzbrojenie testu (Enter albo zamknięcie klapy)."""
        if not self._dialog_open():
            return False

        new_serial = self.sn_entry.get().strip().upper()
        from models import PowerSupplyModels
        valid, msg = PowerSupplyModels.validate_serial(
            self.model_info["model_key"], new_serial)

        if not valid:
            self._cfg(self.sn_status_lbl,
                      text=f"✗ {msg}", fg=self.config.COLOR_ERROR)
            self.sn_entry.config(state="normal")
            self.sn_entry.focus()
            return False

        self._current_sn_is_duplicate = False
        self.serial_number = new_serial
        self._cfg(self.sn_display_label, text=self.serial_number)

        # Reset widoku pomiarów
        self.test_result = None
        self.elapsed_time = 0.0
        self.current_voltage = 0.0
        self.current_current = 0.0
        self.last_valid_voltage = 0.0
        self.last_valid_current = 0.0
        self._cfg(self.voltage_label, text="0 V")
        self._cfg(self.current_label, text="0.00 mA")
        self._cfg(self.time_label, text="0.0 s")
        try:
            self.progress_canvas.coords(self.progress_rect, 0, 0, 0, 30)
        except Exception:
            pass
        self._cfg(self.status_label, text="Sprawdzanie numeru seryjnego...",
                  fg="#666666")

        try:
            self.sn_dialog.grab_release()
            self.sn_dialog.destroy()
        except Exception:
            pass
        self.sn_dialog = None

        threading.Thread(target=self._check_duplicate_async,
                         args=(new_serial,), daemon=True).start()
        return True

    def show_result_and_next_serial(self, result, data):
        if self._closed:
            return
        if self._dialog_open():
            self.update_sn_dialog(result)
            self.sn_dialog.lift()
            self.sn_dialog.focus()
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title("Następny numer seryjny")
        dialog.geometry("460x340")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", self._back_to_menu_from_dialog)

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.sn_dialog = dialog

        result_color = (self.config.COLOR_ACCENT if result == "PASS"
                        else self.config.COLOR_ERROR if result == "FAIL"
                        else "#666666")

        self.sn_result_label = tk.Label(
            dialog, text=f"Ostatni wynik: {result}",
            bg=self.config.COLOR_WHITE, fg=result_color,
            font=("Arial", 13, "bold"))
        self.sn_result_label.pack(pady=(15, 5))

        tk.Frame(dialog, bg="#cccccc", height=1).pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(dialog, text="Zeskanuj kolejny numer seryjny:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11, "bold")).pack(pady=(0, 5))

        self.sn_entry = tk.Entry(dialog, font=("Arial", 14, "bold"), width=28,
                                 justify="center", relief=tk.SOLID, borderwidth=2)
        self.sn_entry.pack(pady=5, padx=30)
        self.sn_entry.focus()

        hint = ("⬆ Zeskanuj SN i zamknij klapę aby rozpocząć test"
                if self._interlock_active()
                else "⬆ Zeskanuj SN i naciśnij ENTER aby rozpocząć test")
        self.sn_status_lbl = tk.Label(dialog, text=hint,
                                      bg=self.config.COLOR_WHITE, fg="#888888",
                                      font=("Arial", 9))
        self.sn_status_lbl.pack()

        # POPRAWKA: w trybie ręcznym (interlock wyłączony/niedostępny) okno
        # nie miało ŻADNEJ możliwości uruchomienia kolejnego testu — jedynym
        # wyjściem był powrót do menu i ponowne skanowanie od zera.
        btn_row = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        btn_row.pack(pady=15)

        tk.Button(btn_row, text="▶ Zatwierdź SN",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 11, "bold"), width=16, height=1,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._arm_next_test_from_dialog
                  ).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_row, text="Powrót do menu",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 11, "bold"), width=16, height=1,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._back_to_menu_from_dialog).pack(side=tk.LEFT, padx=5)

        self.sn_entry.bind("<Return>", lambda e: self._arm_next_test_from_dialog())

    def update_sn_dialog(self, result):
        if self._dup_banner is not None:
            try:
                self._dup_banner.destroy()
            except Exception:
                pass
            self._dup_banner = None
        result_color = (self.config.COLOR_ACCENT if result == "PASS"
                        else self.config.COLOR_ERROR if result == "FAIL"
                        else "#666666")
        self._cfg(self.sn_result_label, text=f"Ostatni wynik: {result}",
                  fg=result_color)
        try:
            self.sn_entry.config(state="normal")
            self.sn_entry.delete(0, tk.END)
            self.sn_entry.focus()
        except Exception:
            pass
        hint = ("Zeskanuj SN i zamknij klapę aby rozpocząć test"
                if self._interlock_active()
                else "Zeskanuj SN i naciśnij ENTER aby rozpocząć test")
        self._cfg(self.sn_status_lbl, text=hint, fg="#888888",
                  bg=self.config.COLOR_WHITE)

    def _back_to_menu_from_dialog(self):
        if self._dialog_open():
            try:
                self.sn_dialog.grab_release()
                self.sn_dialog.destroy()
            except Exception:
                pass
        self.sn_dialog = None
        self._cleanup_and_go_back()


# Zgodność wsteczna dla ewentualnych importów zewnętrznych
_get_current_shift = get_current_shift
_parse_shift_file = parse_shift_file
