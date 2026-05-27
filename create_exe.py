# create_exe.py
import subprocess
import sys
import os

def main():
    # Sprawdź czy PyInstaller jest zainstalowany
    try:
        import PyInstaller
    except ImportError:
        print("[!] PyInstaller nie znaleziony. Instaluję...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[+] PyInstaller zainstalowany.\n")

    # Sprawdź czy main.py istnieje
    if not os.path.exists("main.py"):
        print("[!] BRAK PLIKU: main.py")
        input("\nNaciśnij Enter aby wyjść...")
        sys.exit(1)

    # Pliki danych do spakowania (JSON-y)
    data_files = ["models.json", "operators.json", "config.json"]
    extra_data_args = []
    for f in data_files:
        if os.path.exists(f):
            extra_data_args += ["--add-data", f"{os.path.abspath(f)};."]
            print(f"[+] Znaleziono {f} — zostanie spakowany")
        else:
            print(f"[~] Brak {f} — pomijam")

    print("\n" + "=" * 55)
    print("  Hi-Pot PSU - Builder EXE")
    print("=" * 55)
    print("[*] Buduję .exe, poczekaj...\n")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "Hi-Pot PSU",

        # Moduły standardowe
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=serial",
        "--hidden-import=serial.tools.list_ports",
        "--hidden-import=threading",
        "--hidden-import=time",
        "--hidden-import=json",
        "--hidden-import=csv",
        "--hidden-import=os",
        "--hidden-import=datetime",
        "--hidden-import=hashlib",

        # Moduły lokalne apki
        "--hidden-import=config",
        "--hidden-import=models",
        "--hidden-import=gui",
        "--hidden-import=test_screen",
        "--hidden-import=admin_panel",
        "--hidden-import=hipot_device",
        "--hidden-import=interlock",
        "--hidden-import=arduino",
        "--hidden-import=logger",
        "--hidden-import=settings_manager",

        "main.py"
    ]

    # Dodaj JSON-y
    cmd += extra_data_args

    result = subprocess.run(cmd, capture_output=False, text=True)

    print("\n" + "=" * 55)
    if result.returncode == 0:
        exe_path = os.path.join("dist", "Hi-Pot PSU.exe")
        print(f"[+] SUKCES! Plik EXE gotowy:")
        print(f"    {os.path.abspath(exe_path)}")
    else:
        print(f"[!] BŁĄD podczas budowania (kod: {result.returncode})")
    print("=" * 55)

    input("\nNaciśnij Enter aby zamknąć...")

if __name__ == "__main__":
    main()