# admin_panel.py
"""
Panel administratora aplikacji
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config import Config


class AdminPanel:
    """Klasa panelu administratora"""

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.window = None

    def show(self):
        """Wyświetla okno panelu administratora"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Panel Administratora")
        self.window.geometry("700x600")
        self.window.configure(bg=self.config.COLOR_BG)

        # Wycentruj okno
        self.window.transient(self.parent)

        # Nagłówek
        self.create_header()

        # Główna ramka
        main_frame = tk.Frame(self.window, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        # Zakładki konfiguracji
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        # Zakładka 1: Operatorzy
        self.create_operators_tab()

        # Zakładka 2: Modele zasilaczy
        self.create_models_tab()

        # Zakładka 3: Parametry testów
        self.create_test_params_tab()

        # Zakładka 4: Ustawienia ogólne
        self.create_general_tab()

        # Przyciski na dole
        self.create_buttons()

    def create_header(self):
        """Tworzy nagłówek panelu"""
        header = tk.Frame(self.window, bg=self.config.COLOR_PRIMARY, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        header_label = tk.Label(
            header,
            text="Panel Administratora",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 18, "bold")
        )
        header_label.pack(pady=15)

    def create_operators_tab(self):
        """Zakładka zarządzania operatorami"""
        operators_frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(operators_frame, text="Operatorzy")

        # Nagłówek zakładki
        title_label = tk.Label(
            operators_frame,
            text="Lista autoryzowanych operatorów (HRID)",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(15, 10))

        # Ramka z listą i przyciskami
        content_frame = tk.Frame(operators_frame, bg=self.config.COLOR_WHITE)
        content_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        # Lista operatorów z scrollbarem
        list_frame = tk.Frame(content_frame, bg=self.config.COLOR_WHITE)
        list_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.operators_listbox = tk.Listbox(
            list_frame,
            font=("Courier", 11),
            yscrollcommand=scrollbar.set,
            relief=tk.SOLID,
            borderwidth=1,
            selectmode=tk.SINGLE
        )
        self.operators_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.operators_listbox.yview)

        # Załaduj listę operatorów
        self.load_operators()

        # Panel przycisków akcji
        button_panel = tk.Frame(content_frame, bg=self.config.COLOR_WHITE)
        button_panel.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)

        add_button = tk.Button(
            button_panel,
            text="Dodaj\noperatora",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=12,
            height=3,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.add_operator
        )
        add_button.pack(pady=5)

        remove_button = tk.Button(
            button_panel,
            text="Usuń\noperatora",
            bg=self.config.COLOR_ERROR,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=12,
            height=3,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.remove_operator
        )
        remove_button.pack(pady=5)

        refresh_button = tk.Button(
            button_panel,
            text="Odśwież\nlistę",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=12,
            height=3,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.load_operators
        )
        refresh_button.pack(pady=5)

        # Informacja o liczbie operatorów
        self.operators_count_label = tk.Label(
            operators_frame,
            text=f"Liczba operatorów: {len(self.config.AUTHORIZED_USERS)}",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 10)
        )
        self.operators_count_label.pack(pady=(5, 15))

    def load_operators(self):
        """Ładuje listę operatorów do listboxa"""
        self.operators_listbox.delete(0, tk.END)
        for hrid in sorted(self.config.AUTHORIZED_USERS):
            self.operators_listbox.insert(tk.END, hrid)

        # Aktualizuj licznik
        if hasattr(self, 'operators_count_label'):
            self.operators_count_label.config(
                text=f"Liczba operatorów: {len(self.config.AUTHORIZED_USERS)}"
            )

    def add_operator(self):
        """Dodaje nowego operatora"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Dodaj operatora")
        dialog.geometry("350x180")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.window)
        dialog.grab_set()

        # Wycentruj dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        tk.Label(
            dialog,
            text="Wprowadź HRID nowego operatora:",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 11, "bold")
        ).pack(pady=(20, 10))

        hrid_entry = tk.Entry(
            dialog,
            font=("Arial", 12),
            width=20,
            justify='center',
            relief=tk.SOLID,
            borderwidth=2
        )
        hrid_entry.pack(pady=10)
        hrid_entry.focus()

        error_label = tk.Label(
            dialog,
            text="",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_ERROR,
            font=("Arial", 9)
        )
        error_label.pack()

        def confirm_add():
            hrid = hrid_entry.get().strip()
            if not hrid:
                error_label.config(text="HRID nie może być puste!")
                return
            if hrid in self.config.AUTHORIZED_USERS:
                error_label.config(text="Ten operator już istnieje!")
                return

            self.config.AUTHORIZED_USERS.append(hrid)
            self.load_operators()
            dialog.destroy()
            messagebox.showinfo("Sukces", f"Dodano operatora: {hrid}")

        hrid_entry.bind('<Return>', lambda e: confirm_add())

        button_frame = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        button_frame.pack(pady=15)

        tk.Button(
            button_frame,
            text="Dodaj",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=10,
            relief=tk.FLAT,
            cursor="hand2",
            command=confirm_add
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Anuluj",
            bg="#999999",
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            width=10,
            relief=tk.FLAT,
            cursor="hand2",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)

    def remove_operator(self):
        """Usuwa wybranego operatora"""
        selection = self.operators_listbox.curselection()
        if not selection:
            messagebox.showwarning("Brak wyboru", "Wybierz operatora do usunięcia!")
            return

        hrid = self.operators_listbox.get(selection[0])

        confirm = messagebox.askyesno(
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć operatora:\n{hrid}?"
        )

        if confirm:
            self.config.AUTHORIZED_USERS.remove(hrid)
            self.load_operators()
            messagebox.showinfo("Sukces", f"Usunięto operatora: {hrid}")

    def create_models_tab(self):
        """Zakładka zarządzania modelami zasilaczy"""
        models_frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(models_frame, text="Modele zasilaczy")

        info_label = tk.Label(
            models_frame,
            text="Tutaj będzie zarządzanie modelami zasilaczy",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 11)
        )
        info_label.pack(pady=50)

    def create_test_params_tab(self):
        """Zakładka parametrów testów"""
        test_params_frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(test_params_frame, text="Parametry testów")

        info_label = tk.Label(
            test_params_frame,
            text="Tutaj będzie edycja parametrów testów dla każdego modelu",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 11)
        )
        info_label.pack(pady=50)

    def create_general_tab(self):
        """Zakładka ustawień ogólnych"""
        general_frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(general_frame, text="Ustawienia ogólne")

        # Główna ramka z paddingiem
        main_content = tk.Frame(general_frame, bg=self.config.COLOR_WHITE)
        main_content.pack(expand=True, fill=tk.BOTH, padx=30, pady=20)

        # ========== SEKCJA RS232 ==========
        rs232_label = tk.Label(
            main_content,
            text="Ustawienia komunikacji RS232 (Chroma Hi-Pot)",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 13, "bold")
        )
        rs232_label.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 15))

        # Port COM
        tk.Label(
            main_content,
            text="Port COM:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=1, column=0, sticky='w', pady=8, padx=(20, 10))

        self.com_port_var = tk.StringVar(value=self.config.DEFAULT_COM_PORT)
        com_port_combo = ttk.Combobox(
            main_content,
            textvariable=self.com_port_var,
            values=["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"],
            state="readonly",
            width=15,
            font=("Arial", 10)
        )
        com_port_combo.grid(row=1, column=1, sticky='w', pady=8)

        # Baud Rate
        tk.Label(
            main_content,
            text="Baud Rate:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=2, column=0, sticky='w', pady=8, padx=(20, 10))

        self.baudrate_var = tk.StringVar(value=str(self.config.DEFAULT_BAUDRATE))
        baudrate_combo = ttk.Combobox(
            main_content,
            textvariable=self.baudrate_var,
            values=["300", "600", "1200", "2400", "4800", "9600", "19200"],
            state="readonly",
            width=15,
            font=("Arial", 10)
        )
        baudrate_combo.grid(row=2, column=1, sticky='w', pady=8)

        # Parity
        tk.Label(
            main_content,
            text="Parity:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=3, column=0, sticky='w', pady=8, padx=(20, 10))

        self.parity_var = tk.StringVar(value=self.config.DEFAULT_PARITY)
        parity_combo = ttk.Combobox(
            main_content,
            textvariable=self.parity_var,
            values=["NONE", "EVEN", "ODD"],
            state="readonly",
            width=15,
            font=("Arial", 10)
        )
        parity_combo.grid(row=3, column=1, sticky='w', pady=8)

        # Flow Control
        tk.Label(
            main_content,
            text="Flow Control:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=4, column=0, sticky='w', pady=8, padx=(20, 10))

        self.flow_control_var = tk.StringVar(value=self.config.DEFAULT_FLOW_CONTROL)
        flow_combo = ttk.Combobox(
            main_content,
            textvariable=self.flow_control_var,
            values=["NONE", "SOFTWARE"],
            state="readonly",
            width=15,
            font=("Arial", 10)
        )
        flow_combo.grid(row=4, column=1, sticky='w', pady=8)

        # Separator
        separator = tk.Frame(main_content, bg="#cccccc", height=2)
        separator.grid(row=5, column=0, columnspan=2, sticky='ew', pady=20)

        # ========== SEKCJA INNE USTAWIENIA ==========
        other_label = tk.Label(
            main_content,
            text="Inne ustawienia",
            bg=self.config.COLOR_WHITE,
            fg=self.config.COLOR_PRIMARY,
            font=("Arial", 13, "bold")
        )
        other_label.grid(row=6, column=0, columnspan=2, sticky='w', pady=(0, 15))

        # Automatyczny zapis wyników
        tk.Label(
            main_content,
            text="Automatyczny zapis wyników:",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=7, column=0, sticky='w', pady=8, padx=(20, 10))

        self.auto_save_var = tk.BooleanVar(value=True)
        auto_save_check = tk.Checkbutton(
            main_content,
            variable=self.auto_save_var,
            bg=self.config.COLOR_WHITE,
            activebackground=self.config.COLOR_WHITE
        )
        auto_save_check.grid(row=7, column=1, sticky='w', pady=8)

        # Timeout testu (sekundy)
        tk.Label(
            main_content,
            text="Timeout testu (s):",
            bg=self.config.COLOR_WHITE,
            fg="#333333",
            font=("Arial", 11)
        ).grid(row=8, column=0, sticky='w', pady=8, padx=(20, 10))

        self.timeout_var = tk.StringVar(value="300")
        timeout_entry = tk.Entry(
            main_content,
            textvariable=self.timeout_var,
            width=17,
            font=("Arial", 10)
        )
        timeout_entry.grid(row=8, column=1, sticky='w', pady=8)

        # Przycisk testowy połączenia
        test_connection_btn = tk.Button(
            main_content,
            text="Testuj połączenie RS232",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self.test_rs232_connection
        )
        test_connection_btn.grid(row=9, column=0, columnspan=2, pady=25, sticky='w', padx=20)

        # Status połączenia
        self.connection_status_label = tk.Label(
            main_content,
            text="",
            bg=self.config.COLOR_WHITE,
            font=("Arial", 10)
        )
        self.connection_status_label.grid(row=10, column=0, columnspan=2, sticky='w', padx=20)

    def test_rs232_connection(self):
        """Testuje połączenie z urządzeniem Hi-Pot przez RS232"""
        from hipot_device import ChromaHiPotDevice

        self.connection_status_label.config(
            text="Testowanie połączenia...",
            fg="#FF9800"
        )
        self.window.update()

        try:
            # Stwórz urządzenie z ustawieniami z panelu
            device = ChromaHiPotDevice(
                port=self.com_port_var.get(),
                baudrate=int(self.baudrate_var.get())
            )

            # Próba połączenia
            if device.connect():
                self.connection_status_label.config(
                    text="✓ Połączenie udane!",
                    fg=self.config.COLOR_ACCENT
                )
                device.disconnect()
                messagebox.showinfo("Sukces", "Połączenie z urządzeniem Hi-Pot zostało nawiązane pomyślnie!")
            else:
                self.connection_status_label.config(
                    text="✗ Błąd połączenia!",
                    fg=self.config.COLOR_ERROR
                )
                messagebox.showerror("Błąd",
                                     "Nie udało się połączyć z urządzeniem Hi-Pot.\nSprawdź ustawienia i połączenie.")

        except Exception as e:
            self.connection_status_label.config(
                text=f"✗ Błąd: {str(e)}",
                fg=self.config.COLOR_ERROR
            )
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas testowania połączenia:\n{str(e)}")

    def create_buttons(self):
        """Tworzy przyciski akcji na dole okna"""
        button_frame = tk.Frame(self.window, bg=self.config.COLOR_BG)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        save_button = tk.Button(
            button_frame,
            text="Zapisz zmiany",
            bg=self.config.COLOR_ACCENT,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 11, "bold"),
            width=15,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.save_changes
        )
        save_button.pack(side=tk.LEFT, padx=5)

        close_button = tk.Button(
            button_frame,
            text="Zamknij",
            bg="#999999",
            fg=self.config.COLOR_WHITE,
            font=("Arial", 11, "bold"),
            width=15,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.window.destroy
        )
        close_button.pack(side=tk.RIGHT, padx=5)

    def save_changes(self):
        """Zapisuje zmiany konfiguracji"""
        try:
            # Zapisz ustawienia RS232
            self.config.DEFAULT_COM_PORT = self.com_port_var.get()
            self.config.DEFAULT_BAUDRATE = int(self.baudrate_var.get())
            self.config.DEFAULT_PARITY = self.parity_var.get()
            self.config.DEFAULT_FLOW_CONTROL = self.flow_control_var.get()

            # TODO: Zapis do pliku konfiguracyjnego
            # Na razie tylko w pamięci, później dodamy zapis do JSON

            messagebox.showinfo("Zapisano", "Konfiguracja została zapisana!")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać konfiguracji:\n{str(e)}")
