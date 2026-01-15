# gui.py
"""
Interfejs graficzny aplikacji
"""
import tkinter as tk
from tkinter import ttk
from config import Config


class HiPotTesterApp:
    def __init__(self, root):
        self.root = root
        self.config = Config()

        self.setup_window()
        self.create_widgets()

    def setup_window(self):
        """Konfiguracja głównego okna"""
        self.root.title(self.config.WINDOW_TITLE)
        self.root.geometry(f"{self.config.WINDOW_WIDTH}x{self.config.WINDOW_HEIGHT}")
        self.root.configure(bg=self.config.COLOR_BG)

    def create_widgets(self):
        """Tworzenie widgetów"""
        # Nagłówek
        self.create_header()

    def create_header(self):
        """Nagłówek aplikacji"""
        header_frame = tk.Frame(
            self.root,
            bg=self.config.COLOR_PRIMARY,
            height=80
        )
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="ReconEXT Hi-Pot Tester",
            bg=self.config.COLOR_PRIMARY,
            fg=self.config.COLOR_WHITE,
            font=("Arial", 24, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
