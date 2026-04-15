# gui.py
"""Interfejs graficzny aplikacji"""
import tkinter as tk
from tkinter import ttk, messagebox
from config import Config
from models import PowerSupplyModels
from admin_panel import AdminPanel


class HiPotTesterApp:

    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.current_user = None
        self._setup_window()
        self._show_login_screen()

    def _setup_window(self):
        self.root.title(self.config.WINDOW_TITLE)
        self.root.geometry(f"{self.config.WINDOW_WIDTH}x{self.config.WINDOW_HEIGHT}")
        self.root.configure(bg=self.config.COLOR_BG)
        self._center_window()

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = self.root.winfo_screenwidth()  // 2 - w // 2
        y = self.root.winfo_screenheight() // 2 - h // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------ #
    #  EKRAN LOGOWANIA                                                     #
    # ------------------------------------------------------------------ #
    def _show_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        self.login_frame.pack(expand=True, fill=tk.BOTH)

        header = tk.Frame(self.login_frame, bg=self.config.COLOR_PRIMARY, height=120)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Reconext Hi-Pot PSU",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 28, "bold")).pack(pady=25)

        center = tk.Frame(self.login_frame, bg=self.config.COLOR_BG)
        center.pack(expand=True)

        panel = tk.Frame(center, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        panel.pack(padx=50, pady=50)

        tk.Label(panel, text="Logowanie Operatora",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 20, "bold")).pack(pady=(30, 20))

        tk.Label(panel, text="Wprowadź HRID:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 12)).pack(pady=(10, 5))

        self.hrid_entry = tk.Entry(panel, font=("Arial", 14), width=20,
                                   justify="center", relief=tk.SOLID, borderwidth=2)
        self.hrid_entry.pack(pady=10, padx=50)
        self.hrid_entry.focus()
        self.hrid_entry.bind("<Return>", lambda e: self._attempt_login())

        self.error_label = tk.Label(panel, text="",
                                    bg=self.config.COLOR_WHITE,
                                    fg=self.config.COLOR_ERROR,
                                    font=("Arial", 10))
        self.error_label.pack()

        login_btn = tk.Button(panel, text="ZALOGUJ",
                              bg=self.config.COLOR_ACCENT,
                              fg=self.config.COLOR_WHITE,
                              font=("Arial", 14, "bold"),
                              width=15, height=2, relief=tk.FLAT,
                              cursor="hand2",
                              command=self._attempt_login)
        login_btn.pack(pady=(10, 30), padx=50)
        login_btn.bind("<Enter>", lambda e: login_btn.config(bg="#66BB6A"))
        login_btn.bind("<Leave>", lambda e: login_btn.config(bg=self.config.COLOR_ACCENT))

    def _attempt_login(self):
        hrid = self.hrid_entry.get().strip()
        if not hrid:
            self.error_label.config(text="Pole HRID nie może być puste!")
            return
        if hrid in self.config.AUTHORIZED_USERS:
            self.current_user = hrid
            self._login_success()
        else:
            self.error_label.config(text="Nieprawidłowy HRID! Brak autoryzacji.")
            self.hrid_entry.delete(0, tk.END)
            self.hrid_entry.focus()

    def _login_success(self):
        self.login_frame.destroy()
        self._create_main_app()

    # ------------------------------------------------------------------ #
    #  GŁÓWNA APLIKACJA                                                    #
    # ------------------------------------------------------------------ #
    def _create_main_app(self):
        self._create_header()

        main_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        self._create_scan_panel(main_frame)
        self._create_footer()

        # Skrót do panelu admina: Ctrl+Alt+D (3x)
        self._d_press_count = 0
        self._d_press_timer = None
        self.root.bind("<Control-Alt-d>", self._on_config_shortcut)
        self.root.bind("<Control-Alt-D>", self._on_config_shortcut)

    def _on_config_shortcut(self, event=None):
        self._d_press_count += 1
        if self._d_press_timer:
            self.root.after_cancel(self._d_press_timer)
        self._d_press_timer = self.root.after(1000, self._reset_d_counter)
        if self._d_press_count >= 3:
            self._d_press_count = 0
            self._show_password_dialog()

    def _reset_d_counter(self):
        self._d_press_count = 0

    def _show_password_dialog(self):
        pw_win = tk.Toplevel(self.root)
        pw_win.title("Dostęp do konfiguracji")
        pw_win.geometry("400x220")
        pw_win.configure(bg=self.config.COLOR_BG)
        pw_win.resizable(False, False)
        pw_win.transient(self.root)
        pw_win.grab_set()

        frame = tk.Frame(pw_win, bg=self.config.COLOR_WHITE,
                         relief=tk.RAISED, borderwidth=2)
        frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(frame, text="Dostęp do konfiguracji",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 14, "bold")).pack(pady=(20, 10))

        tk.Label(frame, text="Wprowadź hasło:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).pack(pady=(10, 5))

        pw_entry = tk.Entry(frame, font=("Arial", 12), width=20,
                            justify="center", show="*",
                            relief=tk.SOLID, borderwidth=2)
        pw_entry.pack(pady=10)
        pw_entry.focus()

        err = tk.Label(frame, text="", bg=self.config.COLOR_WHITE,
                       fg=self.config.COLOR_ERROR, font=("Arial", 9))
        err.pack()

        def check_password():
            if pw_entry.get() == "reconext2026":
                pw_win.destroy()
                self._show_config_window()
            else:
                err.config(text="Nieprawidłowe hasło!")
                pw_entry.delete(0, tk.END)
                pw_entry.focus()

        pw_entry.bind("<Return>", lambda e: check_password())

        bf = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        bf.pack(pady=10)
        tk.Button(bf, text="OK", bg=self.config.COLOR_ACCENT,
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  width=10, relief=tk.FLAT, cursor="hand2",
                  command=check_password).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Anuluj", bg="#999999",
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  width=10, relief=tk.FLAT, cursor="hand2",
                  command=pw_win.destroy).pack(side=tk.LEFT, padx=5)

    def _show_config_window(self):
        panel = AdminPanel(self.root, self.config)
        panel.show()

    # ------------------------------------------------------------------ #
    #  PANEL SKANOWANIA                                                    #
    # ------------------------------------------------------------------ #
    def _create_scan_panel(self, parent):
        center = tk.Frame(parent, bg=self.config.COLOR_BG)
        center.pack(expand=True)

        scan_panel = tk.Frame(center, bg=self.config.COLOR_WHITE,
                              relief=tk.RAISED, borderwidth=2)
        scan_panel.pack(padx=50, pady=50)

        tk.Label(scan_panel, text="Wybór modelu i skanowanie SN",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 20, "bold")).pack(pady=(30, 20))

        # --- Dropdown modelu ---
        tk.Label(scan_panel, text="Wybierz model zasilacza:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 12)).pack(pady=(10, 5))

        self.selected_model = tk.StringVar()
        self.model_combo = ttk.Combobox(
            scan_panel,
            textvariable=self.selected_model,
            values=PowerSupplyModels.get_all_models(),
            font=("Arial", 13), width=28, state="readonly")
        self.model_combo.pack(pady=(0, 15), padx=50)
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        self.sn_length_label = tk.Label(
            scan_panel, text="",
            bg=self.config.COLOR_WHITE, fg="#666666",
            font=("Arial", 10, "italic"))
        self.sn_length_label.pack(pady=(0, 5))

        # --- Pole SN ---
        tk.Label(scan_panel, text="Zeskanuj lub wprowadź numer seryjny:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 12)).pack(pady=(10, 5))

        self.serial_entry = tk.Entry(
            scan_panel, font=("Arial", 16, "bold"), width=30,
            justify="center", relief=tk.SOLID, borderwidth=2,
            state="disabled")
        self.serial_entry.pack(pady=15, padx=50)
        self.serial_entry.bind("<Return>", lambda e: self._process_serial())

        self.scan_status_label = tk.Label(
            scan_panel, text="",
            bg=self.config.COLOR_WHITE, font=("Arial", 11))
        self.scan_status_label.pack(pady=5)

        self.confirm_button = tk.Button(
            scan_panel, text="POTWIERDŹ",
            bg="#AAAAAA", fg=self.config.COLOR_WHITE,
            font=("Arial", 14, "bold"), width=20, height=2,
            relief=tk.FLAT, cursor="hand2",
            command=self._process_serial, state="disabled")
        self.confirm_button.pack(pady=(10, 30), padx=50)

    def _on_model_selected(self, event=None):
        model_key = self.selected_model.get()
        model_info = PowerSupplyModels.get_model_info(model_key)
        if model_info:
            length = model_info.get("serial_length", "?")
            if isinstance(length, list):
                length_text = " lub ".join(str(x) for x in length)
            else:
                length_text = str(length)
            self.sn_length_label.config(
                text=f"Wymagana długość SN: {length_text} znaków")

        self.serial_entry.config(state="normal")
        self.confirm_button.config(state="normal", bg=self.config.COLOR_ACCENT)
        self.confirm_button.bind("<Enter>",
            lambda e: self.confirm_button.config(bg="#66BB6A"))
        self.confirm_button.bind("<Leave>",
            lambda e: self.confirm_button.config(bg=self.config.COLOR_ACCENT))
        self.serial_entry.delete(0, tk.END)
        self.scan_status_label.config(text="")
        self.serial_entry.focus()

    def _process_serial(self):
        model_key = self.selected_model.get()
        serial = self.serial_entry.get().strip().upper()

        if not model_key:
            self.scan_status_label.config(
                text="Najpierw wybierz model!",
                fg=self.config.COLOR_ERROR)
            return
        if not serial:
            self.scan_status_label.config(
                text="Wprowadź numer seryjny!",
                fg=self.config.COLOR_ERROR)
            return

        valid, message = PowerSupplyModels.validate_serial(model_key, serial)
        if not valid:
            self.scan_status_label.config(
                text=f"✗ {message}", fg=self.config.COLOR_ERROR)
            self.serial_entry.delete(0, tk.END)
            self.serial_entry.focus()
            return

        model_info = PowerSupplyModels.get_model_info(model_key)
        model_info_full = {"model_key": model_key, **model_info}

        self.scan_status_label.config(
            text=f"✓ Model: {model_key} | SN: {len(serial)} znaków — OK",
            fg=self.config.COLOR_ACCENT)

        self.root.after(800, lambda: self._show_test_screen(serial, model_info_full))

    def _show_test_screen(self, serial, model_info):
        from test_screen import TestScreen
        ts = TestScreen(self.root, self.config, serial, model_info,
                        self.current_user, app_ref=self)
        ts.show()

    # ------------------------------------------------------------------ #
    #  POWRÓT DO SKANOWANIA                                                #
    # ------------------------------------------------------------------ #
    def show_scan_screen(self):
        """Wywoływane z TestScreen przy powrocie do menu."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self._create_header()

        main_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        self._create_scan_panel(main_frame)
        self._create_footer()

        self._d_press_count = 0
        self._d_press_timer = None
        self.root.bind("<Control-Alt-d>", self._on_config_shortcut)
        self.root.bind("<Control-Alt-D>", self._on_config_shortcut)

    # ------------------------------------------------------------------ #
    #  HEADER / FOOTER                                                     #
    # ------------------------------------------------------------------ #
    def _create_header(self):
        header = tk.Frame(self.root, bg=self.config.COLOR_PRIMARY, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="Reconext Hi-Pot PSU",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 22, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

        logout_btn = tk.Button(header, text="Wyloguj",
                               bg=self.config.COLOR_ERROR,
                               fg=self.config.COLOR_WHITE,
                               font=("Arial", 10, "bold"),
                               relief=tk.FLAT, cursor="hand2",
                               command=self._logout)
        logout_btn.pack(side=tk.RIGHT, padx=10, pady=20)

        tk.Label(header, text=f"Operator: {self.current_user}",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=20, pady=15)

    def _create_footer(self):
        footer = tk.Frame(self.root, bg=self.config.COLOR_PRIMARY, height=40)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        footer.pack_propagate(False)
        tk.Label(footer, text="Autor: Kacper Urbanowicz",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=20, pady=10)

    def _logout(self):
        self.current_user = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self._show_login_screen()