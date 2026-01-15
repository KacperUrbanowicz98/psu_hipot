# main.py
"""
ReconEXT Hi-Pot Tester
Główny plik aplikacji
"""
import tkinter as tk
from gui import HiPotTesterApp

def main():
    root = tk.Tk()
    app = HiPotTesterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
