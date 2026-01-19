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
        """Konfiguracja głównego okna"""
        self.root.title(self.config.WINDOW_TITLE)
        self.root.geometry(f"{self.config.WINDOW_WIDTH}x{self.config.WINDOW_HEIGHT}")
        self.root.configure(bg=self.config.COLOR_BG)

        # Wycentruj okno
        self.center_window()

    def center_window(self):
        """Centruje okno na ekranie"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def show_login_screen(self):
        """Wyświetla ekran logowania"""
        # Ramka główna logowania
        self.login_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        self.login_frame.pack(expand=True, fill=tk.BOTH)

        # Logo/Nagłówek
        header_frame = tk.Frame(
            self.login_frame,
            bg=self.config.COLOR_PRIMARY,
            height=120
        )
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="Reconext Hi-Pot PSU",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 28, "bold")
        )
        title_label.pack(pady=25)

        # Centralna ramka logowania
        center_frame = tk.Frame(self.login_frame, bg=self.config.COLOR_BG)
        center_frame.pack(expand=True)

        # Panel logowania
        login_panel = tk.Frame(
            center_frame,
            bg=self.config.COLOR_WHITE,
            relief=tk.RAISED,
            borderwidth=2
        )
        login_panel.pack(padx=50, pady=50)

        # Tytuł logowania
        login_title = tk.Label(
            login_panel,
            text="Logowanie Operatora",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 20, "bold")
        )
        login_title.pack(pady=(30, 20))

        # Etykieta HRID
        hrid_label = tk.Label(
            login_panel,
            text="Wprowadź HRID:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 12)
        )
        hrid_label.pack(pady=(10, 5))

        # Pole wprowadzania HRID
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

        # Bind Enter do logowania
        self.hrid_entry.bind('<Return>', lambda e: self.attempt_login())

        # Etykieta błędu (ukryta na początku)
        self.error_label = tk.Label(
            login_panel,
            text="",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_ERROR,
            font=("Arial", 10)
        )
        self.error_label.pack()

        # Przycisk logowania
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

        # Hover effect
        login_button.bind('<Enter>', lambda e: login_button.config(bg="#66BB6A"))
        login_button.bind('<Leave>', lambda e: login_button.config(bg=self.config.COLOR_ACCENT))

    def attempt_login(self):
        """Próba logowania użytkownika"""
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
        """Akcja po udanym logowaniu"""
        # Usuń ekran logowania
        self.login_frame.destroy()

        # Pokaż główną aplikację
        self.create_main_app()

    def create_main_app(self):
        """Tworzy główny interfejs aplikacji"""
        # Nagłówek
        self.create_header()

        # Główna zawartość
        main_frame = tk.Frame(self.root, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 60))

        # Panel skanowania numeru seryjnego
        self.create_scan_panel(main_frame)

        # Stopka
        self.create_footer()

        # Binding dla konfiguracji: Ctrl+Alt+D (3x)
        self.d_press_count = 0
        self.d_press_timer = None
        self.root.bind('<Control-Alt-d>', self.on_config_shortcut)
        self.root.bind('<Control-Alt-D>', self.on_config_shortcut)

    def on_config_shortcut(self, event):
        """Obsługa skrótu do konfiguracji (Ctrl+Alt+D 3x)"""
        self.d_press_count += 1

        # Anuluj poprzedni timer
        if self.d_press_timer:
            self.root.after_cancel(self.d_press_timer)

        # Reset licznika po 1 sekundzie
        self.d_press_timer = self.root.after(1000, self.reset_d_counter)

        # Po 3 naciśnięciach otwórz okno hasła
        if self.d_press_count >= 3:
            self.d_press_count = 0
            self.show_password_dialog()

    def reset_d_counter(self):
        """Resetuje licznik naciśnięć D"""
        self.d_press_count = 0

    def show_password_dialog(self):
        """Wyświetla dialog do wprowadzenia hasła"""
        password_window = tk.Toplevel(self.root)
        password_window.title("Dostęp do konfiguracji")
        password_window.geometry("400x200")
        password_window.configure(bg=self.config.COLOR_BG)
        password_window.resizable(False, False)

        # Wycentruj okno
        password_window.transient(self.root)
        password_window.grab_set()

        # Ramka główna
        frame = tk.Frame(password_window, bg=self.config.COLOR_WHITE, relief=tk.RAISED, borderwidth=2)
        frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        # Tytuł
        title_label = tk.Label(
            frame,
            text="Dostęp do konfiguracji",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(20, 10))

        # Etykieta hasła
        password_label = tk.Label(
            frame,
            text="Wprowadź hasło:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        )
        password_label.pack(pady=(10, 5))

        # Pole hasła
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

        # Etykieta błędu
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

        # Bind Enter
        password_entry.bind('<Return>', lambda e: check_password())

        # Przyciski
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

        cancel_button = tk.Button(
            button_frame,
            text="Anuluj",
            bg="#999999",
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=10,
            relief=tk.FLAT,
            cursor="hand2",
            command=password_window.destroy
        )
        cancel_button.pack(side=tk.LEFT, padx=5)

    def show_config_window(self):
        """Wyświetla okno konfiguracji"""
        admin_panel = AdminPanel(self.root, self.config)
        admin_panel.show()

    def create_scan_panel(self, parent):
        """Tworzy panel skanowania numeru seryjnego"""
        # Centralna ramka
        center_frame = tk.Frame(parent, bg=self.config.COLOR_BG)
        center_frame.pack(expand=True)

        # Panel skanowania
        scan_panel = tk.Frame(
            center_frame,
            bg=self.config.COLOR_WHITE,
            relief=tk.RAISED,
            borderwidth=2
        )
        scan_panel.pack(padx=50, pady=50)

        # Tytuł
        title_label = tk.Label(
            scan_panel,
            text="Skanowanie numeru seryjnego",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=(30, 20))

        # Instrukcja
        instruction_label = tk.Label(
            scan_panel,
            text="Zeskanuj lub wprowadź numer seryjny zasilacza:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 12)
        )
        instruction_label.pack(pady=(10, 5))

        # Pole na numer seryjny
        self.serial_entry = tk.Entry(
            scan_panel,
            font=("Arial", 16, "bold"),
            width=30,
            justify='center',
            relief=tk.SOLID,
            borderwidth=2
        )
        self.serial_entry.pack(pady=15, padx=50)
        self.serial_entry.focus()

        # Bind Enter do skanowania
        self.serial_entry.bind('<Return>', lambda e: self.process_serial())

        # Etykieta statusu
        self.scan_status_label = tk.Label(
            scan_panel,
            text="",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 11)
        )
        self.scan_status_label.pack(pady=5)

        # Przycisk potwierdzenia
        confirm_button = tk.Button(
            scan_panel,
            text="POTWIERDŹ",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 14, "bold"),
            width=20,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.process_serial
        )
        confirm_button.pack(pady=(10, 30), padx=50)

        # Hover effect
        confirm_button.bind('<Enter>', lambda e: confirm_button.config(bg="#66BB6A"))
        confirm_button.bind('<Leave>', lambda e: confirm_button.config(bg=self.config.COLOR_ACCENT))

    def process_serial(self):
        """Przetwarza zeskanowany numer seryjny"""
        serial = self.serial_entry.get().strip()

        if not serial:
            self.scan_status_label.config(
                text="Wprowadź numer seryjny!",
                fg=self.config.COLOR_ERROR
            )
            return

        # Identyfikacja modelu
        model_info = PowerSupplyModels.identify_model(serial)

        if model_info:
            self.scan_status_label.config(
                text=f"✓ Rozpoznano: {model_info['name']}",
                fg=self.config.COLOR_ACCENT
            )
            # TODO: Przejście do ekranu testu
            self.root.after(1000, lambda: self.show_test_screen(serial, model_info))
        else:
            self.scan_status_label.config(
                text="✗ Nierozpoznany model zasilacza!",
                fg=self.config.COLOR_ERROR
            )
            self.serial_entry.delete(0, tk.END)
            self.serial_entry.focus()

    def show_test_screen(self, serial, model_info):
        """Wyświetla ekran testu dla danego modelu"""
        # TODO: Implementacja ekranu testowego
        print(f"Test dla: {serial}")
        print(f"Model: {model_info['name']}")
        print(f"Parametry: {model_info['test_params']}")

    def create_header(self):
        """Nagłówek aplikacji"""
        header_frame = tk.Frame(
            self.root,
            bg=self.config.COLOR_PRIMARY,
            height=70
        )
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        # Tytuł
        title_label = tk.Label(
            header_frame,
            text="Reconext Hi-Pot PSU",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 22, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)

        # Zalogowany użytkownik - pogrubiony
        user_label = tk.Label(
            header_frame,
            text=f"Operator: {self.current_user}",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 12, "bold")
        )
        user_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # Przycisk wylogowania
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
        """Stopka aplikacji"""
        footer_frame = tk.Frame(
            self.root,
            bg=self.config.COLOR_PRIMARY,
            height=40
        )
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)

        # Autor w prawym dolnym rogu - pogrubiony
        author_label = tk.Label(
            footer_frame,
            text="Autor: Kacper Urbanowicz",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold")
        )
        author_label.pack(side=tk.RIGHT, padx=20, pady=10)

    def logout(self):
        """Wylogowanie użytkownika"""
        self.current_user = None

        # Usuń wszystkie widgety
        for widget in self.root.winfo_children():
            widget.destroy()

        # Pokaż ekran logowania
        self.show_login_screen()
