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

        info_label = tk.Label(
            general_frame,
            text="Tutaj będą ustawienia ogólne aplikacji",
            bg=self.config.COLOR_WHITE,
            fg="#666666",
            font=("Arial", 11)
        )
        info_label.pack(pady=50)

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
        # TODO: Implementacja zapisu do pliku
        messagebox.showinfo("Zapisano", "Konfiguracja została zapisana!")
