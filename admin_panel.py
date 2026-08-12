# admin_panel.py
"""Panel administratora aplikacji"""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from models import PowerSupplyModels
from settings_manager import SettingsManager


def list_com_ports():
    """Realna lista portów COM; przy braku sterowników — lista zapasowa."""
    try:
        from serial.tools import list_ports
        ports = sorted(p.device for p in list_ports.comports())
        if ports:
            return ports
    except Exception as e:
        print(f"[ADMIN] Nie udało się odczytać listy portów: {e}")
    return [f"COM{i}" for i in range(1, 13)]


class AdminPanel:
    """Klasa panelu administratora"""

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.settings = SettingsManager()
        self.window = None
        self._busy = False
        # Wątki robocze (test RS232 / Arduino) nie mogą dotykać Tk —
        # przekazują zadania przez kolejkę opróżnianą w wątku GUI.
        self._ui_queue = queue.Queue()
        self._pump_id = None

    def show(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Panel Administratora")
        self.window.geometry("850x720")
        self.window.configure(bg=self.config.COLOR_BG)
        self.window.transient(self.parent)
        self.window.grab_set()

        self._create_header()

        main_frame = tk.Frame(self.window, bg=self.config.COLOR_BG)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        self._create_operators_tab()
        self._create_profiles_tab()
        self._create_general_tab()
        self._create_logs_tab()
        self._create_interlock_tab()
        self._create_buttons()

        self.window.protocol("WM_DELETE_WINDOW", self._close)
        self._pump_ui()

    # ------------------------------------------------------------------ #
    #  NAGŁÓWEK                                                            #
    # ------------------------------------------------------------------ #
    def _create_header(self):
        header = tk.Frame(self.window, bg=self.config.COLOR_PRIMARY, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Panel Administratora",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 18, "bold")).pack(pady=15)

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — OPERATORZY                                               #
    # ------------------------------------------------------------------ #
    def _create_operators_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Operatorzy")

        tk.Label(frame, text="Lista autoryzowanych operatorów (HRID)",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(pady=(15, 10))

        content = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        content.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        list_frame = tk.Frame(content, bg=self.config.COLOR_WHITE)
        list_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.operators_listbox = tk.Listbox(
            list_frame, font=("Courier", 11),
            yscrollcommand=scrollbar.set,
            relief=tk.SOLID, borderwidth=1, selectmode=tk.SINGLE)
        self.operators_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.operators_listbox.yview)

        btn_panel = tk.Frame(content, bg=self.config.COLOR_WHITE)
        btn_panel.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)

        for text, color, cmd in [
            ("Dodaj",   self.config.COLOR_ACCENT,  self._add_operator),
            ("Usuń",    self.config.COLOR_ERROR,   self._remove_operator),
            ("Odśwież", self.config.COLOR_PRIMARY, self._reload_operators),
        ]:
            tk.Button(btn_panel, text=text, bg=color,
                      fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                      width=12, height=3, relief=tk.FLAT, cursor="hand2",
                      command=cmd).pack(pady=5)

        self.operators_count_label = tk.Label(
            frame, text="", bg=self.config.COLOR_WHITE,
            fg="#666666", font=("Arial", 10))
        self.operators_count_label.pack(pady=(5, 15))

        self._load_operators()

    def _load_operators(self):
        self.operators_listbox.delete(0, tk.END)
        for hrid in sorted(self.config.AUTHORIZED_USERS):
            self.operators_listbox.insert(tk.END, hrid)
        self._update_operator_count()

    def _reload_operators(self):
        """Odśwież = wczytaj ponownie z pliku (np. po edycji na innym stanowisku)."""
        self.config.AUTHORIZED_USERS = list(
            self.settings.load_operators(self.config.AUTHORIZED_USERS))
        self._load_operators()

    def _update_operator_count(self):
        if hasattr(self, "operators_count_label"):
            self.operators_count_label.config(
                text=f"Liczba operatorów: {len(self.config.AUTHORIZED_USERS)}")

    def _add_operator(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Dodaj operatora")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._center(dialog, 350, 200)

        tk.Label(dialog, text="Wprowadź HRID nowego operatora",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 11, "bold")).pack(pady=(20, 10))

        entry = tk.Entry(dialog, font=("Arial", 12), width=20,
                         justify="center", relief=tk.SOLID, borderwidth=2)
        entry.pack(pady=10)
        entry.focus()

        err = tk.Label(dialog, text="", bg=self.config.COLOR_WHITE,
                       fg=self.config.COLOR_ERROR, font=("Arial", 9))
        err.pack()

        def confirm():
            hrid = entry.get().strip()
            if not hrid:
                err.config(text="HRID nie może być puste!")
                return
            # Porównanie bez wielkości liter — inaczej dało się dodać
            # "test" obok istniejącego "TEST".
            if hrid.upper() in {u.upper() for u in self.config.AUTHORIZED_USERS}:
                err.config(text="Ten operator już istnieje!")
                return
            self.config.AUTHORIZED_USERS.append(hrid)
            if not self.settings.save_operators(self.config.AUTHORIZED_USERS):
                self.config.AUTHORIZED_USERS.remove(hrid)
                err.config(text="Nie udało się zapisać pliku operatorów!")
                return
            self._load_operators()
            dialog.destroy()
            messagebox.showinfo("Sukces", f"Dodano operatora: {hrid}",
                                parent=self.window)

        entry.bind("<Return>", lambda e: confirm())

        bf = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        bf.pack(pady=15)
        tk.Button(bf, text="Dodaj", bg=self.config.COLOR_ACCENT,
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  width=10, relief=tk.FLAT, cursor="hand2",
                  command=confirm).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Anuluj", bg="#999999",
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  width=10, relief=tk.FLAT, cursor="hand2",
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _remove_operator(self):
        sel = self.operators_listbox.curselection()
        if not sel:
            messagebox.showwarning("Brak wyboru", "Wybierz operatora do usunięcia!",
                                   parent=self.window)
            return
        hrid = self.operators_listbox.get(sel[0])
        if len(self.config.AUTHORIZED_USERS) <= 1:
            messagebox.showwarning(
                "Ostatni operator",
                "Nie można usunąć ostatniego operatora — nikt nie zalogowałby "
                "się do aplikacji.", parent=self.window)
            return
        if messagebox.askyesno("Potwierdzenie", f"Usunąć operatora {hrid}?",
                               parent=self.window):
            try:
                self.config.AUTHORIZED_USERS.remove(hrid)
            except ValueError:
                return
            if not self.settings.save_operators(self.config.AUTHORIZED_USERS):
                self.config.AUTHORIZED_USERS.append(hrid)
                messagebox.showerror("Błąd", "Nie udało się zapisać zmian!",
                                     parent=self.window)
                return
            self._load_operators()
            messagebox.showinfo("Sukces", f"Usunięto operatora: {hrid}",
                                parent=self.window)

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — PROFILE TESTOWE                                          #
    # ------------------------------------------------------------------ #
    def _create_profiles_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Profile testowe")

        top = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        top.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 5))

        tk.Label(top, text="Profile testowe modeli zasilaczy",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))

        list_frame = tk.Frame(top, bg=self.config.COLOR_WHITE)
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("model", "tryb", "napięcie", "prąd_low", "prąd_high",
                "ramp", "test", "fall", "sn")
        self.profiles_tree = ttk.Treeview(list_frame, columns=cols,
                                          show="headings", height=12)

        headers = {
            "model":     ("Model",      160),
            "tryb":      ("Tryb",        50),
            "napięcie":  ("Napięcie V",  90),
            "prąd_low":  ("I low mA",    80),
            "prąd_high": ("I high mA",   80),
            "ramp":      ("Ramp s",      70),
            "test":      ("Test s",      70),
            "fall":      ("Fall s",      70),
            "sn":        ("Dł. SN",      70),
        }
        for col, (heading, width) in headers.items():
            self.profiles_tree.heading(col, text=heading)
            self.profiles_tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self.profiles_tree.yview)
        self.profiles_tree.configure(yscrollcommand=vsb.set)
        self.profiles_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._load_profiles_tree()

        btn_frame = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        btn_frame.pack(fill=tk.X, padx=15, pady=5)

        for text, color, cmd in [
            ("Dodaj profil",  self.config.COLOR_ACCENT,  self._add_profile),
            ("Edytuj profil", self.config.COLOR_PRIMARY, self._edit_profile),
            ("Usuń profil",   self.config.COLOR_ERROR,   self._delete_profile),
        ]:
            tk.Button(btn_frame, text=text, bg=color,
                      fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                      relief=tk.FLAT, cursor="hand2", padx=15, pady=6,
                      command=cmd).pack(side=tk.LEFT, padx=5)

        self.profiles_tree.bind("<Double-1>", lambda e: self._edit_profile())

    def _load_profiles_tree(self):
        for row in self.profiles_tree.get_children():
            self.profiles_tree.delete(row)
        for key in sorted(PowerSupplyModels.MODELS.keys()):
            data = PowerSupplyModels.MODELS[key]
            p = data.get("test_params", {})
            sn = data.get("serial_length", "?")
            sn_str = "/".join(str(x) for x in sn) if isinstance(sn, list) else str(sn)
            self.profiles_tree.insert("", tk.END, iid=key, values=(
                key, p.get("mode", "?"), p.get("voltage", "?"),
                p.get("current_limit_low", "?"), p.get("current_limit_high", "?"),
                p.get("ramp_time", "?"), p.get("test_time", "?"),
                p.get("fall_time", "?"), sn_str))

    def _get_selected_model_key(self):
        sel = self.profiles_tree.selection()
        if not sel:
            messagebox.showwarning("Brak wyboru", "Wybierz profil z listy!",
                                   parent=self.window)
            return None
        return sel[0]

    def _add_profile(self):
        self._open_profile_form(mode="add")

    def _edit_profile(self):
        key = self._get_selected_model_key()
        if key:
            self._open_profile_form(mode="edit", model_key=key)

    def _delete_profile(self):
        key = self._get_selected_model_key()
        if not key:
            return
        if len(PowerSupplyModels.MODELS) <= 1:
            messagebox.showwarning("Ostatni profil",
                                   "Nie można usunąć ostatniego profilu.",
                                   parent=self.window)
            return
        if not messagebox.askyesno("Potwierdzenie", f"Usunąć profil {key}?",
                                   parent=self.window):
            return
        # POPRAWKA: usunięty profil fabryczny wracał po restarcie aplikacji.
        if PowerSupplyModels.delete_model(key):
            self._load_profiles_tree()
            messagebox.showinfo("Sukces", f"Usunięto profil: {key}",
                                parent=self.window)
        else:
            PowerSupplyModels.reload()
            self._load_profiles_tree()
            messagebox.showerror("Błąd", "Nie udało się zapisać pliku profili!",
                                 parent=self.window)

    def _open_profile_form(self, mode="add", model_key=None):
        dialog = tk.Toplevel(self.window)
        dialog.title("Dodaj profil" if mode == "add" else f"Edytuj profil: {model_key}")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._center(dialog, 480, 660)

        existing = PowerSupplyModels.MODELS.get(model_key, {}) if mode == "edit" else {}
        p = existing.get("test_params", {})
        sn = existing.get("serial_length", 21)
        sn_default = ",".join(str(x) for x in sn) if isinstance(sn, list) else str(sn)

        tk.Label(dialog, text="Dodaj nowy profil" if mode == "add" else "Edytuj profil",
                 bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                 font=("Arial", 13, "bold")).pack(fill=tk.X, pady=(0, 10), ipady=10)

        form = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        form.pack(fill=tk.BOTH, expand=True, padx=25, pady=5)

        def row(r, label, var, width=20, state="normal"):
            tk.Label(form, text=label, bg=self.config.COLOR_WHITE,
                     fg="#333333", font=("Arial", 10),
                     anchor="w", width=24).grid(row=r, column=0, sticky="w", pady=4)
            e = tk.Entry(form, textvariable=var, font=("Arial", 10),
                         width=width, relief=tk.SOLID, borderwidth=1, state=state)
            e.grid(row=r, column=1, sticky="w", pady=4)
            return e

        v_name    = tk.StringVar(value=model_key if mode == "edit" else "")
        v_desc    = tk.StringVar(value=existing.get("description", ""))
        v_sn      = tk.StringVar(value=sn_default)
        v_mode    = tk.StringVar(value=p.get("mode", "AC"))
        v_voltage = tk.StringVar(value=str(p.get("voltage", 3000)))
        v_vtol    = tk.StringVar(value=str(p.get("voltage_tolerance", 50)))
        v_ihigh   = tk.StringVar(value=str(p.get("current_limit_high", 2.5)))
        v_ilow    = tk.StringVar(value=str(p.get("current_limit_low", 0.0)))
        v_ramp    = tk.StringVar(value=str(p.get("ramp_time", 0.0)))
        v_test    = tk.StringVar(value=str(p.get("test_time", 1.0)))
        v_fall    = tk.StringVar(value=str(p.get("fall_time", 0.0)))
        v_freq    = tk.StringVar(value=str(p.get("frequency", 50)))
        v_arc     = tk.StringVar(value=str(p.get("arc_detection", 0.0)))

        row(0, "Nazwa modelu (klucz):", v_name,
            state="disabled" if mode == "edit" else "normal")
        row(1, "Opis:", v_desc)
        row(2, "Długość SN (np. 21 lub 10,21):", v_sn)

        tk.Label(form, text="Tryb:", bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 10),
                 anchor="w", width=24).grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(form, textvariable=v_mode, values=["AC", "DC"],
                     state="readonly", width=18).grid(row=3, column=1,
                                                      sticky="w", pady=4)

        row(4,  "Napięcie [V]:", v_voltage)
        row(5,  "Tolerancja napięcia [V]:", v_vtol)
        row(6,  "Limit prądu HIGH [mA]:", v_ihigh)
        row(7,  "Limit prądu LOW [mA]:", v_ilow)
        row(8,  "Ramp time [s]:", v_ramp)
        row(9,  "Test time [s]:", v_test)
        row(10, "Fall time [s]:", v_fall)
        row(11, "Częstotliwość [Hz]:", v_freq)
        row(12, "Arc detection [mA]:", v_arc)

        err_label = tk.Label(dialog, text="", bg=self.config.COLOR_WHITE,
                             fg=self.config.COLOR_ERROR, font=("Arial", 9),
                             wraplength=430, justify="center")
        err_label.pack()

        def save():
            name = v_name.get().strip() if mode == "add" else model_key
            if not name:
                err_label.config(text="Nazwa modelu nie może być pusta!")
                return
            if mode == "add" and name in PowerSupplyModels.MODELS:
                err_label.config(text="Model o tej nazwie już istnieje!")
                return

            sn_raw = v_sn.get().strip()
            try:
                if "," in sn_raw:
                    sn_val = [int(x.strip()) for x in sn_raw.split(",") if x.strip()]
                else:
                    sn_val = int(sn_raw)
                lengths = sn_val if isinstance(sn_val, list) else [sn_val]
                if not lengths or any(x <= 0 or x > 64 for x in lengths):
                    raise ValueError
            except ValueError:
                err_label.config(text="Nieprawidłowa długość SN (1–64, np. 21 lub 10,21)!")
                return

            try:
                voltage = float(v_voltage.get())
                vtol    = float(v_vtol.get())
                ihigh   = float(v_ihigh.get())
                ilow    = float(v_ilow.get())
                ramp    = float(v_ramp.get())
                ttime   = float(v_test.get())
                fall    = float(v_fall.get())
                freq    = float(v_freq.get())
                arc     = float(v_arc.get())
            except ValueError:
                err_label.config(text="Nieprawidłowe wartości liczbowe!")
                return

            # POPRAWKA: brak jakiejkolwiek walidacji zakresów pozwalał zapisać
            # profil, który Chroma odrzuca (albo, gorzej, przyjmuje) —
            # np. napięcie 0 V, limit LOW > HIGH, ujemne czasy.
            problems = []
            if not (0 < voltage <= 6000):
                problems.append("napięcie musi być w zakresie 1–6000 V")
            if ihigh <= 0:
                problems.append("limit HIGH musi być większy od 0 mA")
            if ilow < 0:
                problems.append("limit LOW nie może być ujemny")
            if ilow >= ihigh:
                problems.append("limit LOW musi być mniejszy od HIGH")
            if ttime <= 0:
                problems.append("czas testu musi być większy od 0 s")
            if min(ramp, fall) < 0:
                problems.append("czasy ramp/fall nie mogą być ujemne")
            if vtol < 0:
                problems.append("tolerancja napięcia nie może być ujemna")
            if problems:
                err_label.config(text="Popraw: " + "; ".join(problems))
                return

            new_model = {
                "name":          name,
                "identifier":    existing.get("identifier", ""),
                "description":   v_desc.get().strip() or f"Zasilacz {name}",
                "serial_length": sn_val,
                "test_params": {
                    "mode":               v_mode.get(),
                    "voltage":            voltage,
                    "voltage_tolerance":  vtol,
                    "current_limit_high": ihigh,
                    "current_limit_low":  ilow,
                    "ramp_time":          ramp,
                    "test_time":          ttime,
                    "fall_time":          fall,
                    "frequency":          freq,
                    "arc_detection":      arc,
                }
            }

            PowerSupplyModels.MODELS[name] = new_model
            if not PowerSupplyModels.save():
                err_label.config(text="Nie udało się zapisać pliku profili!")
                return
            self._load_profiles_tree()
            dialog.destroy()
            messagebox.showinfo(
                "Sukces",
                f"{'Dodano' if mode == 'add' else 'Zaktualizowano'} profil: {name}",
                parent=self.window)

        bf = tk.Frame(dialog, bg=self.config.COLOR_WHITE)
        bf.pack(pady=10)
        tk.Button(bf, text="Zapisz", bg=self.config.COLOR_ACCENT,
                  fg=self.config.COLOR_WHITE, font=("Arial", 11, "bold"),
                  width=12, height=2, relief=tk.FLAT, cursor="hand2",
                  command=save).pack(side=tk.LEFT, padx=8)
        tk.Button(bf, text="Anuluj", bg="#999999",
                  fg=self.config.COLOR_WHITE, font=("Arial", 11, "bold"),
                  width=12, height=2, relief=tk.FLAT, cursor="hand2",
                  command=dialog.destroy).pack(side=tk.LEFT, padx=8)

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — USTAWIENIA OGÓLNE                                        #
    # ------------------------------------------------------------------ #
    def _create_general_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Ustawienia ogólne")

        content = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        content.pack(expand=True, fill=tk.BOTH, padx=30, pady=20)

        tk.Label(content, text="Ustawienia komunikacji RS232 — Chroma Hi-Pot",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        def setting(r, label, var, values=None, entry_type="combo"):
            tk.Label(content, text=label, bg=self.config.COLOR_WHITE,
                     fg="#333333", font=("Arial", 11)).grid(
                row=r, column=0, sticky="w", pady=8, padx=(20, 10))
            if entry_type == "combo":
                w = ttk.Combobox(content, textvariable=var, values=values,
                                 width=15, font=("Arial", 10))
            else:
                w = tk.Entry(content, textvariable=var, width=17, font=("Arial", 10))
            w.grid(row=r, column=1, sticky="w", pady=8)
            return w

        self.com_port_var  = tk.StringVar(value=self.config.DEFAULT_COM_PORT)
        self.baudrate_var  = tk.StringVar(value=str(self.config.DEFAULT_BAUDRATE))
        self.parity_var    = tk.StringVar(value=self.config.DEFAULT_PARITY)
        self.flow_ctrl_var = tk.StringVar(value=self.config.DEFAULT_FLOW_CONTROL)

        ports = list_com_ports()
        if self.config.DEFAULT_COM_PORT not in ports:
            ports = sorted(set(ports + [self.config.DEFAULT_COM_PORT]))
        setting(1, "Port COM:", self.com_port_var, ports)
        setting(2, "Baud Rate:", self.baudrate_var,
                ["300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "115200"])
        setting(3, "Parity:", self.parity_var, ["NONE", "EVEN", "ODD"])
        setting(4, "Flow Control:", self.flow_ctrl_var, ["NONE", "SOFTWARE"])

        tk.Label(content,
                 text="Uwaga: sterownik Chromy pracuje na 8N1 bez sterowania "
                      "przepływem — pola Parity/Flow Control są zapisywane, ale "
                      "nie zmieniają obecnie transmisji.",
                 bg=self.config.COLOR_WHITE, fg="#999999",
                 font=("Arial", 8, "italic"), wraplength=520, justify="left").grid(
            row=5, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 6))

        tk.Frame(content, bg="#cccccc", height=2).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=14)

        tk.Label(content, text="Inne ustawienia",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(0, 15))

        tk.Label(content, text="Automatyczny zapis wyników:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).grid(row=8, column=0, sticky="w",
                                          pady=8, padx=(20, 10))
        self.auto_save_var = tk.BooleanVar(
            value=getattr(self.config, "AUTO_SAVE_RESULTS", True))
        tk.Checkbutton(content, variable=self.auto_save_var,
                       bg=self.config.COLOR_WHITE,
                       activebackground=self.config.COLOR_WHITE).grid(
            row=8, column=1, sticky="w")

        self.timeout_var = tk.StringVar(
            value=str(getattr(self.config, "TEST_TIMEOUT", 300)))
        setting(9, "Timeout testu [s]:", self.timeout_var, entry_type="entry")

        self.test_rs232_btn = tk.Button(
            content, text="Testuj połączenie RS232",
            bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
            command=self._test_rs232)
        self.test_rs232_btn.grid(row=10, column=0, columnspan=2, pady=20,
                                 sticky="w", padx=20)

        self.connection_status_label = tk.Label(
            content, text="", bg=self.config.COLOR_WHITE, font=("Arial", 10))
        self.connection_status_label.grid(row=11, column=0, columnspan=2,
                                          sticky="w", padx=20)

    def _test_rs232(self):
        """
        POPRAWKA: test łączności wykonywał się w wątku GUI z window.update()
        w środku — okno zamierało na kilka sekund, a wielokrotne kliknięcie
        potrafiło otworzyć port kilka razy.
        """
        if self._busy:
            return
        self._busy = True
        self.test_rs232_btn.config(state="disabled")
        self.connection_status_label.config(text="⏳ Testowanie połączenia...",
                                            fg="#FF9800")

        port = self.com_port_var.get()
        try:
            baud = int(self.baudrate_var.get())
        except ValueError:
            self._rs232_done(False, "Nieprawidłowy baud rate")
            return

        def worker():
            from hipot_device import ChromaHiPotDevice
            device = ChromaHiPotDevice(port=port, baudrate=baud)
            try:
                ok = device.connect()
                info = device.idn if ok else ""
                device.disconnect()
                self._safe_after(lambda: self._rs232_done(ok, info))
            except Exception as e:
                msg = str(e)
                self._safe_after(lambda: self._rs232_done(False, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _rs232_done(self, ok: bool, info: str):
        self._busy = False
        try:
            self.test_rs232_btn.config(state="normal")
        except Exception:
            pass
        if ok:
            self.connection_status_label.config(
                text=f"✓ Połączenie udane: {info[:60]}", fg=self.config.COLOR_ACCENT)
        else:
            self.connection_status_label.config(
                text=f"✗ Błąd połączenia. {info}"[:120], fg=self.config.COLOR_ERROR)

    def _safe_after(self, fn):
        self._ui_queue.put(fn)

    def _pump_ui(self):
        self._pump_id = None
        try:
            if not (self.window and self.window.winfo_exists()):
                return
        except Exception:
            return
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as e:
                print(f"[ADMIN] Błąd callbacku: {e}")
        try:
            self._pump_id = self.window.after(40, self._pump_ui)
        except Exception:
            pass

    def _close(self):
        if self._pump_id is not None:
            try:
                self.window.after_cancel(self._pump_id)
            except Exception:
                pass
            self._pump_id = None
        try:
            self.window.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — ŚCIEŻKA LOGÓW                                            #
    # ------------------------------------------------------------------ #
    def _create_logs_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Ścieżka logów")

        tk.Label(frame, text="Lokalizacja zapisu plików logów",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).pack(pady=(22, 4))

        tk.Label(frame,
                 text="Logi są pobierane przez system IFS i wysyłane dalej przez web service.\n"
                      "Wskaż folder na dysku sieciowym dostępny dla systemu IFS.",
                 bg=self.config.COLOR_WHITE, fg="#666666",
                 font=("Arial", 9, "italic"), justify="center").pack(pady=(0, 18))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill=tk.X, padx=30, pady=(0, 18))

        path_outer = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        path_outer.pack(fill=tk.X, padx=30)

        tk.Label(path_outer, text="Ścieżka zapisu logów:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 10, "bold"), anchor="w").pack(anchor="w", pady=(0, 5))

        entry_row = tk.Frame(path_outer, bg=self.config.COLOR_WHITE)
        entry_row.pack(fill=tk.X)

        self.log_dir_var = tk.StringVar(value=getattr(self.config, "LOG_DIR", "logs"))

        self.log_dir_entry = tk.Entry(entry_row, textvariable=self.log_dir_var,
                                      font=("Courier", 11), relief=tk.SOLID,
                                      borderwidth=1)
        self.log_dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X,
                                ipady=6, padx=(0, 8))

        tk.Button(entry_row, text="Przeglądaj…", bg=self.config.COLOR_PRIMARY,
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2", padx=12, pady=6,
                  command=self._browse_log_dir).pack(side=tk.LEFT)

        actions_row = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        actions_row.pack(pady=(14, 4))

        tk.Button(actions_row, text="Sprawdź dostępność", bg="#FF9800",
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._check_log_dir).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(actions_row, text="💾  Zapisz ścieżkę", bg=self.config.COLOR_ACCENT,
                  fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._save_log_dir).pack(side=tk.LEFT)

        self.log_dir_status = tk.Label(frame, text="", bg=self.config.COLOR_WHITE,
                                       font=("Arial", 10), wraplength=700)
        self.log_dir_status.pack(pady=(8, 0))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill=tk.X, padx=30, pady=(20, 8))

        self.log_dir_current_label = tk.Label(
            frame,
            text=f"Aktualnie aktywna ścieżka:  {getattr(self.config, 'LOG_DIR', 'logs')}",
            bg=self.config.COLOR_WHITE, fg="#999999",
            font=("Arial", 9, "italic"), wraplength=700)
        self.log_dir_current_label.pack(pady=(0, 10))

    def _browse_log_dir(self):
        current = self.log_dir_var.get().strip() or os.path.expanduser("~")
        if not os.path.isdir(current):
            current = os.path.expanduser("~")
        chosen = filedialog.askdirectory(title="Wybierz folder zapisu logów",
                                         initialdir=current, parent=self.window)
        if chosen:
            self.log_dir_var.set(os.path.normpath(chosen))
            self.log_dir_status.config(text="", fg="#333333")

    def _check_log_dir(self):
        path = self.log_dir_var.get().strip()
        if not path:
            self.log_dir_status.config(text="✗ Ścieżka jest pusta!",
                                       fg=self.config.COLOR_ERROR)
            return
        if not os.path.isdir(path):
            self.log_dir_status.config(
                text=f"✗ Folder nie istnieje lub jest niedostępny: {path}",
                fg=self.config.COLOR_ERROR)
            return
        test_file = os.path.join(path, "_hipot_write_test.tmp")
        try:
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            self.log_dir_status.config(text="✓ Ścieżka dostępna i zapisywalna",
                                       fg=self.config.COLOR_ACCENT)
        except Exception as e:
            self.log_dir_status.config(text=f"✗ Brak uprawnień do zapisu: {e}",
                                       fg=self.config.COLOR_ERROR)

    def _save_log_dir(self):
        path = self.log_dir_var.get().strip()
        if not path:
            messagebox.showwarning("Błąd", "Ścieżka nie może być pusta!",
                                   parent=self.window)
            return
        if not os.path.isdir(path):
            if not messagebox.askyesno(
                    "Folder nie istnieje",
                    f"Folder nie istnieje:\n{path}\n\nUtworzyć go teraz?",
                    parent=self.window):
                return
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie można utworzyć folderu:\n{e}",
                                     parent=self.window)
                return

        previous = self.config.LOG_DIR
        self.config.LOG_DIR = path
        if not self.settings.save_config(self.config):
            self.config.LOG_DIR = previous
            messagebox.showerror("Błąd", "Nie udało się zapisać konfiguracji!",
                                 parent=self.window)
            return

        self.log_dir_current_label.config(text=f"Aktualnie aktywna ścieżka:  {path}")
        self.log_dir_status.config(text="✓ Ścieżka zapisana pomyślnie",
                                   fg=self.config.COLOR_ACCENT)
        messagebox.showinfo("Sukces", f"Ścieżka logów zapisana:\n{path}",
                            parent=self.window)

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — INTERLOCK (ARDUINO)                                      #
    # ------------------------------------------------------------------ #
    def _create_interlock_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Interlock (Arduino)")

        tk.Label(frame, text="Konfiguracja Hardware Interlock",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).pack(pady=(22, 4))

        tk.Label(frame,
                 text="Arduino Leonardo monitoruje stan klapy bezpieczeństwa (pin 6 → GND).\n"
                      "Zamknięcie klapy uruchamia test automatycznie.",
                 bg=self.config.COLOR_WHITE, fg="#666666",
                 font=("Arial", 9, "italic"), justify="center").pack(pady=(0, 18))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill=tk.X, padx=30, pady=(0, 20))

        content = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        content.pack(fill=tk.X, padx=40)

        def field(r, label, var, values=None, entry_type="combo"):
            tk.Label(content, text=label, bg=self.config.COLOR_WHITE,
                     fg="#333333", font=("Arial", 11),
                     anchor="w", width=26).grid(row=r, column=0, sticky="w", pady=10)
            if entry_type == "combo":
                w = ttk.Combobox(content, textvariable=var, values=values,
                                 width=15, font=("Arial", 10))
            else:
                w = tk.Entry(content, textvariable=var, width=17,
                             font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
            w.grid(row=r, column=1, sticky="w", pady=10)
            return w

        self.interlock_port_var = tk.StringVar(
            value=getattr(self.config, "INTERLOCK_PORT", "COM7"))
        self.interlock_baud_var = tk.StringVar(
            value=str(getattr(self.config, "INTERLOCK_BAUDRATE", 9600)))
        self.interlock_enabled_var = tk.BooleanVar(
            value=getattr(self.config, "INTERLOCK_ENABLED", True))

        ports = list_com_ports()
        if self.interlock_port_var.get() not in ports:
            ports = sorted(set(ports + [self.interlock_port_var.get()]))
        field(0, "Port COM (Arduino):", self.interlock_port_var, ports)
        field(1, "Baud Rate:", self.interlock_baud_var,
              ["4800", "9600", "19200", "38400", "115200"])

        tk.Label(content, text="Interlock aktywny:", bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 11), anchor="w", width=26).grid(
            row=2, column=0, sticky="w", pady=10)
        tk.Checkbutton(content, variable=self.interlock_enabled_var,
                       bg=self.config.COLOR_WHITE,
                       activebackground=self.config.COLOR_WHITE,
                       font=("Arial", 10)).grid(row=2, column=1, sticky="w", pady=10)

        tk.Label(content,
                 text="UWAGA: odznaczenie wyłącza sprzętową blokadę klapy — test "
                      "będzie można uruchomić przyciskiem START niezależnie od "
                      "położenia osłony. Używać wyłącznie na czas serwisu.",
                 bg=self.config.COLOR_WHITE, fg="#c62828",
                 font=("Arial", 8, "bold"), wraplength=520, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))

        tk.Frame(content, bg="#e0e0e0", height=1).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=15)

        btn_row = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        btn_row.pack(pady=(0, 10))

        self.test_interlock_btn = tk.Button(
            btn_row, text="🔌  Testuj połączenie z Arduino",
            bg="#FF9800", fg=self.config.COLOR_WHITE,
            font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
            padx=14, pady=6, command=self._test_interlock)
        self.test_interlock_btn.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(btn_row, text="💾  Zapisz ustawienia",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6, command=self._save_interlock).pack(side=tk.LEFT)

        self.interlock_status_label = tk.Label(
            frame, text="", bg=self.config.COLOR_WHITE, font=("Arial", 10),
            wraplength=700)
        self.interlock_status_label.pack(pady=(6, 0))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill=tk.X, padx=30, pady=(20, 8))

        self.interlock_current_label = tk.Label(
            frame, text=self._interlock_current_text(),
            bg=self.config.COLOR_WHITE, fg="#999999", font=("Arial", 9, "italic"))
        self.interlock_current_label.pack(pady=(0, 10))

    def _interlock_current_text(self) -> str:
        port    = getattr(self.config, "INTERLOCK_PORT", "COM7")
        baud    = getattr(self.config, "INTERLOCK_BAUDRATE", 9600)
        enabled = getattr(self.config, "INTERLOCK_ENABLED", True)
        status  = "aktywny" if enabled else "WYŁĄCZONY"
        return f"Aktualna konfiguracja:  {port}  @{baud} baud  —  {status}"

    def _test_interlock(self):
        if self._busy:
            return
        port = self.interlock_port_var.get()
        try:
            baud = int(self.interlock_baud_var.get())
        except ValueError:
            self.interlock_status_label.config(text="✗ Nieprawidłowy baud rate",
                                               fg=self.config.COLOR_ERROR)
            return

        self._busy = True
        self.test_interlock_btn.config(state="disabled")
        self.interlock_status_label.config(text=f"⏳ Łączenie z Arduino na {port}...",
                                           fg="#FF9800")

        def worker():
            line, error = "", ""
            try:
                import time as _time
                import serial
                with serial.Serial(port, baud, timeout=2) as s:
                    _time.sleep(1.5)
                    s.reset_input_buffer()
                    deadline = _time.time() + 3.0
                    while _time.time() < deadline:
                        if s.in_waiting > 0:
                            line = s.readline().decode("ascii", errors="ignore").strip()
                            if line:
                                break
                        _time.sleep(0.05)
            except Exception as e:
                error = str(e)
            self._safe_after(lambda: self._interlock_done(line, error))

        threading.Thread(target=worker, daemon=True).start()

    def _interlock_done(self, line: str, error: str):
        self._busy = False
        try:
            self.test_interlock_btn.config(state="normal")
        except Exception:
            pass
        if error:
            self.interlock_status_label.config(text=f"✗ Błąd: {error}",
                                               fg=self.config.COLOR_ERROR)
        elif line in ("OPEN", "CLOSED"):
            stan = "🔒 ZAMKNIĘTA" if line == "CLOSED" else "🔓 OTWARTA"
            self.interlock_status_label.config(
                text=f"✓ Arduino odpowiada — klapa: {stan}",
                fg=self.config.COLOR_ACCENT)
        elif line:
            self.interlock_status_label.config(
                text=f"⚠ Arduino odpowiada, nieznany format: '{line}'", fg="#FF9800")
        else:
            self.interlock_status_label.config(
                text="⚠ Port otwarty, ale brak danych — sprawdź baudrate lub szkic",
                fg="#FF9800")

    def _save_interlock(self):
        try:
            baud = int(self.interlock_baud_var.get())
        except ValueError:
            messagebox.showerror("Błąd", "Baud rate musi być liczbą!",
                                 parent=self.window)
            return

        enabled = bool(self.interlock_enabled_var.get())
        if not enabled and not messagebox.askyesno(
                "Wyłączenie interlocka",
                "Wyłączasz sprzętową blokadę klapy bezpieczeństwa.\n"
                "Test będzie można uruchomić przy otwartej osłonie.\n\n"
                "Czy na pewno kontynuować?", parent=self.window, icon="warning"):
            self.interlock_enabled_var.set(True)
            return

        self.config.INTERLOCK_PORT     = self.interlock_port_var.get()
        self.config.INTERLOCK_BAUDRATE = baud
        self.config.INTERLOCK_ENABLED  = enabled
        if not self.settings.save_config(self.config):
            messagebox.showerror("Błąd", "Nie udało się zapisać konfiguracji!",
                                 parent=self.window)
            return

        self.interlock_current_label.config(text=self._interlock_current_text())
        self.interlock_status_label.config(text="✓ Ustawienia interlocka zapisane",
                                           fg=self.config.COLOR_ACCENT)
        messagebox.showinfo("Zapisano",
                            f"Interlock zapisany:\n"
                            f"Port: {self.config.INTERLOCK_PORT}\n"
                            f"Baud: {self.config.INTERLOCK_BAUDRATE}\n"
                            f"Aktywny: {self.config.INTERLOCK_ENABLED}",
                            parent=self.window)

    # ------------------------------------------------------------------ #
    #  PRZYCISKI DOLNE                                                     #
    # ------------------------------------------------------------------ #
    def _create_buttons(self):
        bf = tk.Frame(self.window, bg=self.config.COLOR_BG)
        bf.pack(fill=tk.X, padx=20, pady=(0, 20))

        tk.Button(bf, text="Zapisz zmiany", bg=self.config.COLOR_ACCENT,
                  fg=self.config.COLOR_WHITE, font=("Arial", 11, "bold"),
                  width=15, relief=tk.FLAT, cursor="hand2",
                  command=self._save_changes).pack(side=tk.LEFT, padx=5)

        tk.Button(bf, text="Zamknij", bg="#999999",
                  fg=self.config.COLOR_WHITE, font=("Arial", 11, "bold"),
                  width=15, relief=tk.FLAT, cursor="hand2",
                  command=self._close).pack(side=tk.RIGHT, padx=5)

    def _save_changes(self):
        # POPRAWKA: walidacja PRZED przypisaniem. Poprzednio błędny timeout
        # zostawiał config w stanie częściowo zmienionym (port i baudrate już
        # nadpisane, reszta nie) i nic nie było zapisane na dysk.
        port = self.com_port_var.get().strip()
        if not port:
            messagebox.showerror("Błąd", "Port COM nie może być pusty!",
                                 parent=self.window)
            return
        try:
            baudrate = int(self.baudrate_var.get())
            timeout  = int(self.timeout_var.get())
        except ValueError:
            messagebox.showerror("Błąd", "Baud rate i timeout muszą być liczbami!",
                                 parent=self.window)
            return
        if baudrate <= 0 or not (5 <= timeout <= 3600):
            messagebox.showerror("Błąd",
                                 "Baud rate musi być dodatni, timeout w zakresie "
                                 "5–3600 s.", parent=self.window)
            return

        self.config.DEFAULT_COM_PORT     = port
        self.config.DEFAULT_BAUDRATE     = baudrate
        self.config.DEFAULT_PARITY       = self.parity_var.get()
        self.config.DEFAULT_FLOW_CONTROL = self.flow_ctrl_var.get()
        self.config.AUTO_SAVE_RESULTS    = bool(self.auto_save_var.get())
        self.config.TEST_TIMEOUT         = timeout

        if self.settings.save_config(self.config):
            messagebox.showinfo("Zapisano", "Konfiguracja została zapisana!",
                                parent=self.window)
        else:
            messagebox.showerror("Błąd", "Nie udało się zapisać konfiguracji!",
                                 parent=self.window)

    # ------------------------------------------------------------------ #
    #  HELPER                                                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _center(win, w, h):
        win.update_idletasks()
        x = max(0, win.winfo_screenwidth() // 2 - w // 2)
        y = max(0, win.winfo_screenheight() // 2 - h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
