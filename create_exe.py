# create_exe.py
import subprocess
import sys
import os

def main():
    try:
        import PyInstaller
    except ImportError:
        print("[!] PyInstaller nie znaleziony. Instaluję...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[+] PyInstaller zainstalowany.\n")

    if not os.path.exists("main.py"):
        print("[!] BRAK PLIKU: main.py")
        input("\nNaciśnij Enter aby wyjść...")
        sys.exit(1)

    data_files = ["models.json", "operators.json", "config.json"]
    extra_data_args = []
    for f in data_files:
        if os.path.exists(f):
            extra_data_args += ["--add-data", f"{os.path.abspath(f)};."]
            print(f"[+] Znaleziono {f} — zostanie spakowany")
        else:
            print(f"[~] Brak {f} — pomijam (zostanie utworzony przy pierwszym uruchomieniu)")

    print("\n" + "=" * 55)
    print("  Hi-Pot PSU - Builder EXE")
    print("=" * 55)
    print("[*] Buduję .exe, poczekaj...\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--clean",
        "--name", "Hi-Pot PSU",

        "--hidden-import=tkinter",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=serial",
        "--hidden-import=serial.tools.list_ports",
        "--hidden-import=serial.tools.list_ports_windows",
        "--hidden-import=threading",
        "--hidden-import=time",
        "--hidden-import=json",
        "--hidden-import=csv",
        "--hidden-import=os",
        "--hidden-import=datetime",
        "--hidden-import=hashlib",
        "--hidden-import=pathlib",

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
        "--hidden-import=stats_manager",
        "--hidden-import=shift_stats",

        "main.py"
    ]

    cmd += extra_data_args

    result = subprocess.run(cmd, capture_output=False, text=True)

    print("\n" + "=" * 55)
    if result.returncode == 0:
        exe_path = os.path.join("dist", "Hi-Pot PSU.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"[+] SUKCES! Plik EXE gotowy:")
            print(f"    {os.path.abspath(exe_path)}")
            print(f"    Rozmiar: {size_mb:.1f} MB")
        else:
            print(f"[+] Build zakończony, szukaj w folderze dist/")
    else:
        print(f"[!] BŁĄD podczas budowania (kod: {result.returncode})")
        print(f"    Sprawdź plik build/Hi-Pot PSU/warn-Hi-Pot PSU.txt")
    print("=" * 55)

    input("\nNaciśnij Enter aby zamknąć...")

if __name__ == "__main__":
    main()