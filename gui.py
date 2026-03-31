# gui.py
"""
Interfejs graficzny aplikacji
"""
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

        self.setup_window()
        self.show_login_screen()

    def setup_window(self):
        self.root.title(self.config.WINDOW_TITLE)
        self.root.geometry(f"{self.config.WINDOW_WIDTH}x{self.config.WINDOW_HEIGHT}")
        self.root.configure(bg=self.config.COLOR_BG)
        self.center_window()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def show_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        self.login_frame.pack(expand=True, fill=tk.BOTH)

        header_frame = tk.Frame(self.login_frame, bg=self.config.COLOR_PRIMARY, height=120)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Reconext Hi-Pot PSU",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 28, "bold")
        ).pack(pady=25)

        center_frame = tk.Frame(self.login_frame, bg=self.config.COLOR_BG)
        center_frame.pack(expand=True)

        login_panel = tk.Frame(center_frame, bg=self.config.COLOR_WHITE, relief=tk.RAISED, borderwidth=2)
        login_panel.pack(padx=50, pady=50)

        tk.Label(
            login_panel,
            text="Logowanie Operatora",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 20, "bold")
        ).pack(pady=(30, 20))

        tk.Label(
            login_panel,
            text="Wprowadź HRID:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 12)
        ).pack(pady=(10, 5))

        self.hrid_entry = tk.Entry(
            login_panel,
            font=("Arial", 14),
            width=20,
            justify='center',
            relief=tk.SOLID,
            borderwidth=2
        )
        self.hrid_entry.pack(pady=10, padx=50)
        self.hrid_entry.focus()
        self.hrid_entry.bind('<Return>', lambda e: self.attempt_login())

        self.error_label = tk.Label(
            login_panel,
            text="",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_ERROR,
            font=("Arial", 10)
        )
        self.error_label.pack()

        login_button = tk.Button(
            login_panel,
            text="ZALOGUJ",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 14, "bold"),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.attempt_login
        )
        login_button.pack(pady=(10, 30), padx=50)
        login_button.bind('<Enter>', lambda e: login_button.config(bg="#66BB6A"))
        login_button.bind('<Leave>', lambda e: login_button.config(bg=self.config.COLOR_ACCENT))

    def attempt_login(self):
        hrid = self.hrid_entry.get().strip()
        if not hrid:
            self.error_label.config(text="Pole HRID nie może być puste!")
            return
        if hrid in self.config.AUTHORIZED_USERS:
            self.current_user = hrid
            self.login_success()
        else:
            self.error_label.config(text="Nieprawidłowy HRID! Brak autoryzacji.")
            self.hrid_entry.delete(0, tk.END)
            self.hrid_entry.focus()

    def login_success(self):
        self.login_frame.destroy()
        self.create_main_app()

    def create_main_app(self):
        self.create_header()

        main_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        self.create_scan_panel(main_frame)
        self.create_footer()

        self.d_press_count = 0
        self.d_press_timer = None
        self.root.bind('<Control-Alt-d>', self.on_config_shortcut)
        self.root.bind('<Control-Alt-D>', self.on_config_shortcut)

    def on_config_shortcut(self, event):
        self.d_press_count += 1
        if self.d_press_timer:
            self.root.after_cancel(self.d_press_timer)
        self.d_press_timer = self.root.after(1000, self.reset_d_counter)
        if self.d_press_count >= 3:
            self.d_press_count = 0
            self.show_password_dialog()

    def reset_d_counter(self):
        self.d_press_count = 0

    def show_password_dialog(self):
        password_window = tk.Toplevel(self.root)
        password_window.title("Dostęp do konfiguracji")
        password_window.geometry("400x200")
        password_window.configure(bg=self.config.COLOR_BG)
        password_window.resizable(False, False)
        password_window.transient(self.root)
        password_window.grab_set()

        frame = tk.Frame(password_window, bg=self.config.COLOR_WHITE, relief=tk.RAISED, borderwidth=2)
        frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(
            frame,
            text="Dostęp do konfiguracji",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 14, "bold")
        ).pack(pady=(20, 10))

        tk.Label(
            frame,
            text="Wprowadź hasło:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).pack(pady=(10, 5))

        password_entry = tk.Entry(
            frame,
            font=("Arial", 12),
            width=20,
            justify='center',
            show="*",
            relief=tk.SOLID,
            borderwidth=2
        )
        password_entry.pack(pady=10)
        password_entry.focus()

        error_label = tk.Label(
            frame,
            text="",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_ERROR,
            font=("Arial", 9)
        )
        error_label.pack()

        def check_password():
            if password_entry.get() == "reconext2026":
                password_window.destroy()
                self.show_config_window()
            else:
                error_label.config(text="Nieprawidłowe hasło!")
                password_entry.delete(0, tk.END)
                password_entry.focus()

        password_entry.bind('<Return>', lambda e: check_password())

        button_frame = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        button_frame.pack(pady=(10, 20))

        ok_button = tk.Button(
            button_frame,
            text="OK",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=10,
            relief=tk.FLAT,
            cursor="hand2",
            command=check_password
        )
        ok_button.pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Anuluj",
            bg="#999999",
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=10,
            relief=tk.FLAT,
            cursor="hand2",
            command=password_window.destroy
        ).pack(side=tk.LEFT, padx=5)

    def show_config_window(self):
        admin_panel = AdminPanel(self.root, self.config)
        admin_panel.show()

    def create_scan_panel(self, parent):
        """Tworzy panel wyboru modelu i skanowania numeru seryjnego"""
        center_frame = tk.Frame(parent, bg=self.config.COLOR_BG)
        center_frame.pack(expand=True)

        scan_panel = tk.Frame(
            center_frame,
            bg=self.config.COLOR_WHITE,
            relief=tk.RAISED,
            borderwidth=2
        )
        scan_panel.pack(padx=50, pady=50)

        # Tytuł
        tk.Label(
            scan_panel,
            text="Wybór modelu i skanowanie S/N",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 20, "bold")
        ).pack(pady=(30, 20))

        # --- DROPDOWN MODELU ---
        tk.Label(
            scan_panel,
            text="Wybierz model zasilacza:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 12)
        ).pack(pady=(10, 5))

        self.selected_model = tk.StringVar()
        self.model_combo = ttk.Combobox(
            scan_panel,
            textvariable=self.selected_model,
            values=PowerSupplyModels.get_all_models(),
            font=("Arial", 13),
            width=28,
            state="readonly"
        )
        self.model_combo.pack(pady=(0, 15), padx=50)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)

        # Info o wymaganej długości S/N
        self.sn_length_label = tk.Label(
            scan_panel,
            text="",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 10, "italic")
        )
        self.sn_length_label.pack(pady=(0, 5))

        # --- POLE S/N ---
        tk.Label(
            scan_panel,
            text="Zeskanuj lub wprowadź numer seryjny:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 12)
        ).pack(pady=(10, 5))

        self.serial_entry = tk.Entry(
            scan_panel,
            font=("Arial", 16, "bold"),
            width=30,
            justify='center',
            relief=tk.SOLID,
            borderwidth=2,
            state="disabled"
        )
        self.serial_entry.pack(pady=15, padx=50)
        self.serial_entry.bind('<Return>', lambda e: self.process_serial())

        # Status
        self.scan_status_label = tk.Label(
            scan_panel,
            text="",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 11)
        )
        self.scan_status_label.pack(pady=5)

        # Przycisk POTWIERDŹ
        self.confirm_button = tk.Button(
            scan_panel,
            text="POTWIERDŹ",
            bg="#AAAAAA",
            fg=self.config.COLOR_WHITE,
            font=("Arial", 14, "bold"),
            width=20,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.process_serial,
            state="disabled"
        )
        self.confirm_button.pack(pady=(10, 30), padx=50)

    def on_model_selected(self, event):
        """Obsługa wyboru modelu z dropdownu"""
        model_key = self.selected_model.get()
        model_info = PowerSupplyModels.get_model_info(model_key)

        if model_info:
            length = model_info.get("serial_length", "?")
            if isinstance(length, list):
                length_text = " lub ".join(str(x) for x in length)
            else:
                length_text = str(length)
            self.sn_length_label.config(
                text=f"Wymagana długość S/N: {length_text} znaków"
            )

        # Odblokuj pole S/N i przycisk
        self.serial_entry.config(state="normal")
        self.confirm_button.config(
            state="normal",
            bg=self.config.COLOR_ACCENT
        )
        self.confirm_button.bind('<Enter>', lambda e: self.confirm_button.config(bg="#66BB6A"))
        self.confirm_button.bind('<Leave>', lambda e: self.confirm_button.config(bg=self.config.COLOR_ACCENT))

        # Wyczyść pole i status
        self.serial_entry.delete(0, tk.END)
        self.scan_status_label.config(text="")
        self.serial_entry.focus()

    def process_serial(self):
        """Przetwarza zeskanowany numer seryjny"""
        serial = self.serial_entry.get().strip()
        model_key = self.selected_model.get()

        if not model_key:
            self.scan_status_label.config(
                text="Najpierw wybierz model!",
                fg=self.config.COLOR_ERROR
            )
            return

        if not serial:
            self.scan_status_label.config(
                text="Wprowadź numer seryjny!",
                fg=self.config.COLOR_ERROR
            )
            return

        # Walidacja długości S/N
        valid, message = PowerSupplyModels.validate_serial(model_key, serial)

        if not valid:
            self.scan_status_label.config(
                text=f"✗ {message}",
                fg=self.config.COLOR_ERROR
            )
            self.serial_entry.delete(0, tk.END)
            self.serial_entry.focus()
            return

        # OK — przejdź do testu
        model_info = PowerSupplyModels.get_model_info(model_key)
        model_info_full = {"model_key": model_key, **model_info}

        self.scan_status_label.config(
            text=f"✓ Model: {model_key} | S/N OK ({len(serial)} znaków)",
            fg=self.config.COLOR_ACCENT
        )
        self.root.after(800, lambda: self.show_test_screen(serial, model_info_full))

    def show_test_screen(self, serial, model_info):
        from test_screen import TestScreen
        test_screen = TestScreen(
            self.root,
            self.config,
            serial,
            model_info,
            self.current_user,
            app_ref = self
        )
        test_screen.show()

    def create_header(self):
        header_frame = tk.Frame(self.root, bg=self.config.COLOR_PRIMARY, height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Reconext Hi-Pot PSU",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 22, "bold")
        ).pack(side=tk.LEFT, padx=20, pady=15)

        tk.Label(
            header_frame,
            text=f"Operator: {self.current_user}",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 12, "bold")
        ).pack(side=tk.RIGHT, padx=20, pady=15)

        logout_button = tk.Button(
            header_frame,
            text="Wyloguj",
            bg=self.config.COLOR_ERROR,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self.logout
        )
        logout_button.pack(side=tk.RIGHT, padx=10, pady=20)

    def create_footer(self):
        footer_frame = tk.Frame(self.root, bg=self.config.COLOR_PRIMARY, height=40)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)

        tk.Label(
            footer_frame,
            text="Autor: Kacper Urbanowicz",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT, padx=20, pady=10)

    def show_scan_screen(self):
        """Powrót do ekranu skanowania S/N"""
        for widget in self.root.winfo_children():
            widget.destroy()

        self.create_header()

        main_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        self.create_scan_panel(main_frame)
        self.create_footer()

        self.d_press_count = 0
        self.d_press_timer = None
        self.root.bind('<Control-Alt-d>', self.on_config_shortcut)
        self.root.bind('<Control-Alt-D>', self.on_config_shortcut)

    def logout(self):
        self.current_user = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self.show_login_screen()