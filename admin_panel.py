# admin_panel.py
"""Panel administratora aplikacji"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from models import PowerSupplyModels
from settings_manager import SettingsManager


class AdminPanel:
    """Klasa panelu administratora"""

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.settings = SettingsManager()
        self.window = None

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
        self._create_interlock_tab()     # ← NOWE
        self._create_buttons()

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
            relief=tk.SOLID, borderwidth=1,
            selectmode=tk.SINGLE)
        self.operators_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.operators_listbox.yview)

        self._load_operators()

        btn_panel = tk.Frame(content, bg=self.config.COLOR_WHITE)
        btn_panel.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)

        for text, color, cmd in [
            ("Dodaj",   self.config.COLOR_ACCENT,  self._add_operator),
            ("Usuń",    self.config.COLOR_ERROR,   self._remove_operator),
            ("Odśwież", self.config.COLOR_PRIMARY, self._load_operators),
        ]:
            tk.Button(btn_panel, text=text, bg=color,
                      fg=self.config.COLOR_WHITE, font=("Arial", 10, "bold"),
                      width=12, height=3, relief=tk.FLAT, cursor="hand2",
                      command=cmd).pack(pady=5)

        self.operators_count_label = tk.Label(
            frame, text="", bg=self.config.COLOR_WHITE,
            fg="#666666", font=("Arial", 10))
        self.operators_count_label.pack(pady=(5, 15))
        self._update_operator_count()

    def _load_operators(self):
        self.operators_listbox.delete(0, tk.END)
        for hrid in sorted(self.config.AUTHORIZED_USERS):
            self.operators_listbox.insert(tk.END, hrid)
        self._update_operator_count()

    def _update_operator_count(self):
        if hasattr(self, "operators_count_label"):
            self.operators_count_label.config(
                text=f"Liczba operatorów: {len(self.config.AUTHORIZED_USERS)}")

    def _add_operator(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Dodaj operatora")
        dialog.geometry("350x200")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.window)
        dialog.grab_set()
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
            if hrid in self.config.AUTHORIZED_USERS:
                err.config(text="Ten operator już istnieje!")
                return
            self.config.AUTHORIZED_USERS.append(hrid)
            self.settings.save_operators(self.config.AUTHORIZED_USERS)
            self._load_operators()
            dialog.destroy()
            messagebox.showinfo("Sukces", f"Dodano operatora: {hrid}")

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
            messagebox.showwarning("Brak wyboru", "Wybierz operatora do usunięcia!")
            return
        hrid = self.operators_listbox.get(sel[0])
        if messagebox.askyesno("Potwierdzenie", f"Usunąć operatora {hrid}?"):
            self.config.AUTHORIZED_USERS.remove(hrid)
            self.settings.save_operators(self.config.AUTHORIZED_USERS)
            self._load_operators()
            messagebox.showinfo("Sukces", f"Usunięto operatora: {hrid}")

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

    def _load_profiles_tree(self):
        for row in self.profiles_tree.get_children():
            self.profiles_tree.delete(row)
        for key, data in PowerSupplyModels.MODELS.items():
            p = data["test_params"]
            sn = data["serial_length"]
            sn_str = "/".join(str(x) for x in sn) if isinstance(sn, list) else str(sn)
            self.profiles_tree.insert("", tk.END, iid=key, values=(
                key, p["mode"], p["voltage"],
                p["current_limit_low"], p["current_limit_high"],
                p["ramp_time"], p["test_time"], p["fall_time"], sn_str
            ))

    def _get_selected_model_key(self):
        sel = self.profiles_tree.selection()
        if not sel:
            messagebox.showwarning("Brak wyboru", "Wybierz profil z listy!")
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
        if messagebox.askyesno("Potwierdzenie", f"Usunąć profil {key}?"):
            del PowerSupplyModels.MODELS[key]
            self.settings.save_models(PowerSupplyModels.MODELS)
            self._load_profiles_tree()
            messagebox.showinfo("Sukces", f"Usunięto profil: {key}")

    def _open_profile_form(self, mode="add", model_key=None):
        dialog = tk.Toplevel(self.window)
        dialog.title("Dodaj profil" if mode == "add" else f"Edytuj profil: {model_key}")
        dialog.geometry("480x640")
        dialog.configure(bg=self.config.COLOR_WHITE)
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._center(dialog, 480, 640)

        existing = PowerSupplyModels.MODELS.get(model_key, {}) if mode == "edit" else {}
        p = existing.get("test_params", {})
        sn = existing.get("serial_length", 21)
        sn_default = ",".join(str(x) for x in sn) if isinstance(sn, list) else str(sn)

        tk.Label(dialog,
                 text="Dodaj nowy profil" if mode == "add" else "Edytuj profil",
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

        row(0,  "Nazwa modelu (klucz):", v_name,
            state="disabled" if mode == "edit" else "normal")
        row(1,  "Opis:", v_desc)
        row(2,  "Długość SN (np. 21 lub 10,21):", v_sn)

        tk.Label(form, text="Tryb:", bg=self.config.COLOR_WHITE,
                 fg="#333333", font=("Arial", 10),
                 anchor="w", width=24).grid(row=3, column=0, sticky="w", pady=4)
        mode_combo = ttk.Combobox(form, textvariable=v_mode,
                                  values=["AC", "DC"], state="readonly", width=18)
        mode_combo.grid(row=3, column=1, sticky="w", pady=4)

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
                             fg=self.config.COLOR_ERROR, font=("Arial", 9))
        err_label.pack()

        def save():
            name = v_name.get().strip()
            if not name:
                err_label.config(text="Nazwa modelu nie może być pusta!")
                return
            if mode == "add" and name in PowerSupplyModels.MODELS:
                err_label.config(text="Model o tej nazwie już istnieje!")
                return

            sn_raw = v_sn.get().strip()
            try:
                if "," in sn_raw:
                    sn_val = [int(x.strip()) for x in sn_raw.split(",")]
                else:
                    sn_val = int(sn_raw)
            except ValueError:
                err_label.config(text="Nieprawidłowa długość SN!")
                return

            try:
                new_model = {
                    "name":          name,
                    "identifier":    "",
                    "description":   v_desc.get().strip() or f"Zasilacz {name}",
                    "serial_length": sn_val,
                    "test_params": {
                        "mode":               v_mode.get(),
                        "voltage":            float(v_voltage.get()),
                        "voltage_tolerance":  float(v_vtol.get()),
                        "current_limit_high": float(v_ihigh.get()),
                        "current_limit_low":  float(v_ilow.get()),
                        "ramp_time":          float(v_ramp.get()),
                        "test_time":          float(v_test.get()),
                        "fall_time":          float(v_fall.get()),
                        "frequency":          float(v_freq.get()),
                        "arc_detection":      float(v_arc.get()),
                    }
                }
            except ValueError:
                err_label.config(text="Nieprawidłowe wartości liczbowe!")
                return

            PowerSupplyModels.MODELS[name] = new_model
            self.settings.save_models(PowerSupplyModels.MODELS)
            self._load_profiles_tree()
            dialog.destroy()
            messagebox.showinfo(
                "Sukces",
                f"{'Dodano' if mode == 'add' else 'Zaktualizowano'} profil: {name}")

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
                w = ttk.Combobox(content, textvariable=var,
                                 values=values, state="readonly",
                                 width=15, font=("Arial", 10))
            else:
                w = tk.Entry(content, textvariable=var, width=17,
                             font=("Arial", 10))
            w.grid(row=r, column=1, sticky="w", pady=8)
            return w

        self.com_port_var  = tk.StringVar(value=self.config.DEFAULT_COM_PORT)
        self.baudrate_var  = tk.StringVar(value=str(self.config.DEFAULT_BAUDRATE))
        self.parity_var    = tk.StringVar(value=self.config.DEFAULT_PARITY)
        self.flow_ctrl_var = tk.StringVar(value=self.config.DEFAULT_FLOW_CONTROL)

        setting(1, "Port COM:", self.com_port_var,
                ["COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8"])
        setting(2, "Baud Rate:", self.baudrate_var,
                ["300","600","1200","2400","4800","9600","19200"])
        setting(3, "Parity:", self.parity_var, ["NONE","EVEN","ODD"])
        setting(4, "Flow Control:", self.flow_ctrl_var, ["NONE","SOFTWARE"])

        tk.Frame(content, bg="#cccccc", height=2).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=20)

        tk.Label(content, text="Inne ustawienia",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 15))

        tk.Label(content, text="Automatyczny zapis wyników:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11)).grid(row=7, column=0, sticky="w",
                                          pady=8, padx=(20, 10))
        self.auto_save_var = tk.BooleanVar(value=getattr(
            self.config, "AUTO_SAVE_RESULTS", True))
        tk.Checkbutton(content, variable=self.auto_save_var,
                       bg=self.config.COLOR_WHITE,
                       activebackground=self.config.COLOR_WHITE).grid(
            row=7, column=1, sticky="w")

        self.timeout_var = tk.StringVar(value=str(getattr(
            self.config, "TEST_TIMEOUT", 300)))
        setting(8, "Timeout testu [s]:", self.timeout_var, entry_type="entry")

        tk.Button(content, text="Testuj połączenie RS232",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  command=self._test_rs232).grid(
            row=9, column=0, columnspan=2, pady=20,
            sticky="w", padx=20)

        self.connection_status_label = tk.Label(
            content, text="", bg=self.config.COLOR_WHITE, font=("Arial", 10))
        self.connection_status_label.grid(row=10, column=0, columnspan=2,
                                          sticky="w", padx=20)

    def _test_rs232(self):
        from hipot_device import ChromaHiPotDevice
        self.connection_status_label.config(
            text="Testowanie połączenia...", fg="#FF9800")
        self.window.update()
        try:
            device = ChromaHiPotDevice(
                port=self.com_port_var.get(),
                baudrate=int(self.baudrate_var.get()))
            if device.connect():
                self.connection_status_label.config(
                    text="✓ Połączenie udane!", fg=self.config.COLOR_ACCENT)
                device.disconnect()
                messagebox.showinfo("Sukces", "Połączono z urządzeniem Hi-Pot pomyślnie!")
            else:
                self.connection_status_label.config(
                    text="✗ Błąd połączenia!", fg=self.config.COLOR_ERROR)
                messagebox.showerror("Błąd", "Nie udało się połączyć z Hi-Pot.")
        except Exception as e:
            self.connection_status_label.config(
                text=f"✗ Błąd: {e}", fg=self.config.COLOR_ERROR)
            messagebox.showerror("Błąd", str(e))

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — ŚCIEŻKA LOGÓW                                           #
    # ------------------------------------------------------------------ #
    def _create_logs_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Ścieżka logów")

        tk.Label(frame,
                 text="Lokalizacja zapisu plików logów",
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

        self.log_dir_entry = tk.Entry(
            entry_row, textvariable=self.log_dir_var,
            font=("Courier", 11), relief=tk.SOLID, borderwidth=1)
        self.log_dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=6, padx=(0, 8))

        tk.Button(entry_row, text="Przeglądaj…",
                  bg=self.config.COLOR_PRIMARY, fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  padx=12, pady=6,
                  command=self._browse_log_dir).pack(side=tk.LEFT)

        actions_row = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        actions_row.pack(pady=(14, 4))

        tk.Button(actions_row, text="Sprawdź dostępność",
                  bg="#FF9800", fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6,
                  command=self._check_log_dir).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(actions_row, text="💾  Zapisz ścieżkę",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6,
                  command=self._save_log_dir).pack(side=tk.LEFT)

        self.log_dir_status = tk.Label(
            frame, text="", bg=self.config.COLOR_WHITE, font=("Arial", 10))
        self.log_dir_status.pack(pady=(8, 0))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill=tk.X, padx=30, pady=(20, 8))

        self.log_dir_current_label = tk.Label(
            frame,
            text=f"Aktualnie aktywna ścieżka:  {getattr(self.config, 'LOG_DIR', 'logs')}",
            bg=self.config.COLOR_WHITE, fg="#999999",
            font=("Arial", 9, "italic"))
        self.log_dir_current_label.pack(pady=(0, 10))

    def _browse_log_dir(self):
        current = self.log_dir_var.get().strip() or "C:\\"
        chosen = filedialog.askdirectory(
            title="Wybierz folder zapisu logów",
            initialdir=current,
            parent=self.window)
        if chosen:
            self.log_dir_var.set(chosen.replace("/", "\\"))
            self.log_dir_status.config(text="", fg="#333333")

    def _check_log_dir(self):
        path = self.log_dir_var.get().strip()
        if not path:
            self.log_dir_status.config(
                text="✗ Ścieżka jest pusta!", fg=self.config.COLOR_ERROR)
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
            self.log_dir_status.config(
                text="✓ Ścieżka dostępna i zapisywalna",
                fg=self.config.COLOR_ACCENT)
        except Exception as e:
            self.log_dir_status.config(
                text=f"✗ Brak uprawnień do zapisu: {e}",
                fg=self.config.COLOR_ERROR)

    def _save_log_dir(self):
        path = self.log_dir_var.get().strip()
        if not path:
            messagebox.showwarning("Błąd", "Ścieżka nie może być pusta!", parent=self.window)
            return
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie można utworzyć folderu:\n{e}",
                                     parent=self.window)
                return
        self.config.LOG_DIR = path
        self.settings.save_config(self.config)
        self.log_dir_current_label.config(
            text=f"Aktualnie aktywna ścieżka:  {path}")
        self.log_dir_status.config(
            text="✓ Ścieżka zapisana pomyślnie", fg=self.config.COLOR_ACCENT)
        messagebox.showinfo("Sukces", f"Ścieżka logów zapisana:\n{path}",
                            parent=self.window)

    # ------------------------------------------------------------------ #
    #  ZAKŁADKA — INTERLOCK (ARDUINO)                                      #
    # ------------------------------------------------------------------ #
    def _create_interlock_tab(self):
        frame = tk.Frame(self.notebook, bg=self.config.COLOR_WHITE)
        self.notebook.add(frame, text="Interlock (Arduino)")

        # --- Nagłówek ---
        tk.Label(frame,
                 text="Konfiguracja Hardware Interlock",
                 bg=self.config.COLOR_WHITE, fg=self.config.COLOR_PRIMARY,
                 font=("Arial", 13, "bold")).pack(pady=(22, 4))

        tk.Label(frame,
                 text="Arduino Leonardo monitoruje stan klapy bezpieczeństwa (pin 6 → GND).\n"
                      "Zamknięcie klapy uruchamia test automatycznie.",
                 bg=self.config.COLOR_WHITE, fg="#666666",
                 font=("Arial", 9, "italic"), justify="center").pack(pady=(0, 18))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill=tk.X, padx=30, pady=(0, 20))

        # --- Formularz ustawień ---
        content = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        content.pack(fill=tk.X, padx=40)

        def field(r, label, var, values=None, entry_type="combo"):
            tk.Label(content, text=label, bg=self.config.COLOR_WHITE,
                     fg="#333333", font=("Arial", 11),
                     anchor="w", width=26).grid(row=r, column=0, sticky="w", pady=10)
            if entry_type == "combo":
                w = ttk.Combobox(content, textvariable=var,
                                 values=values, state="readonly",
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

        field(0, "Port COM (Arduino):", self.interlock_port_var,
              ["COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8",
               "COM9","COM10","COM11","COM12"])
        field(1, "Baud Rate:", self.interlock_baud_var,
              ["4800","9600","19200","38400","115200"])

        # Checkbox włącz/wyłącz interlock
        tk.Label(content, text="Interlock aktywny:",
                 bg=self.config.COLOR_WHITE, fg="#333333",
                 font=("Arial", 11), anchor="w", width=26).grid(
            row=2, column=0, sticky="w", pady=10)
        tk.Checkbutton(content, variable=self.interlock_enabled_var,
                       bg=self.config.COLOR_WHITE,
                       activebackground=self.config.COLOR_WHITE,
                       font=("Arial", 10)).grid(row=2, column=1, sticky="w", pady=10)

        tk.Label(content,
                 text="(odznacz aby używać przycisku START ręcznie bez Arduino)",
                 bg=self.config.COLOR_WHITE, fg="#999999",
                 font=("Arial", 8, "italic")).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=(0, 0), pady=(0, 10))

        tk.Frame(content, bg="#e0e0e0", height=1).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=15)

        # --- Przyciski akcji ---
        btn_row = tk.Frame(frame, bg=self.config.COLOR_WHITE)
        btn_row.pack(pady=(0, 10))

        tk.Button(btn_row, text="🔌  Testuj połączenie z Arduino",
                  bg="#FF9800", fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6,
                  command=self._test_interlock).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(btn_row, text="💾  Zapisz ustawienia",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6,
                  command=self._save_interlock).pack(side=tk.LEFT)

        # --- Status ---
        self.interlock_status_label = tk.Label(
            frame, text="", bg=self.config.COLOR_WHITE, font=("Arial", 10))
        self.interlock_status_label.pack(pady=(6, 0))

        tk.Frame(frame, bg="#e0e0e0", height=1).pack(
            fill=tk.X, padx=30, pady=(20, 8))

        # --- Info o aktualnej konfiguracji ---
        self.interlock_current_label = tk.Label(
            frame,
            text=self._interlock_current_text(),
            bg=self.config.COLOR_WHITE, fg="#999999",
            font=("Arial", 9, "italic"))
        self.interlock_current_label.pack(pady=(0, 10))

    def _interlock_current_text(self) -> str:
        port    = getattr(self.config, "INTERLOCK_PORT",    "COM7")
        baud    = getattr(self.config, "INTERLOCK_BAUDRATE", 9600)
        enabled = getattr(self.config, "INTERLOCK_ENABLED",  True)
        status  = "aktywny" if enabled else "wyłączony"
        return f"Aktualna konfiguracja:  {port}  @{baud} baud  —  {status}"

    def _test_interlock(self):
        port = self.interlock_port_var.get()
        baud = int(self.interlock_baud_var.get())
        self.interlock_status_label.config(
            text=f"⏳ Łączenie z Arduino na {port}...", fg="#FF9800")
        self.window.update()
        try:
            import serial
            import time
            with serial.Serial(port, baud, timeout=2) as s:
                time.sleep(1.5)
                s.reset_input_buffer()
                # Czekaj na pierwszą linię przez 2 sekundy
                deadline = time.time() + 2.0
                line = ""
                while time.time() < deadline:
                    if s.in_waiting > 0:
                        line = s.readline().decode("ascii", errors="ignore").strip()
                        break
                    time.sleep(0.05)

            if line in ("OPEN", "CLOSED"):
                stan = "🔒 ZAMKNIĘTA" if line == "CLOSED" else "🔓 OTWARTA"
                self.interlock_status_label.config(
                    text=f"✓ Arduino odpowiada — klapa: {stan}",
                    fg=self.config.COLOR_ACCENT)
            elif line:
                self.interlock_status_label.config(
                    text=f"⚠ Arduino odpowiada, nieznany format: '{line}'",
                    fg="#FF9800")
            else:
                self.interlock_status_label.config(
                    text="⚠ Arduino podłączone, ale brak danych — sprawdź baudrate lub szkic",
                    fg="#FF9800")
        except Exception as e:
            self.interlock_status_label.config(
                text=f"✗ Błąd: {e}", fg=self.config.COLOR_ERROR)

    def _save_interlock(self):
        self.config.INTERLOCK_PORT    = self.interlock_port_var.get()
        self.config.INTERLOCK_BAUDRATE = int(self.interlock_baud_var.get())
        self.config.INTERLOCK_ENABLED  = self.interlock_enabled_var.get()
        self.settings.save_config(self.config)
        self.interlock_current_label.config(text=self._interlock_current_text())
        self.interlock_status_label.config(
            text="✓ Ustawienia interlocka zapisane", fg=self.config.COLOR_ACCENT)
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

        tk.Button(bf, text="Zapisz zmiany",
                  bg=self.config.COLOR_ACCENT, fg=self.config.COLOR_WHITE,
                  font=("Arial", 11, "bold"), width=15,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._save_changes).pack(side=tk.LEFT, padx=5)

        tk.Button(bf, text="Zamknij",
                  bg="#999999", fg=self.config.COLOR_WHITE,
                  font=("Arial", 11, "bold"), width=15,
                  relief=tk.FLAT, cursor="hand2",
                  command=self.window.destroy).pack(side=tk.RIGHT, padx=5)

    def _save_changes(self):
        try:
            self.config.DEFAULT_COM_PORT     = self.com_port_var.get()
            self.config.DEFAULT_BAUDRATE     = int(self.baudrate_var.get())
            self.config.DEFAULT_PARITY       = self.parity_var.get()
            self.config.DEFAULT_FLOW_CONTROL = self.flow_ctrl_var.get()
            self.config.AUTO_SAVE_RESULTS    = self.auto_save_var.get()
            self.config.TEST_TIMEOUT         = int(self.timeout_var.get())
            self.settings.save_config(self.config)
            messagebox.showinfo("Zapisano", "Konfiguracja została zapisana!")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać: {e}")

    # ------------------------------------------------------------------ #
    #  HELPER                                                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _center(win, w, h):
        win.update_idletasks()
        x = win.winfo_screenwidth()  // 2 - w // 2
        y = win.winfo_screenheight() // 2 - h // 2
        win.geometry(f"{w}x{h}+{x}+{y}")