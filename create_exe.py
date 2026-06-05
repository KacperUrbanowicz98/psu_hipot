# create_exe.py
import subprocess
import sys
import os

def create_version_file():
    """Tworzy plik z metadanymi EXE — poprawia reputację w antywirusach."""
    content = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Reconext'),
        StringStruct('FileDescription', 'Hi-Pot PSU Tester'),
        StringStruct('FileVersion', '1.0.0.0'),
        StringStruct('InternalName', 'Hi-Pot PSU'),
        StringStruct('LegalCopyright', 'Reconext 2026'),
        StringStruct('OriginalFilename', 'Hi-Pot PSU.exe'),
        StringStruct('ProductName', 'Reconext Hi-Pot PSU'),
        StringStruct('ProductVersion', '1.0.0.0'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Utworzono version_info.txt")

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

    create_version_file()

    print("\n" + "=" * 55)
    print("  Hi-Pot PSU - Builder EXE")
    print("=" * 55)
    print("[*] Buduję .exe (tryb onedir), poczekaj...\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",        # ← zmienione z --onefile (nie rozpakowuje do %TEMP%)
        "--windowed",
        "--clean",
        "--name", "Hi-Pot PSU",
        "--version-file", "version_info.txt",  # ← metadane EXE

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
        # onedir → folder zamiast pojedynczego EXE
        exe_path = os.path.join("dist", "Hi-Pot PSU", "Hi-Pot PSU.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            folder_path = os.path.join("dist", "Hi-Pot PSU")
            print(f"[+] SUKCES! Folder z aplikacją gotowy:")
            print(f"    {os.path.abspath(folder_path)}")
            print(f"    Uruchamiaj: {os.path.abspath(exe_path)}")
            print(f"    Rozmiar EXE: {size_mb:.1f} MB")
            print(f"\n[!] WAŻNE: kopiuj cały folder 'Hi-Pot PSU', nie sam .exe!")
        else:
            print(f"[+] Build zakończony, szukaj w folderze dist/Hi-Pot PSU/")
    else:
        print(f"[!] BŁĄD podczas budowania (kod: {result.returncode})")
        print(f"    Sprawdź plik build/Hi-Pot PSU/warn-Hi-Pot PSU.txt")
    print("=" * 55)

    input("\nNaciśnij Enter aby zamknąć...")

if __name__ == "__main__":
    main()